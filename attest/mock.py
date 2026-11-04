"""Réponses préenregistrées (ATTEST_BACKEND=mock) : même format que les vrais modèles.

Sert au développement, aux tests automatisés et à la CI. Les positions viennent du DOM avec un
léger bruit, pour que la mesure de masquage ne soit pas triviale.
"""
import json
import os
import random

import numpy as np

REFS = {
    "PSI-4.1": ["DORA 9(4)(d)", "RTS 21(1)(f)(ii)"], "PSI-4.2": ["DORA 9(4)(d)", "RTS 21(1)(f)(ii)"],
    "PSI-4.3": ["DORA 9(4)(d)"], "PSI-4.4": ["DORA 9(4)(c)"], "PSI-4.5": ["DORA 9(4)(c)"],
    "PSI-4.6": ["RTS 12(2)(c)(i)"], "PSI-4.7": ["DORA 9(4)(c)", "RTS 21(1)(c)", "RTS 21(1)(e)(ii)"],
}

# id, règle, titre, objectif, attendu, criticité, page, champ (mock), remédiation, risque, recommandation
CONTROLS = [
    ("C1", "PSI-4.1", "MFA des comptes à privilèges", "Tout compte administrateur s'authentifie avec un second facteur.",
     "mfa_admin == true", "critique", "/admin/users", "mfa_admin", "config",
     "Un mot de passe administrateur volé suffit à prendre le contrôle de la console.",
     "Activer le MFA pour tous les comptes administrateurs."),
    ("C2", "PSI-4.2", "MFA des utilisateurs", "Les utilisateurs d'un système critique s'authentifient avec un second facteur.",
     "mfa_users == true", "elevee", "/admin/security", "mfa_users", "config",
     "Compromission de comptes conseillers par hameçonnage ou réutilisation de mots de passe.",
     "Activer le MFA pour les utilisateurs standards."),
    ("C3", "PSI-4.3", "Robustesse des mots de passe", "Mot de passe d'au moins 12 caractères, avec complexité.",
     "password_min_length >= 12 and password_require_complexity == true", "moyenne", "/admin/security",
     "password_min_length", "config", "Mots de passe devinables par force brute ou dictionnaire.",
     "Porter la longueur minimale à 12 et exiger la complexité."),
    ("C4", "PSI-4.4", "Verrouillage des comptes", "Verrouillage après 5 échecs au plus, jamais désactivé.",
     "1 <= lockout_threshold <= 5", "moyenne", "/admin/security", "lockout_threshold", "config",
     "Attaques par force brute en ligne sans limitation.", "Fixer le verrouillage à 5 échecs."),
    ("C5", "PSI-4.5", "Expiration des sessions", "Sessions inactives expirées après 15 minutes au plus.",
     "1 <= session_timeout_minutes <= 15", "moyenne", "/admin/security", "session_timeout_minutes", "config",
     "Session administrateur laissée ouverte réutilisable par un tiers.", "Fixer l'expiration à 15 minutes."),
    ("C6", "PSI-4.6", "Journalisation de l'administration", "Toutes les actions d'administration sont journalisées.",
     "admin_audit_log == true", "elevee", "/admin/security", "admin_audit_log", "config",
     "Actions d'administration non traçables en cas d'incident.", "Maintenir la journalisation activée."),
    ("C7", "PSI-4.7", "Comptes à privilèges nominatifs", "Aucun compte générique ou partagé n'a de droits d'administration.",
     "admins: login initiale.nom, e-mail personnel", "elevee", "/admin/users", "users", "manual",
     "Actions d'administration non imputables à une personne ; mot de passe partagé.",
     "Désactiver le compte partagé et créer des comptes nominatifs dédiés."),
]

CHECKS = {
    "C1": ("s['mfa_admin'] is True", "{'mfa_admin': s['mfa_admin']}", "'mfa_admin = true'"),
    "C2": ("s['mfa_users'] is True", "{'mfa_users': s['mfa_users']}", "'mfa_users = true'"),
    "C3": ("s['password_min_length'] >= 12 and s['password_require_complexity'] is True",
           "{'password_min_length': s['password_min_length'], 'password_require_complexity': s['password_require_complexity']}",
           "'longueur >= 12 et complexité exigée'"),
    "C4": ("1 <= s['lockout_threshold'] <= 5", "{'lockout_threshold': s['lockout_threshold']}", "'entre 1 et 5'"),
    "C5": ("1 <= s['session_timeout_minutes'] <= 15", "{'session_timeout_minutes': s['session_timeout_minutes']}",
           "'entre 1 et 15 minutes'"),
    "C6": ("s['admin_audit_log'] is True", "{'admin_audit_log': s['admin_audit_log']}", "'admin_audit_log = true'"),
}

