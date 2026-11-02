"""Boucle de l'agent : exigence → contrôles → scripts → exécution → preuves → remédiation → rapport."""
import json
import os
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageFilter

from . import evidence, llm, prompts, report, sam, sandbox

LANG = os.getenv("ATTEST_LANG", "French")
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


def annotate(shot: Path, insp: dict, status: str, out: Path) -> dict:
    """SAM affine la zone qui prouve le constat (surlignée) et les données personnelles (floutées)."""
    img = Image.open(shot).convert("RGB")
    boxes = [tuple(insp["field_box"])] + [tuple(p["box"]) for p in insp.get("pii", [])]
    masks = sam.segment_boxes(shot, boxes)
    field_mask, pii_masks = masks[0], masks[1:]

    pii = np.zeros(field_mask.shape, dtype=bool)
    if pii_masks:                                   # floutage des données personnelles
        # marge de sécurité de quelques pixels autour du masque SAM, puis pixelisation + flou
        raw = Image.fromarray((np.any(pii_masks, axis=0) * 255).astype(np.uint8))
        pii_img = raw.filter(ImageFilter.MaxFilter(15))
        pii = np.asarray(pii_img) > 127
        w, h = img.size
        pixel = img.resize((max(1, w // 12), max(1, h // 12)), Image.BILINEAR).resize((w, h), Image.NEAREST)
        img = Image.composite(pixel.filter(ImageFilter.GaussianBlur(4)), img, pii_img)

    color = np.array([220, 38, 38] if status == "fail" else [22, 163, 74], dtype=np.float32)
    arr = np.asarray(img).astype(np.float32)
    arr[field_mask] = arr[field_mask] * 0.72 + color * 0.28
    edge = field_mask ^ np.asarray(Image.fromarray(field_mask.astype(np.uint8) * 255)
                                   .filter(ImageFilter.MinFilter(5))).astype(bool)
    arr[edge] = color
    Image.fromarray(arr.astype(np.uint8)).save(out)
    return {"field_mask": field_mask, "pii": pii}


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


def remediate(control, result, lab_url) -> dict:
    shown = {k: v for k, v in control.items() if not k.startswith("_")}
    fix = llm.extract_json(llm.ask(
        "fix", prompts.FIX_SYSTEM,
        prompts.FIX_USER.format(control=json.dumps(shown, ensure_ascii=False),
                                result=json.dumps(result, ensure_ascii=False), api_doc=API_DOC, lang=LANG),
        mock_ctx={"control": control}))
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

    for c in controls:
        entry = {"control": c}
        state["controls"].append(entry)
        log(f"2/4 {c['id']} {c['rule']} · {c['title']} : écriture et exécution du script")
        entry["code"], entry["before"] = run_check(c, lab_url, out_dir / "scripts")
        log(f"    → {entry['before']['status']}")
        if entry["before"]["status"] != "error":
            log("3/4 Preuve : capture, vérification visuelle, SAM")
            entry["evidence_before"] = collect_evidence(c, entry["before"], lab_url, out_dir / "evidence", "avant")
        report.write(state, out_dir)

        if auto_fix and entry["before"]["status"] == "fail":
            log("4/4 Remédiation puis nouvelle vérification")
            entry["remediation"] = remediate(c, entry["before"], lab_url)
            if entry["remediation"]["applied"]:
                entry["after"] = sandbox.run(entry["code"], lab_url)   # même script, rejoué
                log(f"    → après correctif : {entry['after']['status']}")
                entry["evidence_after"] = collect_evidence(c, entry["after"], lab_url, out_dir / "evidence", "apres")
            report.write(state, out_dir)

    state["running"] = False
    report.write(state, out_dir)
    (out_dir / "result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str))
    log(f"Rapport : {out_dir / 'report.html'}")
    return state
