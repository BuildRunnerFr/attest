"""Attest Studio — interface web locale.

1. on choisit des textes (bibliothèque d'extraits réglementaires vérifiés, politiques internes, ou son propre texte) ;
2. on choisit la cible (console IAM, dépôt de code) ;
3. Muse Spark propose un programme de travail ANCRÉ (citations vérifiées, origine des seuils, testabilité) ;
4. un auditeur le valide, contrôle par contrôle ;
5. l'audit tourne et le rapport s'affiche en direct.

  python -m lab.app            # terminal 1 : systèmes audités (démo)
  python -m attest.studio      # terminal 2 : http://127.0.0.1:8000
"""
import dataclasses
import io
import json
import os
import threading
import time
import traceback
import uuid

from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_from_directory

from . import config, interpret, llm, targets

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
LIB = config.ROOT / "exigences" / "library"
WORK = config.ROOT / "runs" / "studio"
JOBS: dict = {}
RUN_LOCK = threading.Lock()            # un seul pipeline par dossier : la piste d'audit scellée n'a qu'un auteur
SEVS = ["critique", "elevee", "moyenne", "faible"]

S = {
    "fr": {
        "tagline": "Audit de conformité DORA, ancré dans le texte", "title": "Nouvel audit",
        "intro": "Choisissez le référentiel et la cible. Muse Spark propose un programme de travail ancré dans le texte ; "
                 "vous le validez avant tout test.",
        "step1": "Référentiel", "step1_hint": "Extraits officiels vérifiés (texte anglais) et politiques internes fictives. "
        "Sans politique interne, les seuils sont des propositions à valider.",
        "regulation": "Règlement", "policy": "Politique interne", "own": "Ou votre propre texte (collé ou fichier .md, .txt, .pdf)",
        "paste": "Collez ici un article ou une politique…", "step2": "Cible", "step3": "Interprétation",
        "lang": "Langue du rapport", "go": "Proposer le programme de travail",
        "busy": "Muse Spark lit le texte et propose les contrôles… (environ une minute)",
        "review": "Programme de travail proposé — à valider", "reqs": "exigences lues", "auto": "testables ici",
        "doc": "revue documentaire", "itw": "entretien", "rej": "citations rejetées", "ctrls": "contrôles proposés",
        "warn": "L'IA propose, vous décidez. Chaque contrôle cite le texte dont il découle ; la citation a été vérifiée "
                "mot pour mot. Les seuils marqués « proposition » ne viennent pas de votre politique.",
        "verified": "citation vérifiée", "notfound": "citation introuvable : exigence rejetée", "expected": "Attendu",
        "threshold": "Seuil", "proposal": "proposition à valider", "reviewer": "Votre nom (auditeur qui valide)",
        "remediate": "Proposer et appliquer les correctifs approuvés", "approver": "Approbateur des changements",
        "run": "Valider le programme et lancer l'audit", "running": "Audit en cours…", "done": "Audit terminé",
        "error": "Erreur", "pdf": "Télécharger le PDF", "new": "Nouvel audit", "none": "Choisissez au moins un texte.",
        "sod": "L'approbateur des changements doit être différent de l'auditeur.", "covered": "testée par le contrôle de la politique", "noctrl": "Aucun contrôle retenu.",
        "testability": {"automated": "testable ici", "document": "revue documentaire", "interview": "entretien"},
        "sev": {"critique": "Critique", "elevee": "Élevée", "moyenne": "Moyenne", "faible": "Faible"},
        "noreviewer": "Indiquez votre nom : l'auditeur qui valide le programme signe le rapport.",
        "badtarget": "Cible inconnue.", "jobbusy": "Un audit est en cours : attendez sa fin avant d'en préparer un autre.",
    },
    "en": {
        "tagline": "DORA compliance audits, grounded in the text", "title": "New audit",
        "intro": "Pick the framework and the target. Muse Spark drafts a work programme grounded in the text; "
                 "you approve it before anything is tested.",
        "step1": "Framework", "step1_hint": "Verified official excerpts and fictitious internal policies. Without an "
        "internal policy, thresholds are proposals to approve.",
        "regulation": "Regulation", "policy": "Internal policy", "own": "Or your own text (pasted, or a .md, .txt, .pdf file)",
        "paste": "Paste an article or a policy here…", "step2": "Target", "step3": "Interpretation",
        "lang": "Report language", "go": "Draft the work programme",
        "busy": "Muse Spark is reading the text and drafting controls… (about a minute)",
        "review": "Proposed work programme — for approval", "reqs": "requirements read", "auto": "testable here",
        "doc": "document review", "itw": "interview", "rej": "quotes rejected", "ctrls": "controls proposed",
        "warn": "The AI proposes, you decide. Every control quotes the text it derives from; the quote was checked "
                "word for word. Thresholds marked “proposal” do not come from your policy.",
        "verified": "quote verified", "notfound": "quote not found: requirement rejected", "expected": "Expected",
        "threshold": "Threshold", "proposal": "proposal to approve", "reviewer": "Your name (approving auditor)",
        "remediate": "Propose and apply approved fixes", "approver": "Change approver",
        "run": "Approve the programme and run the audit", "running": "Audit running…", "done": "Audit complete",
        "error": "Error", "pdf": "Download the PDF", "new": "New audit", "none": "Pick at least one text.",
        "sod": "The change approver must not be the auditor.", "covered": "tested by the policy control", "noctrl": "No control selected.",
        "testability": {"automated": "testable here", "document": "document review", "interview": "interview"},
        "sev": {"critique": "Critical", "elevee": "High", "moyenne": "Medium", "faible": "Low"},
        "noreviewer": "Enter your name: the auditor who approves the programme signs the report.",
        "badtarget": "Unknown target.", "jobbusy": "An audit is running: wait for it to finish before preparing another.",
    },
}

