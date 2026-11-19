"""The no-AI baseline SQL writer: a handful of hand-written rules.

It works like a vending machine: it only understands the few buttons we
built. Press something else and nothing comes out. That is the point.
Its score is the "walking speed" we compare the AI writer against.

It knows 4 question shapes:
  A. "status of order NX-12345"            -> orders
  B. "delivery from <depot> to <city>"     -> delivery_times
  C. "how many <product> [in <city>]"      -> stock_available
  D. "what does <product> cost / price"    -> products
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import connect  # noqa: E402

# Load the store's vocabulary once: product names, colours, depot cities.
_con = connect()
_PRODUCT_NAMES = sorted({r[0] for r in _con.execute("SELECT DISTINCT name FROM products")}, key=len, reverse=True)
_COLORS = [r[0] for r in _con.execute("SELECT DISTINCT color FROM products WHERE color IS NOT NULL")]
_DEPOTS = [(r[0], r[1], r[2]) for r in _con.execute("SELECT depot_id, depot_name, city FROM depots")]
_DESTINATIONS = [r[0] for r in _con.execute("SELECT DISTINCT destination_city FROM delivery_times")]
_con.close()


def _find_product(q):
    """Return the product name mentioned in the question, if any."""
    for name in _PRODUCT_NAMES:                      # full name first: "AeroTask Pro Mesh"
        if name.lower() in q:
            return name
    for name in _PRODUCT_NAMES:                      # then its first word: "AeroTask"
        first = name.split()[0].lower()
        if len(first) >= 5 and re.search(rf"\b{re.escape(first)}\b", q):
            return name
    return None


def _find_color(q):
    for color in _COLORS:
        if re.search(rf"\b{color.lower()}\b", q):
            return color
    return None


def _find_depot(text):
    for depot_id, depot_name, city in _DEPOTS:
        if city.lower() in text or depot_name.lower() in text:
            return depot_id
    return None


def write_sql(question: str):
    q = question.lower()

    # A. order status
    m = re.search(r"\b(nx-\d+)\b", q)
    if m and "status" in q:
        return {"sql": f"SELECT order_id, status FROM orders WHERE order_id = '{m.group(1).upper()}'", "confidence": 0.95}

    # B. delivery time: "... from <depot> to <city> ..."
    m = re.search(r"from (.+?) to (.+)", q)
    if m and ("deliver" in q or "days" in q):
        depot = _find_depot(m.group(1))
        dest = next((d for d in _DESTINATIONS if d.lower() in m.group(2)), None)
        if depot and dest:
            return {"sql": f"SELECT days FROM delivery_times WHERE depot_id = '{depot}' AND destination_city = '{dest}'", "confidence": 0.9}

    product, color = _find_product(q), _find_color(q)
    if not product:
        return None                                   # the vending machine has no button for this
    where = f"p.name = '{product}'" + (f" AND p.color = '{color}'" if color else "")

    # C. stock: "how many ..."
    if "how many" in q:
        depot = _find_depot(q)
        if depot and "total" not in q and "across" not in q:
            return {"sql": ("SELECT s.available FROM stock_available s JOIN products p USING (sku) "
                            f"WHERE {where} AND s.depot_id = '{depot}'"), "confidence": 0.9}
        return {"sql": ("SELECT SUM(s.available) AS total_available FROM stock_available s "
                        f"JOIN products p USING (sku) WHERE {where}"), "confidence": 0.85}

    # D. price
    if "cost" in q or "price" in q:
        return {"sql": f"SELECT DISTINCT p.unit_price FROM products p WHERE {where}", "confidence": 0.9}

    return None


write_sql.label = "baseline (rules, no AI)"