FIXES = {
    "C1": {"mfa_admin": True}, "C2": {"mfa_users": True},
    "C3": {"password_min_length": 12, "password_require_complexity": True},
    "C4": {"lockout_threshold": 5}, "C5": {"session_timeout_minutes": 15}, "C6": {"admin_audit_log": True},
}

_rng = random.Random(7)


def _jitter(box, px=6):
    return [int(v + _rng.randint(-px, px)) for v in box]


def _shift_ip(p: dict) -> list:
    box = _jitter(p["box"], 3)
    if p.get("kind") == "ipv4":
        box[0] += 40
    return box


def _code(cid: str) -> str:
    if cid == "C7":
        return """```python
import json, os, re, requests

H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
users = requests.get(os.environ["LAB_URL"] + "/api/users", headers=H, timeout=10).json()
LOGIN = re.compile(r"^[a-z]\\.[a-z]+(?:-[a-z]+)*$")
FUNCTIONAL = re.compile(r"partage|shared|admin|ops|support|helpdesk|svc|service|root|equipe|team|noreply|exploit|it-", re.I)
generic = [u["login"] for u in users if u["role"] == "admin" and (
    not LOGIN.match(u["login"]) or FUNCTIONAL.search(u["email"].split("@")[0]))]
print(json.dumps({"status": "fail" if generic else "pass", "observed": {"generic_admin_accounts": generic},
                  "expected": "aucun compte administrateur générique ou partagé",
                  "detail": f"{len(generic)} compte(s) administrateur non nominatif(s)."}, ensure_ascii=False))
```"""
    cond, observed, expected = CHECKS[cid]
    return f"""```python
import json, os, requests

H = {{"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}}
s = requests.get(os.environ["LAB_URL"] + "/api/security", headers=H, timeout=10).json()
ok = {cond}
print(json.dumps({{"status": "pass" if ok else "fail", "observed": {observed},
                  "expected": {expected},
                  "detail": "Valeur lue via l'API d'administration (compte d'audit en lecture seule)."}},
                 ensure_ascii=False))
```"""


