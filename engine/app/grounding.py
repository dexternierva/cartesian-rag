"""The grounding check: before we believe "No", check the question was asked correctly.

WHY THIS EXISTS (a real failure, 2026-11-12)
    A small model wrote   WHERE p.name = 'Mesh Chair'
    No product is called 'Mesh Chair', so the database returned nothing,
    and the engine told the shopper "No, nothing matches" - while 48 chairs
    sat in a warehouse. The query was SAFE (the guard let it through) but
    it searched for something that doesn't exist.

THE IDEA
    An empty result is a claim: "this doesn't exist". Before passing that
    claim on, we check every exact value the query searched for
    (name = '...', material = '...') really exists in that column.

    Think of a librarian who says "we don't have that book". A good one
    first checks you spelled the title right.

WHEN A VALUE IS MISSING, IS THAT A MISTAKE OR A REAL "NO"?
    - "Do you sell PINK chairs?"  -> color = 'Pink'. Nothing like 'pink' exists
      in the colour column at all. That's an honest "No". Allowed.
    - material = 'Mesh'           -> 'Mesh' doesn't exist exactly, but
      'Breathable mesh' and 'Elastomer mesh' do. That's a MISTAKE
      (should have used LIKE '%mesh%'). Flagged, with suggestions.
    - name = 'Mesh Chair'         -> product names are proper names, like
      'AeroTask Pro Mesh'. A name that isn't on the list is almost always
      invented. Flagged, with similar real names.
"""
import re

# column name -> (table, column) where its real values live
CHECKED_COLUMNS = {
    "name": ("products", "name"),
    "color": ("products", "color"),
    "category": ("products", "category"),
    "material": ("products", "material"),
    "armrests": ("products", "armrests"),
    "depot_id": ("depots", "depot_id"),
    "depot_name": ("depots", "depot_name"),
    "city": ("depots", "city"),
    "destination_city": ("delivery_times", "destination_city"),
    "status": ("orders", "status"),
}
# For these, ANY value not on the list is treated as invented: they are names
# and codes, which people don't make up. (family was added 2026-11-12, after the
# model wrote family = 'AeroTask Pro Mesh' when the column holds codes like 'AT'.)
STRICT_COLUMNS = {"name", "depot_id", "depot_name", "family", "sku", "order_id", "customer_id", "policy_id"}


def _all_text_columns():
    """Every text column in the database, so no column can slip past the check."""
    from db import connect
    con = connect()
    found = {}
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        for col in con.execute(f"PRAGMA table_info({table})"):
            if (col[2] or "TEXT").upper() == "TEXT":
                found.setdefault(col[1], (table, col[1]))
    con.close()
    return found


CHECKED_COLUMNS.update({c: tc for c, tc in _all_text_columns().items() if c not in CHECKED_COLUMNS})
_EQUALS = re.compile(r"(?i)\b(?:\w+\.)?(" + "|".join(sorted(CHECKED_COLUMNS, key=len, reverse=True))
                     + r")\s*=\s*'((?:[^']|'')*)'")


def _similar(con, table, column, value, limit=5):
    """Real values that contain the searched value, or share a word with it."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", value) if len(w) >= 4] or [value]
    found = []
    for w in [value] + words:
        for (v,) in con.execute(f"SELECT DISTINCT {column} FROM {table} "
                                f"WHERE {column} LIKE ? ORDER BY 1 LIMIT {limit}", (f"%{w}%",)):
            if v not in found:
                found.append(v)
    return found[:limit]


def ungrounded_values(sql: str, con) -> list:
    """Return a list of problems: (column, value_used, [similar real values])."""
    problems = []
    for column, raw in _EQUALS.findall(sql):
        column = column.lower()
        value = raw.replace("''", "'")
        table, real_column = CHECKED_COLUMNS[column]
        exists = con.execute(f"SELECT 1 FROM {table} WHERE {real_column} = ? LIMIT 1", (value,)).fetchone()
        if exists:
            continue
        similar = _similar(con, table, real_column, value)
        if column in ("family", "sku"):
            similar = similar or [r[0] for r in con.execute(f"SELECT DISTINCT {real_column} FROM {table} LIMIT 8")]
        if column in STRICT_COLUMNS or similar:
            problems.append((column, value, similar))
        # else: nothing remotely like it exists -> an honest "we don't have that"
    return problems


SUBJECT_COLUMNS = {"name": "product", "color": "color", "category": "category", "sku": "sku",
                   "depot_id": "depot_id", "depot_name": "depot", "city": "city",
                   "order_id": "order_id", "status": "status"}


def subject_of(sql: str, con) -> dict:
    """WHAT the answer is about, read from the query's own exact filters (R6).

    "available: 48" is true but says nothing. The query knows more:
        WHERE p.name = 'AeroTask Pro Mesh' AND p.color = 'Navy' AND s.depot_id = 'IND-04'
    Only values that really exist in the database are kept (the same check as grounding),
    so the screen can write "48 navy AeroTask Pro Mesh at Indianapolis Regional"
    without the AI writing a single word of it.
    """
    found = {}
    for column, raw in _EQUALS.findall(sql):
        column = column.lower()
        if column not in SUBJECT_COLUMNS:
            continue
        value = raw.replace("''", "'")
        table, real_column = CHECKED_COLUMNS[column]
        if con.execute(f"SELECT 1 FROM {table} WHERE {real_column} = ? LIMIT 1", (value,)).fetchone():
            found[SUBJECT_COLUMNS[column]] = value
    if "depot_id" in found and "depot" not in found:
        row = con.execute("SELECT depot_name FROM depots WHERE depot_id = ?", (found["depot_id"],)).fetchone()
        if row:
            found["depot"] = row[0]
    if "product" in found and "color" in found and "sku" not in found:
        rows = con.execute("SELECT sku FROM products WHERE name = ? AND color = ?",
                           (found["product"], found["color"])).fetchall()
        if len(rows) == 1:
            found["sku"] = rows[0][0]       # closes E39's gap: the receipt can name the product
    return found


def explain(problems: list) -> str:
    """Turn problems into a message the SQL writer can learn from on its retry."""
    parts = []
    for column, value, similar in problems:
        hint = f" Real values like it: {', '.join(repr(s) for s in similar)}." if similar else ""
        if column == "material":
            hint += " Materials are descriptions, so match them with LIKE '%word%'."
        if column == "family":
            hint += " family holds short codes (like 'AT'); to match a product by its name use name = '...'."
        if column == "name":
            hint += (" Only use name = '...' for a real product name; if the person described a"
                     " product instead of naming it, filter by category, material, color and armrests.")
        parts.append(f"{column} = '{value}' does not exist in the database.{hint}")
    return "The query returned no rows because: " + " ".join(parts)
