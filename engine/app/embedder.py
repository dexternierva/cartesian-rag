"""Embeddings: the meaning detective.

THE IDEA
    An embedding model turns a piece of text into a long list of numbers
    (a "vector"), like GPS coordinates for MEANING. Texts about similar
    things land close together on the map, even with different words:

        "desk lamp"   -> [0.12, -0.80, 0.33, ...]   } close together
        "a light"     -> [0.10, -0.77, 0.35, ...]   }
        "USB cable"   -> [-0.64, 0.21, 0.02, ...]   <- far away

    To search, we turn the question into coordinates too and find the
    nearest products. "Nearness" is measured with cosine similarity:
    1.0 = same direction (same meaning), 0 = unrelated.

SETTINGS (environment variables, optional)
    OLLAMA_EMBED_MODEL   default: nomic-embed-text   (ollama pull nomic-embed-text)
    OLLAMA_URL           default: http://localhost:11434

Product embeddings are saved to data/embeddings-<model>.json so they are
computed once, not on every search.
"""
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"

# nomic-embed-text was trained with these labels in front of the text;
# using them gives better matches. Other models don't need them.
_DOC_PREFIX = "search_document: " if EMBED_MODEL.startswith("nomic") else ""
_QUERY_PREFIX = "search_query: " if EMBED_MODEL.startswith("nomic") else ""


def _embed(texts: list) -> list:
    """Ask Ollama for the vectors of several texts at once."""
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode("utf-8")
    request = urllib.request.Request(f"{OLLAMA_URL}/api/embed", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))["embeddings"]
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "ignore")[:200]
        raise SystemExit(f"Ollama embedding error ({err.code}): {detail}\n"
                         f"Is the model downloaded?  Try:  ollama pull {EMBED_MODEL}")
    except urllib.error.URLError:
        raise SystemExit(f"Could not reach Ollama at {OLLAMA_URL}. Is Ollama running?")


def embed_query(text: str) -> list:
    return _embed([_QUERY_PREFIX + text])[0]


def embed_documents(doc_ids: list, texts: list) -> list:
    """Vectors for all products, using the saved file when the text hasn't changed."""
    slug = re.sub(r"[^a-z0-9]+", "-", EMBED_MODEL.lower()).strip("-")
    cache_file = CACHE_DIR / f"embeddings-{slug}.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}

    def key(doc_id, text):                      # changes whenever the text changes
        return doc_id + ":" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

    missing = [(i, t) for i, t in zip(doc_ids, texts) if key(i, t) not in cache]
    if missing:
        print(f"  (computing embeddings for {len(missing)} products with {EMBED_MODEL} ...)")
        vectors = _embed([_DOC_PREFIX + t for _, t in missing])
        for (doc_id, text), vector in zip(missing, vectors):
            cache[key(doc_id, text)] = vector
        cache_file.write_text(json.dumps(cache), encoding="utf-8")
    return [cache[key(i, t)] for i, t in zip(doc_ids, texts)]


def cosine(a: list, b: list) -> float:
    """How close two meanings are: 1.0 = same direction, 0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0
