"""The store's vocabulary, and a checker that keeps extracted values real.

An extractor (rules or AI) reads a question and fills in a FORM:
    {"color": "navy", "material": "mesh", "quantity": 40, ...}

Before any SQL is built, every value on the form is checked against the
real database vocabulary ("grounded"):
    "navy"            -> "Navy"            (fixed: same word, different case)
    "Ergonomic Chair" -> removed, noted    (not a real product name)
This is the same idea as the grounding check in the SQL station, applied
earlier: we check the FORM instead of the finished SQL.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import connect  # noqa: E402

_con = connect()
PRODUCT_NAMES = sorted({r[0] for r in _con.execute("SELECT DISTINCT name FROM products")})
COLORS = sorted({r[0] for r in _con.execute("SELECT DISTINCT color FROM products WHERE color IS NOT NULL")})
CATEGORIES = sorted({r[0] for r in _con.execute("SELECT DISTINCT category FROM products")})
ARMRESTS = sorted({r[0] for r in _con.execute(
    "SELECT DISTINCT armrests FROM products WHERE armrests IS NOT NULL AND armrests != 'None'")})
DESTINATIONS = sorted({r[0] for r in _con.execute("SELECT DISTINCT destination_city FROM delivery_times")})
_con.close()

# Materials are free-text descriptions ("Breathable mesh"), so the form holds a
# KEYWORD that is matched with LIKE '%keyword%'.
MATERIAL_KEYWORDS = ["mesh", "leather", "fabric", "nylon", "polypropylene"]
INTENTS = ["find_products", "total_cost", "average_price"]

FIELDS = ["intent", "product_name", "category", "color", "material", "armrests",
          "max_unit_price", "quantity", "single_depot", "destination_city", "max_delivery_days"]


def _match(value, allowed):
    """Case-insensitive match against a list of real values. None if no match."""
    if value is None:
        return None
    for real in allowed:
        if str(value).strip().lower() == real.lower():
            return real
    return None


def _number(value, cast):
    try:
        n = cast(re.sub(r"[^0-9.]", "", str(value))) if value is not None else None
        return n if n is not None and n > 0 else None
    except ValueError:
        return None


def ground(form: dict) -> tuple:
    """Return (clean_form, notes). Notes say what was fixed or thrown away, and why."""
    clean, notes = {}, []

    def keep(field, value, original):
        if value is not None:
            clean[field] = value
        elif original not in (None, "", []):
            notes.append(f"{field} = {original!r} is not a value this store uses, so it was ignored")

    keep("intent", _match(form.get("intent"), INTENTS), form.get("intent"))
    keep("product_name", _match(form.get("product_name"), PRODUCT_NAMES), form.get("product_name"))
    keep("category", _match(form.get("category"), CATEGORIES), form.get("category"))
    keep("color", _match(form.get("color"), COLORS), form.get("color"))
    material = str(form.get("material") or "").lower()
    keep("material", next((m for m in MATERIAL_KEYWORDS if m in material), None), form.get("material"))
    keep("armrests", _match(form.get("armrests"), ARMRESTS), form.get("armrests"))
    keep("destination_city", _match(form.get("destination_city"), DESTINATIONS), form.get("destination_city"))
    keep("max_unit_price", _number(form.get("max_unit_price"), float), form.get("max_unit_price"))
    keep("quantity", _number(form.get("quantity"), int), form.get("quantity"))
    keep("max_delivery_days", _number(form.get("max_delivery_days"), int), form.get("max_delivery_days"))
    sd = form.get("single_depot")
    if isinstance(sd, str) and sd.strip().lower() in ("true", "false"):
        sd = sd.strip().lower() == "true"          # models sometimes write "true" as text
    if isinstance(sd, bool):
        clean["single_depot"] = sd
    return clean, notes