def answer(task: str, user: str, ctx: dict) -> str:
    if task == "plan":
        return json.dumps([
            {"id": i, "rule": r, "title": t, "objective": o, "expected": e, "severity": sev,
             "test_procedure": f"Lecture de la configuration via l'API en lecture seule et comparaison à {r}.",
             "references": REFS[r], "risk": risk, "recommendation": reco, "evidence_page": p,
             "remediation": rem, "_field": f}
            for i, r, t, o, e, sev, p, f, rem, risk, reco in CONTROLS], ensure_ascii=False)

    if task == "interpret":
        return interpret(ctx)

    if task == "code":
        if ctx["control"].get("_check"):
            repo = ctx["control"]["evidence_page"].split("/")[2]
            return repo_code(ctx["control"]["_check"], repo)
        return _code(ctx["control"]["id"])

    if task == "inspect":
        dom, c, res = ctx["dom"], ctx["control"], ctx["result"]
        if dom.get("lines"):                          # page de code : lignes désignées par le test
            boxes = code_boxes(dom, res)
            return json.dumps({"corroborates": True, "field_text": "lignes en cause",
                               "field_boxes": [_jitter(b, 3) for b in boxes],
                               "comment": "Les lignes encadrées correspondent au résultat du test.",
                               "pii": [{"text": p["text"], "box": _shift_ip(p)} for p in dom["pii"]],
                               "injection_detected": False}, ensure_ascii=False)
        if c["id"] == "C7":
            generic = (res.get("observed") or {}).get("generic_admin_accounts", []) if isinstance(res.get("observed"), dict) else []
            boxes = [u["box"] for login, u in dom["users"].items() if login in generic]
            text = "Comptes génériques : " + (", ".join(generic) or "aucun")
        elif c["evidence_page"] == "/admin/users":
            boxes = [u["box"] for u in dom["users"].values() if u["role"] == "admin"]
            text = "Comptes admin a.lefloch et ops : MFA " + ("Oui" if res["status"] == "pass" else "Non")
        else:
            boxes = [dom["rows"][c.get("_field", "mfa_users")]]
            text = c["title"]
        return json.dumps({
            "corroborates": True, "field_text": text, "field_boxes": [_jitter(b) for b in boxes],
            "comment": f"Ligne « {text} » : valeur cohérente avec la lecture API.",
            # comme Muse Spark lors du premier audit réel : boîtes des IP décalées d'environ 40 px vers la droite
            "pii": [{"text": p["text"], "box": _shift_ip(p)} for p in dom["pii"]],
            "injection_detected": bool(dom.get("has_note")) and c["evidence_page"] == "/admin/users",
        }, ensure_ascii=False)

    if task == "fix":
        c = ctx["control"]
        if c.get("_check") or ctx.get("kind") == "code":
            return json.dumps({"type": "manual", "rationale": "Correction de code : réalisée par l'équipe de développement.",
                               "actions": [c["recommendation"], "Ouvrir un ticket pour l'équipe de développement.",
                                           "Contre-vérifier par un nouvel audit du dépôt après correction."]},
                              ensure_ascii=False)
        if c["id"] == "C7":
            return json.dumps({"type": "manual", "rationale": "Compte partagé : décision du propriétaire requise.",
                               "actions": ["Identifier les utilisateurs réels du compte « ops ».",
                                           "Créer des comptes administrateurs nominatifs avec MFA.",
                                           "Désactiver le compte « ops » et révoquer ses accès."]},
                              ensure_ascii=False)
        return json.dumps({"type": "config", "method": "PATCH", "path": "/api/security", "body": FIXES[c["id"]],
                           "rationale": f"Alignement minimal sur la règle {c['rule']}.",
                           "impact": "Les utilisateurs concernés devront s'adapter à la nouvelle règle à leur prochaine connexion."},
                          ensure_ascii=False)
    raise ValueError(task)


