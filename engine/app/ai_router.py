"""The AI tie-breaker for the router: used ONLY when the rules found nothing.

WHY (real result, 2026-11-12)
    The rules router scored 35/35 on questions it was written for, but 4/8 on
    fresh ones, and ALL four misses fell into its default bucket ("search").
    Two of them were upset customers who would have been shown a product list.

THE DESIGN: rules first, AI only for the leftovers
    - Most questions match a rule -> answered in microseconds, no AI.
    - Questions the rules can't place -> the AI picks ONE word from four.
    Writing one word is the cheapest thing a model can do (the stopwatch showed
    writing is the slow part), so this costs roughly 1-2 seconds, only when needed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from writers.ollama_writer import _chat  # noqa: E402

STATIONS = ["handoff", "sql", "hybrid", "search"]

RULES = """You sort customer messages for an online office-furniture store into ONE station.

- handoff: the customer is upset, complaining, has a problem with an order or item, or wants a person.
- sql: a simple fact lookup: a count, a price, a status, which warehouse, the cheapest or priciest item.
- hybrid: shopping with rules to apply: a quantity, a budget, a deadline, a destination, or a total cost.
- search: finding a product by description, with no numbers or rules.

Reply with JSON only: {"station": "<one of: handoff, sql, hybrid, search>"}
"""

# Solved examples. None of these is a test question.
EXAMPLES = [
    ("The armrest snapped off after two days, what are you going to do about it?", "handoff"),
    ("How many white lamps are in Dallas?", "sql"),
    ("Need fifteen black desks under $400 by Friday", "hybrid"),
    ("something cosy for a reading corner", "search"),
]


def classify(question: str):
    """Return one station name, or None if the model's reply can't be used."""
    messages = [{"role": "system", "content": RULES}]
    for q, station in EXAMPLES:
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": json.dumps({"station": station})})
    messages.append({"role": "user", "content": question})
    try:
        station = json.loads(_chat(messages)).get("station", "")
    except (json.JSONDecodeError, AttributeError):
        return None
    station = str(station).strip().lower()
    return station if station in STATIONS else None     # never trust a label we didn't offer