CSS = """
:root{--ink:#14171c;--mute:#5d6470;--line:#dfe2e7;--navy:#0f2747;--ok:#166534;--ko:#b91c1c;--warn:#8a5a00}
*{box-sizing:border-box}body{margin:0;background:#eef0f3;color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
header{background:var(--navy);color:#dbe3ef;padding:12px 24px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header b{color:#fff;font-size:17px}header .sp{flex:1}header a{color:#dbe3ef;text-decoration:none;font-size:13px}
main{max-width:1000px;margin:0 auto;padding:26px 16px 60px}main.wide{max-width:1200px}
h1{font:600 28px/1.2 Georgia,serif;margin:0 0 6px}p.sub{color:var(--mute);margin:0 0 20px}
.step{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-bottom:16px}
.step h2{font:600 18px Georgia,serif;margin:0 0 6px;color:var(--navy)}.hint{color:var(--mute);font-size:13px;margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px}
label.item{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line);border-radius:8px;padding:10px 12px;cursor:pointer;background:#fafbfc}
label.item:hover{border-color:#9aa5b8}label.item small{display:block;color:var(--mute);font-size:12px}
label.item.policy{background:#f5f8ff}
textarea{width:100%;margin:10px 0;border:1px solid var(--line);border-radius:8px;padding:10px;font:13px ui-monospace,Menlo,monospace}
details summary{cursor:pointer;color:var(--navy);margin-top:12px;font-size:14px}
select,input[type=text],input:not([type]){border:1px solid var(--line);border-radius:6px;padding:7px 9px;font:inherit;background:#fff}
button{background:var(--navy);color:#fff;border:0;border-radius:8px;padding:11px 18px;font:600 15px inherit;cursor:pointer}
button:hover{background:#1b3b66}.row{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.alert{border:1px solid #f1c27d;background:#fff8eb;border-radius:8px;padding:10px 14px;margin:0 0 14px}
.busy[hidden]{display:none}.busy{position:fixed;inset:0;background:#0f2747e6;color:#fff;display:flex;align-items:center;justify-content:center;font:600 18px Georgia,serif;padding:20px;text-align:center}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:0 0 14px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 12px}.kpi b{display:block;font:600 22px Georgia,serif}.kpi span{font-size:12px;color:var(--mute)}
.req{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.req.rejected{opacity:.75;border-style:dashed}
.rh{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.ref{font:600 12px ui-monospace,Menlo,monospace;color:var(--navy)}
.tb{font-size:11.5px;font-weight:600;border-radius:4px;padding:2px 8px;background:#e7f3ea;color:var(--ok)}
.tb.document,.tb.interview{background:#fdf3e1;color:var(--warn)}.tb.rejected{background:#fde8e8;color:var(--ko)}
blockquote{margin:10px 0 6px;padding:6px 12px;border-left:3px solid var(--line);color:#3b4250;font-style:italic;font-size:14px}
.q-ok{color:var(--ok);font-size:12px;font-style:normal}.q-ko{color:var(--ko);font-size:12px;font-style:normal}
label.ctrl{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:start;border-top:1px solid #eef0f3;padding:10px 0 4px;cursor:pointer}
label.ctrl small{color:var(--mute)}code{font:12.5px ui-monospace,Menlo,monospace;background:#f3f4f6;border-radius:4px;padding:1px 5px}
em.prop{font-style:normal;font-size:11px;font-weight:600;color:var(--warn);background:#fdf3e1;border-radius:4px;padding:1px 6px;margin-left:4px}
.sign{position:sticky;bottom:0;background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;box-shadow:0 -4px 16px #0000000f}
.bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 12px}.bar .sp{flex:1}
.status{font:600 22px/1.25 Georgia,serif;margin:0}.status.error{color:var(--ko)}
a.btn{display:inline-flex;align-items:center;border-radius:8px;padding:9px 16px;font-weight:600;font-size:14px;text-decoration:none;
background:var(--navy);color:#fff;border:1px solid var(--navy)}a.btn:hover{background:#1b3b66}
a.btn.ghost{background:transparent;color:var(--navy)}a.btn.ghost:hover{background:#fff}a.btn[hidden]{display:none}
iframe{width:100%;height:calc(100vh - 150px);border:1px solid var(--line);border-radius:10px;background:#fff}
@media (max-width:640px){label.ctrl{grid-template-columns:auto 1fr}label.ctrl select{grid-column:2}
.bar .status{flex-basis:100%}.bar .sp{display:none}}
"""