def sam_output(boxes, size) -> str:
    """Fabrique une sortie SAM au vrai format filaire (masques one_bit encodés en base85)."""
    from meta_sam_parser._mask_codec import _encode_raster

    W, H = size
    recs = []
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        mh, mw = max(4, (y2 - y1) // 4), max(4, (x2 - x1) // 4)
        m = np.zeros((mh, mw), dtype=np.uint8)
        m[1:mh - 1, 1:mw - 1] = 1
        payload = _encode_raster(bytes(m.flatten()), mw, mh)
        recs.append(f"{i + 1}<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={W};h={H};c=0.93|>"
                    f"<|mask;x=0;y=0;c=0.91;data={mh},{mw},{payload}|>")
    return "<0f>" + ",".join(recs)


# =====================================================================================================
# Interprétation d'articles et cible « dépôt de code » (Attest Studio)
# =====================================================================================================
import re as _re

CODE = {
    "secrets": ("PDS-2.1", "Aucun secret en clair dans le code", "Aucun mot de passe, clé ou jeton n'est écrit en clair dans le code ou la configuration versionnée.",
                "aucune affectation littérale de secret hors des tests", "critique", ["RTS 7(2)"],
                "Un secret versionné est exposé à toute personne ayant accès au dépôt et reste dans l'historique git.",
                "Retirer et révoquer le secret, puis le charger depuis le coffre-fort ou une variable d'environnement."),
    "tls": ("PDS-2.2", "Vérification TLS des appels sortants", "Tout appel réseau sortant vérifie le certificat du serveur.",
            "aucun verify=False", "elevee", ["DORA 9(3)(a)", "RTS 6(2)(a)"],
            "Un attaquant placé sur le réseau peut intercepter ou modifier les ordres de virement.",
            "Supprimer verify=False et épingler l'autorité de certification du prestataire."),
    "hash": ("PDS-2.3", "Hachage robuste des mots de passe", "Les mots de passe sont hachés avec argon2, bcrypt, scrypt ou PBKDF2.",
             "ni MD5 ni SHA-1 pour un usage de sécurité", "elevee", ["RTS 6(3)", "RTS 6(4)"],
             "En cas de fuite de la base, les mots de passe sont retrouvés en quelques secondes.",
             "Migrer vers argon2id, avec renouvellement des empreintes à la prochaine connexion."),
    "sast": ("PDS-2.4", "Analyse statique de sécurité en CI", "La chaîne d'intégration continue exécute une analyse statique de sécurité.",
             "bandit, semgrep ou CodeQL dans la CI", "moyenne", ["RTS 16(3)"],
             "Des vulnérabilités atteignent la production sans détection.",
             "Ajouter une étape bandit ou semgrep bloquante à la CI."),
    "deps": ("PDS-2.5", "Dépendances épinglées et auditées", "Chaque dépendance est épinglée à une version exacte et auditée en CI.",
             "paquet==version partout et pip-audit en CI", "moyenne", ["RTS 16(4)", "RTS 16(8)"],
             "Une version vulnérable ou compromise d'une dépendance s'installe sans contrôle.",
             "Épingler les versions et ajouter pip-audit à la CI."),
    "testdata": ("PDS-2.6", "Données de test synthétiques", "Les jeux de test sont synthétiques et déclarés comme tels ; aucun export de production.",
                 "\"synthetic\": true dans chaque jeu ; aucun export de production", "elevee", ["RTS 16(5)(a)"],
                 "Des données clients réelles sont exposées hors production.",
                 "Supprimer l'export, purger l'historique git et générer des données synthétiques."),
    "authlog": ("PDS-2.7", "Journalisation des authentifications", "Les réussites et les échecs d'authentification sont journalisés.",
                "journalisation dans la fonction de login", "moyenne", ["RTS 12(2)(c)(i)"],
                "Les tentatives de connexion frauduleuses passent inaperçues.",
                "Journaliser chaque tentative : identifiant, résultat, horodatage."),
}
CODE_BY_RULE = {v[0]: k for k, v in CODE.items()}
APP_BY_RULE = {r: i for i, r, *_ in CONTROLS}

# exigences réglementaires reconnues quand aucune politique interne n'est fournie (clé, testabilité, source du seuil)
REG_APP = [(r"strong authentication methods|strong authentication mechanisms", "automated", ["C1", "C2"], "NIST SP 800-63B (proposal)"),
           (r"generic and shared user accounts", "automated", ["C7"], "text"),
           (r"logical and physical access control, as referred", "automated", ["C6"], "text"),
           (r"segregation of duties", "interview", [], ""),
           (r"at least once a year", "document", [], ""),
           (r"develop, document,? and implement", "document", [], "")]
REG_CODE = [(r"source code reviews covering both static and dynamic", "automated", ["sast"], "OWASP ASVS 4.0 (proposal)"),
            (r"protect cryptographic keys through their whole lifecycle", "automated", ["secrets"], "text"),
            (r"security of the means of transfer of data", "automated", ["tls"], "text"),
            (r"selection of cryptographic techniques", "automated", ["hash"], "NIST SP 800-63B (proposal)"),
            (r"non-production environments only store", "automated", ["testdata"], "text"),
            (r"security testing of software packages", "automated", ["deps"], "OWASP ASVS 4.0 (proposal)"),
            (r"logical and physical access control, as referred", "automated", ["authlog"], "text"),
            (r"monitor the implementation of that action plan", "interview", [], ""),
            (r"develop, document,? and implement", "document", [], "")]


def _clause(line: str) -> str:
    """Partie citable d'une ligne : sans le préfixe « (a) » ou « Article 16(3): »."""
    m = _re.match(r"^\s*(?:\([a-z]+\)|\([ivx]+\)|Article [\d()a-z]+:?)\s*", line)
    return line[m.end():].strip() if m else line.strip()


def _app_control(cid, source):
    i, r, t, o, e, sev, p, f, rem, risk, reco = next(x for x in CONTROLS if x[0] == cid)
    return {"rule": r, "title": t, "objective": o, "expected": e, "severity": sev, "references": REFS[r],
            "test_procedure": f"Lecture de la configuration via l'API en lecture seule et comparaison à {r}.",
            "risk": risk, "recommendation": reco, "evidence_page": p, "remediation": rem, "_field": f,
            "threshold_source": source}


def _code_control(key, repo, source):
    rule, t, o, e, sev, refs, risk, reco = CODE[key]
    return {"rule": rule, "title": t, "objective": o, "expected": e, "severity": sev, "references": refs,
            "test_procedure": "Analyse du dépôt via la passerelle en lecture seule (arborescence, fichiers, recherche).",
            "risk": risk, "recommendation": reco, "evidence_page": f"/repo/{repo}/view?path=README.md",
            "remediation": "manual", "_check": key, "threshold_source": source}


def interpret(ctx: dict) -> str:
    texts, kind, repo = ctx["texts"], ctx["kind"], ctx.get("repo", "")
    lines = [l for l in texts.splitlines() if len(l.strip()) > 25 and not l.startswith(("#", "===", "|---"))]
    reqs = []
    for l in lines:                                   # 1. règles d'une politique interne (lignes de tableau)
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) >= 2 and _re.fullmatch(r"P[SD][IS]-\d\.\d", cells[0]):
            rule, text = cells[0], cells[1]
            if kind == "app" and rule in APP_BY_RULE:
                ctrls = [_app_control(APP_BY_RULE[rule], rule)]
            elif kind == "code" and rule in CODE_BY_RULE:
                ctrls = [_code_control(CODE_BY_RULE[rule], repo, rule)]
            else:
                reqs.append({"ref": rule, "quote": text, "summary": text, "testability": "document",
                             "why": "Règle sans lien avec cette cible.", "controls": []})
                continue
            reqs.append({"ref": rule, "quote": text, "summary": text, "testability": "automated",
                         "why": "Vérifiable par l'interface en lecture seule de la cible.", "controls": ctrls})
    if reqs:                                          # 1 bis. clauses du règlement couvertes par la politique
        tested = {c["rule"] for r in reqs for c in r["controls"]}
        for rx, testability, keys, source in (REG_APP if kind == "app" else REG_CODE):
            line = next((l for l in lines if _re.search(rx, l, _re.I)), None)
            if not line:
                continue
            rules = [(next(x for x in CONTROLS if x[0] == k)[1] if kind == "app" else CODE[k][0]) for k in keys]
            cov = [r for r in rules if r in tested]
            reqs.append({"ref": "", "quote": _clause(line), "summary": _clause(line)[:120],
                         "testability": "automated" if cov else ("document" if testability == "automated" else testability),
                         "why": "Couverte par les contrôles de la politique interne." if cov else "Nécessite une revue.",
                         "controls": [], "covered_by": cov})
    if not reqs:                                      # 2. texte réglementaire seul : seuils proposés
        for rx, testability, keys, source in (REG_APP if kind == "app" else REG_CODE):
            line = next((l for l in lines if _re.search(rx, l, _re.I)), None)
            if not line:
                continue
            ctrls = [(_app_control(k, source) if kind == "app" else _code_control(k, repo, source)) for k in keys]
            for c in ctrls:
                c["rule"] = c["references"][0]
            reqs.append({"ref": "", "quote": _clause(line), "summary": _clause(line)[:120],
                         "testability": testability,
                         "why": {"automated": "Vérifiable par l'interface de la cible.",
                                 "document": "Nécessite la revue d'une politique ou d'une procédure.",
                                 "interview": "Nécessite un entretien avec les équipes."}[testability],
                         "controls": ctrls})
    reqs.append({"ref": "?", "quote": "La banque doit tout chiffrer en quantique.", "summary": "Citation inventée (test du garde-fou).",
                 "testability": "automated", "why": "", "controls": [_app_control("C1", "text")] if kind == "app"
                 else [_code_control("tls", repo, "text")]})
    return json.dumps({"requirements": reqs}, ensure_ascii=False)


