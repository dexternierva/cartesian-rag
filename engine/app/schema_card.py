"""Build the "schema card": a short description of the database.

WHY: an AI can't write SQL for tables it has never seen. The schema card
is the map we hand it: table names, column names, a few example values.
(A new waiter gets a floor plan of the restaurant on day one.)

The no-AI baseline doesn't read this, but the AI writer will.

Run:  python schema_card.py     -> prints the card
"""
from db import connect

# Columns where listing the possible values helps the SQL writer
# (e.g. it must know colours are 'Navy', not 'navy blue').
LIST_VALUES_FOR = {
    "products": ["category", "color", "material", "armrests"],
    "depots": ["depot_id", "city"],
    "delivery_times": ["destination_city"],
    "orders": ["status"],
}


def build_schema_card() -> str:
    con = connect()
    lines = ["DATABASE: store.db (SQLite)", ""]
    objects = con.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name"
    ).fetchall()
    for obj in objects:
        name = obj["name"]
        cols = con.execute(f"PRAGMA table_info({name})").fetchall()
        col_text = ", ".join(f"{c['name']} {c['type'] or 'TEXT'}".strip() for c in cols)
        lines.append(f"{obj['type'].upper()} {name}({col_text})")
        for col in LIST_VALUES_FOR.get(name, []):
            vals = [r[0] for r in con.execute(
                f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL ORDER BY 1")]
            lines.append(f"  values of {col}: {', '.join(map(str, vals))}")
        lines.append("")
    lines += [
        "NOTES",
        "- stock_available.available = on_hand - reserved. Use it for 'in stock' questions.",
        "- A product family (e.g. 'AeroTask Pro Mesh') has one SKU per colour.",
        "- delivery_times.days = days from a depot to a destination city.",
    ]
    con.close()
    return "\n".join(lines)


if __name__ == "__main__":
    print(build_schema_card())
