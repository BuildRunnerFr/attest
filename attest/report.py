"""Rapport d'audit (HTML + PDF). Pendant l'exécution, la page se recharge seule : c'est l'écran de démo.

Structure d'un rapport d'audit bancaire : synthèse pour la direction, périmètre et méthode, tableau
des constats, constats détaillés (critère / constat / risque / recommandation), annexes de traçabilité.
"""
import html
import json
import re
from pathlib import Path

from . import config
from .i18n import t

CSS = """
:root{--ink:#14171c;--mute:#5d6470;--line:#dfe2e7;--paper:#fff;--bg:#eef0f3;--navy:#0f2747;
--crit:#8a1c1c;--high:#c2410c;--med:#a16207;--low:#4b5563;--ok:#166534;--ko:#b91c1c;--rev:#a16207}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.doc{max-width:1060px;margin:0 auto;background:var(--paper);box-shadow:0 1px 4px #0001}
.band{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;background:var(--navy);color:#dbe3ef;
 padding:8px 40px;font-size:12px;letter-spacing:.03em}
.band b{color:#fff}
.cover{padding:40px 40px 28px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mute);margin:0 0 10px}
h1{font:600 30px/1.2 Georgia,"Times New Roman",serif;margin:0 0 6px}
.cover .sys{color:var(--mute);margin:0 0 22px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:4px 24px;font-size:13px;color:var(--mute)}
.meta b{color:var(--ink);font-weight:600}
section{padding:30px 40px;border-bottom:1px solid var(--line)}
h2{font:600 21px/1.25 Georgia,"Times New Roman",serif;margin:0 0 18px;color:var(--navy)}
h3{font-size:15px;margin:22px 0 10px}
.ops{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:18px}
.op{border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.op span{display:block;font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
.op b{display:inline-block;margin-top:6px;font:600 20px/1.2 Georgia,serif}
.op.insuffisant b{color:var(--crit)}.op.reserve b{color:var(--med)}.op.ameliorer b{color:var(--high)}.op.globalement b{color:var(--med)}.op.satisfaisant b{color:var(--ok)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:20px}
.kpi{background:#f6f7f9;border-radius:8px;padding:12px 14px}
.kpi b{display:block;font:600 24px/1.1 Georgia,serif}.kpi span{font-size:12.5px;color:var(--mute)}
.dist{display:flex;height:10px;border-radius:5px;overflow:hidden;background:#e5e7eb;margin:6px 0 4px}
.dist i{display:block}.legend{font-size:12px;color:var(--mute);display:flex;gap:14px;flex-wrap:wrap}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
ul.msgs{margin:6px 0 0;padding-left:20px}ul.msgs li{margin:4px 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);
 border-bottom:2px solid var(--line);padding:8px 8px}
td{border-bottom:1px solid var(--line);padding:8px;vertical-align:top}
.tbl{overflow-x:auto}
.pill{display:inline-block;font-size:11.5px;font-weight:600;border-radius:999px;padding:2px 9px;white-space:nowrap;color:#fff}
.sev-critique{background:var(--crit)}.sev-elevee{background:var(--high)}.sev-moyenne{background:var(--med)}.sev-faible{background:var(--low)}
.st-pass{background:var(--ok)}.st-fail{background:var(--ko)}.st-review,.st-error{background:var(--rev)}.st-wait{background:#9ca3af}
.fs{font-size:12px;font-weight:600;white-space:nowrap}.fs-closed{color:var(--ok)}.fs-open,.fs-rejected{color:var(--ko)}
.fs-action_plan,.fs-pending{color:var(--med)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:6px 28px}
dl.kv{display:grid;grid-template-columns:170px 1fr;gap:6px 14px;margin:0;font-size:13.5px}
dl.kv dt{color:var(--mute)}dl.kv dd{margin:0}
.card{border:1px solid var(--line);border-radius:12px;margin:0 0 20px;overflow:hidden;break-inside:avoid-page}
.card .hd{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 16px;background:#f7f8fa;border-bottom:1px solid var(--line)}
.card .ref{font:600 12px ui-monospace,Menlo,monospace;color:var(--navy)}
.card .ti{font-weight:600;flex:1;min-width:220px}
.card .bd{padding:16px}
.c4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 22px;margin-bottom:14px}
.c4 h4{margin:0 0 4px;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.c4 p{margin:0}
code,.mono{font:12.5px ui-monospace,Menlo,monospace}
.obs{background:#f6f7f9;border-radius:6px;padding:2px 6px}
.ev{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
figure{margin:0}figure img{width:100%;border:1px solid var(--line);border-radius:8px;display:block}
figcaption{font-size:12px;color:var(--mute);margin-top:6px}
.chg{margin-top:14px;border-left:3px solid var(--navy);background:#f4f6fa;border-radius:0 8px 8px 0;padding:10px 14px;font-size:13px}
.chg.manual{border-color:var(--med);background:#fdf8ec}
.chg ol{margin:6px 0 0;padding-left:18px}
details{margin-top:12px}summary{cursor:pointer;color:var(--mute);font-size:12.5px}
details pre{background:#16191f;color:#e5e7eb;padding:12px;border-radius:8px;overflow:auto;font:12px/1.5 ui-monospace,Menlo,monospace}
.compact .bd{padding:12px 16px}
blockquote{margin:8px 0 0;padding:6px 10px;border-left:3px solid var(--line);color:var(--mute);font-size:12.5px;font-style:italic}
.tb{display:inline-block;font-size:11px;font-weight:600;border-radius:4px;padding:1px 7px;background:#eef1f5;color:var(--navy)}
.tb.document,.tb.interview{background:#fdf3e1;color:#8a5a00}.tb.rejected{background:#fde8e8;color:var(--ko)}
.small{font-size:12.5px;color:var(--mute)}
.hash{font:11.5px ui-monospace,Menlo,monospace;color:var(--mute);word-break:break-all}
.alert.abort{border-color:#e5a3a3;background:#fdecec;color:var(--ko);font-weight:600}
.alert{border:1px solid #f1c27d;background:#fff8eb;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:13.5px}
.live{display:inline-block;width:8px;height:8px;border-radius:50%;background:#ef4444;margin-right:6px;animation:p 1s infinite}
@keyframes p{50%{opacity:.25}}
footer{padding:16px 40px;font-size:12px;color:var(--mute);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
@media screen and (max-width:720px){.band,.cover,section,footer{padding-left:16px;padding-right:16px}
 .two,.c4,.ev{grid-template-columns:1fr}dl.kv{grid-template-columns:1fr}h1{font-size:24px}
 .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media print{body{background:#fff;font-size:11px}.doc{box-shadow:none;max-width:none}.band{display:none}
 section{padding:14px 0;border:0}.cover{padding:0 0 14px}footer{display:none}h1{font-size:24px}
 h2{font-size:17px;break-after:avoid}.kpi b{font-size:18px}.card{break-inside:auto}figure{break-inside:avoid}
 #annexes{break-before:page}details{display:none}.live{display:none}figcaption{font-size:10px}
 table{font-size:10.5px}.pill{font-size:9.5px}}
"""


