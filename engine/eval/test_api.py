"""Automated tests for the API: a robot that clicks every button and checks the result.

    python test_api.py

Uses FastAPI's TestClient, which talks to the API directly in memory: no server
to start, no network. Each test prints PASS or FAIL. This is the kind of test a
QA engineer writes once and runs after every change (a regression test).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))

from fastapi.testclient import TestClient  # noqa: E402

from api import app  # noqa: E402

try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    from jsonschema import Draft7Validator as Validator

client = TestClient(app)
validator = Validator(json.loads((HERE.parent / "contract" / "answer.schema.json").read_text(encoding="utf-8")))
results = []


def check(name, condition, detail=""):
    results.append(condition)
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"   ({detail})" if detail and not condition else ""))


# 1. The kitchen is open
r = client.get("/health")
check("GET /health answers 200", r.status_code == 200, r.text)
check("health says status ok", r.json().get("status") == "ok")

# 2. Elena's question gets the two right chairs, in a valid ticket
r = client.post("/ask", json={"question": "Need 40 ergonomic mesh chairs with 4D armrests in navy, "
                                          "under $350 each, delivered to Chicago within 3 days."})
ticket = r.json()
skus = sorted(c["sku"] for c in ticket.get("components", []) if c.get("type") == "product_card")
check("POST /ask answers 200", r.status_code == 200, r.text[:200])
check("ticket follows the contract", not list(validator.iter_errors(ticket)),
      "; ".join(e.message for e in list(validator.iter_errors(ticket))[:2]))
check("Elena gets exactly AeroTask + ErgoFlex", skus == ["AT-NAV-4D", "EF-ELT-NV"], str(skus))
check("every card has a receipt", all(c["citation_ids"] for c in ticket["components"]))

# 3. Memory without a memory: the browser sends the previous form back
r2 = client.post("/ask", json={"question": "Same chairs, but they must arrive in Chicago within 2 days.",
                               "previous": ticket["constraints"]})
skus2 = sorted(c["sku"] for c in r2.json().get("components", []) if c.get("type") == "product_card")
check("follow-up keeps the old rules and changes one", skus2 == ["AT-NAV-4D"], str(skus2))

# 4. Without the previous form, the API can't know what "same chairs" means
r3 = client.post("/ask", json={"question": "Same chairs, but they must arrive in Chicago within 2 days."})
check("follow-up WITHOUT the form does not invent the old rules",
      r3.json().get("constraints", {}).get("quantity") is None, json.dumps(r3.json().get("constraints")))

# 5. Safety: an upset customer goes to a person
r = client.post("/ask", json={"question": "My order is 4 days late and I want a refund right now!"})
check("angry customer -> handoff", r.json().get("state") == "handoff", r.json().get("state"))

# 6. Ambiguous -> "Did you mean...?"
r = client.post("/ask", json={"question": "Show me the navy shell"})
check("ambiguous question -> disambiguate", r.json().get("state") == "disambiguate", r.json().get("state"))

# 7. Bad requests are refused politely, not crashed on
r = client.post("/ask", json={"question": ""})
check("empty question -> 422 (rejected)", r.status_code == 422, str(r.status_code))
r = client.post("/ask", json={"wrong_field": "hello"})
check("missing question -> 422 (rejected)", r.status_code == 422, str(r.status_code))
r = client.post("/ask", json={"question": "x" * 501})
check("question over 500 characters -> 422", r.status_code == 422, str(r.status_code))

# 8. An attack attempt is just text: it can't reach the database as a command
r = client.post("/ask", json={"question": "navy chairs'; DROP TABLE products; --"})
check("SQL-injection attempt answered safely (200, valid ticket)",
      r.status_code == 200 and not list(validator.iter_errors(r.json())), str(r.status_code))
r = client.post("/ask", json={"question": "How many navy AeroTask Pro Mesh chairs are available in Indianapolis?"})
check("...and the products table still works afterwards", r.json().get("message") == "available: 48", r.json().get("message"))

# 9. R6: a lookup says WHAT the number is about (from the query's own checked filters)
r = client.post("/ask", json={"question": "How many navy AeroTask Pro Mesh chairs are available in Indianapolis?"})
subj = r.json().get("subject", {})
check("lookup names its subject (product, colour, depot, sku)",
      subj.get("product") == "AeroTask Pro Mesh" and subj.get("color") == "Navy"
      and subj.get("depot") and subj.get("sku") == "AT-NAV-4D", str(subj))

# 10. R5: "nothing matches" offers ways out as DATA, and tapping one works
r = client.post("/ask", json={"question": "40 navy mesh chairs with 4D armrests under $300 delivered to Chicago within 2 days"})
t = r.json()
fields = [o["field"] for o in t.get("relax", [])]
check("no-results answer lists ways out (relax)", t.get("state") == "no_results" and len(fields) >= 1, str(t.get("relax")))
check("...and that ticket still follows the contract", not list(validator.iter_errors(t)))
if fields:
    r2 = client.post("/ask", json={"question": "Without " + t["relax"][0]["label"], "previous": t["constraints"], "drop": fields[0]})
    t2 = r2.json()
    check("tapping the first way out gives results", t2.get("state") == "answer"
          and len([c for c in t2["components"] if c.get("type") == "product_card"]) == t["relax"][0]["matches"],
          f"{t2.get('state')} {t2.get('message')}")
    check("...and the removed requirement is gone from the form", fields[0] not in t2.get("constraints", {})
          or t2["constraints"].get(fields[0]) is False)

# 11. R4: removing a requirement chip re-runs the SAME form minus that box, without AI
r = client.post("/ask", json={"question": "Without the price limit", "previous": ticket["constraints"], "drop": "max_unit_price"})
t3 = r.json()
skus3 = sorted(c["sku"] for c in t3.get("components", []) if c.get("type") == "product_card")
check("removing 'under $350' lets the $365 trap chair back in", "ST-NAV-4D" in skus3 or len(skus3) > len(skus), str(skus3))
check("...every other requirement is kept", all(t3["constraints"].get(k) == v for k, v in ticket["constraints"].items()
                                               if k != "max_unit_price"), str(t3.get("constraints")))
r = client.post("/ask", json={"question": "x", "previous": ticket["constraints"], "drop": "intent"})
check("removing something that isn't a requirement -> 422", r.status_code == 422, str(r.status_code))

print(f"\n{sum(results)} / {len(results)} checks passed")
sys.exit(0 if all(results) else 1)
