"""Accès aux modèles.

Trois backends (variable ATTEST_BACKEND) :
- meta  : Meta Model API (https://api.meta.ai/v1), Muse Spark / Muse Wonder / SAM 3.1
- local : un serveur compatible OpenAI que tu héberges (Muse Glimmer via llama.cpp `llama-server`,
          vLLM ou SGLang). SAM reste appelé via l'API Meta si MODEL_API_KEY est défini.
- mock  : réponses préenregistrées, pour tester tout le pipeline sans clé.
"""
import base64
import json
import mimetypes
import os
import re
from pathlib import Path

BACKEND = os.getenv("ATTEST_BACKEND", "mock")
META_BASE_URL = os.getenv("META_BASE_URL", "https://api.meta.ai/v1")
MODEL_REASON = os.getenv("ATTEST_MODEL_REASON", "muse-spark-1.3")   # plan, vérification, remédiation
MODEL_CODE = os.getenv("ATTEST_MODEL_CODE", "muse-spark-1.3")      # génération des scripts de contrôle
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "muse-glimmer")


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def meta_client():
    from openai import OpenAI
    return OpenAI(base_url=META_BASE_URL, api_key=os.environ["MODEL_API_KEY"])


def _local_client():
    from openai import OpenAI
    return OpenAI(base_url=LOCAL_BASE_URL, api_key=os.getenv("LOCAL_API_KEY", "none"))


def ask(task: str, system: str, user: str, image: Path | None = None, code: bool = False,
        mock_ctx: dict | None = None) -> str:
    """Envoie une requête texte (+ image éventuelle) et renvoie le texte de la réponse."""
    if BACKEND == "mock":
        from . import mock
        return mock.answer(task, user, mock_ctx or {})

    if BACKEND == "local":
        content = [{"type": "text", "text": user}]
        if image:
            content.append({"type": "image_url", "image_url": {"url": data_url(image)}})
        r = _local_client().chat.completions.create(
            model=LOCAL_MODEL, temperature=0.1,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
        return r.choices[0].message.content

    # Meta Model API, via l'API Responses (format documenté sur dev.meta.ai)
    content = [{"type": "input_text", "text": user}]
    if image:
        content.append({"type": "input_image", "image_url": data_url(image)})
    r = meta_client().responses.create(
        model=MODEL_CODE if code else MODEL_REASON,
        instructions=system,
        input=[{"type": "message", "role": "user", "content": content}],
    )
    return r.output_text


def extract_json(text: str):
    """Récupère le premier objet ou tableau JSON d'une réponse de modèle."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise ValueError(f"pas de JSON dans la réponse : {text[:200]}")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"
