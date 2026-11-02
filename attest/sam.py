"""SAM 3.1 : transformer une boîte approximative (donnée par Muse Spark) en masque précis.

Format de requête et de réponse : https://dev.meta.ai/docs/sam/segmenting et /reading-segmentation
Les masques sont décodés avec le parseur officiel `meta-sam-parser`.
"""
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image

from . import llm

RECORD = re.compile(r"(\d+)<\|box;([^|]*)\|><\|mask;([^|]*)\|>")


def _fields(body: str) -> dict:
    out = {}
    for part in body.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v
    return out


def parse(output_text: str) -> list[dict]:
    """Analyse la sortie texte de SAM. Renvoie [{id, box:(x1,y1,x2,y2), mask: ndarray bool (box-local)}]."""
    from meta_sam_parser import SegmentationMask, decode_mask_to_raster

    objects = []
    for line in output_text.strip().splitlines():
        for obj_id, box_body, mask_body in RECORD.findall(line):
            box = _fields(box_body)
            data = _fields(mask_body)["data"]           # "<H>,<W>,<enc>payload"
            h, w, payload = data.split(",", 2)
            enc = "lossless" if payload.startswith("~") else "one_bit"
            raster = decode_mask_to_raster(SegmentationMask(enc, payload, int(w), int(h)))
            mask = np.frombuffer(raster, dtype=np.uint8).reshape(int(h), int(w)).astype(bool)
            objects.append({
                "id": int(obj_id),
                "box": tuple(int(float(box[k])) for k in ("x1", "y1", "x2", "y2")),
                "confidence": float(box["c"]) if "c" in box else None,
                "mask": mask,
            })
    return objects


def full_mask(obj: dict, size: tuple[int, int]) -> np.ndarray:
    """Replace le masque (local à la boîte) dans une image pleine taille."""
    W, H = size
    x1, y1, x2, y2 = obj["box"]
    out = np.zeros((H, W), dtype=bool)
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    local = Image.fromarray(obj["mask"].astype(np.uint8) * 255).resize((bw, bh), Image.NEAREST)
    out[y1:y1 + bh, x1:x1 + bw] = (np.array(local) > 127)[: H - y1, : W - x1]
    return out


def segment_boxes(image: Path, boxes: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
    """Un masque pleine taille par boîte. En cas d'échec de SAM, renvoie la boîte elle-même."""
    size = Image.open(image).size
    if not boxes:
        return []
    try:
        objs = _call_sam(image, boxes, size)
        by_id = {o["id"]: full_mask(o, size) for o in objs}
        return [by_id.get(i + 1, _box_mask(b, size)) for i, b in enumerate(boxes)]
    except Exception as e:  # la démo ne doit jamais casser sur SAM
        print(f"  [SAM] repli sur les boîtes : {e}")
        return [_box_mask(b, size) for b in boxes]


def _box_mask(b, size):
    W, H = size
    m = np.zeros((H, W), dtype=bool)
    m[max(0, b[1]):b[3], max(0, b[0]):b[2]] = True
    return m


def _call_sam(image: Path, boxes, size) -> list[dict]:
    W, H = size
    prompt = "<0f>" + ",".join(
        f"{i + 1}<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={W};h={H}|>"
        for i, (x1, y1, x2, y2) in enumerate(boxes))

    if llm.BACKEND == "mock" or not os.getenv("MODEL_API_KEY"):
        from . import mock
        llm.USAGE.add("sam-3.1 (mock)", "segment", images=1)
        return parse(mock.sam_output(boxes, size))

    import time
    t0 = time.time()

    public = os.getenv("PUBLIC_EVIDENCE_BASE_URL")  # si l'API refuse les data: URL
    image_url = f"{public.rstrip('/')}/{image.parent.name}/{image.name}" if public else llm.data_url(image)
    r = llm.meta_client().responses.create(
        model="sam-3.1",
        input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": image_url},
        ]}],
        metadata={"mask_encoding": "one_bit", "include_confidence": "true"},
    )
    llm.USAGE.add("sam-3.1", "segment", seconds=time.time() - t0, images=1)
    return parse(r.output_text)