HEAD = """<!doctype html><html lang="{{ lang }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Attest Studio</title><style>{{ css|safe }}</style></head><body>
<header><b>Attest Studio</b><span>{{ s.tagline }}</span><span class="sp"></span>
<a href="/?lang=fr">FR</a><a href="/?lang=en">EN</a></header>"""

INDEX = HEAD + """<main><h1>{{ s.title }}</h1><p class="sub">{{ s.intro }}</p>
{% if error %}<div class="alert">{{ error }}</div>{% endif %}
<form method="post" action="/interpret" enctype="multipart/form-data" id="f"><input type="hidden" name="lang" value="{{ lang }}">
<section class="step"><h2>1 · {{ s.step1 }}</h2><p class="hint">{{ s.step1_hint }}</p><div class="grid">
{% for it in library %}<label class="item {{ it.kind }}"><input type="checkbox" name="lib" value="{{ it.id }}">
<span><b>{{ it.title }}</b><small>{{ s.policy if it.kind == 'policy' else s.regulation }}</small></span></label>{% endfor %}
</div><details><summary>{{ s.own }}</summary><textarea name="pasted" rows="6" placeholder="{{ s.paste }}"></textarea>
<input type="file" name="upload" accept=".md,.txt,.pdf"></details></section>
<section class="step"><h2>2 · {{ s.step2 }}</h2><div class="grid">
{% for tid, t in targets.items() %}<label class="item"><input type="radio" name="target" value="{{ tid }}" {% if loop.first %}checked{% endif %}>
<span><b>{{ t.label[lang] }}</b><small>{{ tid }}</small></span></label>{% endfor %}</div></section>
<section class="step"><h2>3 · {{ s.step3 }}</h2><div class="row"><button type="submit">{{ s.go }}</button>
<span class="hint">Muse Spark · {{ backend }}</span></div></section></form>
<div id="busy" class="busy" hidden>{{ s.busy }}</div></main>
<script>document.getElementById('f').addEventListener('submit',()=>{document.getElementById('busy').hidden=false})</script></body></html>"""

