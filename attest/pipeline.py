"""Déroulé d'une mission d'audit Attest.

Phase 1 — Constat (lecture seule, en parallèle) : test scripté + preuve capturée, relue, annotée, scellée.
Phase 2 — Remédiation (option --remediate) : demandes de changement rédigées par l'IA, APPROUVÉES par le
          propriétaire du système (jamais par l'auditeur), appliquées avec un compte de changement distinct
          et journalisées par le système (DORA 9(4)(e)).
Phase 3 — Contre-vérification : le même script est rejoué, une nouvelle preuve est scellée.
Puis : rapport HTML + PDF, manifeste, piste d'audit chaînée.
"""
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

from . import catalog, config, evidence, llm, prompts, report, sam, sandbox, targets
from .i18n import t
from .trail import Trail, sha256_file

WORKERS = int(os.getenv("ATTEST_WORKERS", "6"))
FIX_ROUTE = ("PATCH", "/api/security")
FIX_KEYS = {"mfa_admin": bool, "mfa_users": bool, "password_min_length": int,
            "password_require_complexity": bool, "lockout_threshold": int,
            "session_timeout_minutes": int, "admin_audit_log": bool}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def shown(c: dict) -> dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


class Ctx:
    def __init__(self, mission, out: Path, trail: Trail, fresh: bool):
        self.mission, self.out, self.trail, self.fresh = mission, out, trail, fresh
        self.target = targets.get(mission.target)
        self.doc = targets.api_doc(mission.target)            # interface en lecture seule de la cible

    def rel(self, p: Path) -> str:
        return str(p.relative_to(self.out))


# ---------- tests ----------

def _safe_run(code: str, ctx) -> dict:
    try:
        return sandbox.run(code, ctx.mission.lab_url, config.AUDIT_TOKEN)
    except sandbox.UnsafeCode as e:
        return {"status": "error", "detail": f"refusé par le garde-fou : {e}"}
    except Exception as e:
        return {"status": "error", "detail": f"{type(e).__name__}: {e}"}


def _write_test(control: dict, error: str | None, doc: str) -> str:
    prev = f"\nYOUR PREVIOUS VERSION FAILED WITH:\n{error}\nFix it." if error else ""
    txt = llm.ask("code", prompts.CODE_SYSTEM,
                  prompts.CODE_USER.format(control=json.dumps(shown(control), ensure_ascii=False),
                                           api_doc=doc, previous_error=prev),
                  code=True, mock_ctx={"control": control})
    return llm.extract_code(txt)


def run_test(e: dict, ctx: Ctx):
    c = e["control"]
    code = None if ctx.fresh else catalog.library_get(c, ctx.doc)
    origin, res = "library", None
    if code:
        res = _safe_run(code, ctx)
        if res["status"] == "error":
            log(f"  {c['id']} script de bibliothèque en échec, réécriture : {res['detail'][:100]}")
            code = None
    if code is None:
        origin, error = "generated", None
        for _ in range(2):                                  # une auto-correction autorisée
            try:
                code = _write_test(c, error, ctx.doc)
            except llm.BudgetExceeded:
                raise                                       # plafond de dépense : l'audit s'arrête
            except Exception as ex:                         # panne du modèle : contrôle non concluant
                code = f"# {t('log.nocode')} : {type(ex).__name__}: {str(ex)[:200]}\n"
                res = {"status": "error", "detail": f"{t('log.model_error')} : {type(ex).__name__}: {str(ex)[:240]}"}
                log(f"  {c['id']} {res['detail']}")
                break
            res = _safe_run(code, ctx)
            if res["status"] != "error":
                catalog.library_put(c, code, ctx.doc)
                break
            error = res["detail"]
    path = ctx.out / "scripts" / f"{c['id']}_{catalog._safe(c['rule'])}.py"
    path.write_text(code)
    sha = sha256_file(path)
    e["test"] = {"script": ctx.rel(path), "sha256": sha, "origin": origin, "code": code}
    e["before"] = res
    ctx.trail.log("test_executed", control=c["id"], rule=c["rule"], origin=origin,
                  file=ctx.rel(path), sha256=sha, result=res)


# ---------- preuves ----------

