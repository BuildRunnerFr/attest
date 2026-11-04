"""Interprétation ANCRÉE d'un texte réglementaire (et/ou d'une politique) en programme de travail pour une cible.

Garde-fous, dans l'ordre où ils s'appliquent :
1. Ancrage : chaque exigence cite mot pour mot le texte ; la citation est vérifiée par du code, pas par le modèle.
   Citation introuvable → exigence rejetée, affichée comme telle, jamais auditée.
2. Origine des seuils : politique interne, standard public nommé (« proposition ») ou le texte lui-même.
3. Testabilité : « automatisable sur cette cible », « revue documentaire » ou « entretien ». Seule la première produit
   des tests ; les autres sont listées dans le rapport comme NON couvertes : Attest ne prétend pas tout auditer.
4. Validation humaine obligatoire avant l'audit (Attest Studio).
"""
import re
import unicodedata

from . import config, llm, prompts, targets
from .trail import sha256_text

TESTABILITY = {"automated", "document", "interview"}
_ELLIPSIS = re.compile(r"\s*(?:\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)\s*")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("«", '"'), ("»", '"'), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    s = re.sub(r"[`*_|]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


# négation (ou exception) qu'une coupure « […] » ne doit jamais faire disparaître
_NEGATION = re.compile(r"(?<!\w)(?:not|no|never|ne|pas|sauf|except|unless|without|sans|nor|ni)(?!\w)|(?<!\w)n'|n't(?!\w)")
_MIN_WORDS = 4


def verify_quote(quote: str, text: str) -> bool:
    """Vrai si la citation figure mot pour mot dans UN texte (un document, sans en-tête).

    Au plus une coupure « […] » (deux fragments, dans l'ordre), chaque fragment d'au moins 4 mots et aligné sur des
    limites de mots ; le passage omis entre les deux fragments ne doit contenir aucune négation ni exception.
    """
    t, q = _norm(text), _norm(quote)
    whole = q.strip(" \"'.;:,")                       # citation intégrale (le texte peut contenir « … » lui-même)
    if len(whole) >= 15 and len(whole.split()) >= _MIN_WORDS and \
            re.search(r"(?<!\w)" + re.escape(whole) + r"(?!\w)", t):
        return True
    parts = [p.strip(" \"'.;:,") for p in _ELLIPSIS.split(q)]
    parts = [p for p in parts if p]
    if not parts or len(parts) > 2 or sum(len(p) for p in parts) < 15:
        return False
    if any(len(p.split()) < _MIN_WORDS for p in parts):
        return False
    pats = [re.compile(r"(?<!\w)" + re.escape(p) + r"(?!\w)") for p in parts]
    for m in pats[0].finditer(t):
        if len(pats) == 1:
            return True
        m2 = pats[1].search(t, m.end())               # la plus proche : le passage omis le plus court
        if not m2:
            return False
        if not _NEGATION.search(t, m.end(), m2.start()):
            return True
    return False


def verify_quote_in(quote: str, texts: list) -> bool:
    """Vérification document par document : tous les fragments dans le même document, en-têtes « === » exclus."""
    return any(verify_quote(quote, body) for _, body in texts)


def interpret(texts: list, target_id: str) -> dict:
    """texts : liste de (titre, contenu). Renvoie exigences, contrôles proposés et couverture."""
    joined = "\n\n".join(f"=== {title} ===\n{body}" for title, body in texts)
    target = targets.get(target_id)
    raw = llm.ask("interpret", prompts.INTERPRET_SYSTEM,
                  prompts.INTERPRET_USER.format(texts=joined, target_label=targets.label(target_id),
                                                api_doc=targets.api_doc(target_id), lang=config.lang_name()),
                  mock_ctx={"texts": joined, "kind": target["kind"], "repo": target.get("repo", "")})
    data = llm.extract_json(raw)
    items = data.get("requirements", []) if isinstance(data, dict) else data
    requirements, n = [], 0
    for r in items:
        if not isinstance(r, dict):
            continue
        quote = str(r.get("quote", "")).strip()
        verified = verify_quote_in(quote, texts)
        testability = str(r.get("testability", "document")).lower()
        testability = testability if testability in TESTABILITY else "document"
        controls = []
        if verified and testability == "automated":
            for c in r.get("controls") or []:
                if not isinstance(c, dict):
                    continue
                n += 1
                c = dict(c, id=f"C{n}")
                c.setdefault("quote", quote)
                c.setdefault("references", [r.get("ref", "")])
                c.setdefault("evidence_page", target["default_page"])
                controls.append(c)
        cov = r.get("covered_by") or []
        requirements.append({"ref": str(r.get("ref", "")), "quote": quote, "quote_verified": verified,
                             "summary": str(r.get("summary", "")), "testability": testability,
                             "why": str(r.get("why", "")), "controls": controls,
                             "covered_by": [str(x) for x in (cov if isinstance(cov, list) else [cov]) if x]})
    # rattachement : une clause « automatisable » sans contrôle propre doit pointer un contrôle réellement proposé
    rules = {c.get("rule") for r in requirements for c in r["controls"]}
    for r in requirements:
        if r["quote_verified"] and r["testability"] == "automated" and not r["controls"]:
            r["covered_by"] = [x for x in r["covered_by"] if x in rules]
            if not r["covered_by"]:
                r["testability"] = "document"
                r["why"] = (r["why"] + " — " if r["why"] else "") + "aucun contrôle de rattachement proposé"
        elif r["controls"]:
            r["covered_by"] = []
    counts = {k: sum(1 for r in requirements if r["quote_verified"] and r["testability"] == k) for k in TESTABILITY}
    counts.update(requirements=len(requirements), rejected=sum(not r["quote_verified"] for r in requirements),
                  controls=n, covered=sum(1 for r in requirements if r["covered_by"]))
    return {"target": target_id, "texts": [t for t, _ in texts], "text_sha256": sha256_text(joined),
            "model": llm.model_for(False), "requirements": requirements, "counts": counts}