REVIEW = HEAD + """<main><h1>{{ s.review }}</h1><p class="sub">{{ it.texts|join(' · ') }} → <b>{{ target_label }}</b></p>
{% if error %}<div class="alert">{{ error }}</div>{% endif %}
<div class="kpis">{% for k, v in kpis %}<div class="kpi"><b>{{ v }}</b><span>{{ k }}</span></div>{% endfor %}</div>
<div class="alert">{{ s.warn }}</div>
<form method="post" action="/run/{{ sid }}">
{% for r in it.requirements %}<div class="req {{ '' if r.quote_verified else 'rejected' }}"><div class="rh">
{% if r.ref %}<span class="ref">{{ r.ref }}</span>{% endif %}
<span class="tb {{ r.testability if r.quote_verified else 'rejected' }}">{{ s.testability[r.testability] if r.quote_verified else s.notfound }}</span>
<span>{{ r.summary }}</span></div>
<blockquote>« {{ r.quote }} » {% if r.quote_verified %}<span class="q-ok">✓ {{ s.verified }}</span>{% else %}<span class="q-ko">✗ {{ s.notfound }}</span>{% endif %}</blockquote>
{% if r.covered_by %}<p class="hint">↳ {{ s.covered }} {{ r.covered_by|join(', ') }}</p>{% endif %}
{% if r.why %}<p class="hint">{{ r.why }}</p>{% endif %}
{% for c in r.controls %}<label class="ctrl"><input type="checkbox" name="ctrl" value="{{ c.id }}" checked>
<span><b>{{ c.id }} · {{ c.title }}</b><br>{{ c.objective }}<br><small>{{ s.expected }} : <code>{{ c.expected }}</code> · {{ s.threshold }} : {{ c.threshold_source }}
{% if 'proposal' in (c.threshold_source or '')|lower %}<em class="prop">{{ s.proposal }}</em>{% endif %}</small></span>
<select name="sev_{{ c.id }}">{% for sv in sevs %}<option value="{{ sv }}" {% if sv == c.severity %}selected{% endif %}>{{ s.sev[sv] }}</option>{% endfor %}</select></label>{% endfor %}
</div>{% endfor %}
<div class="sign"><label>{{ s.reviewer }} <input name="reviewer" required></label>
{% if remediable %}<label><input type="checkbox" name="remediate"> {{ s.remediate }}</label>
<label>{{ s.approver }} <input name="approver" value="{{ 'IAM owner (demo)' if lang == 'en' else 'Responsable IAM (démo)' }}"></label>{% endif %}
<button>{{ s.run }}</button></div></form></main></body></html>"""

AUDIT = HEAD + """<main class="wide"><div class="bar"><div class="status" id="st">{{ s.running }}</div><span class="sp"></span>
<a id="pdf" class="btn" href="/files/{{ sid }}/audit/report.pdf" hidden>{{ s.pdf }}</a>
<a class="btn ghost" href="/?lang={{ lang }}">{{ s.new }}</a></div>
<iframe id="rep" title="report"></iframe></main>
<script>
const st=document.getElementById('st'),rep=document.getElementById('rep'),pdf=document.getElementById('pdf');let shown=false;
async function poll(){const r=await fetch('/status/{{ sid }}');const j=await r.json();
 if(j.report&&!shown){rep.src='/files/{{ sid }}/audit/report.html';shown=true}
 if(j.state==='done'){st.textContent='{{ s.done }}';pdf.hidden=!j.pdf;rep.src='/files/{{ sid }}/audit/report.html?'+Date.now();return}
 if(j.state==='error'){st.textContent='{{ s.error }} : '+j.message;st.className='status error';return}
 setTimeout(poll,2500)}
poll();</script></body></html>"""


def lang_of(value=None) -> str:
    v = (value or request.values.get("lang") or config.lang()).lower()
    return "en" if v.startswith("en") else "fr"


def library() -> list:
    out = []
    for p in sorted(LIB.glob("*.md")):
        first = p.read_text().splitlines()[0]
        out.append({"id": p.stem, "title": first.lstrip("# ").strip(),
                    "kind": "policy" if p.stem.startswith("politique") else "regulation"})
    return sorted(out, key=lambda x: (x["kind"] == "policy", x["title"]))


def read_upload(f) -> str:
    data = f.read()
    if f.filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    return data.decode("utf-8", errors="replace")


