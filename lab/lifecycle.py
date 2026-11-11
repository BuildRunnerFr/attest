"""Cycle de vie des accès : rapprochement RH ↔ comptes sur des données FICTIVES, et vérité terrain de la
politique PSI-5 (départs, comptes orphelins, comptes dormants, droits incompatibles, mutations, revues d'accès).

Trois ensembles servis par la console de démonstration (lecture seule, paginés) :
- le registre RH (`/api/hr/employees`) ;
- les comptes de l'application et leurs droits (`/api/lifecycle/accounts`) ;
- le catalogue des droits (`/api/lifecycle/entitlements`).
Tout est généré par graine : personnes, matricules, adresses en `.example`. Chaque cas planté a son jumeau
« presque fautif » qui doit être jugé conforme (départ le jour même, 90 jours pile, compte déjà désactivé…).
« expected » et « expected_offenders » viennent de l'oracle ci-dessous ; l'agent ne les voit jamais.

Régénérer les fichiers :  python -m lab.lifecycle
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

from .scenarios import FIRST_XL, LAST_XL

DIR = Path(__file__).with_name("lifecycle_scenarios")
PAGE_SIZE = 100
DEFAULT = "lc-01-kerlann"

DORMANT_DAYS, MOVER_DAYS, REVIEW_DAYS = 90, 30, 365
SOD_PAIRS = [("paiements.saisie", "paiements.validation"), ("credit.instruction", "credit.decision")]
ENTITLEMENTS = [
    {"name": "commun.messagerie", "department": None, "privileged": False},
    {"name": "paiements.saisie", "department": "paiements", "privileged": False},
    {"name": "paiements.validation", "department": "paiements", "privileged": False},
    {"name": "paiements.admin", "department": "paiements", "privileged": True},
    {"name": "credit.instruction", "department": "credit", "privileged": False},
    {"name": "credit.decision", "department": "credit", "privileged": False},
    {"name": "tresorerie.operations", "department": "tresorerie", "privileged": False},
    {"name": "tresorerie.admin", "department": "tresorerie", "privileged": True},
    {"name": "conformite.consultation", "department": "conformite", "privileged": False},
    {"name": "rh.dossiers", "department": "rh", "privileged": False},
]
DEPARTMENTS = ["paiements", "credit", "tresorerie", "conformite", "rh"]
_DEPT = {e["name"]: e["department"] for e in ENTITLEMENTS}
_PRIV = {e["name"] for e in ENTITLEMENTS if e["privileged"]}
RULES = [f"PSI-5.{i}" for i in range(1, 7)]


def _d(s: str) -> date:
    return date.fromisoformat(s)


# ---------- oracle : la politique PSI-5 écrite en code (référence de notation) ----------

def offenders(sc: dict) -> dict:
    """Comptes en infraction, par règle (identifiants triés)."""
    as_of = _d(sc["as_of"])
    emp = {e["employee_id"]: e for e in sc["employees"]}
    out = {r: [] for r in RULES}
    for a in sc["accounts"]:
        if not a["enabled"]:
            continue                                        # un compte désactivé ne donne plus d'accès
        e = emp.get(a["employee_id"]) if a["type"] == "person" else emp.get(a["owner_employee_id"])
        gone = e is not None and e["end_date"] is not None and _d(e["end_date"]) < as_of
        ents = set(a["entitlements"])
        if a["type"] == "person" and gone:
            out["PSI-5.1"].append(a["login"])
        if e is None or (a["type"] == "service" and gone):
            out["PSI-5.2"].append(a["login"])
        if a["type"] == "person":
            last = _d(a["last_login"]) if a["last_login"] else _d(a["created"])
            if (as_of - last).days > DORMANT_DAYS:
                out["PSI-5.3"].append(a["login"])
        if any(x in ents and y in ents for x, y in SOD_PAIRS):
            out["PSI-5.4"].append(a["login"])
        if (a["type"] == "person" and e is not None and e["transfer_date"]
                and (as_of - _d(e["transfer_date"])).days > MOVER_DAYS
                and any(_DEPT[x] == e["previous_department"] != e["department"] for x in ents)):
            out["PSI-5.5"].append(a["login"])
        if ents & _PRIV and (a["last_access_review"] is None
                             or (as_of - _d(a["last_access_review"])).days > REVIEW_DAYS):
            out["PSI-5.6"].append(a["login"])
    return {r: sorted(v) for r, v in out.items()}


def expected(sc: dict) -> dict:
    return {r: "fail" if v else "pass" for r, v in offenders(sc).items()}


# ---------- génération ----------

def _base(rng, domain, n, as_of: date, leavers: int):
    """Situation saine : chaque salarié actif a un compte actif et récent ; les partis ont un compte désactivé."""
    employees, accounts, used = [], [], set()
    iso = lambda d: d.isoformat()
    for i in range(n):
        f, last = rng.choice(FIRST_XL), rng.choice(LAST_XL)
        login, local, k = f"{f[0]}.{last}", f"{f}.{last}", 2
        while login in used:
            login, local, k = f"{f[0]}.{last}{k}", f"{f}.{last}{k}", k + 1
        used.add(login)
        dept = rng.choice(DEPARTMENTS)
        start = as_of - timedelta(days=rng.randint(200, 4000))
        left = i < leavers
        end = as_of - timedelta(days=rng.randint(5, 400)) if left else None
        eid = f"E{10000 + i * 7 + rng.randint(0, 6)}"
        employees.append({"employee_id": eid, "first_name": f.title(), "last_name": last.title(), "department": dept,
                          "status": "left" if left else "active", "start_date": iso(start),
                          "end_date": iso(end) if end else None, "previous_department": None, "transfer_date": None})
        own = [e["name"] for e in ENTITLEMENTS if e["department"] == dept and not e["privileged"]]
        ents = ["commun.messagerie", rng.choice(own)]
        review = None
        if not left and rng.random() < 0.06 and any(e["department"] == dept and e["privileged"] for e in ENTITLEMENTS):
            ents.append(f"{dept}.admin")
            review = iso(as_of - timedelta(days=rng.randint(20, 300)))
        last_login = (end - timedelta(days=rng.randint(0, 3))) if left else as_of - timedelta(days=rng.randint(0, 60))
        accounts.append({"login": login, "email": f"{local}@{domain}", "type": "person", "employee_id": eid,
                         "owner_employee_id": None, "enabled": not left, "created": iso(start),
                         "last_login": iso(last_login), "entitlements": sorted(ents), "last_access_review": review})
    actives = [e for e in employees if e["status"] == "active"]
    for name in ("svc-batch-paiements", "svc-reporting", "svc-sauvegarde"):
        owner = rng.choice(actives)
        accounts.append({"login": name, "email": f"{name}@{domain}", "type": "service", "employee_id": None,
                         "owner_employee_id": owner["employee_id"], "enabled": True,
                         "created": iso(as_of - timedelta(days=900)), "last_login": None,
                         "entitlements": ["commun.messagerie"], "last_access_review": None})
    return employees, accounts


class _Edit:
    """Mutations d'une situation saine : cas plantés et jumeaux « presque fautifs »."""

    def __init__(self, rng, employees, accounts, as_of):
        self.rng, self.emp, self.acc, self.as_of = rng, {e["employee_id"]: e for e in employees}, accounts, as_of
        self.touched = set()

    def pick(self, late=False, pred=lambda a, e: True):
        """Un compte de personne active, jamais modifié ; `late` : hors de la première page de l'annuaire."""
        order = sorted(self.acc, key=lambda a: a["login"])
        pool = [a for i, a in enumerate(order) if a["type"] == "person" and a["enabled"] and a["login"] not in self.touched
                and len(a["entitlements"]) == 2 and (not late or i >= PAGE_SIZE) and pred(a, self.emp[a["employee_id"]])]
        a = self.rng.choice(pool)
        self.touched.add(a["login"])
        return a, self.emp[a["employee_id"]]

    def day(self, n):
        return (self.as_of - timedelta(days=n)).isoformat()

    def leaver(self, days_ago, enabled=True, late=False):
        a, e = self.pick(late)
        e["status"], e["end_date"] = ("left" if days_ago > 0 else "active"), self.day(days_ago)
        a["enabled"], a["last_login"] = enabled, self.day(max(days_ago, 0) + 1)
        return a["login"]

    def orphan(self, enabled=True):
        a, e = self.pick()
        a["employee_id"], a["enabled"] = "E99" + a["employee_id"][3:], enabled      # matricule absent du registre RH
        return a["login"]

    def service_owner_left(self, name, domain):
        a, e = self.pick()
        e["status"], e["end_date"] = "left", self.day(40)
        a["enabled"] = False                                                         # son compte personnel est bien fermé
        self.acc.append({"login": name, "email": f"{name}@{domain}", "type": "service", "employee_id": None,
                         "owner_employee_id": e["employee_id"], "enabled": True, "created": self.day(700),
                         "last_login": None, "entitlements": ["commun.messagerie"], "last_access_review": None})
        return name

    def dormant(self, days, late=False):
        a, _ = self.pick(late)
        a["last_login"] = self.day(days)
        return a["login"]

    def sod(self, pair, enabled=True, late=False):
        dept = _DEPT[pair[0]]
        a, e = self.pick(late)
        e["department"] = dept
        a["entitlements"], a["enabled"] = sorted({"commun.messagerie", *pair}), enabled
        if not enabled:
            e["status"], e["end_date"] = "left", self.day(12)
        return a["login"]

    def cross(self):
        """Presque fautif : deux droits de familles différentes, qui ne forment pas une paire incompatible."""
        a, e = self.pick()
        e["department"] = "paiements"
        a["entitlements"] = sorted({"commun.messagerie", "paiements.saisie", "conformite.consultation"})
        return a["login"]

    def mover(self, days_ago, keep_old=True):
        a, e = self.pick(pred=lambda a, e: e["department"] != "rh")
        old = e["department"]
        new = next(d for d in DEPARTMENTS if d not in (old, "rh"))
        e["previous_department"], e["department"], e["transfer_date"] = old, new, self.day(days_ago)
        new_right = next(x["name"] for x in ENTITLEMENTS if x["department"] == new and not x["privileged"])
        old_right = next(x for x in a["entitlements"] if _DEPT[x] == old)
        a["entitlements"] = sorted({"commun.messagerie", new_right} | ({old_right} if keep_old else set()))
        return a["login"]

    def review(self, days, late=False):
        a, e = self.pick(late, pred=lambda a, e: e["department"] in ("paiements", "tresorerie"))
        a["entitlements"] = sorted({*a["entitlements"], f"{e['department']}.admin"})
        a["last_access_review"] = None if days is None else self.day(days)
        return a["login"]


