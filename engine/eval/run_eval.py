"""Score an answering method against the answer key.

    python run_eval.py <method> [set]

METHODS
    baseline         SQL station, rule-based SQL writer (no AI)
    ollama           SQL station, the AI writes the whole SQL
    hybrid-rules     Hybrid station, rules fill in the form (no AI)
    hybrid-ollama    Hybrid station, the AI fills in the form, code builds the SQL
    hybrid-both      Hybrid station, the AI fills the form and the rules fill any gaps

QUESTION SETS
    sql    simple lookups (Q01-Q10, Q21)              <- default
    hard   maths + Elena's multi-rule questions (Q11-Q16)
    fresh  7 NEW phrasings written after the rules (Q29-Q35): the fair test

Examples:
    python run_eval.py ollama
    python run_eval.py hybrid-ollama hard

For every question it checks: right answer? ticket follows the contract? how long?
Results are saved to eval/results/<method>-<set>.json, with every ticket.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(ENGINE / "app"))

try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    from jsonschema import Draft7Validator as Validator

ROUTE_SETS = {"sql": {"sql"}, "hard": {"python", "hybrid"}, "fresh": set()}


def load_method(name):
    """Return (answer_function, label, warm_up_function or None)."""
    if name in ("baseline", "ollama"):
        from sql_station import answer_with_sql
        if name == "baseline":
            from writers.baseline import write_sql
            warm = None
        else:
            from writers.ollama_writer import warm_up, write_sql
            warm = warm_up
        return (lambda q, previous=None: answer_with_sql(q, write_sql)), write_sql.label, warm
    if name == "hybrid-both":
        from hybrid_station import answer_with_hybrid
        from extractors.combined import make_combined
        from extractors.ollama_extractor import extract as ai_extract, warm_up
        from extractors.rules import extract as rules_extract
        both = make_combined(ai_extract, rules_extract)
        return (lambda q, previous=None: answer_with_hybrid(q, both, previous)), both.label, warm_up
    if name in ("hybrid-rules", "hybrid-ollama"):
        from hybrid_station import answer_with_hybrid
        if name == "hybrid-rules":
            from extractors.rules import extract
            warm = None
        else:
            from extractors.ollama_extractor import extract, warm_up
            warm = warm_up
        return (lambda q, previous=None: answer_with_hybrid(q, extract, previous)), extract.label, warm
    raise SystemExit(f"Unknown method '{name}'. Use: baseline, ollama, hybrid-rules, hybrid-ollama, hybrid-both")


def grade(q, ticket):
    """Is the ticket's answer the same as the answer key's?"""
    if ticket["route"] == "handoff":
        return False
    if ticket["state"] not in q.get("accepted_states", [q["expected_state"]]):
        return False
    if q.get("expected_sku"):                    # right for the RIGHT reason: check the receipts
        cited = {c.get("row_key", {}).get("sku") for c in ticket.get("citations", [])}
        if q["expected_sku"] not in cited:
            return False
    rows = ticket.get("table", {}).get("rows", [])
    expected = q["expected"]
    if q["answer_type"] == "number":
        if ticket["state"] == "no_results":       # "none" is right only if the truth is 0
            return float(expected) == 0
        cells = rows[0] if rows else []
        return any(isinstance(c, (int, float)) and abs(c - float(expected)) < 0.01 for c in cells)
    if q["answer_type"] == "text":
        return bool(rows) and expected in rows[0]
    if q["answer_type"] == "sku_set":
        cols = ticket["table"]["columns"]
        i = cols.index("sku") if "sku" in cols else 0
        return sorted({r[i] for r in rows}) == sorted(expected)
    return False


def main():
    method = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    set_name = sys.argv[2] if len(sys.argv) > 2 else "sql"
    if set_name not in ROUTE_SETS:
        raise SystemExit("Question set must be 'sql', 'hard' or 'fresh'")
    answer, label, warm = load_method(method)

    schema = json.loads((ENGINE / "contract" / "answer.schema.json").read_text(encoding="utf-8"))
    validator = Validator(schema)
    key = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if set_name == "fresh":
        questions = [q for q in key["questions"] if q.get("set") == "fresh"]
    else:
        questions = [q for q in key["questions"] if q["expected_route"] in ROUTE_SETS[set_name] and not q.get("set")]

    cold_start_s = None
    if warm:
        print(f"Model: {__import__('writers.ollama_writer', fromlist=['x']).OLLAMA_MODEL}   (change with: $env:OLLAMA_MODEL = ...)")
        print("Warming up the model (cold start) ...")
        cold_start_s = warm()
        print(f"Model ready in {cold_start_s:.1f} s. Timings below are for a WARM model.\n")

    print(f"Method: {method}  ({label})   Set: {set_name}   Questions: {len(questions)}\n")
    print(f"{'ID':<5}{'result':<10}{'ticket':<8}{'state':<12}{'ms':>8}  answer")
    print("-" * 80)
    try:
        from writers.ollama_writer import CALL_STATS
    except Exception:
        CALL_STATS = []
    CALL_STATS.clear()
    results, tickets = [], {}
    right = valid = wrong = handoffs = 0
    for q in questions:
        # CONVERSATION MEMORY: a follow-up gets the form (constraints) of the question before it
        previous = tickets.get(q.get("follow_up_of"), {}).get("constraints")
        ticket = answer(q["question"], previous)
        tickets[q["id"]] = ticket
        errors = list(validator.iter_errors(ticket))
        ticket_ok = not errors
        correct = grade(q, ticket)
        # Three outcomes: RIGHT, handoff ("I don't know", safe), WRONG (confidently wrong, dangerous)
        outcome = "RIGHT" if correct else ("handoff" if ticket["state"] == "handoff" else "WRONG")
        right += outcome == "RIGHT"
        wrong += outcome == "WRONG"
        handoffs += outcome == "handoff"
        valid += ticket_ok
        print(f"{q['id']:<5}{outcome:<10}{'OK' if ticket_ok else 'BROKEN':<8}"
              f"{ticket['state']:<12}{ticket['timing_ms']['total']:>8.1f}  {ticket['message'][:36]}")
        results.append({"id": q["id"], "question": q["question"], "expected": q["expected"],
                        "outcome": outcome, "correct": correct, "ticket_valid": ticket_ok,
                        "contract_errors": [e.message for e in errors][:3],
                        "form": ticket.get("constraints"), "sql": ticket.get("trace", {}).get("sql"),
                        "ticket": ticket})

    n = len(questions)
    times = sorted(r["ticket"]["timing_ms"]["total"] for r in results)
    median = times[n // 2]
    print("-" * 80)
    print(f"RIGHT:           {right} / {n}  ({right / n:.0%})")
    print(f"handoff (safe):  {handoffs} / {n}")
    print(f"WRONG (danger):  {wrong} / {n}")
    print(f"Contract-valid:  {valid} / {n}")
    print(f"Median time:     {median:.1f} ms   (design budget: 1200 ms)")

    if CALL_STATS:
        k = len(CALL_STATS)
        avg = {f: sum(s[f] for s in CALL_STATS) / k for f in CALL_STATS[0]}
        print(f"\nWhere the model's time goes (average of {k} calls):")
        print(f"  reading the prompt:  {avg['read_tokens']:6.0f} tokens in {avg['read_s']:5.1f} s"
              f"   ({avg['read_tokens'] / max(avg['read_s'], 1e-9):5.0f} tokens/s)")
        print(f"  writing the answer:  {avg['write_tokens']:6.0f} tokens in {avg['write_s']:5.1f} s"
              f"   ({avg['write_tokens'] / max(avg['write_s'], 1e-9):5.0f} tokens/s)")
        print(f"  loading the model:                 {avg['load_s']:5.1f} s")

    misses = [r for r in results if r["outcome"] != "RIGHT"]
    if misses:
        print("\nMisses, to learn from:")
        for r in misses:
            print(f"  {r['id']} [{r['outcome']}] {r['question']}")
            print(f"       expected: {r['expected']}")
            if r["form"] is not None:
                print(f"       form:     {json.dumps(r['form'])}")
            print(f"       SQL used: {r['sql'] or '(none)'}")
            if r["contract_errors"]:
                print(f"       contract: {r['contract_errors']}")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    model = re.search(r"\(([^)]+)\)", label)
    slug = method + (f"-{re.sub(r'[^a-z0-9]+', '-', model.group(1).lower()).strip('-')}"
                     if model and method in ("ollama", "hybrid-ollama", "hybrid-both") else "") + f"-{set_name}"
    out = out_dir / f"{slug}.json"
    out.write_text(json.dumps({"method": method, "writer": label, "set": set_name, "cold_start_s": cold_start_s,
                               "accuracy": right / n, "right": right, "handoff": handoffs, "wrong": wrong,
                               "total": n, "contract_valid": valid, "median_ms": median,
                               "model_calls": list(CALL_STATS),
                               "results": results}, indent=2), encoding="utf-8")
    print(f"\nSaved -> {out}")

    # Side-by-side with every earlier run on the same question set
    others = []
    for f in sorted(out_dir.glob(f"*-{set_name}.json")):
        if f == out:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("total") == n:
            others.append((f.stem.replace(f"-{set_name}", ""), d))
    if others:
        cols = others + [(slug.replace(f"-{set_name}", "") + " (now)", {"right": right, "handoff": handoffs,
                                                                         "wrong": wrong, "median_ms": median})]
        # Short column names, one row per run (easier to read than very wide columns)
        print(f"\nAll runs on the '{set_name}' set:")
        print(f"  {'run':<44}{'right':>6}{'handoff':>9}{'wrong':>7}{'median ms':>11}")
        for name, d in cols:
            r = d.get("right", d.get("correct", "-"))
            print(f"  {name:<44}{r:>6}{d.get('handoff', '-'):>9}{d.get('wrong', '-'):>7}{d['median_ms']:>11.0f}")


if __name__ == "__main__":
    main()
