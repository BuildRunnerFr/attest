"""Boucle de l'agent : exigence → contrôles → scripts → exécution → preuves → remédiation → rapport."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

from . import evidence, llm, prompts, report, sam, sandbox

LANG = os.getenv("ATTEST_LANG", "French")
WORKERS = int(os.getenv("ATTEST_WORKERS", "6"))   # contrôles traités en parallèle
ROOT = Path(__file__).resolve().parent.parent
API_DOC = (ROOT / "lab" / "API.md").read_text()
ALLOWED_FIX_KEYS = {"mfa_admin", "mfa_users", "password_min_length", "password_require_complexity",
                    "lockout_threshold", "session_timeout_minutes", "admin_audit_log"}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------- étapes ----------

def plan(requirement: str) -> list[dict]:
    txt = llm.ask("plan", prompts.PLAN_SYSTEM,
                  prompts.PLAN_USER.format(requirement=requirement, api_doc=API_DOC, lang=LANG))
    return llm.extract_json(txt)


def write_check(control: dict, error: str | None = None) -> str:
    prev = f"\nYOUR PREVIOUS VERSION FAILED WITH:\n{error}\nFix it." if error else ""
    shown = {k: v for k, v in control.items() if not k.startswith("_")}
    txt = llm.ask("code", prompts.CODE_SYSTEM,
                  prompts.CODE_USER.format(control=json.dumps(shown, ensure_ascii=False),
                                           api_doc=API_DOC, previous_error=prev),
                  code=True, mock_ctx={"control": control})
    return llm.extract_code(txt)


def run_check(control: dict, lab_url: str, scripts_dir: Path) -> tuple[str, dict]:
    code, error = None, None
    for attempt in range(2):                       # une auto-correction autorisée
        code = write_check(control, error)
        try:
            res = sandbox.run(code, lab_url)
        except sandbox.UnsafeCode as e:
            res = {"status": "error", "detail": f"refusé par le garde-fou : {e}"}
        if res["status"] != "error":
            break
        error = res["detail"]
        log(f"  script en erreur, nouvelle tentative : {error[:120]}")
    (scripts_dir / f"{control['id']}.py").write_text(code)
    return code, res


def inspect(control: dict, result: dict, shot: Path, dom: dict) -> dict:
    w, h = Image.open(shot).size
    shown = {k: v for k, v in control.items() if not k.startswith("_")}
    txt = llm.ask("inspect", prompts.INSPECT_SYSTEM.format(w=w, h=h),
                  prompts.INSPECT_USER.format(control=json.dumps(shown, ensure_ascii=False),
                                              result=json.dumps(result, ensure_ascii=False), lang=LANG),
                  image=shot, mock_ctx={"control": control, "result": result, "dom": dom})
    return llm.extract_json(txt)


def snap(mask: np.ndarray, box, pad: int = 10):
    """Resserre une boîte sur ce que SAM a réellement segmenté à l'intérieur (± pad).

    Sur une capture d'écran, SAM découpe les glyphes et non la ligne : on garde donc
    l'enveloppe de son masque, limitée à la zone de Muse Spark (les pixels parasites
    hors zone sont ignorés)."""
    H, W = mask.shape
    x1, y1, x2, y2 = [int(v) for v in box]
    X1, Y1, X2, Y2 = max(0, x1 - pad), max(0, y1 - pad), min(W, x2 + pad), min(H, y2 + pad)
    ys, xs = np.nonzero(mask[Y1:Y2, X1:X2])
    if len(xs) < 20:                                # SAM n'a rien trouvé : on garde la boîte
        return (max(0, x1), max(0, y1), min(W, x2), min(H, y2))
    return (X1 + int(xs.min()), Y1 + int(ys.min()), X1 + int(xs.max()) + 1, Y1 + int(ys.max()) + 1)


def field_boxes(insp: dict) -> list:
    boxes = insp.get("field_boxes") or ([insp["field_box"]] if insp.get("field_box") else [])
    return [tuple(int(v) for v in b) for b in boxes if len(b) == 4]


def annotate(shot: Path, insp: dict, status: str, out: Path) -> dict:
    """SAM affine les zones qui prouvent le constat (surlignées) et les données personnelles (floutées)."""
    img = Image.open(shot).convert("RGB")
    W, H = img.size
    fboxes = field_boxes(insp)
    pboxes = [tuple(int(v) for v in p["box"]) for p in insp.get("pii", []) if len(p.get("box", [])) == 4]
    masks = sam.segment_boxes(shot, fboxes + pboxes)
    fmasks, pmasks = masks[:len(fboxes)], masks[len(fboxes):]

    # 1. floutage : boîte de Muse Spark ∪ masque SAM dilaté (en rédaction, mieux vaut trop que pas assez)
    pii = np.zeros((H, W), dtype=bool)
    for b, m in zip(pboxes, pmasks):
        x1, y1, x2, y2 = b
        pii[max(0, y1 - 3):y2 + 3, max(0, x1 - 3):x2 + 3] = True
        pii |= np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(11))) > 127
    if pii.any():
        pii_img = Image.fromarray(pii.astype(np.uint8) * 255)
        pixel = img.resize((max(1, W // 12), max(1, H // 12)), Image.BILINEAR).resize((W, H), Image.NEAREST)
        img = Image.composite(pixel.filter(ImageFilter.GaussianBlur(4)), img, pii_img)

    # 2. surlignage : rectangle propre autour de ce que SAM a segmenté dans chaque zone
    rgb = (220, 38, 38) if status == "fail" else (22, 163, 74)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    snapped = []
    for b, m in zip(fboxes, fmasks):
        x1, y1, x2, y2 = snap(m, b)
        x1, y1, x2, y2 = x1 - 6, y1 - 5, x2 + 6, y2 + 5
        snapped.append((x1, y1, x2, y2))
        draw.rounded_rectangle((x1, y1, x2, y2), radius=6, fill=rgb + (60,), outline=rgb + (255,), width=3)
    Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB").save(out)
    return {"field_boxes": snapped, "pii": pii}


def measure(masks: dict, dom: dict, control: dict) -> dict:
    """Précision mesurée contre le DOM (vérité terrain jamais montrée au modèle)."""
    covered = []
    union = masks["pii"]
    for p in dom.get("pii", []):
        x1, y1, x2, y2 = p["box"]
        zone = union[y1:y2, x1:x2]
        covered.append(float(zone.mean()) if zone.size else 0.0)
    return {
        "pii_total": len(covered),
        "pii_redacted": sum(c >= 0.8 for c in covered),   # ≥ 80 % de la zone floutée
    }


def collect_evidence(control, result, lab_url, ev_dir: Path, tag: str) -> dict:
    shot = ev_dir / f"{control['id']}_{tag}_raw.png"
    dom = evidence.capture(lab_url + control["evidence_page"], shot)
    insp = inspect(control, result, shot, dom)
    final = ev_dir / f"{control['id']}_{tag}.png"
    masks = annotate(shot, insp, result["status"], final)
    shot.unlink()                                   # on ne garde pas la version non floutée
    return {"image": f"evidence/{final.name}", "inspection": insp, "metrics": measure(masks, dom, control)}


def propose_fix(control, result) -> dict:
    shown = {k: v for k, v in control.items() if not k.startswith("_")}
    return llm.extract_json(llm.ask(
        "fix", prompts.FIX_SYSTEM,
        prompts.FIX_USER.format(control=json.dumps(shown, ensure_ascii=False),
                                result=json.dumps(result, ensure_ascii=False), api_doc=API_DOC, lang=LANG),
        mock_ctx={"control": control}))


def apply_fix(fix: dict, lab_url) -> dict:
    # garde-fou : une seule route autorisée, et seulement des clés connues
    if fix.get("method") != "PATCH" or fix.get("path") != "/api/security" \
            or not set(fix.get("body", {})) <= ALLOWED_FIX_KEYS:
        return {"fix": fix, "applied": False, "reason": "correctif refusé par le garde-fou"}
    r = requests.patch(lab_url + fix["path"], json=fix["body"], timeout=10)
    return {"fix": fix, "applied": r.ok, "reason": "" if r.ok else r.text[:200]}


# ---------- orchestration ----------

def run(requirement_path: Path, lab_url: str, out_dir: Path, auto_fix: bool = True, reset: bool = True):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence").mkdir(exist_ok=True)
    (out_dir / "scripts").mkdir(exist_ok=True)
    if reset:
        requests.post(lab_url + "/api/reset", timeout=5)

    state = {"requirement": requirement_path.read_text(), "backend": llm.BACKEND,
             "started": time.strftime("%Y-%m-%d %H:%M"), "controls": [], "running": True}
    report.write(state, out_dir)

    log("1/4 Lecture de l'exigence et plan des contrôles")
    controls = plan(state["requirement"])
    log(f"    {len(controls)} contrôles")

    entries = [{"control": c} for c in controls]
    state["controls"] = entries
    lock = threading.Lock()

    def refresh():
        with lock:
            report.write(state, out_dir)

    # Phase 1 — constat : tous les contrôles en parallèle, AVANT toute correction
    def observe(e):
        c = e["control"]
        e["code"], e["before"] = run_check(c, lab_url, out_dir / "scripts")
        log(f"2/4 {c['id']} {c['rule']} · {c['title']} → {e['before']['status']}")
        refresh()
        if e["before"]["status"] != "error":
            e["evidence_before"] = collect_evidence(c, e["before"], lab_url, out_dir / "evidence", "avant")
            log(f"3/4 {c['id']} preuve capturée, vérifiée et annotée")
        refresh()

    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(observe, entries))

    failed = [e for e in entries if e["before"]["status"] == "fail"]
    if auto_fix and failed:
        # Phase 2 — remédiation : correctifs proposés en parallèle, appliqués un par un
        log(f"4/4 Remédiation de {len(failed)} non-conformités")
        with ThreadPoolExecutor(WORKERS) as pool:
            fixes = list(pool.map(lambda e: propose_fix(e["control"], e["before"]), failed))
        for e, fix in zip(failed, fixes):
            e["remediation"] = apply_fix(fix, lab_url)
            log(f"    {e['control']['id']} correctif {'appliqué' if e['remediation']['applied'] else 'REFUSÉ'}")
        refresh()

        # Phase 3 — contre-vérification : mêmes scripts rejoués, nouvelles preuves
        def recheck(e):
            if not e["remediation"]["applied"]:
                return
            e["after"] = sandbox.run(e["code"], lab_url)
            e["evidence_after"] = collect_evidence(e["control"], e["after"], lab_url, out_dir / "evidence", "apres")
            log(f"    {e['control']['id']} après correctif → {e['after']['status']}")
            refresh()

        with ThreadPoolExecutor(WORKERS) as pool:
            list(pool.map(recheck, failed))

    state["running"] = False
    report.write(state, out_dir)
    (out_dir / "result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str))
    log(f"Rapport : {out_dir / 'report.html'}")
    return state