def render(tpl: str, lang: str, **kw):
    return render_template_string(tpl, css=CSS, s=S[lang], lang=lang, **kw)


@app.get("/")
def index():
    lang = lang_of()
    return render(INDEX, lang, library=library(), targets=targets.TARGETS, backend=llm.BACKEND, error=None)


def running() -> bool:
    return any(j.get("state") == "running" for j in JOBS.values())


def index_error(lang: str, error: str):
    return render(INDEX, lang, library=library(), targets=targets.TARGETS, backend=llm.BACKEND, error=error)


@app.post("/interpret")
def do_interpret():
    lang = lang_of()
    if running():                                       # le compteur de coût est partagé avec l'audit en cours
        return index_error(lang, S[lang]["jobbusy"]), 409
    target_id = request.form.get("target", "iam-console")
    if target_id not in targets.TARGETS:               # cible forgée : targets.get lèverait SystemExit
        return index_error(lang, S[lang]["badtarget"]), 400
    os.environ["ATTEST_LANG"] = lang
    texts = []
    for lib_id in request.form.getlist("lib"):
        p = LIB / f"{lib_id}.md"
        if p.exists() and p.parent == LIB:
            body = p.read_text()
            texts.append((body.splitlines()[0].lstrip("# ").strip(), body))
    if request.form.get("pasted", "").strip():
        texts.append(("Texte fourni" if lang == "fr" else "Provided text", request.form["pasted"]))
    up = request.files.get("upload")
    if up and up.filename:
        try:
            texts.append((up.filename, read_upload(up)))
        except Exception as ex:
            return render(INDEX, lang, library=library(), targets=targets.TARGETS, backend=llm.BACKEND,
                          error=f"{up.filename} : {ex}")
    if not texts:
        return render(INDEX, lang, library=library(), targets=targets.TARGETS, backend=llm.BACKEND, error=S[lang]["none"])
    llm.USAGE.reset()                                   # coût de cette mission : interprétation + audit
    try:
        result = interpret.interpret(texts, target_id)
    except Exception as ex:
        traceback.print_exc()
        return render(INDEX, lang, library=library(), targets=targets.TARGETS, backend=llm.BACKEND,
                      error=f"{type(ex).__name__} : {ex}")
    sid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = WORK / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / "interpretation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (d / "texts.json").write_text(json.dumps({"lang": lang, "target": target_id, "texts": texts}, ensure_ascii=False))
    return redirect(f"/review/{sid}?lang={lang}")


def load(sid: str):
    d = WORK / sid
    if "/" in sid or ".." in sid or not (d / "interpretation.json").exists():
        abort(404)
    return d, json.loads((d / "interpretation.json").read_text()), json.loads((d / "texts.json").read_text())


@app.get("/review/<sid>")
def review(sid, error=None):
    d, it, meta = load(sid)
    lang = meta["lang"]
    s, k = S[lang], it["counts"]
    kpis = [(s["reqs"], k["requirements"]), (s["auto"], k["automated"]), (s["doc"], k["document"]),
            (s["itw"], k["interview"]), (s["rej"], k["rejected"]), (s["ctrls"], k["controls"])]
    return render(REVIEW, lang, sid=sid, it=it, kpis=kpis, sevs=SEVS, error=error,
                  target_label=targets.TARGETS[meta["target"]]["label"][lang],
                  remediable=targets.TARGETS[meta["target"]]["remediable"])


def build_mission(sid: str, meta: dict, reviewer: str):
    base = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
    t = targets.get(meta["target"])
    titles = [title for title, _ in meta["texts"]]
    short = " · ".join(x.split(" — ")[0] for x in titles)
    code, en = t["kind"] == "code", meta["lang"] == "en"
    if code and en:
        scope_in = ["Source code, configuration and CI pipeline of the repository", "Versioned test datasets"]
        scope_out = ["Dynamic testing (DAST) and penetration testing", "Runtime and production environments",
                     "Git history"]
    elif code:
        scope_in = ["Code source, configuration et chaîne CI du dépôt", "Jeux de données de test versionnés"]
        scope_out = ["Tests dynamiques (DAST) et tests d'intrusion", "Environnements d'exécution et de production",
                     "Historique git"]
    else:
        scope_in, scope_out = base.scope_in, base.scope_out
    system = targets.text(meta["target"], "system", meta["lang"])
    return dataclasses.replace(
        base, id=f"AUD-{sid[:8]}-{sid[-4:].upper()}", title=f"{system} — {short}", system=system,
        target=meta["target"], framework_label=" · ".join(titles), lead_auditor=reviewer,
        owner=targets.text(meta["target"], "owner", meta["lang"]),
        requirement_text="\n\n".join(body for _, body in meta["texts"]), scope_in=scope_in, scope_out=scope_out)


