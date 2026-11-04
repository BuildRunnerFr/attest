"""SAM 3.1 : découpage en lots de 16 objets au plus (limite de l'API constatée sur une exécution réelle)."""
from PIL import Image

from attest import sam


def test_segment_boxes_lots_de_16(tmp_path, monkeypatch):
    img = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), "white").save(img)
    calls = []

    def fake_call(image, boxes, size):
        assert len(boxes) <= sam.MAX_OBJECTS, "plus de 16 objets envoyés en une requête"
        calls.append(len(boxes))
        return []                                   # aucun masque → repli boîte par boîte

    monkeypatch.setattr(sam, "_call_sam", fake_call)
    boxes = [(i, i, i + 10, i + 10) for i in range(37)]
    masks = sam.segment_boxes(img, boxes)
    assert calls == [16, 16, 5]
    assert len(masks) == 37
    assert masks[36][40:46, 40:46].all()            # la 37e boîte garde son propre masque


def test_segment_boxes_mock_reel(tmp_path, monkeypatch):
    monkeypatch.setattr(sam.llm, "BACKEND", "mock")
    img = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), "white").save(img)
    boxes = [(10 * i, 5, 10 * i + 8, 20) for i in range(20)]
    masks = sam.segment_boxes(img, boxes)
    assert len(masks) == 20 and all(m.any() for m in masks)


def test_backend_local_n_appelle_pas_l_api(tmp_path, monkeypatch):
    """Mode confidentiel : même avec une clé dans .env, la capture ne part pas vers l'API Meta."""
    monkeypatch.setattr(sam.llm, "BACKEND", "local")
    monkeypatch.setenv("MODEL_API_KEY", "x")
    def boom(*a, **k):
        raise AssertionError("client de l'API Meta créé en mode local")
    monkeypatch.setattr(sam.llm, "meta_client", boom)
    img = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), "white").save(img)
    masks = sam.segment_boxes(img, [(10, 10, 50, 30)])
    assert len(masks) == 1
