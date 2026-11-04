"""Chaque référence réglementaire citée (catalogues de contrôles, colonne « Fondement » des politiques)
doit pointer vers un article / paragraphe / point présent dans la bibliothèque `exigences/library`.

La bibliothèque est la seule source des extraits réglementaires : une référence qui n'y figure pas
(ex. l'ancien « RTS 21(3) ») ne peut pas être montrée à l'auditeur et doit être corrigée."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "exigences" / "library"

ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}
REF = re.compile(r"(\d+)((?:\([0-9a-z]+\))+)")


def library_anchors() -> set[tuple]:
    """Ancres (texte, article, paragraphe, point, sous-point) lues dans les extraits DORA / RTS.

    Formats reconnus : titre « # DORA — article 9(4) … », ligne « Article 21(1): … »,
    lignes « (c) … » (point) et « (ii) … » (sous-point romain du point courant)."""
    anchors: set[tuple] = set()
    for f in sorted(LIB.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        head = lines[0] if lines else ""
        reg = "DORA" if head.startswith("# DORA") else "RTS" if head.startswith("# RTS") else None
        if reg is None:          # politique interne : pas un texte réglementaire
            continue
        art = para = point = None
        m = re.search(r"article (\d+)\((\d+)\)", head, re.I)
        if m:
            art, para = m.groups()
            anchors.add((reg, art, para))
        for line in lines[1:]:
            line = line.strip()
            m = re.match(r"Article (\d+)\((\d+)\)\s*:", line)
            if m:
                art, para = m.groups()
                point = None
                anchors.add((reg, art, para))
                continue
            m = re.match(r"\(([a-z]+)\)\s", line)
            if not m or art is None:
                continue
            tok = m.group(1)
            # « (i) » est un sous-point romain s'il suit un point lettré (sauf juste après « (h) »)
            if tok in ROMAN and point is not None and not (tok == "i" and point == "h"):
                anchors.add((reg, art, para, point, tok))
            else:
                point = tok
                anchors.add((reg, art, para, point))
    return anchors


def parse_refs(text: str) -> list[tuple]:
    """« DORA 9(4)(d) ; RTS 21(1)(c) et 21(1)(e)(ii) » → [("DORA","9","4","d"), ("RTS","21","1","c"), …].

    Une mention entre parenthèses avec espace (« (bonnes pratiques) ») n'est pas une subdivision."""
    out = []
    for part in re.split(r"[;\n]", text):
        m = re.search(r"\b(DORA|RTS)\b", part)
        if not m:
            continue
        reg = m.group(1)
        for num, subs in REF.findall(part[m.end():]):
            out.append((reg, num, *re.findall(r"\(([0-9a-z]+)\)", subs)))
    return out


def control_refs() -> list[tuple[str, str]]:
    out = []
    for f in sorted((ROOT / "controls").glob("*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")).get("controls", []):
            for r in c.get("references") or []:
                out.append((f"{f.name}:{c.get('id')}", r))
    return out


def policy_refs() -> list[tuple[str, str]]:
    """Colonne « Fondement » (ou « Basis ») des tableaux de politique dans exigences/."""
    out = []
    for f in sorted((ROOT / "exigences").rglob("*.md")):
        col = None
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                col = None
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if col is None:
                low = [c.lower() for c in cells]
                col = next((i for i, c in enumerate(low) if c in ("fondement", "basis")), None)
                continue
            if col < len(cells) and not set(cells[col]) <= set("-: "):
                out.append((f"{f.relative_to(ROOT)}:{cells[0]}", cells[col]))
    return out


def test_parser_reads_library_points():
    a = library_anchors()
    assert ("RTS", "21", "1", "c") in a
    assert ("RTS", "21", "1", "e", "ii") in a
    assert ("RTS", "12", "2", "c", "i") in a
    assert ("DORA", "9", "4", "e") in a
    assert ("RTS", "21", "3") not in a
    assert parse_refs("DORA 9(4)(d) (bonnes pratiques)") == [("DORA", "9", "4", "d")]
    assert parse_refs("RTS 6(3) et 6(4)") == [("RTS", "6", "3"), ("RTS", "6", "4")]


def test_references_found():
    assert len(control_refs()) >= 7
    assert len(policy_refs()) >= 14


@pytest.mark.parametrize("where,ref", control_refs() + policy_refs())
def test_reference_resolves_to_library(where, ref):
    anchors = library_anchors()
    parsed = parse_refs(ref)
    assert parsed, f"{where}: aucune référence DORA/RTS lisible dans « {ref} »"
    for r in parsed:
        assert len(r) >= 3, f"{where}: « {ref} » ne précise pas le paragraphe"
        assert r in anchors, f"{where}: « {ref} » → {r} absent de exigences/library"