def inspect(control: dict, result: dict, shot: Path, dom: dict) -> dict:
    w, h = Image.open(shot).size
    txt = llm.ask("inspect", prompts.INSPECT_SYSTEM.format(w=w, h=h),
                  prompts.INSPECT_USER.format(control=json.dumps(shown(control), ensure_ascii=False),
                                              result=json.dumps(result, ensure_ascii=False),
                                              lang=config.lang_name()),
                  image=shot, mock_ctx={"control": control, "result": result, "dom": dom})
    try:
        insp = llm.extract_json(txt)
    except ValueError:                                  # une seconde chance : JSON seul, rien d'autre
        txt = llm.ask("inspect", prompts.INSPECT_SYSTEM.format(w=w, h=h),
                      prompts.INSPECT_USER.format(control=json.dumps(shown(control), ensure_ascii=False),
                                                  result=json.dumps(result, ensure_ascii=False),
                                                  lang=config.lang_name())
                      + "\n\nYour previous answer was not valid JSON. Return ONLY the JSON object.",
                      image=shot, mock_ctx={"control": control, "result": result, "dom": dom})
        insp = llm.extract_json(txt)
    if not isinstance(insp, dict):
        raise ValueError("réponse de vérification visuelle inattendue")
    insp["pii"] = [p for p in insp.get("pii") or [] if isinstance(p, dict)]
    return insp


def snap(mask: np.ndarray, box, pad: int = 10):
    """Resserre une boîte sur ce que SAM a réellement segmenté à l'intérieur (± pad).
    Sur une capture d'écran, SAM découpe les glyphes et non la ligne : on garde l'enveloppe de son
    masque, limitée à la zone proposée par Muse Spark (les pixels parasites hors zone sont ignorés)."""
    H, W = mask.shape
    x1, y1, x2, y2 = [int(v) for v in box]
    X1, Y1, X2, Y2 = max(0, x1 - pad), max(0, y1 - pad), min(W, x2 + pad), min(H, y2 + pad)
    ys, xs = np.nonzero(mask[Y1:Y2, X1:X2])
    if len(xs) < 20:
        return (max(0, x1), max(0, y1), min(W, x2), min(H, y2))
    return (X1 + int(xs.min()), Y1 + int(ys.min()), X1 + int(xs.max()) + 1, Y1 + int(ys.max()) + 1)


def as_box(v):
    """Boîte [x1, y1, x2, y2] lue avec tolérance : liste, objet {x1..}/{left..}/{x, y, w, h}, texte, décimaux."""
    if isinstance(v, dict):
        for ks in (("x1", "y1", "x2", "y2"), ("left", "top", "right", "bottom"), ("x", "y", "w", "h")):
            if all(k in v for k in ks):
                vals = [v[k] for k in ks]
                if ks[2] == "w":
                    try:
                        vals = [float(vals[0]), float(vals[1]), float(vals[0]) + float(vals[2]),
                                float(vals[1]) + float(vals[3])]
                    except (TypeError, ValueError):
                        return None
                v = vals
                break
        else:
            return None
    if isinstance(v, str):
        v = re.findall(r"-?\d+(?:\.\d+)?", v)
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        x1, y1, x2, y2 = (int(round(float(a))) for a in v)
    except (TypeError, ValueError):
        return None
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    return (x1, y1, x2, y2) if x2 - x1 >= 2 and y2 - y1 >= 2 else None


def field_boxes(insp: dict) -> list:
    boxes = insp.get("field_boxes") or ([insp["field_box"]] if insp.get("field_box") else [])
    boxes = boxes if isinstance(boxes, list) else [boxes]
    return [b for b in (as_box(x) for x in boxes) if b]


def to_rows(box, rows: list):
    """Page de code : la zone est alignée sur les lignes entières qu'elle recouvre (None si aucune)."""
    x1, y1, x2, y2 = box
    hit = [r for r in rows if min(y2, r[3]) - max(y1, r[1]) >= 0.4 * (r[3] - r[1])]
    if not hit:
        return None
    return (min(r[0] for r in hit), min(r[1] for r in hit), max(r[2] for r in hit), max(r[3] for r in hit))


