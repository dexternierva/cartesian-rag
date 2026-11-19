"""The Search station: find products by description.

    question -> KEYWORD list + MEANING list -> FUSION -> top 5 -> ticket

Three modes, so we can measure each detective alone and together:
    keyword   BM25 only            (no AI needed)
    meaning   embeddings only      (needs Ollama + an embedding model)
    hybrid    both, fused with RRF (the case study's design)
"""
import time
import uuid
from datetime import datetime, timezone

from bm25 import BM25
from db import connect

TOP_K = 5
RRF_K = 60     # the standard constant for Reciprocal Rank Fusion

_index = None  # built once, on first search


def row_to_text(p) -> str:
    """ROW-LEVEL SERIALIZATION: turn one table row into one searchable sentence.

    We keep the column names as labels ("Material: Breathable mesh") so the
    meaning of each value isn't lost. A row cut into loose words would forget
    that 'Navy' is a colour and '4D' is an armrest type.
    """
    parts = [f"Product: {p['name']}", f"Category: {p['category']}", f"Color: {p['color']}"]
    if p["material"]:
        parts.append(f"Material: {p['material']}")
    if p["armrests"] and p["armrests"] != "None":
        parts.append(f"Armrests: {p['armrests']}")
    parts.append(f"Description: {p['description']}")
    return " | ".join(parts)


def _build_index():
    global _index
    if _index is None:
        con = connect()
        products = [dict(r) for r in con.execute("SELECT * FROM products ORDER BY sku")]
        con.close()
        texts = [row_to_text(p) for p in products]
        _index = {"products": products, "texts": texts, "bm25": BM25(texts), "vectors": None}
    return _index


def _ranking(scores: list) -> list:
    """Indexes of documents from best to worst, ignoring zero scores."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [i for i in order if scores[i] > 0]


def search(question: str, mode: str = "hybrid", k: int = TOP_K) -> list:
    """Return the top-k products as dicts: sku, name, score, and each detective's rank."""
    index = _build_index()
    products = index["products"]

    keyword_rank, meaning_rank = [], []
    if mode in ("keyword", "hybrid"):
        keyword_rank = _ranking(index["bm25"].scores(question))
    if mode in ("meaning", "hybrid"):
        from embedder import cosine, embed_documents, embed_query
        if index["vectors"] is None:
            index["vectors"] = embed_documents([p["sku"] for p in products], index["texts"])
        q_vec = embed_query(question)
        meaning_rank = _ranking([cosine(q_vec, v) for v in index["vectors"]])

    # FUSION with Reciprocal Rank Fusion (RRF):
    # each detective gives a product 1 / (60 + its rank). Add the two up.
    # A product both detectives rank highly beats one only a single detective likes.
    # We use RANKS, not raw scores, because the two detectives score on
    # completely different scales (like judging by stars vs by percent).
    fused = {}
    for ranking in (keyword_rank, meaning_rank):
        for position, doc_index in enumerate(ranking, start=1):
            fused[doc_index] = fused.get(doc_index, 0.0) + 1.0 / (RRF_K + position)

    # GROUP BY FAMILY: the same chair in 3 colours should take ONE slot, not three.
    # (On screen, colours are buttons on one product card, so the list should match.)
    results, seen = [], set()
    for i in sorted(fused, key=fused.get, reverse=True):
        family = products[i]["family"]
        if family in seen:
            continue
        seen.add(family)
        siblings = [p for p in products if p["family"] == family]
        results.append({
            "sku": products[i]["sku"],
            "name": products[i]["name"],
            "color": products[i]["color"],
            "score": round(fused[i], 5),
            "keyword_rank": keyword_rank.index(i) + 1 if i in keyword_rank else None,
            "meaning_rank": meaning_rank.index(i) + 1 if i in meaning_rank else None,
            "variants": [{"color": s["color"], "sku": s["sku"]} for s in siblings],
            "_row": products[i],
        })
        if len(results) == k:
            break
    return results


def _status(available: int) -> str:
    return "in_stock" if available >= 10 else ("low_stock" if available > 0 else "out_of_stock")


# Words that appear in many product names and say little about WHICH product.
_GENERIC = {"chair", "chairs", "desk", "desks", "office", "pro", "task", "show", "find", "looking"}


