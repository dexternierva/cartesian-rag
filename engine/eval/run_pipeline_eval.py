"""Score the WHOLE engine: router + every station, the way a shopper would use it.

    python run_pipeline_eval.py no-ai     # rules everywhere (no Ollama needed)
    python run_pipeline_eval.py ai        # Ollama where it helps

Two scores:
  1. ROUTER  - did each question go to the right station?
               (all 35 answer-key questions + 8 fresh router-only questions)
  2. ANSWERS - was the final answer right? (the 35 answer-key questions)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(ENGINE / "app"))
sys.path.insert(0, str(HERE))

import engine  # noqa: E402
from run_eval import grade  # noqa: E402

try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    from jsonschema import Draft7Validator as Validator

# expected_route in the answer key -> the station that should handle it
STATION_FOR = {"sql": "sql", "python": "hybrid", "hybrid": "hybrid", "search": "search", "handoff": "handoff"}


def grade_any(q, t):
    """Pick the right marking method for each kind of question."""
    if q["answer_type"] == "state_only":
        return t["state"] == q["expected_state"]
    if q["answer_type"] == "top5_includes":
        if t["state"] != q["expected_state"] or t["route"] != "search":
            return False
        families = [row[6].split(",") for row in t.get("table", {}).get("rows", [])]
        return any(any(s in q["expected"] for s in fam) for fam in families)
    return grade(q, t)


def main():
    preset = sys.argv[1] if len(sys.argv) > 1 else "no-ai"
    if preset not in engine.PRESETS:
        raise SystemExit(f"Preset must be one of: {', '.join(engine.PRESETS)}")
    validator = Validator(json.loads((ENGINE / "contract" / "answer.schema.json").read_text(encoding="utf-8")))
    key = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]
    main_qs = [q for q in key if q.get("set") != "router-fresh"]
    router_qs = [q for q in key if q.get("set") == "router-fresh"]

    if engine.PRESETS[preset]["sql_writer"] == "ollama":
        print(f"Model: {__import__('writers.ollama_writer', fromlist=['x']).OLLAMA_MODEL}   (change with: $env:OLLAMA_MODEL = ...)")
        print("Warming up the model ...")
        print(f"Ready in {engine.warm_up(preset):.1f} s.\n")

    print(f"Preset: {preset}   {engine.PRESETS[preset]}\n")
    print(f"{'ID':<5}{'should go':<10}{'went to':<10}{'answer':<9}{'ms':>9}  question")
    print("-" * 92)
    tickets, results = {}, []
    counts = {"RIGHT": 0, "handoff": 0, "WRONG": 0}
    route_ok = valid = 0
    for q in main_qs:
        previous = tickets.get(q.get("follow_up_of"), {}).get("constraints")
        t = engine.ask(q["question"], previous, preset)
        tickets[q["id"]] = t
        should, went = STATION_FOR[q["expected_route"]], t["trace"]["station"]
        route_ok += should == went
        valid += not list(validator.iter_errors(t))
        correct = grade_any(q, t)
        outcome = "RIGHT" if correct else ("handoff" if t["state"] == "handoff" else "WRONG")
        counts[outcome] += 1
        mark = "" if should == went else "  <- router"
        print(f"{q['id']:<5}{should:<10}{went:<10}{outcome:<9}{t['timing_ms']['total']:>9.0f}  "
              f"{q['question'][:44]}{mark}")
        results.append({"id": q["id"], "should": should, "went": went, "outcome": outcome,
                        "router_reason": t["trace"]["router_reason"], "ticket": t})

    print("-" * 92)
    print("Fresh router questions (written AFTER the router; router not changed since):")
    fresh_ok = 0
    for q in router_qs:
        went, reason = engine.choose_station(q["question"], None, preset)
        ok = went == q["expected_station"]
        fresh_ok += ok
        print(f"{q['id']:<5}{q['expected_station']:<10}{went:<10}{'ok' if ok else 'MISS':<9}{'':>9}  "
              f"{q['question'][:44]}   ({reason})")

    n = len(main_qs)
    times = sorted(r["ticket"]["timing_ms"]["total"] for r in results)
    print("-" * 92)
    print(f"ROUTER    known questions: {route_ok} / {n}    fresh questions: {fresh_ok} / {len(router_qs)}")
    print(f"ANSWERS   RIGHT {counts['RIGHT']} / {n}    handoff (safe) {counts['handoff']}    WRONG (danger) {counts['WRONG']}")
    print(f"CONTRACT  {valid} / {n} tickets valid")
    print(f"TIME      median {times[n // 2]:.0f} ms    slowest {times[-1]:.0f} ms")
    by_station = {}
    for r in results:
        s = by_station.setdefault(r["went"], {"n": 0, "right": 0, "ms": []})
        s["n"] += 1
        s["right"] += r["outcome"] == "RIGHT"
        s["ms"].append(r["ticket"]["timing_ms"]["total"])
    print("\nBy station:")
    for name, s in sorted(by_station.items()):
        ms = sorted(s["ms"])
        print(f"  {name:<8} {s['right']:>2} / {s['n']:<3} right    median {ms[len(ms) // 2]:>8.0f} ms")

    out = HERE / "results" / f"pipeline-{preset}.json"
    out.write_text(json.dumps({"preset": preset, "router_known": route_ok, "router_fresh": fresh_ok,
                               "router_fresh_total": len(router_qs), **counts, "total": n,
                               "contract_valid": valid, "median_ms": times[n // 2], "results": results},
                              indent=2), encoding="utf-8")
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
