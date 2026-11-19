"""The router: the head chef who reads each order and sends it to a station.

    question ──► ROUTER ──┬──► handoff   angry, refund, "talk to a person"
                          ├──► sql       exact lookups: how many, which depot, status
                          ├──► hybrid    rules to apply: quantity, budget, deadline, totals
                          └──► search    descriptions: "a breathable chair for long shifts"

It's plain rules (no AI): every decision takes microseconds and prints its
reason, so you can always see WHY a question went where it did.

ORDER MATTERS. The checks run top to bottom and the first match wins:
    1. safety first   (an angry customer must never get a product list)
    2. order numbers  (NX-12345 is always a lookup)
    3. maths words    (average, total cost, "how much for")
    4. lookup words   (how many, which depot, cheapest, in stock)
    5. rule words     ($ amounts, quantities, "within 3 days", follow-ups)
    6. everything else -> search
"""
import re

HANDOFF = re.compile(
    r"\b(refund|chargeback|cancel+ing my card|cancel my card|furious|angry|unacceptable|lawyer|"
    r"complain|complaint|(talk|speak) to (a|an|someone|somebody)( real)?( person| human| agent| manager)?)\b")
LATE_ORDER = re.compile(r"\b(late|delayed|never arrived|hasn'?t arrived|where is my (order|delivery))\b")
MY_ORDER = re.compile(r"\bmy (order|delivery|package|parcel)\b")
ORDER_ID = re.compile(r"\bnx-\d+\b")
MATHS = re.compile(r"\b(average|mean|how much for|how much would)\b")
TOTAL_COST = re.compile(r"\b(total|altogether|in all)\b")
MONEY_WORD = re.compile(r"\b(cost|price|pay|spend)\b")
LOOKUP = re.compile(
    r"\b(how many|which depot|which warehouse|the most|cheapest|most expensive|in stock|are left|"
    r"do you (sell|have|carry|stock)|status|how long|what does .+ cost|price of the)\b")
NUMBER_WORDS = (r"ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
                r"hundred|dozen")
RULES = re.compile(
    r"\$\s*\d+|\b\d+\s*dollars\b|\bwithin \d+|\bin \d+ (business )?days?\b|"
    r"\b\d+\s+(units?|chairs?|desks?|pieces|of them)\b|\b(need|want|order|buy|get|like)\b[^.?!]*\b\d+\b|"
    rf"\b({NUMBER_WORDS})\b")
FOLLOW_UP = re.compile(r"\b(same|those|these|them|that one)\b")
DEFAULT_REASON = "description only, no numbers or rules"   # the fall-through bucket


def route(question: str, has_previous: bool = False) -> tuple:
    """Return (station, reason). Station is one of: handoff, sql, hybrid, search."""
    q = question.lower()
    if HANDOFF.search(q):
        return "handoff", f"safety word: '{HANDOFF.search(q).group(0)}'"
    if LATE_ORDER.search(q) and MY_ORDER.search(q):
        return "handoff", "complaint about the customer's own order"
    if ORDER_ID.search(q):
        return "sql", f"order number {ORDER_ID.search(q).group(0).upper()}"
    if MATHS.search(q):
        return "hybrid", f"maths word: '{MATHS.search(q).group(0)}'"
    if TOTAL_COST.search(q) and MONEY_WORD.search(q):
        return "hybrid", "total cost"
    if LOOKUP.search(q):
        return "sql", f"lookup words: '{LOOKUP.search(q).group(0)}'"
    if has_previous and FOLLOW_UP.search(q):
        return "hybrid", "follow-up to the previous request"
    if RULES.search(q):
        return "hybrid", f"rule to apply: '{RULES.search(q).group(0).strip()}'"
    return "search", DEFAULT_REASON


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Need 40 navy mesh chairs under $350 delivered to Chicago within 3 days."
    station, reason = route(q)
    print(f"{q}\n  -> {station}   ({reason})")
