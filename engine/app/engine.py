"""The engine's front door: one function, ask(), for every question.

    ticket = ask("Need 40 navy mesh chairs under $350...")

    ask() ──► router picks a station ──► station answers ──► ticket (the contract)

Which tools each station uses is chosen with a PRESET:
    "no-ai"  rules everywhere          fast (milliseconds), no Ollama needed
    "ai"     Ollama where it helps     slower (seconds), smarter with new phrasing
"""
import time
import uuid

import router

PRESETS = {
    "no-ai": {"sql_writer": "baseline", "extractor": "rules", "search_mode": "keyword", "ai_router": False},
    "ai":    {"sql_writer": "ollama",   "extractor": "both",  "search_mode": "hybrid",  "ai_router": True},
}


def choose_station(question: str, previous: dict = None, preset: str = "no-ai") -> tuple:
    """Rules first. Only if the rules fell through to their default, ask the AI (one word)."""
    station, reason = router.route(question, has_previous=bool(previous))
    if PRESETS[preset]["ai_router"] and reason == router.DEFAULT_REASON:
        from ai_router import classify
        ai_station = classify(question)
        if ai_station:
            return ai_station, f"AI tie-breaker (rules found nothing): {ai_station}"
    return station, reason

_tools = {}


def _get_tools(preset: str) -> dict:
    """Load each tool once and keep it (loading AI tools is slow)."""
    if preset in _tools:
        return _tools[preset]
    cfg = PRESETS[preset]
    if cfg["sql_writer"] == "ollama":
        from writers.ollama_writer import write_sql
    else:
        from writers.baseline import write_sql
    from extractors.rules import extract as rules_extract
    if cfg["extractor"] == "rules":
        extractor = rules_extract
    else:
        from extractors.ollama_extractor import extract as ai_extract
        if cfg["extractor"] == "both":
            from extractors.combined import make_combined
            extractor = make_combined(ai_extract, rules_extract)
        else:
            extractor = ai_extract
    _tools[preset] = {"write_sql": write_sql, "extractor": extractor, "search_mode": cfg["search_mode"]}
    return _tools[preset]


def warm_up(preset: str) -> float:
    """Load the AI model before the first real question (no-op for 'no-ai')."""
    if PRESETS[preset]["sql_writer"] != "ollama":
        return 0.0
    from extractors.ollama_extractor import warm_up as warm_extractor
    from writers.ollama_writer import warm_up as warm_writer
    return warm_writer() + warm_extractor()


def _router_handoff(question, reason, started):
    return {
        "contract_version": "0.1", "query_id": "q_" + uuid.uuid4().hex[:10], "question": question,
        "route": "handoff", "state": "handoff", "confidence": 0.9,
        "message": "Connecting you to a specialist. They'll see this chat and your details, "
                   "so you won't need to repeat anything.",
        "components": [{"type": "handoff", "reason": "critical_intent",
                        "summary": f"Customer message: \"{question}\". Router reason: {reason}."}],
        "citations": [], "timing_ms": {"total": round((time.perf_counter() - started) * 1000, 1)},
    }


# Requirements a shopper may remove with one tap (R4 chips, R5 relax buttons).
DROPPABLE = {"quantity", "category", "color", "material", "armrests", "max_unit_price",
             "destination_city", "max_delivery_days", "single_depot"}


def _form_as_is(question, previous=None):
    """An 'extractor' that reads nothing: the form arrives already edited by the shopper."""
    return {"follow_up": True}


_form_as_is.label = "form edited by the shopper (no AI)"


def ask(question: str, previous: dict = None, preset: str = "no-ai", drop: str = None) -> dict:
    """Answer any question. 'previous' = the form (constraints) of the last answer, for follow-ups.

    drop = one requirement the shopper removed (a chip's x, or a "show it without..." button).
    Then nothing is re-read or re-guessed: the previous form minus that one box goes straight
    to the hybrid station. No AI, so it answers in milliseconds.
    """
    started = time.perf_counter()
    if drop:
        if drop not in DROPPABLE or not previous:
            raise ValueError(f"Can't remove '{drop}': not a removable requirement, or no previous form.")
        form = dict(previous)
        if drop == "single_depot":
            form["single_depot"] = False         # "remove the one-warehouse rule" = allow several
        else:
            form.pop(drop, None)
        from hybrid_station import answer_with_hybrid
        ticket = answer_with_hybrid(question, _form_as_is, form)
        trace = ticket.setdefault("trace", {})
        trace["station"] = "hybrid"
        trace["router_reason"] = f"The shopper removed one requirement: {drop}"
        ticket["timing_ms"]["total"] = round((time.perf_counter() - started) * 1000, 1)
        return ticket

    station, reason = choose_station(question, previous, preset)
    tools = _get_tools(preset)

    if station == "handoff":
        ticket = _router_handoff(question, reason, started)
    elif station == "sql":
        from sql_station import answer_with_sql
        ticket = answer_with_sql(question, tools["write_sql"])
    elif station == "hybrid":
        from hybrid_station import answer_with_hybrid
        ticket = answer_with_hybrid(question, tools["extractor"], previous)
    else:
        from search_station import answer_with_search
        ticket = answer_with_search(question, tools["search_mode"])

    trace = ticket.setdefault("trace", {})
    trace["station"] = station
    trace["router_reason"] = reason
    ticket["timing_ms"]["total"] = round((time.perf_counter() - started) * 1000, 1)
    return ticket


if __name__ == "__main__":
    import json
    import sys
    preset = "no-ai"
    args = sys.argv[1:]
    if args and args[0] in PRESETS:
        preset, args = args[0], args[1:]
    q = " ".join(args) or "Need 40 navy mesh chairs with 4D armrests under $350, Chicago within 3 days."
    t = ask(q, preset=preset)
    print(f"Question: {q}")
    print(f"Router:   {t['trace']['station']}  ({t['trace']['router_reason']})")
    print(f"State:    {t['state']}  |  {t['message']}")
    print(f"Time:     {t['timing_ms']['total']} ms")
    print("Ticket:  ", json.dumps(t)[:300], "...")
