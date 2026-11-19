"""The Hybrid station: the AI fills in a FORM, our code builds the SQL.

    question ──► EXTRACTOR fills the form ──► GROUND the values ──► BUILD SQL from
                 (rules or AI)                (real words only)      a tested template
             ──► RUN ──► pick best depot per product ──► PACK cards + receipts

Why this split? The small model got 0/6 on these questions when it had to write
the whole SQL itself. Filling in a form with allowed values is a much easier job,
and turning a form into SQL is something plain code does perfectly every time.

SAFETY: the user's words never go INTO the SQL text. Values are passed separately
as "parameters" (the ? marks). The database treats them as data, never as commands.
That blocks a classic attack called SQL injection.
"""
import re
import time
import uuid
from datetime import datetime, timezone

from db import connect
from extractors.vocab import FIELDS, ground

MAX_CARDS = 3


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_sql(sql, params):
    """SQL with the values filled in, for people to read in the audit drawer."""
    out = sql
    for p in params:
        out = out.replace("?", repr(p) if isinstance(p, str) else str(p), 1)
    return " ".join(out.split())


def _status(n):
    return "in_stock" if n >= 10 else ("low_stock" if n > 0 else "out_of_stock")


FOLLOW_UP_WORDS = re.compile(r"\b(same|those|these|them|that one|instead|but)\b", re.I)


def merge_follow_up(previous: dict, form: dict, question: str = "") -> dict:
    """CONVERSATION MEMORY: "Same chairs, but within 2 days" = the old form + the new change.

    A follow-up is detected by the AI's flag OR by plain words like "same" and "those".
    (Bug found 2026-11-12: after the speed fix, the AI stopped writing "follow_up": true,
    the old form was never merged, and Q14 lost its quantity and budget.)
    """
    if not previous or not (form.get("follow_up") or FOLLOW_UP_WORDS.search(question)):
        return form
    merged = dict(previous)
    merged.update({k: v for k, v in form.items() if v is not None and k != "follow_up"})
    return merged


def _filters(c):
    """Turn the clean form into WHERE pieces + parameters. Each rule is one line."""
    where, params = [], []
    if c.get("product_name"):
        where.append("p.name = ?"); params.append(c["product_name"])
    if c.get("category"):
        where.append("p.category = ?"); params.append(c["category"])
    if c.get("color"):
        where.append("p.color = ?"); params.append(c["color"])
    if c.get("material"):
        where.append("LOWER(p.material) LIKE ?"); params.append(f"%{c['material']}%")
    if c.get("armrests"):
        where.append("p.armrests = ?"); params.append(c["armrests"])
    if c.get("max_unit_price"):
        where.append("p.unit_price <= ?"); params.append(c["max_unit_price"])
    return where, params


def _find(con, c):
    """Rows of (sku, name, color, price, depot, available, days) that pass every rule."""
    where, params = _filters(c)
    city, max_days, qty = c.get("destination_city"), c.get("max_delivery_days"), c.get("quantity") or 1
    sql = ("SELECT p.sku, p.name, p.color, p.unit_price, p.material, p.armrests, p.weight_rating_lb, "
           "s.depot_id, s.depot_name, s.available" + (", t.days" if city else "") +
           " FROM products p JOIN stock_available s USING (sku)" +
           (" JOIN delivery_times t ON t.depot_id = s.depot_id AND t.destination_city = ?" if city else ""))
    all_params = ([city] if city else []) + params
    if city and max_days:
        where.append("t.days <= ?"); all_params.append(max_days)
    single = c.get("single_depot", True) is not False      # default: one shipment from one warehouse
    if single:
        where.append("s.available >= ?"); all_params.append(qty)
    else:
        where.append("s.available > 0")
    sql += (" WHERE " + " AND ".join(where)) if where else ""
    rows = [dict(r) for r in con.execute(sql, all_params)]

    if not single:   # add stock up ACROSS depots, keep products whose total is enough
        totals = {}
        for r in rows:
            totals[r["sku"]] = totals.get(r["sku"], 0) + r["available"]
        rows = [r for r in rows if totals[r["sku"]] >= qty]
        for r in rows:
            r["total_available"] = totals[r["sku"]]
    # one row per product: the depot that delivers fastest, then has the most stock
    best = {}
    for r in sorted(rows, key=lambda r: (r.get("days") or 0, -r["available"])):
        best.setdefault(r["sku"], r)
    return sorted(best.values(), key=lambda r: (r["unit_price"], r["sku"])), sql, all_params


