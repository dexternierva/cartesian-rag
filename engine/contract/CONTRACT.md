# The Answer Contract (v0.1)

The contract is the **order ticket** between the dining room (the screens) and the kitchen (the RAG engine). The kitchen may cook however it likes, but every plate it sends out must fill in this ticket exactly. The official rules live in [`answer.schema.json`](answer.schema.json), and the three filled-in tickets in [`examples/`](examples/) show what it looks like.

```
  SCREENS (dining room)                         ENGINE (kitchen)
  ┌──────────────────┐   question (text)        ┌──────────────────┐
  │ Assistant widget │ ───────────────────────► │ router → SQL /   │
  │ Audit drawer     │                          │ search → pack    │
  │ Ops console      │ ◄─────────────────────── │ the ticket       │
  └──────────────────┘   answer (THIS CONTRACT) └──────────────────┘
          ▲                                              ▲
          └───────── both sides agree on this ───────────┘
```

## Why a contract?

1. **The screen never guesses.** It draws only what the ticket says. No hard-coded numbers.
2. **The engine can change inside.** Swap the search method or the AI model, and the screens keep working as long as the ticket still fits.
3. **It's testable.** A script checks that every answer matches the schema before a screen sees it.

## Which screen box uses which field

| Screen (wireframe) | What you see | Contract field |
| --- | --- | --- |
| S1 widget | Which state to show (results, "Did you mean?", specialist) | `state` |
| S1 widget | Sentence above the cards | `message` |
| S1 product card | Name, colour, price | `components[].name`, `.color`, `.unit_price` |
| S1 product card | Spec chips | `components[].specs` (max 4) |
| S1 product card | Colour buttons + stock per colour | `components[].variants` |
| S1 product card | "● In stock · 48 units at Indianapolis Regional" | `components[].stock` |
| S1 product card | "Delivers to Chicago in 2 days" | `components[].delivery` |
| S1 product card | Blue Source badge | `components[].citation_ids` → `citations[]` |
| S1 "Show calculation" | 40 × $320.00 = $12,800.00 | `calculation` |
| S2 audit drawer | Confidence | `citations[].confidence` |
| S2 audit drawer | "Extracted 2 min ago" | `citations[].read_at` |
| S2 audit drawer | Schema view (field / value) | `citations[].fields` |
| S2 audit drawer | Executed SQL | `citations[].sql` |
| S2 audit drawer | Spec document tab | `citations[]` where `kind = "document"` |
| States board | "Did you mean…?" chips | `components[]` where `type = "choices"` |
| States board | "Connecting you to a specialist" | `components[]` where `type = "handoff"` |
| Any result table (later) / eval script | Raw result rows | `table` (added in step 4) |
| Streaming state | (later) the loading message per stage | `route` + `timing_ms` |

## Rules the engine must follow

- **No naked numbers.** Any price, stock count or date in `message` must also appear in a cited field.
- **Confidence picks the state:** 0.85 or more → `answer`; 0.65 to 0.84 → `disambiguate`; below 0.65 → `handoff`.
- **Every product card cites at least one row** (`citation_ids` can't be empty).
- **`read_at` is required** on every citation, because the audit drawer promises "synced X min ago".
- **Stock status words:** `available` of 10 or more → `in_stock`; 1 to 9 → `low_stock`; 0 → `out_of_stock`.

## Check the examples

```bash
pip install jsonschema
python validate_examples.py
```