_REPO_HEAD = '''import json, os, re, requests

B = os.environ["LAB_URL"] + "/api/repo/__REPO__"
H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}


def get(endpoint, **params):
    r = requests.get(B + endpoint, headers=H, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def view(path):
    return "/repo/__REPO__/view?path=" + path


def report(ok, observed, expected, detail, page):
    print(json.dumps({"status": "pass" if ok else "fail", "observed": observed, "expected": expected,
                      "detail": detail, "evidence_page": page}, ensure_ascii=False))
'''

_REPO_CHECKS = {
    "secrets": r'''m = [x for x in get("/search", q=r"(?i)(password|passwd|secret|api_key|token)\w*\s*=\s*[\"'][^\"']{6,}[\"']")["matches"]
     if not x["path"].startswith("tests/")]
if m:
    get("/file", path=m[0]["path"])                   # le fichier désigné comme preuve est relu
report(not m, {"matches": m}, "aucun secret littéral", f"{len(m)} secret(s) en clair dans le code.",
       view(m[0]["path"]) if m else view("README.md"))''',
    "tls": r'''m = get("/search", q=r"verify\s*=\s*False")["matches"]
if m:
    get("/file", path=m[0]["path"])
report(not m, {"matches": m}, "aucun verify=False", f"{len(m)} appel(s) sans vérification TLS.",
       view(m[0]["path"]) if m else view("README.md"))''',
    "hash": r'''m = get("/search", q=r"hashlib\.(md5|sha1)\(")["matches"]
if m:
    get("/file", path=m[0]["path"])
report(not m, {"matches": m}, "argon2, bcrypt, scrypt ou PBKDF2", f"{len(m)} usage(s) de MD5 ou SHA-1.",
       view(m[0]["path"]) if m else view("README.md"))''',
    "sast": r'''ci = [f for f in get("/tree")["files"] if f.startswith(".github/workflows/")]
steps, tools = [], []
for f in ci:
    for i, l in enumerate(get("/file", path=f)["lines"], 1):
        if "run:" in l:
            steps.append({"path": f, "line": i, "text": l.strip()})
        if re.search(r"(?i)bandit|semgrep|codeql", l):
            tools.append(l.strip())
report(bool(tools), {"matches": steps, "sast_tools": tools}, "bandit, semgrep ou CodeQL dans la CI",
       "Aucune analyse statique de sécurité dans la CI." if not tools else "Analyse statique présente.",
       view(ci[0]) if ci else view("README.md"))''',
    "deps": r'''lines = get("/file", path="requirements.txt")["lines"]
loose = [{"path": "requirements.txt", "line": i, "text": l.strip()} for i, l in enumerate(lines, 1)
         if l.strip() and not l.startswith("#") and not re.fullmatch(r"[A-Za-z0-9_.\-\[\]]+==[0-9][\w.]*", l.strip())]
ci = [f for f in get("/tree")["files"] if f.startswith(".github/workflows/")]
audit = any(re.search(r"pip-audit|safety", " ".join(get("/file", path=f)["lines"])) for f in ci)
report(not loose and audit, {"matches": loose, "dependency_audit_in_ci": audit}, "paquet==version et pip-audit en CI",
       f"{len(loose)} dépendance(s) non épinglée(s) ; audit en CI : {'oui' if audit else 'non'}.", view("requirements.txt"))''',
    "testdata": r'''fx = [f for f in get("/tree")["files"] if f.startswith("tests/fixtures/") and f.endswith(".json")]
bad, marks = [], []
for f in fx:
    lines = get("/file", path=f)["lines"]
    data = json.loads("\n".join(lines))
    if "prod" in f.lower() or not (isinstance(data, dict) and data.get("synthetic") is True):
        bad.append(f)
        marks += [{"path": f, "line": i, "text": l.strip()} for i, l in enumerate(lines, 1) if re.search(r"(?i)prod", l)]
report(not bad, {"files": bad, "matches": marks}, "jeux synthétiques déclarés, aucun export de production",
       f"{len(bad)} jeu(x) de test non synthétique(s).", view(bad[0]) if bad else view("README.md"))''',
    "authlog": r'''lines = get("/file", path="app/auth.py")["lines"]
logged = [l for l in lines if re.search(r"log\w*\.(info|warning|error|exception)\(", l)]
login = [{"path": "app/auth.py", "line": i, "text": l.strip()} for i, l in enumerate(lines, 1) if "def login" in l]
report(bool(logged), {"matches": login, "log_calls": len(logged)}, "réussites et échecs journalisés",
       "La fonction de login ne journalise rien." if not logged else "Authentifications journalisées.", view("app/auth.py"))''',
}


def repo_code(check: str, repo: str) -> str:
    return "```python\n" + _REPO_HEAD.replace("__REPO__", repo) + "\n\n" + _REPO_CHECKS[check] + "\n```"


def code_boxes(dom: dict, result: dict) -> list:
    page = str(result.get("evidence_page") or "")
    path = page.split("path=", 1)[1] if "path=" in page else ""
    obs = result.get("observed") if isinstance(result.get("observed"), dict) else {}
    lines = [m["line"] for m in obs.get("matches", []) if isinstance(m, dict) and m.get("path") == path]
    return [dom["lines"][str(n)] for n in lines if str(n) in dom.get("lines", {})]