def annotate(shot: Path, insp: dict, status: str, out: Path, net_boxes=(), rows=()) -> dict:
    """Masque les données personnelles puis encadre les lignes probantes (SAM affine les deux).

    Masquage en deux couches : (1) ce que Muse Spark a repéré, affiné par SAM ; (2) un filet
    déterministe — les données personnelles reconnues dans le texte de la page (net_boxes).
    La confidentialité ne dépend donc jamais de la seule précision d'un modèle."""
    img = Image.open(shot).convert("RGB")
    W, H = img.size
    fboxes = field_boxes(insp)
    pboxes = [b for b in (as_box(p.get("box")) for p in insp.get("pii", [])) if b]
    masks = sam.segment_boxes(shot, fboxes + pboxes)
    fmasks, pmasks = masks[:len(fboxes)], masks[len(fboxes):]

    # couche 1 : boîte du modèle ∪ masque SAM dilaté (en rédaction, mieux vaut trop que pas assez)
    pii_model = np.zeros((H, W), dtype=bool)
    if pmasks:                                      # une seule dilatation pour l'union des masques SAM
        union = np.logical_or.reduce(pmasks)
        pii_model |= np.asarray(Image.fromarray(union.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(11))) > 127
    for x1, y1, x2, y2 in pboxes:
        pii_model[max(0, y1 - 3):y2 + 3, max(0, x1 - 3):x2 + 3] = True
    # couche 2 : filet déterministe
    pii = pii_model.copy()
    for x1, y1, x2, y2 in net_boxes:
        pii[max(0, y1 - 4):y2 + 4, max(0, x1 - 4):x2 + 4] = True
    if pii.any():
        pii_img = Image.fromarray(pii.astype(np.uint8) * 255)
        pixel = img.resize((max(1, W // 12), max(1, H // 12)), Image.BILINEAR).resize((W, H), Image.NEAREST)
        img = Image.composite(pixel.filter(ImageFilter.GaussianBlur(4)), img, pii_img)

    rgb = {"fail": (192, 38, 28), "pass": (22, 128, 60)}.get(status, (161, 92, 0))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for b, m in zip(fboxes, fmasks):
        if rows:                                   # page de code : lignes entières, rien hors du code
            box = to_rows(b, rows)
            if box is None:
                continue
            x1, y1, x2, y2 = box
            draw.rounded_rectangle((x1 - 2, y1, x2 + 2, y2), radius=4, fill=rgb + (55,),
                                   outline=rgb + (255,), width=3)
            continue
        x1, y1, x2, y2 = snap(m, b)
        draw.rounded_rectangle((x1 - 6, y1 - 5, x2 + 6, y2 + 5), radius=6, fill=rgb + (55,),
                               outline=rgb + (255,), width=3)
    Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB").save(out)
    return {"pii": pii, "pii_model": pii_model}


def measure(masks: dict, dom: dict) -> dict:
    """Couverture mesurée sur les données personnelles présentes dans la page (jamais montrées au modèle) :
    ce que Muse Spark + SAM ont repéré seuls, et ce qui est masqué au final."""
    def covered(mask, box):
        x1, y1, x2, y2 = box
        zone = mask[max(0, y1):y2, max(0, x1):x2]
        return zone.size > 0 and float(zone.mean()) >= 0.8
    items = dom.get("pii", [])
    return {"pii_total": len(items),
            "pii_masked": sum(covered(masks["pii"], p["box"]) for p in items),
            "pii_found_by_model": sum(covered(masks["pii_model"], p["box"]) for p in items)}


def evidence_page(control: dict, result: dict) -> str:
    """La page qui prouve le résultat : celle désignée par le test (ex. le fichier fautif d'un dépôt),
    sinon celle prévue au programme de travail. Toujours un chemin local de la passerelle."""
    page = str(result.get("evidence_page") or "")
    if page.startswith("/") and "://" not in page and ".." not in page:
        return page
    return control["evidence_page"]


def collect_evidence(e: dict, result: dict, phase: str, ctx: Ctx) -> dict:
    c = e["control"]
    raw = ctx.out / "evidence" / f"{c['id']}_{phase}_raw.png"
    page = evidence_page(c, result)
    dom = evidence.capture(ctx.mission.lab_url + page, raw, config.AUDIT_TOKEN)
    insp = inspect(c, result, raw, dom)
    final = ctx.out / "evidence" / f"{c['id']}_{phase}.png"
    masks = annotate(raw, insp, result["status"], final,
                     net_boxes=[tuple(p["box"]) for p in dom.get("pii", [])],
                     rows=[tuple(r) for r in dom.get("lines", {}).values()])
    raw.unlink()                                   # la capture non masquée n'est pas conservée
    sha = sha256_file(final)
    metrics = measure(masks, dom)
    ctx.trail.log("evidence_sealed", control=c["id"], phase=phase, file=ctx.rel(final), sha256=sha,
                  page=page, corroborates=insp.get("corroborates"),
                  injection_detected=bool(insp.get("injection_detected")), **metrics)
    return {"image": ctx.rel(final), "sha256": sha, "inspection": insp, "metrics": metrics, "page": page,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}


def classify(result: dict, ev: dict | None) -> str:
    if result.get("status") == "error":
        return "error"
    if ev and ev["inspection"].get("corroborates") is False:
        return "review"                            # test et preuve en désaccord : un humain tranche
    return result["status"]


def observe(e: dict, ctx: Ctx, refresh):
    c = e["control"]
    run_test(e, ctx)
    refresh()
    ev = None
    if e["before"]["status"] != "error":
        try:
            ev = collect_evidence(e, e["before"], "before", ctx)
        except Exception as ex:
            e["evidence_error"] = f"{type(ex).__name__} : {str(ex)[:240]}"
            ctx.trail.log("evidence_failed", control=c["id"], phase="before", error=e["evidence_error"])
            log(f"  {c['id']} preuve impossible : {e['evidence_error']}")
    e["evidence_before"] = ev
    e["status_before"] = classify(e["before"], ev)
    log(f"{t('log.test')} {c['id']} {c['rule']} · {c['title']} → {t('st.' + e['status_before'])}"
        + (f" · {t('log.evidence')}" if ev else ""))
    refresh()


# ---------- remédiation ----------

def propose_fix(e: dict, ctx: Ctx) -> dict:
    c = e["control"]
    try:
        prop = llm.extract_json(llm.ask(
            "fix", prompts.FIX_SYSTEM,
            prompts.FIX_USER.format(control=json.dumps(shown(c), ensure_ascii=False),
                                    result=json.dumps(e["before"], ensure_ascii=False),
                                    api_doc=ctx.doc, lang=config.lang_name()),
            mock_ctx={"control": c, "kind": ctx.target["kind"]}))
        if not isinstance(prop, dict):
            raise ValueError("réponse de remédiation inattendue")
    except llm.BudgetExceeded:
        raise
    except Exception as ex:                             # pas de correctif automatique : plan d'action manuel
        log(f"  {c['id']} {t('log.fix_error')} : {type(ex).__name__}: {str(ex)[:160]}")
        ctx.trail.log("fix_proposal_failed", control=c["id"], error=f"{type(ex).__name__}: {str(ex)[:240]}")
        prop = {"type": "manual", "rationale": t("f.fix_fallback")}
    if c["remediation"] == "manual" or prop.get("type") == "manual" or not ctx.target["remediable"]:
        return {"type": "manual", "actions": prop.get("actions") or [c["recommendation"]],
                "rationale": prop.get("rationale", c["recommendation"])}
    return {"type": "config", "method": str(prop.get("method", "")).upper(), "path": prop.get("path", ""),
            "body": prop.get("body") or {}, "rationale": prop.get("rationale", ""), "impact": prop.get("impact", "")}


def guard_fix(prop: dict) -> str | None:
    """Liste blanche des correctifs applicables automatiquement. Renvoie la raison d'un refus."""
    if (prop["method"], prop["path"]) != FIX_ROUTE:
        return f"route non autorisée : {prop['method']} {prop['path']}"
    if not prop["body"]:
        return "correctif vide"
    for k, v in prop["body"].items():
        if k not in FIX_KEYS:
            return f"paramètre non autorisé : {k}"
        if type(v) is not FIX_KEYS[k]:
            return f"type invalide pour {k}"
    return None


def apply_change(prop: dict, ticket: str, approver: str, ctx: Ctx) -> dict:
    """Applique un changement APPROUVÉ, puis vérifie qu'il figure au journal du système audité."""
    try:
        r = requests.patch(ctx.mission.lab_url + prop["path"], json=prop["body"], timeout=15,
                           headers={"Authorization": f"Bearer {config.CHANGE_TOKEN}",
                                    "X-Change-Ticket": ticket, "X-Approved-By": approver})
    except requests.RequestException as ex:
        return {"applied": False, "http": None, "journal": None, "error": str(ex)}
    entry = None
    try:
        j = requests.get(ctx.mission.lab_url + "/api/journal", timeout=10,
                         headers={"Authorization": f"Bearer {config.AUDIT_TOKEN}"})
        if j.ok:
            entry = next((x for x in reversed(j.json()) if x.get("ticket") == ticket), None)
    except (requests.RequestException, ValueError):
        pass                                        # changement non retrouvé au journal : signalé dans le rapport
    out = {"applied": r.ok, "http": r.status_code, "journal": entry}
    if not r.ok:
        out["error"] = r.text[:200]
    return out


def preflight(mission) -> None:
    """Avant toute mission : le système répond, refuse l'accès anonyme, et le compte d'audit fonctionne."""
    url = mission.lab_url
    try:
        anon = requests.get(url + "/api/security", timeout=5)
    except requests.RequestException:
        sys.exit(t("pre.unreachable").format(url=url))
    if anon.status_code != 401:
        sys.exit(t("pre.noauth"))
    ro = requests.get(url + "/api/journal", timeout=5, headers={"Authorization": f"Bearer {config.AUDIT_TOKEN}"})
    if ro.status_code != 200:
        sys.exit(t("pre.token").format(code=ro.status_code))


def remediation(entries: list, ctx: Ctx, approve_all: bool, approver: str) -> list:
    findings = sorted((e for e in entries if e.get("finding")), key=lambda e: e["finding"]["id"])
    if not findings:
        return []
    if approver.strip().lower() == ctx.mission.lead_auditor.strip().lower():
        sys.exit(t("pre.sod"))
    log(f"{t('log.remediation')} : {len(findings)}")
    with ThreadPoolExecutor(WORKERS) as pool:
        proposals = list(pool.map(lambda e: propose_fix(e, ctx), findings))

    interactive = sys.stdin.isatty() and not approve_all
    decisions = []
    for e, prop in zip(findings, proposals):
        c, f = e["control"], e["finding"]
        ticket = f"CHG-{ctx.mission.id}-{f['id'][2:]}"          # CHG-…-03 corrige F-03
        e["change"] = {"ticket": ticket, **prop}
        if prop["type"] == "manual":
            f["status"] = "action_plan"
            ctx.trail.log("action_plan", finding=f["id"], control=c["id"], actions=prop["actions"])
            log(f"  {f['id']} {c['rule']} → {t('fs.action_plan')}")
            continue
        refusal = guard_fix(prop)
        if refusal:
            e["change"]["guard_refusal"] = refusal
            f["status"] = "pending"
            ctx.trail.log("change_refused_by_guard", ticket=ticket, reason=refusal)
            log(f"  {ticket} refusé par le garde-fou : {refusal}")
            continue

        print(f"\n  ┌─ {t('f.change')} {ticket}\n"
              f"  │ {f['id']} · {c['rule']} · {t('sev.' + c['severity'])} · {c['title']}\n"
              f"  │ {prop['method']} {prop['path']} {json.dumps(prop['body'], ensure_ascii=False)}\n"
              f"  │ {prop['rationale']}\n"
              + (f"  │ {t('f.impact')} : {prop['impact']}\n" if prop.get("impact") else "")
              + "  └─", flush=True)
        if approve_all:
            ok, mode = True, "pre-approved"
        elif interactive:
            ok = input(t("log.approve").format(a=approver)).strip().lower() in ("o", "oui", "y", "yes")
            mode = "interactive"
        else:
            ok, mode = False, "no-approver"
        ctx.trail.log("change_decision", ticket=ticket, finding=f["id"], approved=ok,
                      approver=approver if ok else None, mode=mode, change=prop)
        decisions.append({"ticket": ticket, "finding": f["id"], "approved": ok,
                          "approver": approver if ok else "", "mode": mode,
                          "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        if not ok:
            f["status"] = "rejected" if mode == "interactive" else "pending"
            continue
        e["change"].update(approved_by=approver, approved_at=time.strftime("%Y-%m-%d %H:%M:%S"), mode=mode,
                           **apply_change(prop, ticket, approver, ctx))
        ctx.trail.log("change_applied", ticket=ticket, http=e["change"]["http"],
                      journal_recorded=bool(e["change"]["journal"]))
        log(f"  {ticket} → {t('f.applied') if e['change']['applied'] else t('f.notapplied')}")
    return decisions


def verify_fix(e: dict, ctx: Ctx, refresh):
    res = _safe_run(e["test"]["code"], ctx)           # le même script, rejoué tel quel
    ev = None
    try:
        ev = collect_evidence(e, res, "after", ctx) if res["status"] != "error" else None
    except Exception as ex:
        e["evidence_error_after"] = f"{type(ex).__name__} : {str(ex)[:240]}"
        ctx.trail.log("evidence_failed", control=e["control"]["id"], phase="after", error=e["evidence_error_after"])
        log(f"  {e['control']['id']} preuve impossible : {e['evidence_error_after']}")
    e["after"], e["evidence_after"] = res, ev
    e["status_after"] = classify(res, ev)
    if e["status_after"] == "pass":
        e["finding"]["status"] = "closed"
    ctx.trail.log("retest", control=e["control"]["id"], result=res, status=e["status_after"])
    log(f"{t('log.verify')} {e['control']['id']} → {t('st.' + e['status_after'])}")
    refresh()


# ---------- synthèse ----------

def opinion(severities: list, inconclusive: int = 0) -> str:
    """Opinion fondée sur les constats ; un contrôle non concluant (erreur de test) ne vaut jamais conformité."""
    if "critique" in severities:
        return "insuffisant"
    if "elevee" in severities:
        return "ameliorer"
    if inconclusive:
        return "reserve"
    return "globalement" if severities else "satisfaisant"


def raise_findings(entries: list, mission) -> None:
    today = date.today()
    order = {s: i for i, s in enumerate(config.SEVERITIES)}
    failing = sorted((e for e in entries if e["status_before"] == "fail"),
                     key=lambda e: (order[e["control"]["severity"]], e["control"]["id"]))
    for n, e in enumerate(failing, 1):
        sev = e["control"]["severity"]
        e["finding"] = {"id": f"F-{n:02d}", "severity": sev, "status": "open", "owner": mission.owner,
                        "due": (today + timedelta(days=int(mission.sla_days.get(sev, 180)))).isoformat()}


def issue(state: dict, ctx: Ctx, refresh) -> None:
    """Émission de fin : rapport HTML/PDF, result.json, piste et manifeste (chemin normal comme chemin d'échec)."""
    out_dir, trail = ctx.out, ctx.trail
    state["running"] = False
    state["trail_head"] = trail.head
    refresh()
    html = out_dir / "report.html"
    pdf = out_dir / "report.pdf"
    try:
        report.to_pdf(html, pdf)
    except Exception as ex:
        log(f"PDF non généré : {ex}")
    result = out_dir / "result.json"
    result.write_text(json.dumps({k: v for k, v in state.items()}, ensure_ascii=False, indent=2, default=str))
    trail.log("report_issued", file="report.html", sha256=sha256_file(html), aborted=bool(state.get("aborted")),
              pdf_sha256=sha256_file(pdf) if pdf.exists() else None, result_sha256=sha256_file(result))
    files = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name not in ("manifest.json", "trail.jsonl"))
    (out_dir / "manifest.json").write_text(json.dumps({
        "mission": state["mission"]["id"], "run_id": state["run_id"], "issued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "trail_head": trail.head, "aborted": state.get("aborted"),
        "files": [{"path": ctx.rel(p), "sha256": sha256_file(p)} for p in files]}, indent=2))
    log(f"{t('log.report')} : {html}" + (f" · {pdf.name}" if pdf.exists() else ""))


def run(mission, out_dir: Path, remediate: bool = False, approve_all: bool = False,
        approver: str = "", fresh: bool = False, replan: bool = False, reset_lab: bool = False,
        controls: list | None = None, catalogue_meta: dict | None = None, interpretation: dict | None = None,
        run_id: str | None = None):
    t0 = time.time()
    preflight(mission)
    for d in ("evidence", "scripts"):
        (out_dir / d).mkdir(parents=True, exist_ok=True)
    trail = Trail(out_dir / "trail.jsonl")
    ctx = Ctx(mission, out_dir, trail, fresh)
    trail.log("engagement_opened", mission=mission.id, system=mission.system, backend=llm.BACKEND,
              lead_auditor=mission.lead_auditor, framework=str(mission.requirement_path.name))

    def portable(v):                     # jamais de chemin absolu (nom d'utilisateur, arborescence locale)
        if isinstance(v, Path):
            try:
                return str(v.resolve().relative_to(config.ROOT))
            except ValueError:
                return v.name
        return v

    state = {"mission": {k: portable(v) for k, v in asdict(mission).items()},
             "run_id": run_id or out_dir.name, "started": time.strftime("%Y-%m-%d %H:%M"), "lang": config.lang(),
             "target": mission.target, "target_label": targets.label(mission.target),
             "backend": llm.BACKEND, "models": {"reason": llm.model_for(False), "code": llm.model_for(True),
                                                 "segmentation": "sam-3.1"},
             "entries": [], "running": True, "decisions": [], "remediation_requested": remediate}

    lock = threading.Lock()

    def refresh():
        with lock:
            state["usage"] = llm.USAGE.cost()
            state["duration_s"] = round(time.time() - t0)
            report.write(state, out_dir)

    try:
        _phases(state, ctx, refresh, remediate, approve_all, approver, replan, reset_lab,
                controls, catalogue_meta, interpretation)
    except BaseException as ex:                     # y compris BudgetExceeded, SystemExit, Ctrl+C
        state["aborted"] = f"{type(ex).__name__}: {str(ex)[:300]}"
        trail.log("engagement_aborted", error=state["aborted"])
        log(f"{t('log.aborted')} : {state['aborted']}")
        try:
            issue(state, ctx, refresh)
        except Exception as ex2:                    # ne masque jamais l'erreur d'origine
            log(f"émission impossible : {type(ex2).__name__}: {ex2}")
        raise
    issue(state, ctx, refresh)
    return state


def _phases(state, ctx, refresh, remediate, approve_all, approver, replan, reset_lab,
            controls, catalogue_meta, interpretation):
    mission, out_dir, trail = ctx.mission, ctx.out, ctx.trail
    if reset_lab:
        requests.post(mission.lab_url + "/api/reset", timeout=5,
                      headers={"Authorization": f"Bearer {config.CHANGE_TOKEN}"})
        trail.log("demo_environment_reset")
    refresh()
    if controls is None:
        controls, cat_meta = catalog.load_or_plan(mission, trail, replan=replan)
    else:                                                  # programme validé dans Attest Studio
        controls = catalog.normalize(controls, ctx.target["default_page"])
        cat_meta = catalogue_meta or {"source": "studio"}
        trail.log("catalogue_validated", controls=len(controls), reviewer=cat_meta.get("reviewer"),
                  reviewed=cat_meta.get("reviewed", False))
    state["catalogue"] = cat_meta
    state["interpretation"] = interpretation
    state["entries"] = entries = [{"control": c} for c in controls]
    log(f"{t('log.plan')} : {len(controls)} · {cat_meta['source']}")
    refresh()

    with ThreadPoolExecutor(WORKERS) as pool:                         # Phase 1 — constat
        list(pool.map(lambda e: observe(e, ctx, refresh), entries))
    raise_findings(entries, mission)
    inconclusive = sum(1 for e in entries if e.get("status_before") == "error")
    state["opinion_initial"] = opinion([e["finding"]["severity"] for e in entries if e.get("finding")], inconclusive)
    refresh()

    if remediate:                                                       # Phase 2 — remédiation
        state["decisions"] = remediation(entries, ctx, approve_all, approver)
        refresh()
        applied = [e for e in entries if e.get("change", {}).get("applied")]
        with ThreadPoolExecutor(WORKERS) as pool:                       # Phase 3 — contre-vérification
            list(pool.map(lambda e: verify_fix(e, ctx, refresh), applied))
        if applied:
            shot = out_dir / "evidence" / "journal.png"
            evidence.capture(mission.lab_url + "/admin/journal", shot, config.AUDIT_TOKEN)
            state["journal_evidence"] = {"image": ctx.rel(shot), "sha256": sha256_file(shot)}
            trail.log("evidence_sealed", control="journal", phase="after", file=ctx.rel(shot),
                      sha256=state["journal_evidence"]["sha256"], page="/admin/journal")

    state["opinion_final"] = opinion([e["finding"]["severity"] for e in entries
                                      if e.get("finding") and e["finding"]["status"] != "closed"], inconclusive)
    state["injection_detected"] = any(
        (e.get(k) or {}).get("inspection", {}).get("injection_detected") for e in entries
        for k in ("evidence_before", "evidence_after"))