def colon() -> str:
    return " : " if config.lang() == "fr" else ": "


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def pill_sev(s):
    return f'<span class="pill sev-{e(s)}">{e(t("sev." + s))}</span>'


def pill_st(s):
    if not s:
        return '<span class="pill st-wait">…</span>'
    return f'<span class="pill st-{e(s)}">{e(t("st." + s))}</span>'


def fstatus(f):
    return f'<span class="fs fs-{e(f["status"])}">{e(t("fs." + f["status"]))}</span>' if f else ""


_EMAIL = re.compile(r"([A-Za-z0-9])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}\b")
_IBAN = re.compile(r"\b([A-Z]{2}\d{2})(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")


_SECRET = re.compile(r"(?i)((?:password|passwd|secret|api_key|token)\w*\s*=\s*\\?[\"'])([^\"'\\]{4,})(\\?[\"'])")


def redact(s: str) -> str:
    """Pseudonymise les données personnelles dans le texte distribué (la piste d'audit, à accès
    restreint, conserve les valeurs brutes pour leur valeur probante)."""
    s = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)[:2]}••••{m.group(3)}", s)
    s = _EMAIL.sub(lambda m: f"{m.group(1)}•••@{m.group(2)}", s)
    s = _IPV4.sub(lambda m: f"{m.group(1)}.{m.group(2)}.•.•", s)
    return _IBAN.sub(lambda m: f"{m.group(1)} •••• ••••", s)


