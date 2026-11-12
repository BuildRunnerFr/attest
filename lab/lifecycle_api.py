"""Routes en lecture seule du rapprochement RH ↔ comptes (voir lab/lifecycle.py et lab/LIFECYCLE_API.md).

Trois listes paginées (100 par page, en-têtes X-Total-Count / X-Page / X-Total-Pages / Link rel="next") et deux
pages HTML de preuve. Le scénario servi est choisi par POST /api/reset {"scenario": "lc-…"} ; aucune écriture."""
import os
from html import escape

from flask import abort, jsonify, render_template_string, request

from . import lifecycle

_current = {"id": os.getenv("LAB_LIFECYCLE_SCENARIO", lifecycle.DEFAULT)}
_cache: dict = {}


def select(sid: str | None) -> bool:
    """Choisit le scénario servi ; faux si l'identifiant n'est pas un scénario de cycle de vie."""
    sid = sid or os.getenv("LAB_LIFECYCLE_SCENARIO", lifecycle.DEFAULT)
    if not (lifecycle.DIR / f"{sid}.json").exists():
        return False
    _current["id"] = sid
    return True


def scenario() -> dict:
    sid = _current["id"]
    if sid not in _cache:
        _cache.clear()
        _cache[sid] = lifecycle.load()[sid]
    return _cache[sid]