RELAXABLE = [("max_delivery_days", "the delivery-time limit"), ("max_unit_price", "the price limit"),
             ("color", "the colour"), ("armrests", "the armrest type"), ("material", "the material"),
             ("single_depot", "the one-warehouse rule")]


def _relax_options(con, c):
    """When nothing matches ALL rules, find each ONE rule whose removal gives results.

    Returned as DATA (field, label, matches), not only as a sentence, so the screen can
    turn each one into a button: "Show the 1 option without the delivery-time limit".
    (Expert review finding R5, 2026-11-18: a hint you have to retype is half a hint.)
    """
    options = []
    for field, label in RELAXABLE:
        if c.get(field) is None or (field == "single_depot" and c.get(field) is False):
            continue
        looser = dict(c)
        looser[field] = False if field == "single_depot" else None
        rows, _, _ = _find(con, looser)
        if rows:
            options.append({"field": field, "label": label, "matches": len(rows)})
    return options


def _relax_hint(con, c):
    """The first relax option as a sentence (kept for the message)."""
    options = _relax_options(con, c)
    if not options:
        return None
    o = options[0]
    return f"Without {o['label']}, {o['matches']} option{'s' if o['matches'] > 1 else ''} would match."


def message_set_by_depot_hint(scope) -> bool:
    """True when the one-warehouse note already explained an empty result."""
    return "more qualif" in (scope.get("message") or "")


def _handoff(question, summary, started, constraints=None):
    t = {"contract_version": "0.1", "query_id": "q_" + uuid.uuid4().hex[:10], "question": question,
         "route": "handoff", "state": "handoff", "confidence": 0.3,
         "message": "I couldn't understand that well enough to search reliably, so I'm connecting you to a specialist.",
         "components": [{"type": "handoff", "reason": "low_confidence", "summary": summary}],
         "citations": [], "timing_ms": {"total": round((time.perf_counter() - started) * 1000, 1)}}
    if constraints:
        t["constraints"] = constraints
    return t


