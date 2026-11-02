"""Accès aux modèles, avec mesure des jetons et du coût de chaque appel.

Trois backends (variable ATTEST_BACKEND) :
- meta  : Meta Model API (https://api.meta.ai/v1) — Muse Spark + SAM 3.1
- local : serveur compatible OpenAI que la banque héberge (Muse Glimmer via llama.cpp `llama-server`,
          vLLM ou SGLang) : aucune donnée d'audit ne sort du SI. SAM via l'API si MODEL_API_KEY est défini.
- mock  : réponses préenregistrées, pour développer et tester sans clé.
"""
import base64
import json
import mimetypes
import os
import re
import threading
import time
from collections import defaultdict
from pathlib import Path

from . import config

BACKEND = os.getenv("ATTEST_BACKEND", "mock")
META_BASE_URL = os.getenv("META_BASE_URL", "https://api.meta.ai/v1")
MODEL_REASON = os.getenv("ATTEST_MODEL_REASON", "muse-spark-1.3")   # plan, vérification visuelle, remédiation
MODEL_CODE = os.getenv("ATTEST_MODEL_CODE", "muse-spark-1.3")      # écriture des scripts de test
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "muse-glimmer")


# ---------- mesure de l'usage ----------

class Usage:
    def __init__(self):
        self._lock = threading.Lock()
        self.by_model = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "seconds": 0.0, "images": 0})
        self.by_task = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0})
        self.estimated = BACKEND == "mock"

    def reset(self):
        with self._lock:
            self.by_model.clear()
            self.by_task.clear()

    def add(self, model, task, inp=0, out=0, seconds=0.0, images=0):
        with self._lock:
            m = self.by_model[model]
            m["calls"] += 1; m["input"] += inp; m["output"] += out; m["seconds"] += seconds; m["images"] += images
            t = self.by_task[task]
            t["calls"] += 1; t["input"] += inp; t["output"] += out

    def cost(self) -> dict:
        prices = config.pricing()
        rows, total, unknown = [], 0.0, []
        for model, u in sorted(self.by_model.items()):
            p = prices.get("models", {}).get(model)
            img = prices.get("images", {}).get(model)
            if p:
                c = u["input"] / 1e6 * p["input"] + u["output"] / 1e6 * p["output"]
            elif img and img.get("known"):
                c = u["images"] * img["per_image"]
            else:
                c = None
                unknown.append(model)
            total += c or 0.0
            rows.append({"model": model, **u, "cost_usd": c})
        return {"rows": rows, "total_usd": total, "unpriced": unknown, "estimated": self.estimated}


USAGE = Usage()


# ---------- appels ----------

def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def meta_client():
    from openai import OpenAI
    return OpenAI(base_url=META_BASE_URL, api_key=os.environ["MODEL_API_KEY"], max_retries=5, timeout=180)


def _local_client():
    from openai import OpenAI
    return OpenAI(base_url=LOCAL_BASE_URL, api_key=os.getenv("LOCAL_API_KEY", "none"), max_retries=3, timeout=300)


def model_for(code: bool) -> str:
    if BACKEND == "local":
        return LOCAL_MODEL
    if BACKEND == "mock":
        return "mock"
    return MODEL_CODE if code else MODEL_REASON


def ask(task: str, system: str, user: str, image: Path | None = None, code: bool = False,
        mock_ctx: dict | None = None) -> str:
    """Envoie une requête texte (+ image éventuelle) et renvoie le texte de la réponse."""
    t0 = time.time()
    model = model_for(code)

    if BACKEND == "mock":
        from . import mock
        out = mock.answer(task, user, mock_ctx or {})
        USAGE.add("mock", task, (len(system) + len(user)) // 4 + (1500 if image else 0), len(out) // 4,
                  time.time() - t0)
        return out

    if BACKEND == "local":
        content = [{"type": "text", "text": user}]
        if image:
            content.append({"type": "image_url", "image_url": {"url": data_url(image)}})
        r = _local_client().chat.completions.create(
            model=model, temperature=0.1,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
        u = r.usage
        USAGE.add(model, task, getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0,
                  time.time() - t0)
        return r.choices[0].message.content

    # Meta Model API, via l'API Responses (format documenté sur dev.meta.ai)
    content = [{"type": "input_text", "text": user}]
    if image:
        content.append({"type": "input_image", "image_url": data_url(image)})
    r = meta_client().responses.create(
        model=model, instructions=system,
        input=[{"type": "message", "role": "user", "content": content}],
    )
    u = r.usage
    USAGE.add(model, task, getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0,
              time.time() - t0)
    return r.output_text


def extract_json(text: str):
    """Récupère le premier objet ou tableau JSON d'une réponse de modèle."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError(f"pas de JSON dans la réponse : {text[:200]}")
    obj, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    return obj


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"
