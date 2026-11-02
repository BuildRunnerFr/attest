"""Rapport d'audit HTML. Pendant l'exécution, la page se recharge seule : c'est l'écran de démo."""
import html
import json
from pathlib import Path

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#17191d;--mute:#6b6f78;--line:#e4e2dc;--ko:#c0261c;--ok:#16803c;--warn:#a15c00}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 20px 64px}
h1{font:600 28px/1.2 ui-serif,Georgia,serif;margin:0}
.sub{color:var(--mute);margin:6px 0 24px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:28px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font:600 28px/1.1 ui-serif,Georgia,serif}.kpi span{color:var(--mute);font-size:13px}
details.req{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:24px}
details.req pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace;color:#333}
.c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:18px}
.hd{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.tag{font:600 12px ui-monospace,Menlo,monospace;background:#efede7;border-radius:6px;padding:3px 8px}
.t{font-weight:600;font-size:17px;flex:1;min-width:200px}
.st{font-weight:600;font-size:12px;letter-spacing:.04em;text-transform:uppercase;border-radius:999px;padding:4px 10px;color:#fff}
.st.fail{background:var(--ko)}.st.pass{background:var(--ok)}.st.error{background:var(--warn)}
.arrow{color:var(--mute)}
.obj{color:var(--mute);margin:8px 0 14px}
.ev{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
figure{margin:0}figure img{width:100%;border:1px solid var(--line);border-radius:8px;display:block}
figcaption{font-size:13px;color:var(--mute);margin-top:6px}
.fix{margin-top:14px;font-size:14px;background:#f3f7f4;border-left:3px solid var(--ok);padding:10px 12px;border-radius:0 8px 8px 0}
.fix code{font:12.5px ui-monospace,Menlo,monospace}
details.code{margin-top:12px}details.code summary{cursor:pointer;color:var(--mute);font-size:13px}
details.code pre{background:#1d1f24;color:#e6e6e6;padding:12px;border-radius:8px;overflow:auto;font:12.5px/1.5 ui-monospace,Menlo,monospace}
.live{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--ko);margin-right:6px;animation:p 1s infinite}
@keyframes p{50%{opacity:.25}}
"""


def _st(s):
    return f'<span class="st {s}">{ {"pass": "conforme", "fail": "non conforme", "error": "erreur"}.get(s, s)}</span>'


def _fig(ev, label):
    if not ev:
        return ""
    i = ev["inspection"]
    m = ev["metrics"]
    pii = f" · données personnelles floutées : {m['pii_redacted']}/{m['pii_total']}" if m["pii_total"] else ""
    ok = "corrobore" if i.get("corroborates") else "NE corrobore PAS"
    return (f'<figure><img src="{ev["image"]}" alt="preuve {label}"><figcaption><b>{label}</b> — '
            f'la capture {ok} le résultat. {html.escape(i.get("comment", ""))}{pii}</figcaption></figure>')


def write(state: dict, out: Path):
    cs = state["controls"]
    before_fail = sum(e.get("before", {}).get("status") == "fail" for e in cs)
    final_pass = sum((e.get("after") or e.get("before") or {}).get("status") == "pass" for e in cs)
    pii_t = sum(e.get(k, {}).get("metrics", {}).get("pii_total", 0) for e in cs for k in ("evidence_before", "evidence_after"))
    pii_r = sum(e.get(k, {}).get("metrics", {}).get("pii_redacted", 0) for e in cs for k in ("evidence_before", "evidence_after"))

    cards = []
    for e in cs:
        c = e["control"]
        b = e.get("before", {}).get("status", "…")
        a = e.get("after", {}).get("status")
        status = _st(b) + (f' <span class="arrow">→</span> {_st(a)}' if a else "")
        fix = ""
        if e.get("remediation"):
            r = e["remediation"]
            fix = (f'<div class="fix"><b>Correctif {"appliqué" if r["applied"] else "non appliqué"}</b> : '
                   f'<code>{html.escape(r["fix"].get("method", ""))} {html.escape(r["fix"].get("path", ""))} '
                   f'{html.escape(json.dumps(r["fix"].get("body", {}), ensure_ascii=False))}</code><br>'
                   f'{html.escape(r["fix"].get("rationale", ""))} {html.escape(r.get("reason", ""))}</div>')
        obs = e.get("before", {})
        cards.append(f"""<section class="c"><div class="hd"><span class="tag">{html.escape(c['rule'])}</span>
<span class="t">{html.escape(c['title'])}</span>{status}</div>
<p class="obj">{html.escape(c['objective'])}<br><b>Constaté</b> : <code>{html.escape(json.dumps(obs.get('observed', obs.get('detail', '')), ensure_ascii=False))}</code>
 · <b>Attendu</b> : <code>{html.escape(str(obs.get('expected', c.get('expected', ''))))}</code></p>
<div class="ev">{_fig(e.get('evidence_before'), 'Avant')}{_fig(e.get('evidence_after'), 'Après correctif')}</div>{fix}
<details class="code"><summary>Script de contrôle écrit par l'agent</summary><pre>{html.escape(e.get('code', ''))}</pre></details></section>""")

    live = '<span class="live"></span>Audit en cours · ' if state.get("running") else ""
    refresh = '<meta http-equiv="refresh" content="2">' if state.get("running") else ""
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{refresh}<title>Rapport d'audit Attest</title><style>{CSS}</style></head><body><main>
<h1>Rapport d'audit — authentification forte</h1>
<p class="sub">{live}Banque Kerlann (fictive) · {state['started']} · modèles : {html.escape(state['backend'])}</p>
<div class="kpis">
<div class="kpi"><b>{len(cs)}</b><span>contrôles exécutés</span></div>
<div class="kpi"><b style="color:var(--ko)">{before_fail}</b><span>non conformités constatées</span></div>
<div class="kpi"><b style="color:var(--ok)">{final_pass}/{len(cs)}</b><span>conformes après remédiation</span></div>
<div class="kpi"><b>{pii_r}/{pii_t}</b><span>données personnelles floutées dans les preuves</span></div>
</div>
<details class="req"><summary>Exigence auditée</summary><pre>{html.escape(state['requirement'])}</pre></details>
{''.join(cards)}</main></body></html>"""
    (out / "report.html").write_text(page)
