"""Check every example ticket against the contract.

Think of this as the restaurant manager holding each sample ticket up
against the official ticket form: is anything missing or in the wrong box?

Run:  python validate_examples.py
"""
import json
from pathlib import Path

try:
    from jsonschema import Draft202012Validator  # jsonschema 4.x
except ImportError:  # older jsonschema (3.x) only knows draft-07; our rules work there too
    from jsonschema import Draft7Validator as Draft202012Validator

HERE = Path(__file__).parent
schema = json.loads((HERE / "answer.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)

all_ok = True
for path in sorted((HERE / "examples").glob("*.json")):
    ticket = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(ticket), key=lambda e: list(e.path))

    # Extra house rule the schema can't express: every citation_id a card
    # points to must exist in the citations list.
    known = {c["id"] for c in ticket.get("citations", [])}
    for comp in ticket.get("components", []):
        for cid in comp.get("citation_ids", []):
            if cid not in known:
                errors.append(f"card {comp.get('sku')} points to missing citation {cid}")

    if errors:
        all_ok = False
        print(f"FAIL  {path.name}")
        for e in errors:
            where = "/".join(str(p) for p in getattr(e, "path", [])) or "(top)"
            print(f"      - {where}: {getattr(e, 'message', e)}")
    else:
        print(f"OK    {path.name}")

print("\nAll tickets follow the contract." if all_ok else "\nSome tickets break the contract.")
