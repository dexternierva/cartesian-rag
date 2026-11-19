"""The AI form filler: a local model reads the question and fills in the form.

This is a much EASIER job than writing SQL:
    - no tables, no joins, no SQL syntax
    - every field has a short list of allowed values
    - our tested code turns the form into SQL afterwards

Settings: uses the same OLLAMA_MODEL / OLLAMA_URL as the SQL writer.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from extractors.vocab import (ARMRESTS, CATEGORIES, COLORS, DESTINATIONS,  # noqa: E402
                              INTENTS, MATERIAL_KEYWORDS, PRODUCT_NAMES)
from writers.ollama_writer import OLLAMA_MODEL, _chat  # noqa: E402

EMPTY_FORM = {"follow_up": False, "intent": None, "product_name": None, "category": None, "color": None,
              "material": None, "armrests": None, "max_unit_price": None, "quantity": None,
              "single_depot": None, "destination_city": None, "max_delivery_days": None}

RULES = f"""You read shopping questions and fill in a search form. You never write SQL.

Reply with JSON only. Possible keys: {", ".join(EMPTY_FORM)}.
Write ONLY the keys the question gives a value for. Leave every other key out completely
(do not write null). Never guess.

ALLOWED VALUES (copy them exactly; anything else must be null)
- intent: {", ".join(INTENTS)}
    find_products = they want matching products; total_cost = price x quantity; average_price = an average
- product_name: ONLY if the person names one of these exact products: {", ".join(PRODUCT_NAMES)}
    If they DESCRIBE a product ("ergonomic mesh chair"), product_name is null; use category/material/armrests instead.
- category: {", ".join(CATEGORIES)}
- color: {", ".join(COLORS)}
- material: one keyword from: {", ".join(MATERIAL_KEYWORDS)}
- armrests: {", ".join(ARMRESTS)}
- destination_city: {", ".join(DESTINATIONS)}
- max_unit_price, quantity, max_delivery_days: numbers
- single_depot: true if all units must come from one warehouse, false if they don't mind, null if not said
- follow_up: write "follow_up": true only if the question refers back to the previous request ("same chairs", "those")
"""


def _filled_only(form: dict) -> dict:
    """Drop empty boxes. SPEED: the model writes ~8 tokens per second on a CPU,
    so every '"material": null' it doesn't have to write saves real time."""
    return {k: v for k, v in form.items() if v not in (None, False)}

# Solved examples. None of them is a test question (that would be cheating).
EXAMPLES = [
    ("Looking for 12 white standing desks under $600 that can reach Austin in 2 days.",
     {**EMPTY_FORM, "intent": "find_products", "category": "Desks", "color": "White", "max_unit_price": 600,
      "quantity": 12, "destination_city": "Austin", "max_delivery_days": 2}),
    ("What would 5 black Duo Monitor Arms cost altogether?",
     {**EMPTY_FORM, "intent": "total_cost", "product_name": "Duo Monitor Arm", "color": "Black", "quantity": 5}),
    ("Average price of leather office chairs?",
     {**EMPTY_FORM, "intent": "average_price", "category": "Office chairs", "material": "leather"}),
    ("I need 30 grey fabric chairs with 3D arms, any warehouse is fine.",
     {**EMPTY_FORM, "intent": "find_products", "category": "Office chairs", "color": "Grey", "material": "fabric",
      "armrests": "3D", "quantity": 30, "single_depot": False}),
]


def extract(question: str, previous: dict = None) -> dict:
    messages = [{"role": "system", "content": RULES}]
    for q, form in EXAMPLES:
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": json.dumps(_filled_only(form))})
    if previous:
        messages.append({"role": "user", "content":
                         f"(Context: the previous request's form was {json.dumps(previous)})\n{question}"})
    else:
        messages.append({"role": "user", "content": question})
    try:
        form = json.loads(_chat(messages))
    except json.JSONDecodeError:
        return {}
    return form if isinstance(form, dict) else {}


def warm_up() -> float:
    t0 = time.perf_counter()
    extract("Looking for 3 black writing desks under $300.")
    return time.perf_counter() - t0


extract.label = f"ollama form-filler ({OLLAMA_MODEL})"
