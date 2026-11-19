"""Prove the answer key is right BEFORE we grade the engine with it.

A teacher checks the answer sheet before marking tests: if the answer
sheet is wrong, every student gets marked wrong. This script does that.

For each question:
  - if it has a gold_sql, run it on store.db and compare with 'expected'
  - if it's a search question, check the expected SKUs really exist

Run:  python check_answer_key.py
"""
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB = (HERE.parent / "data" / "store.db").resolve()
key = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

# immutable=1 opens the file read-only without locking it (safe on synced folders)
con = sqlite3.connect(f"file:{DB.as_posix()}?immutable=1", uri=True)
all_skus = {row[0] for row in con.execute("SELECT sku FROM products")}

def check(q):
    kind, expected = q["answer_type"], q["expected"]
    if "gold_sql" in q:
        rows = con.execute(q["gold_sql"]).fetchall()
        if kind == "number":
            got = rows[0][0] if rows and rows[0][0] is not None else 0
            return abs(float(got) - float(expected)) < 0.01, got
        if kind == "text":
            got = rows[0][0] if rows else None
            return got == expected, got
        if kind == "sku_set":
            got = sorted(r[0] for r in rows)
            return got == sorted(expected), got
    if kind == "top5_includes":
        missing = [s for s in expected if s not in all_skus]
        return not missing, ("all exist" if not missing else f"missing {missing}")
    if kind == "state_only":
        return True, "(graded on state only)"
    if kind == "route_only":
        return True, f"(router test: should go to {q['expected_station']})"
    return False, "no way to check"

ok_count = 0
print(f"{'ID':<5}{'route':<8}{'state':<14}{'result':<7}got")
print("-" * 70)
for q in key["questions"]:
    ok, got = check(q)
    ok_count += ok
    print(f"{q['id']:<5}{q['expected_route']:<8}{q['expected_state']:<14}{'OK' if ok else 'WRONG':<7}{got}")

total = len(key["questions"])
print("-" * 70)
print(f"{ok_count} / {total} answers confirmed against store.db")