def job(sid: str, mission, controls, cat_meta, it, remediate: bool, approver: str, lang: str):
    from . import pipeline
    JOBS[sid] = {"state": "running"}                   # déjà posé sous verrou par run() ; appel direct possible
    os.environ["ATTEST_LANG"] = lang
    try:
        pipeline.run(mission, WORK / sid / "audit", controls=controls, catalogue_meta=cat_meta, run_id=sid,
                     interpretation=it, remediate=remediate, approve_all=remediate, approver=approver)
        JOBS[sid] = {"state": "done"}
    except SystemExit as ex:
        JOBS[sid] = {"state": "error", "message": str(ex)}
    except Exception as ex:
        traceback.print_exc()
        JOBS[sid] = {"state": "error", "message": f"{type(ex).__name__}: {ex}"}


@app.post("/run/<sid>")
def run(sid):
    d, it, meta = load(sid)
    lang = meta["lang"]
    reviewer = request.form.get("reviewer", "").strip()
    approver = request.form.get("approver", "").strip()
    if not reviewer:
        return review(sid, error=S[lang]["noreviewer"])
    remediate = bool(request.form.get("remediate")) and targets.TARGETS[meta["target"]]["remediable"]
    if remediate and approver.lower() == reviewer.lower():
        return review(sid, error=S[lang]["sod"])
    chosen = set(request.form.getlist("ctrl"))
    controls = []
    for r in it["requirements"]:
        for c in r["controls"]:
            if c["id"] in chosen and r["quote_verified"]:
                sev = request.form.get(f"sev_{c['id']}", c.get("severity"))
                controls.append(dict(c, severity=sev if sev in SEVS else c.get("severity", "moyenne")))
    if not controls:
        return review(sid, error=S[lang]["noctrl"])
    # Double clic sur « Lancer l'audit » ou audit déjà fait : pas de second pipeline sur le même dossier.
    with RUN_LOCK:
        if sid in JOBS or (d / "audit").exists():
            return redirect(f"/audit/{sid}")
        JOBS[sid] = {"state": "running"}
    try:
        cat_meta = {"source": "studio", "reviewed": True, "reviewer": reviewer,
                    "path": f"runs/studio/{sid}/catalogue.json", "validated_at": time.strftime("%Y-%m-%d %H:%M")}
        (d / "catalogue.json").write_text(json.dumps({**cat_meta, "controls": controls}, ensure_ascii=False, indent=2))
        os.environ["ATTEST_LANG"] = lang
        mission = build_mission(sid, meta, reviewer)
        threading.Thread(target=job, args=(sid, mission, controls, cat_meta, it, remediate, approver, lang),
                         daemon=True).start()
    except Exception:
        JOBS.pop(sid, None)
        raise
    return redirect(f"/audit/{sid}")


@app.get("/audit/<sid>")
def audit(sid):
    d, it, meta = load(sid)
    return render(AUDIT, meta["lang"], sid=sid)


@app.get("/status/<sid>")
def status(sid):
    d = WORK / sid / "audit"
    j = JOBS.get(sid, {"state": "done" if (d / "report.pdf").exists() else "unknown"})
    return jsonify(**j, report=(d / "report.html").exists(), pdf=(d / "report.pdf").exists())


@app.get("/files/<sid>/<path:path>")
def files(sid, path):
    load(sid)
    return send_from_directory(WORK / sid, path)


if __name__ == "__main__":
    port = int(os.getenv("STUDIO_PORT", "8000"))
    print(f"Attest Studio : http://127.0.0.1:{port}  (la console auditée doit tourner : python -m lab.app)")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
