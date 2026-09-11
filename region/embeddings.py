"""Semantic search via embeddings.

Query: text-search-query model.
Document: text-search-doc model.
Threshold: 0.35 + gap 0.02.
"""

import json
import math
import os

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("YANDEX_API_KEY", "")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")

# Путь к embeddings.json: рядом с модулем, в region/data/
_this_dir = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(_this_dir, "data", "embeddings.json")
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", DEFAULT_PATH)

EMBED_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"

CONFIDENCE_THRESHOLD = 0.35
GAP_THRESHOLD = 0.02

_embeddings: dict[str, list[float]] | None = None


def _debug_enabled() -> bool:
    return os.getenv("DEBUG_SEARCH", "").lower() in ("1", "true", "yes")


def _log(msg: str) -> None:
    if _debug_enabled():
        print(f"[search] {msg}")


def _load_embeddings() -> dict[str, list[float]]:
    global _embeddings
    if _embeddings is None:
        if not os.path.exists(EMBEDDINGS_PATH):
            _log(f"embeddings.json не найден: {EMBEDDINGS_PATH}")
            _embeddings = {}
        else:
            with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
                _embeddings = json.load(f)
            _log(f"загружено {len(_embeddings)} эмбеддингов")
    return _embeddings


def _embed_query(text: str) -> list[float] | None:
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "modelUri": f"emb://{FOLDER_ID}/text-search-query/latest",
        "text": text,
    }
    try:
        r = requests.post(EMBED_URL, headers=headers, json=body, timeout=15)
    except requests.RequestException as e:
        _log(f"сеть: {e}")
        return None
    if r.status_code != 200:
        _log(f"HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        return r.json()["embedding"]
    except (KeyError, IndexError) as e:
        _log(f"парсинг: {e}")
        return None


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search_region(address: str) -> str | None:
    embeddings = _load_embeddings()
    if not embeddings:
        return None

    query_vec = _embed_query(address)
    if not query_vec:
        _log(f"не удалось получить эмбеддинг для {address!r}")
        return None

    scores = []
    for region, vec in embeddings.items():
        scores.append((region, _cosine(query_vec, vec)))
    scores.sort(key=lambda x: -x[1])

    if not scores:
        return None

    top_region, top_score = scores[0]
    second_score = scores[1][1] if len(scores) > 1 else 0.0
    gap = top_score - second_score

    _log(f"для {address!r}:")
    for region, score in scores[:3]:
        _log(f"    {score:.4f}  {region}")
    _log(f"    топ-1: {top_score:.4f} (порог {CONFIDENCE_THRESHOLD})")
    _log(f"    разрыв: {gap:.4f} (порог {GAP_THRESHOLD})")

    if top_score < CONFIDENCE_THRESHOLD:
        _log(f"    → None (ниже порога скора)")
        return None

    if gap < GAP_THRESHOLD:
        _log(f"    → None (разрыв слишком мал)")
        return None

    return top_region


if __name__ == "__main__":
    os.environ["DEBUG_SEARCH"] = "1"

    tests = [
        "г. Москва, ул. Ленина, 15",
        "Химки",
        "Новосибирск, ул. Кирова",
        "г. Сочи",
        "абракадабра",
        "ул. Ленина, дом 5",
    ]
    for addr in tests:
        region = search_region(addr)
        print(f"{addr!r:40} → {region!r}\n")