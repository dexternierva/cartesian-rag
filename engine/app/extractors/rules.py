"""The no-AI form filler: reads a question with patterns and fills in the form.

Patterns (called "regular expressions") are like a search-and-highlight tool:
    "under $350"       -> max_unit_price = 350
    "within 3 days"    -> max_delivery_days = 3
    "40 ... chairs"    -> quantity = 40

This is the baseline. It's fast and predictable, but it only understands
phrasings someone thought of in advance.
"""
import re

from extractors.vocab import COLORS, DESTINATIONS, MATERIAL_KEYWORDS, PRODUCT_NAMES

ONE_DEPOT = r"\b(one|single|same|a single)\s+(warehouse|depot|location|place)\b|\ball from one\b"
ANY_DEPOT = r"\b(don'?t mind which|any warehouse|any depot|across|combined|in total|from anywhere)\b"
FOLLOW_UP = r"\b(same|those|these|them|that one)\b"


def extract(question: str, previous: dict = None) -> dict:
    q = question.lower()
    form = {"follow_up": bool(previous) and bool(re.search(FOLLOW_UP, q))}

    # --- what kind of question? ---
    if re.search(r"\baverage\b|\bmean\b", q):
        form["intent"] = "average_price"
    elif re.search(r"\b(total|altogether|in all)\b", q) and re.search(r"\b(cost|price|pay)\b", q):
        form["intent"] = "total_cost"
    else:
        form["intent"] = "find_products"

    # --- numbers: price, days, then quantity (whatever number is left) ---
    m = re.search(r"(?:under|below|less than|up to|max(?:imum)?|no more than)\s*\$\s*(\d+(?:\.\d+)?)", q)
    if m:
        form["max_unit_price"] = float(m.group(1))
    m = re.search(r"(?:within|in|under)\s+(\d+)\s+(?:business\s+)?days?", q)
    if m:
        form["max_delivery_days"] = int(m.group(1))
    used = {m.group(1) for m in re.finditer(r"\$\s*(\d+)|(\d+)\s+(?:business\s+)?days?", q) if m.group(1)}
    used |= {m.group(2) for m in re.finditer(r"\$\s*(\d+)|(\d+)\s+(?:business\s+)?days?", q) if m.group(2)}
    for m in re.finditer(r"\b(\d+)\b", q):
        if m.group(1) not in used and not re.match(r"\s*d\b", q[m.end():m.end() + 2]):   # skip "4D"
            form["quantity"] = int(m.group(1))
            break

    # --- words from the store's vocabulary ---
    for name in sorted(PRODUCT_NAMES, key=len, reverse=True):
        if name.lower() in q:
            form["product_name"] = name
            break
    for color in COLORS:
        if re.search(rf"\b{color.lower()}\b", q):
            form["color"] = color
            break
    for material in MATERIAL_KEYWORDS:
        if re.search(rf"\b{material}\b", q):
            form["material"] = material
            break
    m = re.search(r"\b([234])d\b", q)
    if m:
        form["armrests"] = f"{m.group(1)}D"
    for city in DESTINATIONS:
        if city.lower() in q:
            form["destination_city"] = city
            break
    if re.search(r"\bdesks?\b", q):
        form["category"] = "Desks"
    elif re.search(r"\bchairs?\b", q) and not re.search(r"\b(guest|side|stack)", q):
        form["category"] = "Office chairs"

    # --- one warehouse or many? ---
    if re.search(ANY_DEPOT, q):
        form["single_depot"] = False
    elif re.search(ONE_DEPOT, q):
        form["single_depot"] = True
    return form


extract.label = "rules (no AI)"