def compact(v, n=160):
    s = redact(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
    return s if len(s) <= n else s[:n] + "…"


def figure(ev, label):
    if not ev:
        return ""
    i, m = ev["inspection"], ev["metrics"]
    corro = t("f.corro_yes") if i.get("corroborates") is not False else t("f.corro_no")
    pii = ""
    if m.get("pii_total"):
        pii = f" · {m['pii_masked']}/{m['pii_total']} {t('f.pii')}"
        if m.get("pii_found_by_model", m["pii_total"]) < m["pii_total"]:
            pii += f" ({t('f.pii_model').format(n=m['pii_found_by_model'])})"
    return (f'<figure><a href="{e(ev["image"])}" target="_blank"><img src="{e(ev["image"])}" alt="{e(label)}"></a><figcaption><b>{e(label)}</b> — {e(corro)} '
            f'{e(redact(i.get("comment", "")))}{e(pii)}<br><span class="hash">{e(ev["ts"])} · SHA-256 {e(ev["sha256"][:16])}…</span>'
            f'</figcaption></figure>')


def change_box(en):
    ch = en.get("change")
    if not ch:
        return ""
    if ch["type"] == "manual":
        steps = "".join(f"<li>{e(a)}</li>" for a in ch.get("actions", []))
        return (f'<div class="chg manual"><b>{e(t("f.manual"))}</b> · {e(ch["ticket"])}<br>{e(ch.get("rationale", ""))}'
                f'<ol>{steps}</ol></div>')
    body = f'{e(ch["method"])} {e(ch["path"])} {e(json.dumps(ch["body"], ensure_ascii=False))}'
    lines = [f'<b>{e(t("f.change"))} {e(ch["ticket"])}</b> · <code>{body}</code>',
             e(ch.get("rationale", ""))]
    if ch.get("impact"):
        lines.append(f'{e(t("f.impact"))}{colon()}{e(ch["impact"])}')
    if ch.get("guard_refusal"):
        lines.append(f'⚠ {e(ch["guard_refusal"])}')
    if ch.get("approved_by"):
        lines.append(f'{e(t("f.approved"))}{colon()}<b>{e(ch["approved_by"])}</b> · {e(ch.get("approved_at", ""))} · '
                     + (f'{e(t("mode." + ch["mode"]))} · ' if ch.get("mode", "interactive") != "interactive" else "")
                     + f'{e(t("f.applied") if ch.get("applied") else t("f.notapplied"))}')
    j = ch.get("journal")
    if j:
        lines.append(f'{e(t("f.journal"))}{colon()}{e(j["ts"])} · {e(j["actor"])} · {e("; ".join(j["changes"]))}')
    return '<div class="chg">' + "<br>".join(lines) + "</div>"


def card(en):
    c, f = en["control"], en.get("finding")
    before = en.get("before") or {}
    test = en.get("test") or {}
    origin = t("f.origin." + test.get("origin", "generated")) if test else ""
    script = (f'<details><summary>{e(t("f.script"))} · {e(origin)} · SHA-256 {e(test.get("sha256", "")[:16])}…'
              f'</summary><pre>{e(test.get("code", ""))}</pre></details>') if test else ""
    refs = ", ".join(c.get("references", []))
    head = (f'<div class="hd">{"<span class=ref>" + e(f["id"]) + "</span>" if f else ""}'
            f'<span class="ref">{e(c["rule"])}</span><span class="ti">{e(c["title"])}</span>'
            f'{pill_sev(c["severity"])} {pill_st(en.get("status_before"))}'
            f'{" → " + pill_st(en.get("status_after")) if en.get("status_after") else ""} {fstatus(f)}</div>')

    if not f and en.get("status_before") == "pass":       # contrôle conforme : version compacte
        return (f'<div class="card compact">{head}<div class="bd"><p class="small">{e(t("f.compliant"))} — '
                f'{e(c["objective"])} · {e(refs)}<br>{e(t("f.observed"))}{colon()}<code class="obs">'
                f'{e(compact(before.get("observed", "")))}</code></p>'
                f'<div class="ev">{figure(en.get("evidence_before"), t("f.before"))}</div>{script}</div></div>')

    detail = redact(str(before.get("detail", "")))
    quote = (f'<blockquote>« {e(c["quote"])} »</blockquote>' if c.get("quote") else "")
    source = (f'<br><span class="small">{e(t("f.threshold"))}{colon()}{e(c["threshold_source"])}</span>'
              if c.get("threshold_source") else "")
    return (f'<div class="card">{head}<div class="bd"><div class="c4">'
            f'<div><h4>{e(t("f.criteria"))}</h4><p>{e(c["objective"])}<br><span class="small">{e(c["rule"])} · {e(refs)}</span>{source}</p>{quote}</div>'
            f'<div><h4>{e(t("f.condition"))}</h4><p>{e(t("f.observed"))}{colon()}<code class="obs">{e(compact(before.get("observed", "")))}</code><br>'
            f'{e(t("f.expected"))}{colon()}<code class="obs">{e(compact(before.get("expected", c.get("expected", ""))))}</code><br>'
            f'<span class="small">{e(detail)}</span></p></div>'
            f'<div><h4>{e(t("f.risk"))}</h4><p>{e(c.get("risk", ""))}</p></div>'
            f'<div><h4>{e(t("f.reco"))}</h4><p>{e(c.get("recommendation", ""))}'
            + (f'<br><span class="small">{e(t("t.due"))}{colon()}{e(f["due"])} · {e(t("t.owner"))}{colon()}{e(f["owner"])}</span>' if f else "")
            + f'</p></div></div>'
            f'<p class="small">{e(t("f.test"))}{colon()}{e(c.get("test_procedure", ""))}</p>'
            f'<div class="ev">{figure(en.get("evidence_before"), t("f.before"))}{figure(en.get("evidence_after"), t("f.after"))}</div>'
            + "".join(f'<div class="alert">⚠ {e(t("f.noevidence"))}{colon()}{e(en[k])}</div>'
                      for k in ("evidence_error", "evidence_error_after") if en.get(k))
            + f'{change_box(en)}{script}</div></div>')


def money(x: float, lang: str) -> str:
    return f"{x:,.3f} $".replace(",", " ").replace(".", ",") if lang == "fr" else f"${x:,.3f}"


def key_messages(lang, total, n, sev, closed, still_open, review) -> list:
    """Messages clés déterministes (aucune phrase de synthèse n'est générée par le modèle)."""
    def pl(k, one, many):
        return one if k == 1 else many
    if lang == "fr":
        adj = {"critique": ("critique", "critiques"), "elevee": ("élevé", "élevés"),
               "moyenne": ("moyen", "moyens"), "faible": ("faible", "faibles")}
        parts = [f"{sev[s]} {pl(sev[s], *adj[s])}" for s in adj if sev[s]]
        out = [f"{n} {pl(n, 'constat', 'constats')} sur {total} contrôles : {', '.join(parts)}." if n
               else "Aucun constat : tous les contrôles testés sont conformes."]
        if closed:
            out.append(f"{closed} {pl(closed, 'constat corrigé', 'constats corrigés')} via le processus de changement, "
                       f"puis {pl(closed, 'vérifié', 'vérifiés')} par un nouveau test.")
        if still_open:
            out.append(f"{still_open} {pl(still_open, 'constat reste ouvert', 'constats restent ouverts')}, "
                       "avec un plan d'action, un porteur et une échéance.")
        if review:
            out.append(f"{review} {pl(review, 'contrôle', 'contrôles')} à revoir : le test et la preuve visuelle ne concordent pas.")
        return out
    adj = {"critique": "critical", "elevee": "high", "moyenne": "medium", "faible": "low"}
    parts = [f"{sev[s]} {adj[s]}" for s in adj if sev[s]]
    out = [f"{n} {pl(n, 'finding', 'findings')} across {total} controls: {', '.join(parts)}." if n
           else "No findings: every tested control is compliant."]
    if closed:
        out.append(f"{closed} {pl(closed, 'finding', 'findings')} fixed through change management, then verified by re-testing.")
    if still_open:
        out.append(f"{still_open} {pl(still_open, 'finding remains', 'findings remain')} open, with an action plan, an owner and a due date.")
    if review:
        out.append(f"{review} {pl(review, 'control needs', 'controls need')} review: the test and the visual evidence disagree.")
    return out


def coverage(state: dict) -> str:
    """Annexe : ce que l'interprétation du référentiel a retenu, et surtout ce qu'Attest N'A PAS testé."""
    it = state.get("interpretation")
    if not it:
        return ""
    k = it["counts"]
    rows = "".join(
        f'<tr><td class="mono">{e(r["ref"])}</td><td>« {e(r["quote"][:220])} »</td>'
        f'<td><span class="tb {"rejected" if not r["quote_verified"] else r["testability"]}">'
        f'{e(t("cov.rejected") if not r["quote_verified"] else t("cov." + r["testability"]))}</span></td>'
        f'<td>{len(r["controls"]) or ("→ " + ", ".join(r.get("covered_by") or []) if r.get("covered_by") else 0)}</td>'
        f'<td class="small">{e(r["why"])}</td></tr>' for r in it["requirements"])
    summary = t("cov.summary").format(n=k["requirements"], a=k["automated"], d=k["document"], i=k["interview"],
                                      r=k["rejected"], c=k["controls"], v=k.get("covered", 0))
    return (f'<h3>{e(t("a.coverage"))}</h3><p class="small">{e(summary)}</p><div class="tbl"><table><tr>'
            f'<th>{e(t("t.id"))}</th><th>{e(t("cov.quote"))}</th><th>{e(t("cov.test"))}</th><th>{e(t("a.control"))}</th>'
            f'<th></th></tr>{rows}</table></div>')


def write(state: dict, out: Path):
    m = state["mission"]
    entries = state.get("entries", [])
    findings = [x for x in entries if x.get("finding")]
    closed = [x for x in findings if x["finding"]["status"] == "closed"]
    still_open = [x for x in findings if x["finding"]["status"] != "closed"]
    review = [x for x in entries if x.get("status_before") == "review"]
    errors = [x for x in entries if x.get("status_before") == "error"]     # non concluants : jamais conformes
    sev_count = {s: sum(1 for x in findings if x["finding"]["severity"] == s)
                 for s in ("critique", "elevee", "moyenne", "faible")}
    pii = sum((x.get(k) or {}).get("metrics", {}).get("pii_masked", 0)
              for x in entries for k in ("evidence_before", "evidence_after"))
    usage = state.get("usage", {"rows": [], "total_usd": 0, "unpriced": [], "estimated": True})
    cost = money(usage["total_usd"], state.get("lang", "fr")) + (" *" if usage.get("estimated") or usage.get("unpriced") else "")
    running = state.get("running")
    dur = state.get("duration_s", 0)

    # ---- 1. synthèse
    ops = f'<div class="op {e(state.get("opinion_initial", ""))}"><span>{e(t("opinion.initial"))}</span><b>{e(t("op." + state["opinion_initial"])) if state.get("opinion_initial") else "…"}</b></div>'
    if state.get("remediation_requested") and not running and state.get("opinion_final"):
        ops += f'<div class="op {e(state.get("opinion_final", ""))}"><span>{e(t("opinion.final"))}</span><b>{e(t("op." + state["opinion_final"]))}</b></div>'
    # seule une approbation interactive est une approbation humaine ; la pré-approbation de démo est signalée à part
    approvals = sum(1 for d in state.get("decisions", []) if d["approved"] and d.get("mode") == "interactive")
    pre = sum(1 for d in state.get("decisions", []) if d["approved"] and d.get("mode") == "pre-approved")
    pre_txt = f' · {pre} {t("k.preapproved")}' if pre else ""
    kpis = "".join(f'<div class="kpi"><b>{v}</b><span>{e(t(k))}{e(pre_txt) if k == "k.approvals" else ""}</span></div>' for k, v in [
        ("k.controls", len(entries)), ("k.findings", len(findings)), ("k.closed", len(closed)),
        ("k.open", len(still_open)), ("k.approvals", approvals), ("k.pii", pii),
        ("k.duration", f"{dur // 60} min {dur % 60:02d} s"), ("k.cost", e(cost))])
    colors = {"critique": "var(--crit)", "elevee": "var(--high)", "moyenne": "var(--med)", "faible": "var(--low)"}
    total = max(1, len(findings))
    dist = "".join(f'<i style="width:{100 * n / total:.1f}%;background:{colors[s]}"></i>' for s, n in sev_count.items() if n)
    legend = "".join(f'<span><i style="background:{colors[s]}"></i>{e(t("sev." + s))}{colon()}{n}</span>' for s, n in sev_count.items())
    msgs = key_messages(state.get("lang", "fr"), len(entries), len(findings), sev_count, len(closed),
                        len(still_open), len(review)) if entries and not running and not state.get("aborted") else []
    if errors and not running:
        msgs.append(t("msg.error").format(n=len(errors)))
    no_ev = sum(1 for x in entries if x.get("evidence_error"))
    if no_ev and not running:
        msgs.append(t("msg.noevidence").format(n=no_ev))
    inj = f'<div class="alert">⚠ {e(t("msg.injection"))}</div>' if state.get("injection_detected") else ""
    if state.get("aborted"):                      # échec visible : le rapport partiel ne vaut pas opinion
        inj = f'<div class="alert abort">⛔ {e(t("aborted"))}<br><span class="mono">{e(redact(state["aborted"]))}</span></div>' + inj
    s1 = (f'<section id="s1"><h2>{e(t("s1"))}</h2><div class="ops">{ops}</div><div class="kpis">{kpis}</div>'
          + (f'<div class="dist">{dist}</div><div class="legend">{legend}</div>' if findings else "")
          + inj + (f'<h3>{e(t("msg.title"))}</h3><ul class="msgs">' + "".join(f"<li>{e(x)}</li>" for x in msgs) + "</ul>" if msgs else "")
          + "</section>")

    # ---- 2. périmètre et méthode
    cat = state.get("catalogue", {})
    cat_txt = ((t("cat.reviewed") + (f" ({cat['reviewer']})" if cat.get("reviewer") else "")) if cat.get("reviewed")
               else t("cat.planned") if cat.get("source") == "planned" else t("cat.reused")) \
        + (f" · {cat.get('path', '')}" if cat else "")
    kv = [("m.mission", m["id"]), ("m.entity", m["entity"]), ("m.system", m["system"]),
          ("m.crit", m["system_criticality"]), ("m.env", m["environment"]), ("m.owner", m["owner"]),
          ("m.auditor", m["lead_auditor"]), ("m.date", state["started"]),
          ("m.framework", m.get("framework_label") or "DORA art. 9(4) · RTS (UE) 2024/1774 art. 12, 21 · PSI-4"),
          ("m.target", state.get("target_label", "")), ("m.catalogue", cat_txt)]
    s2 = (f'<section id="s2"><h2>{e(t("s2"))}</h2><dl class="kv">'
          + "".join(f"<dt>{e(t(k))}</dt><dd>{e(v)}</dd>" for k, v in kv) + "</dl>"
          f'<div class="two"><div><h3>{e(t("m.in"))}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in m["scope_in"]) + "</ul></div>"
          f'<div><h3>{e(t("m.out"))}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in m["scope_out"]) + "</ul></div></div>"
          f'<h3>{e(t("method.title"))}</h3><ol>' + "".join(f"<li>{e(x)}</li>" for x in t("method")) + "</ol>"
          f'<h3>{e(t("limits.title"))}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in t("limits")) + "</ul></section>")

    # ---- 3. tableau des constats
    rows = []
    for x in sorted(entries, key=lambda x: (x.get("finding") is None, (x.get("finding") or {}).get("id", ""), x["control"]["id"])):
        c, f = x["control"], x.get("finding")
        rows.append(f'<tr><td class="mono">{e(f["id"]) if f else "—"}</td><td class="mono">{e(c["rule"])}</td>'
                    f'<td>{e(c["title"])}</td><td>{pill_sev(c["severity"])}</td><td>{pill_st(x.get("status_before"))}</td>'
                    f'<td>{pill_st(x.get("status_after")) if x.get("status_after") else ""}</td><td>{fstatus(f)}</td>'
                    f'<td class="mono">{e(f["due"]) if f else ""}</td></tr>')
    s3 = (f'<section id="s3"><h2>{e(t("s3"))}</h2><div class="tbl"><table><tr><th>{e(t("t.id"))}</th><th>{e(t("t.rule"))}</th>'
          f'<th>{e(t("t.title"))}</th><th>{e(t("t.sev"))}</th><th>{e(t("t.before"))}</th><th>{e(t("t.after"))}</th>'
          f'<th>{e(t("t.status"))}</th><th>{e(t("t.due"))}</th></tr>' + "".join(rows) + "</table></div></section>")

    # ---- 4. détail
    ordered = sorted(entries, key=lambda x: (x.get("finding") is None, (x.get("finding") or {}).get("id", ""), x["control"]["id"]))
    s4 = f'<section id="s4"><h2>{e(t("s4"))}</h2>' + "".join(card(x) for x in ordered) + "</section>"

    # ---- annexes
    trace = "".join(
        f'<tr><td>{e(", ".join(x["control"].get("references", [])))}</td><td class="mono">{e(x["control"]["rule"])}</td>'
        f'<td>{e(x["control"]["id"])} · {e(x["control"]["title"])}</td>'
        f'<td class="hash">{e((x.get("test") or {}).get("sha256", "")[:16])} · {e(t("f.origin." + (x.get("test") or {}).get("origin", "generated")))}</td>'
        f'<td>{pill_st(x.get("status_before"))} {("→ " + pill_st(x.get("status_after"))) if x.get("status_after") else ""}</td></tr>'
        for x in entries)
    evid = []
    for x in entries:
        for k, lab in (("evidence_before", t("f.before")), ("evidence_after", t("f.after"))):
            ev = x.get(k)
            if ev:
                evid.append(f'<tr><td class="mono">{e(ev["image"])}</td><td>{e(x["control"]["id"])} · {e(lab)}</td>'
                            f'<td>{e(ev["ts"])}</td><td class="hash">{e(ev["sha256"])}</td></tr>')
    je = state.get("journal_evidence")
    if je:
        evid.append(f'<tr><td class="mono">{e(je["image"])}</td><td>{e(t("f.journal"))}</td><td></td><td class="hash">{e(je["sha256"])}</td></tr>')
    urows = "".join(
        f'<tr><td class="mono">{e(r["model"])}</td><td>{r["calls"]}</td><td>{r["input"]:,}</td><td>{r["output"]:,}</td>'
        f'<td>{r["images"]}</td><td>{("%.4f" % r["cost_usd"]) if r["cost_usd"] is not None else e(t("a.unpriced"))}</td></tr>'
        for r in usage["rows"])
    urows += f'<tr><td><b>{e(t("a.total"))}</b></td><td></td><td></td><td></td><td></td><td><b>{usage["total_usd"]:.4f}</b></td></tr>'
    dec = "".join(f'<tr><td class="mono">{e(d["ticket"])}</td><td>{e(d["finding"])}</td><td>{"✔" if d["approved"] else "✘"}</td>'
                  f'<td>{e(d["approver"])}</td><td>{e(t("mode." + d["mode"]))}</td><td>{e(d["ts"])}</td></tr>' for d in state.get("decisions", []))
    journal = ""
    if je:
        journal = (f'<h3>{e(t("a.journal"))}</h3><figure><img src="{e(je["image"])}" alt="journal"><figcaption class="hash">'
                   f'SHA-256 {e(je["sha256"])}</figcaption></figure>')
    evs = [x.get(k) for x in entries for k in ("evidence_before", "evidence_after") if x.get(k)]
    p_tot = sum(v["metrics"].get("pii_total", 0) for v in evs)
    p_mod = sum(v["metrics"].get("pii_found_by_model", v["metrics"].get("pii_masked", 0)) for v in evs)
    p_fin = sum(v["metrics"].get("pii_masked", 0) for v in evs)
    pii_line = f'<p class="small">{e(t("a.pii_line").format(f=p_mod, t=p_tot, m=p_fin))}</p>' if p_tot else ""
    note = pii_line + (f'<p class="small">* {e(t("a.estimated"))}</p>' if usage.get("estimated") else "")
    if usage.get("unpriced"):
        note += f'<p class="small">* {e(", ".join(usage["unpriced"]))}{colon()}{e(t("a.unpriced"))} (pricing.toml)</p>'
    annexes = (f'<section id="annexes"><h2>{e(t("s5"))}</h2>'
               f'<h3>{e(t("a.trace"))}</h3><div class="tbl"><table><tr><th>{e(t("a.req"))}</th><th>{e(t("t.rule"))}</th>'
               f'<th>{e(t("a.control"))}</th><th>{e(t("a.script"))}</th><th>{e(t("a.result"))}</th></tr>{trace}</table></div>'
               f'<h3>{e(t("a.evidence"))}</h3><div class="tbl"><table><tr><th>{e(t("a.file"))}</th><th></th><th></th>'
               f'<th>{e(t("a.hash"))}</th></tr>{"".join(evid)}</table></div>'
               f'<h3>{e(t("a.ai"))}</h3><div class="tbl"><table><tr><th>{e(t("a.model"))}</th><th>{e(t("a.calls"))}</th>'
               f'<th>{e(t("a.in"))}</th><th>{e(t("a.out"))}</th><th>{e(t("a.images"))}</th><th>{e(t("a.cost"))}</th></tr>{urows}</table></div>{note}'
               + (f'<h3>{e(t("a.human"))}</h3><div class="tbl"><table><tr><th>{e(t("a.ticket"))}</th><th>{e(t("t.id"))}</th><th></th>'
                  f'<th>{e(t("f.approved"))}</th><th>{e(t("a.mode"))}</th><th>{e(t("m.date"))}</th></tr>{dec}</table></div>' if dec else "")
               + f'<h3>{e(t("a.guards"))}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in t("a.guards_list")) + "</ul>"
               f'<h3>{e(t("a.integrity"))}</h3><p class="small">{e(t("a.integrity_text"))}</p>'
               f'<p class="hash">{e(state.get("trail_head", "…"))}</p>{journal}{coverage(state)}</section>')

    live = f'<span class="live"></span>{e(t("running"))} · ' if running else ""
    refresh = '<meta http-equiv="refresh" content="3">' if running else ""
    page = f"""<!doctype html><html lang="{e(state.get('lang', 'fr'))}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{refresh}
<title>{e(t("report"))} {e(m["id"])}</title><style>{CSS}</style></head><body><div class="doc">
<div class="band"><span><b>{e(t("classification"))}{colon().rstrip()}</b> {e(m["classification"])}</span><span>{live}{e(m["id"])} · Attest</span></div>
<div class="cover"><p class="eyebrow">{e(t("report"))} · {e(m["id"])}</p><h1>{e(m["title"])}</h1>
<p class="sys">{e(m["entity"])} · {e(m["system"])}</p>
<div class="meta"><span>{e(t("m.auditor"))}{colon()}<b>{e(m["lead_auditor"])}</b></span><span>{e(t("m.owner"))}{colon()}<b>{e(m["owner"])}</b></span>
<span>{e(t("m.date"))}{colon()}<b>{e(state["started"])}</b></span><span>{e(t("run"))}{colon()}<b>{e(state["run_id"])}</b></span></div></div>
{s1}{s2}{s3}{s4}{annexes}
<footer><span>{e(m["classification"])}</span><span>Attest · {e(state["backend"])} · {e(state["models"]["reason"])} + {e(state["models"]["segmentation"])}</span></footer>
</div></body></html>"""
    tmp = out / "report.html.tmp"
    tmp.write_text(page)
    tmp.replace(out / "report.html")            # écriture atomique : la page live ne se lit jamais à moitié


def to_pdf(html_path: Path, pdf_path: Path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(html_path.resolve().as_uri())
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
                 display_header_footer=True, header_template="<span></span>",
                 footer_template='<div style="font-size:8px;color:#666;width:100%;padding:0 12mm;display:flex;'
                                 'justify-content:space-between"><span>Attest</span><span>'
                                 '<span class="pageNumber"></span>/<span class="totalPages"></span></span></div>')
        b.close()