def build() -> list:
    out = []

    def add(sid, label, entity, brand, seed, n, leavers, plant, tests):
        rng = random.Random(seed)
        as_of = date(2026, 11, 2)
        domain = brand
        employees, accounts = _base(rng, domain, n, as_of, leavers)
        ed = _Edit(rng, employees, accounts, as_of)
        planted = plant(ed, domain)
        sc = {"id": sid, "label": label, "entity": entity, "system": "Registre RH et habilitations (cycle de vie des accès)",
              "tests": tests, "as_of": as_of.isoformat(), "entitlements": ENTITLEMENTS,
              "employees": sorted(employees, key=lambda e: e["employee_id"]),
              "accounts": sorted(accounts, key=lambda a: a["login"]), "notes": []}
        sc["expected_offenders"] = offenders(sc)
        sc["expected"] = expected(sc)
        want = {r: sorted(v) for r, v in planted.items()}
        assert sc["expected_offenders"] == {r: want.get(r, []) for r in RULES}, (sid, sc["expected_offenders"], want)
        out.append(sc)

    def kerlann(ed, d):
        p = {"PSI-5.1": [ed.leaver(3), ed.leaver(45, late=True), ed.leaver(200, late=True)],
             "PSI-5.2": [ed.orphan(), ed.service_owner_left("svc-export-compta", d)],
             "PSI-5.3": [ed.dormant(91), ed.dormant(150, late=True), ed.dormant(400, late=True)],
             "PSI-5.4": [ed.sod(SOD_PAIRS[0], late=True), ed.sod(SOD_PAIRS[1])],
             "PSI-5.5": [ed.mover(31), ed.mover(120)],
             "PSI-5.6": [ed.review(366, late=True), ed.review(None)]}
        p["PSI-5.3"].append(p["PSI-5.1"][2])           # parti depuis 200 jours et toujours actif : aussi dormant
        near(ed)
        return p

    def near(ed):
        """Jumeaux conformes de chaque cas."""
        ed.leaver(0)                      # dernier jour aujourd'hui : encore salarié
        ed.leaver(-20)                    # départ annoncé, à venir
        ed.leaver(30, enabled=False)      # parti, compte désactivé
        ed.orphan(enabled=False)          # compte sans salarié, mais désactivé
        ed.dormant(90)                    # 90 jours pile
        ed.sod(SOD_PAIRS[0], enabled=False)
        ed.cross()
        ed.mover(30)                      # mutation il y a 30 jours pile : délai non échu
        ed.mover(200, keep_old=False)     # mutation ancienne, anciens droits retirés
        ed.review(365)                    # revue il y a 365 jours pile

    def oceane(ed, d):
        near(ed)
        return {}

    def menhir(ed, d):
        p = {"PSI-5.1": [ed.leaver(9, late=True)], "PSI-5.4": [ed.sod(SOD_PAIRS[1], late=True)]}
        near(ed)
        return p

    add("lc-01-kerlann", "Cycle de vie des accès non conforme, 430 salariés", "Banque Kerlann (fictive)",
        "kerlann-banque.example", 5101, 430, 28, kerlann,
        "6 règles en défaut : 3 partants encore actifs, 2 comptes orphelins, comptes dormants, 2 cumuls de droits "
        "incompatibles, 2 mutations non nettoyées, 2 revues d'accès en retard ; 10 cas presque fautifs à côté.")
    add("lc-02-oceane", "Cycle de vie des accès conforme, cas limites seulement", "Crédit Océane (fictif)",
        "credit-oceane.example", 5102, 380, 22, oceane,
        "Aucun constat attendu : départ le jour même, départ à venir, 90 et 365 jours pile, mutation de 30 jours, "
        "comptes fautifs mais désactivés.")
    add("lc-03-menhir", "Cycle de vie des accès mixte : un partant et un cumul, loin dans l'annuaire",
        "Menhir Finance (fictive)", "menhir-finance.example", 5103, 250, 15, menhir,
        "2 règles en défaut, un seul compte chacune, tous deux hors de la première page : une lecture partielle "
        "conclut à tort « conforme ».")
    return out


def load() -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("*.json"))}


if __name__ == "__main__":
    DIR.mkdir(exist_ok=True)
    for sc in build():
        (DIR / f"{sc['id']}.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(sc["id"], len(sc["employees"]), len(sc["accounts"]), sc["expected"],
              {r: len(v) for r, v in sc["expected_offenders"].items()})