def _slice(rows: list, base: str):
    size = lifecycle.PAGE_SIZE
    try:
        page, per = int(request.args.get("page", 1)), min(int(request.args.get("per_page", size)), size)
    except ValueError:
        abort(400, "page et per_page doivent être des entiers")
    if page < 1 or per < 1:
        abort(400, "page et per_page doivent être ≥ 1")
    pages = max(1, -(-len(rows) // per))
    info = {"page": page, "per_page": per, "pages": pages, "total": len(rows),
            "next": f"{base}?page={page + 1}&per_page={per}" if page < pages else None}
    return rows[(page - 1) * per: page * per], info


def _json(rows: list, base: str):
    part, info = _slice(rows, base)
    resp = jsonify(part)
    resp.headers["X-Total-Count"], resp.headers["X-Page"] = str(info["total"]), str(info["page"])
    resp.headers["X-Total-Pages"] = str(info["pages"])
    if info["next"]:
        resp.headers["Link"] = f'<{info["next"]}>; rel="next"'
    return resp


def _nav(info: dict, base: str) -> str:
    links = []
    if info["page"] > 1:
        links.append(f'<a rel="prev" href="{base}?page={info["page"] - 1}&amp;per_page={info["per_page"]}">← page précédente</a>')
    if info["next"]:
        links.append(f'<a rel="next" href="{info["next"].replace("&", "&amp;")}">page suivante →</a>')
    return (f'<p class="sub" id="pagination">Page {info["page"]} / {info["pages"]} · {info["total"]} lignes · '
            f'{info["per_page"]} par page {" ".join(links)}</p>')


def register(app, caller, page_template: str):
    def render(title, sub, body):
        sc = scenario()
        return render_template_string(page_template, brand=f'{sc["entity"]} · habilitations', title=title, sub=sub, body=body)

    @app.get("/api/lifecycle/meta")
    def lc_meta():
        caller()
        sc = scenario()
        return jsonify(as_of=sc["as_of"], entity=sc["entity"], employees=len(sc["employees"]), accounts=len(sc["accounts"]))

    @app.get("/api/lifecycle/entitlements")
    def lc_entitlements():
        caller()
        return jsonify(scenario()["entitlements"])

    @app.get("/api/hr/employees")
    def lc_employees():
        caller()
        return _json(scenario()["employees"], "/api/hr/employees")

    @app.get("/api/lifecycle/accounts")
    def lc_accounts():
        caller()
        return _json(scenario()["accounts"], "/api/lifecycle/accounts")

    @app.get("/lifecycle/accounts")
    def lc_accounts_page():
        caller()
        sc = scenario()
        rows, info = _slice(sc["accounts"], "/lifecycle/accounts")
        body = "".join(
            f'<tr id="user-{escape(a["login"])}" data-role="{a["type"]}"><td>{escape(a["login"])}</td>'
            f'<td>{escape(a["employee_id"] or a["owner_employee_id"] or "—")}</td>'
            f'<td class="v {"ok" if a["enabled"] else "ko"}">{"Actif" if a["enabled"] else "Désactivé"}</td>'
            f'<td>{a["last_login"] or "—"}</td><td>{escape(", ".join(a["entitlements"]))}</td>'
            f'<td>{a["last_access_review"] or "—"}</td></tr>' for a in rows)
        return render("Comptes et habilitations", f"Situation au {sc['as_of']}", _nav(info, "/lifecycle/accounts") +
                      "<table><tr><th>Identifiant</th><th>Matricule (ou responsable)</th><th>État</th>"
                      f"<th>Dernière connexion</th><th>Droits</th><th>Dernière revue</th></tr>{body}</table>")

    @app.get("/lifecycle/reconciliation")
    def lc_reconciliation_page():
        """Chaque compte à côté de la fiche RH de son titulaire (ou du responsable d'un compte de service)."""
        caller()
        sc = scenario()
        emp = {e["employee_id"]: e for e in sc["employees"]}
        rows, info = _slice(sc["accounts"], "/lifecycle/reconciliation")
        body = ""
        for a in rows:
            ref = a["employee_id"] or a["owner_employee_id"]
            e = emp.get(ref)
            hr = ("<td>Absent du registre</td><td>—</td><td>—</td><td>—</td>" if e is None else
                  f'<td>{"Parti" if e["status"] == "left" else "Actif"}</td><td>{e["end_date"] or "—"}</td>'
                  f'<td>{e["department"]}</td>'
                  f'<td>{(e["previous_department"] + " → " + e["transfer_date"]) if e["transfer_date"] else "—"}</td>')
            body += (f'<tr id="user-{escape(a["login"])}" data-role="{a["type"]}"><td>{escape(a["login"])}</td>'
                     f'<td>{"Personne" if a["type"] == "person" else "Service"}</td>'
                     f'<td class="v {"ok" if a["enabled"] else "ko"}">{"Actif" if a["enabled"] else "Désactivé"}</td>'
                     f'<td>{escape(ref or "—")}</td>{hr}<td>{a["last_login"] or "—"}</td>'
                     f'<td>{escape(", ".join(a["entitlements"]))}</td><td>{a["last_access_review"] or "—"}</td></tr>')
        return render("Rapprochement comptes ↔ registre RH", f"Situation au {sc['as_of']}",
                      _nav(info, "/lifecycle/reconciliation") +
                      "<style>main{max-width:1500px} td,th{padding:8px 10px;font-size:13px}</style>"
                      "<table><tr><th>Identifiant</th><th>Type</th><th>État du compte</th><th>Matricule / responsable</th>"
                      "<th>Statut RH</th><th>Fin de contrat</th><th>Service</th><th>Ancien service → mutation</th>"
                      f"<th>Dernière connexion</th><th>Droits</th><th>Dernière revue</th></tr>{body}</table>")

    @app.get("/lifecycle/hr")
    def lc_hr_page():
        caller()
        sc = scenario()
        rows, info = _slice(sc["employees"], "/lifecycle/hr")
        body = "".join(
            f'<tr id="emp-{e["employee_id"]}"><td>{e["employee_id"]}</td><td>{escape(e["first_name"])} {escape(e["last_name"])}</td>'
            f'<td>{e["department"]}</td><td class="v">{"Parti" if e["status"] == "left" else "Actif"}</td>'
            f'<td>{e["end_date"] or "—"}</td><td>{e["previous_department"] or "—"}</td><td>{e["transfer_date"] or "—"}</td></tr>'
            for e in rows)
        return render("Registre RH", f"Situation au {sc['as_of']}", _nav(info, "/lifecycle/hr") +
                      "<table><tr><th>Matricule</th><th>Salarié</th><th>Service</th><th>Statut</th><th>Fin de contrat</th>"
                      f"<th>Ancien service</th><th>Date de mutation</th></tr>{body}</table>")