def ambiguous_families(question: str) -> list:
    """"Did you mean...?" check.

    Take the question's DISTINCTIVE words that appear in product names
    ("shell" in "Show me the navy shell"). If several product families from
    DIFFERENT categories all contain them, the question is ambiguous:
    a shell chair, a shell jacket and a shell side chair are different things.
    Returns one representative row per family, or [] if not ambiguous.
    """
    from bm25 import tokenize
    index = _build_index()
    colors = {p["color"].lower() for p in index["products"] if p["color"]}
    name_words = {w for p in index["products"] for w in tokenize(p["name"])}
    terms = [w for w in tokenize(question) if w in name_words and w not in _GENERIC and w not in colors]
    if not terms:
        return []
    families = {}
    for p in index["products"]:
        if all(t in tokenize(p["name"]) for t in terms):
            families.setdefault(p["family"], p)
    if len(families) >= 2 and len({p["category"] for p in families.values()}) >= 2:
        return list(families.values())
    return []


def answer_with_search(question: str, mode: str = "hybrid") -> dict:
    """Search, then pack the results into a contract ticket with product cards."""
    started = time.perf_counter()
    hits = search(question, mode)
    retrieval_ms = (time.perf_counter() - started) * 1000
    read_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    con = connect()
    components, citations = [], []
    for n, hit in enumerate(hits[:3], start=1):          # cards for the top 3
        p = hit["_row"]
        stock = con.execute(
            "SELECT depot_id, depot_name, available FROM stock_available WHERE sku = ? "
            "ORDER BY available DESC LIMIT 1", (p["sku"],)).fetchone()
        specs = [s for s in (p["material"],
                             f"{p['armrests']} armrests" if p["armrests"] and p["armrests"] != "None" else None,
                             f"{int(p['weight_rating_lb'])} lb rating" if p["weight_rating_lb"] else None) if s]
        cid = f"c{n}"
        sql = f"SELECT * FROM products WHERE sku = '{p['sku']}'"
        citations.append({
            "id": cid, "kind": "db_row", "database": "store.db", "table": "products",
            "row_key": {"sku": p["sku"]},
            "fields": {c: p[c] for c in ("sku", "name", "category", "color", "unit_price", "material", "description")},
            "sql": sql, "read_at": read_at,
            "confidence": 1.0,
        })
        components.append({
            "type": "product_card", "sku": p["sku"], "name": p["name"], "color": p["color"],
            "unit_price": p["unit_price"], "currency": "USD", "specs": specs,
            "variants": hit["variants"],
            "stock": {"status": _status(stock["available"]) if stock else "out_of_stock",
                      "available": stock["available"] if stock else 0,
                      "depot_id": stock["depot_id"] if stock else "none",
                      "depot_name": stock["depot_name"] if stock else "No depot"},
            "citation_ids": [cid],
        })
    con.close()

    candidates = ambiguous_families(question)
    if candidates:
        # Different kinds of product match equally well: ask instead of guessing.
        components = [{"type": "choices", "prompt": "Pick a match", "options": [
            {"label": p["name"], "description": f"{p['category']} · {p['color']} · ${p['unit_price']:,.0f}",
             "follow_up_question": f"Show me the {p['color'].lower()} {p['name']}"}
            for p in candidates[:5]]}]
        citations = []

    return {
        "contract_version": "0.1",
        "query_id": "q_" + uuid.uuid4().hex[:10],
        "question": question,
        "route": "search",
        "state": "disambiguate" if candidates else ("answer" if hits else "no_results"),
        "confidence": 0.7 if candidates else (0.8 if hits else 0.9),
        "message": (f"{len(candidates)} different kinds of product match that. Which one do you mean?" if candidates
                    else f"Here are the closest matches for \"{question}\"." if hits
                    else "No. Nothing in the store matches that right now."),
        "components": components,
        "citations": citations,
        "table": {"columns": ["rank", "sku", "name", "score", "keyword_rank", "meaning_rank", "family_skus"],
                  "rows": [[i, h["sku"], h["name"], h["score"], h["keyword_rank"], h["meaning_rank"],
                            ",".join(v["sku"] for v in h["variants"])]
                           for i, h in enumerate(hits, start=1)]},
        "trace": {"sql": None, "tries": 1, "writer": f"search ({mode})"},
        "timing_ms": {"retrieval": round(retrieval_ms, 1),
                      "total": round((time.perf_counter() - started) * 1000, 1)},
    }


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "keyword"
    q = " ".join(sys.argv[2:]) or "Stackable chairs for a waiting room"
    print(f"Mode: {mode}   Question: {q}\n")
    for i, h in enumerate(search(q, mode), start=1):
        print(f"{i}. {h['sku']:<12}{h['name']:<28}{h['color']:<9} score={h['score']}  "
              f"keyword#{h['keyword_rank']}  meaning#{h['meaning_rank']}")
