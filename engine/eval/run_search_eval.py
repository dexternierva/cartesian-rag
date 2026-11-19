"""Score the Search station against the answer key.

    python run_search_eval.py keyword     # BM25 only (no AI needed)
    python run_search_eval.py meaning     # embeddings only (needs Ollama)
    python run_search_eval.py hybrid      # both, fused
    python run_search_eval.py all         # all three, side by side

HOW SEARCH IS MARKED
    Search rarely has one "right answer", so we ask a gentler question:
    "Is a correct product somewhere in the top 5?"  This is called hit@5.
    We also note the POSITION of the first correct product (1 = top of the
    list). A dash means it wasn't in the top 5 at all.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(ENGINE / "app"))

from search_station import answer_with_search  # noqa: E402

try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    from jsonschema import Draft7Validator as Validator


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "keyword"
    modes = ["keyword", "meaning", "hybrid"] if arg == "all" else [arg]
    schema = json.loads((ENGINE / "contract" / "answer.schema.json").read_text(encoding="utf-8"))
    validator = Validator(schema)
    key = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    questions = [q for q in key["questions"] if q["expected_route"] == "search" and not q.get("set")]

    table = {q["id"]: {} for q in questions}
    summary = {}
    for mode in modes:
        hits, valid, times, results = 0, 0, [], []
        for q in questions:
            ticket = answer_with_search(q["question"], mode)
            valid += not list(validator.iter_errors(ticket))
            ranked = [row[1] for row in ticket["table"]["rows"]]          # one SKU per product family
            families = [row[6].split(",") for row in ticket["table"]["rows"]]   # every colour of each family
            position = next((i for i, skus in enumerate(families, start=1)
                             if any(s in q["expected"] for s in skus)), None)
            hits += position is not None
            times.append(ticket["timing_ms"]["total"])
            table[q["id"]][mode] = position
            results.append({"id": q["id"], "question": q["question"], "expected": q["expected"],
                            "position": position, "top5": ranked, "ticket": ticket})
        n = len(questions)
        times.sort()
        summary[mode] = {"hit_at_5": hits, "total": n, "contract_valid": valid, "median_ms": times[n // 2]}
        out_dir = HERE / "results"
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"search-{mode}.json").write_text(
            json.dumps({"mode": mode, **summary[mode], "results": results}, indent=2), encoding="utf-8")

    print(f"Search questions: {len(questions)}   (number = position of the first correct product; - = not in top 5)\n")
    print(f"{'ID':<5}" + "".join(f"{m:>9}" for m in modes) + "   question")
    print("-" * 84)
    for q in questions:
        cells = "".join(f"{(table[q['id']][m] or '-'):>9}" for m in modes)
        print(f"{q['id']:<5}{cells}   {q['question'][:46]}")
    print("-" * 84)
    print(f"{'hit@5':<5}" + "".join(f"{str(summary[m]['hit_at_5']) + '/' + str(summary[m]['total']):>9}" for m in modes))
    print(f"{'valid':<5}" + "".join(f"{str(summary[m]['contract_valid']) + '/' + str(summary[m]['total']):>9}" for m in modes)
          + "   (tickets that follow the contract)")
    print(f"{'ms':<5}" + "".join(f"{summary[m]['median_ms']:>9.0f}" for m in modes) + "   (median time per search)")
    print(f"\nSaved -> {HERE / 'results'} (search-<mode>.json)")


if __name__ == "__main__":
    main()
