"""Record real engine answers for the GitHub prototype ("photos of real dishes").

GitHub Pages can't run Python, so the online prototype can't call the engine.
Instead, we run the engine here, on a real computer, and SAVE its tickets in
prototype/answers.json. The prototype then replays them. Nothing in that file
is hand-written: every ticket came out of engine.ask().

    python record_demo.py          # rules only (fast, no Ollama)
    python record_demo.py ai       # with Ollama: use this for the published demo

Each "Did you mean...?" answer offers chips; the questions behind those chips
are recorded too, so clicking a chip in the demo also shows a real answer.

Shopping answers show their requirements as chips the shopper can remove (R4),
and "nothing matches" answers offer ways out (R5). Each removal is recorded too:
it re-runs the same form minus one box, with no AI, so it takes milliseconds.
"""
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import engine

OUT = Path(__file__).resolve().parents[2] / "prototype" / "answers.json"

# The demo conversation. "follows" = this question continues an earlier one
# (its form is sent along, exactly as the browser would do with the live API).
DEMO = [
    {"question": "Need 40 ergonomic mesh chairs with 4D armrests in navy, under $350 each, delivered to Chicago within 3 days."},
    {"question": "Same chairs, but they must arrive in Chicago within 2 days.", "follows": 0},
    {"question": "What would 40 navy AeroTask Pro Mesh chairs cost in total?"},
    {"question": "How many navy AeroTask Pro Mesh chairs are available in Indianapolis?"},
    {"question": "40 navy mesh chairs with 4D armrests under $300 delivered to Chicago within 2 days"},
    {"question": "Show me the navy shell"},
    {"question": "Something to charge my laptop"},
    {"question": "A breathable chair that's comfortable for long shifts"},
    {"question": "My order is 4 days late and I want a refund right now!"},
]


DROP_LABEL = {"quantity": "the quantity", "category": "the category", "color": "the colour",
              "material": "the material", "armrests": "the armrest type", "max_unit_price": "the price limit",
              "destination_city": "the delivery city", "max_delivery_days": "the delivery-time limit",
              "single_depot": "the one-warehouse rule"}


def drops_for(ticket):
    """Every one-tap removal this answer offers: its requirement chips + its ways out."""
    c = ticket.get("constraints") or {}
    if ticket.get("route") != "hybrid" or c.get("intent") != "find_products":
        return []
    fields = [f for f in DROP_LABEL if f != "single_depot" and c.get(f) is not None]
    fields += [o["field"] for o in ticket.get("relax", []) if o["field"] not in fields]
    return fields


def main():
    preset = sys.argv[1] if len(sys.argv) > 1 else "no-ai"
    if preset not in engine.PRESETS:
        raise SystemExit(f"Preset must be one of: {', '.join(engine.PRESETS)}")
    if engine.PRESETS[preset]["sql_writer"] == "ollama":
        print(f"Model: {__import__('writers.ollama_writer', fromlist=['x']).OLLAMA_MODEL}   (change with: $env:OLLAMA_MODEL = ...)")
        print("Warming up the model ...")
        print(f"Ready in {engine.warm_up(preset):.1f} s.\n")

    model = None
    if preset != "no-ai":
        from writers.ollama_writer import OLLAMA_MODEL
        model = OLLAMA_MODEL

    recorded, queue = [], [dict(item) for item in DEMO]
    while queue:
        item = queue.pop(0)
        previous = recorded[item["follows"]]["ticket"].get("constraints") if "follows" in item else None
        ticket = engine.ask(item["question"], previous, preset, drop=item.get("drop"))
        entry = {"question": item["question"], "ticket": ticket}
        if "follows" in item:
            entry["follows"] = recorded[item["follows"]]["question"]
        if item.get("is_chip"):
            entry["from_chip"] = True        # reached by tapping a "Did you mean...?" chip
        if item.get("drop"):
            entry["drop"] = item["drop"]
        recorded.append(entry)
        # record each one-tap removal (only from answers the shopper asked for, not from removals)
        if not item.get("drop") and not item.get("is_chip"):
            for field in drops_for(ticket):
                queue.append({"question": f"Without {DROP_LABEL[field]}", "follows": len(recorded) - 1, "drop": field})
        print(f"{ticket['timing_ms']['total']:>9.0f} ms  {ticket['state']:<12} {item['question'][:60]}")
        # record the questions behind "Did you mean...?" chips, once each
        for comp in ticket.get("components", []):
            if comp.get("type") == "choices" and not item.get("is_chip"):
                for opt in comp["options"]:
                    queue.append({"question": opt["follow_up_question"], "is_chip": True})

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "about": "Real tickets recorded from the CartesianRAG engine. Not hand-written. "
                 "The prototype replays them because GitHub Pages can't run Python.",
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preset": preset,
        "model": model,
        "machine": f"{platform.system()} {platform.machine()}",
        "answers": recorded,
    }, indent=1), encoding="utf-8")
    print(f"\nSaved {len(recorded)} real answers -> {OUT}")


if __name__ == "__main__":
    main()