def answer_with_hybrid(question: str, extractor, previous: dict = None) -> dict:
    started = time.perf_counter()

    # 1. EXTRACT: fill in the form (this is the only step that may use AI)
    raw = extractor(question, previous) or {}
    extract_ms = (time.perf_counter() - started) * 1000
    raw = merge_follow_up(previous, raw, question)

    # 2. GROUND: keep only real values
    c, notes = ground(raw)
    intent = c.get("intent")
    useful = [f for f in FIELDS if f not in ("intent", "single_depot") and c.get(f) is not None]
    if not intent or not useful:
        return _handoff(question, "The form came back empty or without a known intent. "
                        + " ".join(notes), started, c or None)

    con = connect()
    t0 = time.perf_counter()
    read_at = _now_iso()
    components, citations, calculation, message = [], [], None, ""
    relax = []      # ways out the screen can offer as buttons (R5)

    # 3. BUILD + RUN, by intent
    if intent == "total_cost":
        if not (c.get("product_name") and c.get("quantity")):
            con.close()
            return _handoff(question, "A total needs a named product and a quantity.", started, c)
        sql = "SELECT sku, name, color, unit_price FROM products WHERE name = ?" + (" AND color = ?" if c.get("color") else "")
        params = [c["product_name"]] + ([c["color"]] if c.get("color") else [])
        rows = [dict(r) for r in con.execute(sql + " ORDER BY sku", params)]
        qty = c["quantity"]
        prices = sorted({r["unit_price"] for r in rows})
        if rows and len(prices) > 1:
            # No colour given and colours cost DIFFERENT amounts: don't pick one, ask.
            con.close()
            return {
                "contract_version": "0.1", "query_id": "q_" + uuid.uuid4().hex[:10], "question": question,
                "route": "python", "state": "disambiguate", "confidence": 0.7,
                "message": f"{rows[0]['name']} costs different amounts by colour. Which colour?",
                "constraints": {k: v for k, v in c.items() if v is not None},
                "components": [{"type": "choices", "prompt": "Pick a colour", "options": [
                    {"label": r["color"], "description": f"${r['unit_price']:,.2f} each",
                     "follow_up_question": f"What would {qty} {r['color'].lower()} {r['name']} cost in total?"}
                    for r in rows[:5]]}],
                "citations": [], "timing_ms": {"generation": round(extract_ms, 1),
                                               "total": round((time.perf_counter() - started) * 1000, 1)}}
        if rows:
            # One price. If no colour was given, the answer covers EVERY colour, and says so:
            # we cite every colour's row instead of silently picking the first one.
            r = rows[0]
            total = round(qty * r["unit_price"], 2)
            for n, row in enumerate(rows, start=1):
                citations.append({"id": f"c{n}", "kind": "db_row", "database": "store.db", "table": "products",
                                  "row_key": {"sku": row["sku"]}, "fields": row, "sql": _display_sql(sql, params),
                                  "read_at": read_at, "confidence": 1.0})
            calculation = {"formula": "quantity x unit_price", "inputs": {"quantity": qty, "unit_price": r["unit_price"]},
                           "result": total, "citation_ids": [cc["id"] for cc in citations]}
            table = {"columns": ["sku", "name", "quantity", "unit_price", "total"],
                     "rows": [[row["sku"], row["name"], qty, row["unit_price"], total] for row in rows]}
            colour_text = r["color"] if len(rows) == 1 else f"any colour: {', '.join(x['color'] for x in rows)}, same price"
            message = f"{qty} x {r['name']} ({colour_text}) at ${r['unit_price']:,.2f} = ${total:,.2f}."
        route = "python"

    elif intent == "average_price":
        where, params = _filters(c)
        sql = ("SELECT ROUND(AVG(p.unit_price), 2) AS average_unit_price, COUNT(*) AS products_counted "
               "FROM products p" + (" WHERE " + " AND ".join(where) if where else ""))
        r = dict(con.execute(sql, params).fetchone())
        rows = [r] if r["products_counted"] else []
        if rows:
            calculation = {"formula": "average of unit_price", "inputs": {"products_counted": r["products_counted"]},
                           "result": r["average_unit_price"], "citation_ids": ["c1"]}
            citations.append({"id": "c1", "kind": "db_row", "database": "store.db", "table": "products",
                              "row_key": {"aggregate": "AVG(unit_price)"}, "fields": r,
                              "sql": _display_sql(sql, params), "read_at": read_at, "confidence": 1.0})
            table = {"columns": ["average_unit_price", "products_counted"],
                     "rows": [[r["average_unit_price"], r["products_counted"]]]}
            message = f"The average price across {r['products_counted']} products is ${r['average_unit_price']:,.2f}."
        route = "python"

    else:  # find_products
        rows, sql, params = _find(con, c)
        shown = _display_sql(sql, params)
        for n, r in enumerate(rows[:MAX_CARDS], start=1):
            cid = f"c{n}"
            citations.append({"id": cid, "kind": "db_row", "database": "store.db", "table": "stock_available",
                              "row_key": {"sku": r["sku"], "depot_id": r["depot_id"]},
                              "fields": {k: r[k] for k in ("sku", "depot_id", "available", "unit_price")},
                              "sql": shown, "read_at": read_at, "confidence": 1.0})
            specs = [s for s in (r["material"],
                                 f"{r['armrests']} armrests" if r["armrests"] and r["armrests"] != "None" else None,
                                 f"{int(r['weight_rating_lb'])} lb rating" if r["weight_rating_lb"] else None) if s]
            card = {"type": "product_card", "sku": r["sku"], "name": r["name"], "color": r["color"],
                    "unit_price": r["unit_price"], "currency": "USD", "specs": specs,
                    "stock": {"status": _status(r["available"]), "available": r["available"],
                              "depot_id": r["depot_id"], "depot_name": r["depot_name"]},
                    "citation_ids": [cid]}
            if c.get("destination_city") and r.get("days") is not None:
                card["delivery"] = {"destination_city": c["destination_city"], "days": r["days"],
                                    "meets_deadline": c.get("max_delivery_days") is None or r["days"] <= c["max_delivery_days"]}
            components.append(card)
        table = {"columns": ["sku", "name", "unit_price", "depot_id", "available", "days"],
                 "rows": [[r["sku"], r["name"], r["unit_price"], r["depot_id"], r["available"], r.get("days")] for r in rows]}
        if rows:
            message = (f"Found {len(rows)} products that match everything you asked for." if len(rows) > 1
                       else "Found 1 product that matches everything you asked for.")
        if c.get("single_depot") is None and c.get("quantity", 1) > 1:
            # The question didn't say whether units may come from several warehouses.
            # We assumed ONE (the stricter rule) - so we say so, and what changes if not.
            looser, _, _ = _find(con, {**c, "single_depot": False})
            extra = len({r["sku"] for r in looser} - {r["sku"] for r in rows})
            if extra:
                relax = [{"field": "single_depot", "label": "the one-warehouse rule", "matches": len(looser)}]
                message = (message if rows else "Nothing matches with everything shipped from one warehouse.") + \
                          f" {extra} more qualif{'y' if extra > 1 else 'ies'} if the units can come from several warehouses."
        route = "hybrid"

    if not rows:
        if intent == "find_products" and not relax:
            relax = _relax_options(con, c)
        hint = _relax_hint(con, c) if intent == "find_products" else None
        table = {"columns": [], "rows": []}
        if not (intent == "find_products" and message_set_by_depot_hint(locals())):
            message = "Nothing matches everything you asked for right now." + (f" {hint}" if hint else "")
        shown_sql = None
    else:
        shown_sql = citations[0]["sql"] if citations else None
    con.close()

    contract_constraints = {k: v for k, v in c.items() if v is not None}
    ticket = {
        "contract_version": "0.1",
        "query_id": "q_" + uuid.uuid4().hex[:10],
        "question": question,
        "route": route,
        "state": "answer" if rows else "no_results",
        "confidence": 0.7 if notes else float(getattr(extractor, "confidence", 0.85)),
        "message": message + (f" (Note: {'; '.join(notes)}.)" if notes else ""),
        "constraints": contract_constraints,
        "components": components,
        "citations": citations,
        "table": table,
        "trace": {"sql": shown_sql, "tries": 1, "writer": getattr(extractor, "label", "extractor")},
        "timing_ms": {"generation": round(extract_ms, 1),
                      "retrieval": round((time.perf_counter() - t0) * 1000, 1),
                      "total": round((time.perf_counter() - started) * 1000, 1)},
    }
    if calculation:
        ticket["calculation"] = calculation
    if relax:
        ticket["relax"] = relax
    return ticket


if __name__ == "__main__":
    import json
    import sys
    from extractors.rules import extract
    q = " ".join(sys.argv[1:]) or "Need 40 ergonomic mesh chairs with 4D armrests in navy, under $350 each, delivered to Chicago within 3 days."
    t = answer_with_hybrid(q, extract)
    print("Question:", q)
    print("Form:    ", json.dumps(t.get("constraints")))
    print("State:   ", t["state"], "|", t["message"])
    print("SQL:     ", t["trace"]["sql"] if "trace" in t else None)
    for row in t.get("table", {}).get("rows", []):
        print("   ", row)
