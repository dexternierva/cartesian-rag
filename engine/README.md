# CartesianRAG Engine — Steps 2 & 3: the Contract and the Pantry

Before the RAG engine (the "kitchen") can be built, two things must exist:

1. **The contract** — the order ticket the kitchen must fill in for the screens.
2. **The pantry** — a fake store database, plus a test with an answer key.

```
  SCREENS (dining room)        CONTRACT (order ticket)        ENGINE (kitchen)        PANTRY
  ┌───────────────┐         ┌───────────────────────┐       ┌──────────────┐     ┌──────────┐
  │ widget, cards │ ◄────── │ answer.schema.json    │ ◄──── │ (step 4,     │ ──► │ store.db │
  │ audit drawer  │         │ "what every answer    │       │  not built   │     │ 6 tables │
  └───────────────┘         │  must contain"        │       │  yet)        │     └──────────┘
                            └───────────────────────┘       └──────────────┘          ▲
                                                                   ▲                  │
                                                                   └── graded by ── eval/questions.json
                                                                                     (22 Qs + answer key)
```

## How to run everything (Windows)

```bash
python -m pip install pandas jsonschema

cd engine/data
python build_store.py           # builds store.db + csv/ (same data every time)

cd ../contract
python validate_examples.py     # checks the 3 sample tickets follow the contract

cd ../eval
python check_answer_key.py      # proves all 22 answers against store.db
```

## Folder map

| Path                            | What it is                                            | Restaurant analogy                       |
| ------------------------------- | ----------------------------------------------------- | ---------------------------------------- |
| `contract/answer.schema.json`   | The rules every answer must follow (JSON Schema)      | The blank order form                     |
| `contract/CONTRACT.md`          | Which screen box reads which field                    | Which dish goes to which table           |
| `contract/examples/*.json`      | 3 filled-in answers: results, "did you mean", handoff | Sample tickets                           |
| `contract/validate_examples.py` | Checks tickets against the form                       | The manager checking tickets             |
| `data/build_store.py`           | Builds the database from a recipe                     | The shopping list + stocking the shelves |
| `data/store.db`                 | The database (SQLite, one file)                       | The pantry                               |
| `data/csv/`                     | The same tables as CSV, to open in Excel              | A printed inventory sheet                |
| `eval/questions.json`           | 22 test questions with correct answers                | The teacher's answer key                 |
| `eval/check_answer_key.py`      | Proves every answer against the database              | Checking the answer key itself           |

## What's in the pantry

```
 depots ──────────────┐
 (5 warehouses)       │ depot_id
                      ▼
 delivery_times    inventory ◄────── sku ────── products
 (depot → city,    (sku × depot:                (54 products: chairs,
  days)             on_hand, reserved)           desks, accessories,
                      │                          a jacket, a cable)
                      ▼
               stock_available  (a VIEW: available = on_hand − reserved)

 orders   (4 orders, for Task B later)        policies  (4 sample policy clauses)
```

**Story rows vs filler rows.** Story rows are written by hand: the products from the storyboards plus **traps**. Filler rows are random (with a fixed seed, so they're identical every run) and are never navy, so they can't change Elena's answer.

**The five traps.** Each one breaks exactly one of Elena's rules, so a careless engine gets caught:

| Trap | SKU | Breaks which rule |
| --- | --- | --- |
| Meridian Mesh Executive | MX-NAV-4D | $365, over the $350 budget |
| Pulse Task Mesh | PT-NAV-4D | Only in Dallas, 4 days to Chicago (needs ≤ 3) |
| Brio Mesh Task | BR-NAV-3D | 3D armrests, not 4D |
| Regent Leather Manager | RG-NAV-4D | Leather, not mesh |
| Corsa Mesh | CM-NAV-4D | 50 total, but split 25 + 25, so no single depot has 40 |

Plus three look-alikes for other tests: a **Harbor Shell** side chair and a **Summit Trail Shell** jacket (for "Did you mean…?"), and a **navy USB-C cable** (to check "navy" doesn't drag in chairs).

## The answer key (22 questions)

| Route the engine should pick | Questions | What they test |
| --- | --- | --- |
| `sql` (exact numbers) | Q01–Q10, Q21 | Stock, prices, sorting, totals, honest "none" |
| `python` (maths over rows) | Q11–Q12 | Totals and averages |
| `hybrid` (rules + description) | Q13–Q16 | Elena's question and follow-ups; traps; one depot vs many |
| `search` (meaning) | Q17–Q20 | Descriptions, vocabulary mismatch, ambiguity |
| `handoff` (send to a human) | Q22 | Angry customer, critical intent |

## Mental models

1. **Contract = stencil.** An answer that doesn't fit the stencil never reaches the screen.
2. **Design rules become data rules.** The drawer shows "synced 2 min ago", so `read_at` is required.
3. **Seeded randomness = a deck shuffled the same way every time.**
4. **Traps = trick questions on a test.** Each one checks one rule at a time.
5. **Check the answer key before grading.** `check_answer_key.py` must say 22 / 22 before we trust any engine score.

## Step 4a: the Text-to-SQL station (built, baseline scored)

```
 question -> 1. WRITER -> 2. GUARD -> 3. RUN -> 4. PACK -> ticket (contract)
             words->SQL   safe?       read-only  receipts
             (swappable)
```

| File | Job | Analogy |
| --- | --- | --- |
| `app/db.py` | Opens store.db read-only | A glass case: look, don't touch |
| `app/schema_card.py` | Describes the tables for an AI writer | The floor plan a new waiter gets |
| `app/sql_guard.py` | Blocks unsafe SQL (one statement, SELECT only, known tables) | The bouncer |
| `app/sql_station.py` | Runs the 4 steps and builds the ticket | The assembly line |
| `app/writers/baseline.py` | No-AI writer: 4 hand-written rules | A vending machine |
| `eval/run_eval.py` | Scores a writer against the answer key | The marking machine |
| `eval/results/baseline.json` | The scores plus every real ticket | Photos of real dishes |

```bash
cd engine/app  && python sql_guard.py       # watch the bouncer allow/block 5 queries
cd engine/app  && python schema_card.py     # print the map an AI writer will get
cd engine/eval && python run_eval.py        # score the baseline
```

**Baseline score (no AI): 6 / 11 correct (55%), 11 / 11 contract-valid, 0 wrong answers.**
The 5 misses are honest hand-offs ("I can't answer that reliably"), never made-up numbers.
This is the number an AI writer has to beat.

## Step 4b: the AI writer (Ollama, runs on your PC)

`app/writers/ollama_writer.py` sends a local model three things (the **prompt**): rules, the schema card, and 5 solved examples. The model replies with SQL, which still goes through the guard.

**One-time setup**

1. Install Ollama from https://ollama.com/download and open it.
2. Download a model (pick by your PC's memory):

   | Your RAM | Command | Download size |
   | --- | --- | --- |
   | 16 GB or more | `ollama pull qwen2.5-coder:7b` | about 4.7 GB |
   | 8 GB | `ollama pull qwen2.5-coder:3b` | about 2 GB |

3. If you chose a model other than `qwen2.5-coder:7b`, tell the code (PowerShell):
   `$env:OLLAMA_MODEL = "qwen2.5-coder:3b"`

**Run**

```bash
cd engine/app  && python check_ollama.py      # 3 checks: running? model there? can it answer?
cd engine/eval && python run_eval.py ollama   # score it and compare with the baseline
```

**Safety paths (tested with a scripted stand-in for Ollama):**

| If the model... | The station... |
| --- | --- |
| writes SQL with a mistake (bad column) | shows it the error and lets it fix it once |
| ignores the JSON format | still finds the SQL in its reply |
| writes something dangerous (`DROP TABLE`) | blocks it and hands off to a human |
| writes valid SQL that answers the wrong question | can't tell! Only the answer key catches this (marked **WRONG**) |

## Step 4c: the Search station (keyword scored; meaning + hybrid ready to run)

```
 question -> KEYWORD detective (BM25) ---+
                                         +--> FUSION (RRF) -> top 5 -> ticket
          -> MEANING detective (vectors) +
```

| File | Job | Analogy |
| --- | --- | --- |
| `app/bm25.py` | Keyword scoring, written from scratch | A detective who matches exact words |
| `app/embedder.py` | Turns text into "meaning coordinates" via Ollama | A detective who matches ideas |
| `app/search_station.py` | Row-to-text, both searches, fusion, ticket | The search desk |
| `eval/run_search_eval.py` | Scores search with hit@5 | The marking machine for search |

```bash
cd engine/app  && python bm25.py                                    # tiny demo of keyword scoring
cd engine/app  && python search_station.py keyword "rain jacket"    # try any search
cd engine/eval && python run_search_eval.py keyword                 # no AI needed

ollama pull nomic-embed-text                                        # one-time, about 270 MB
cd engine/eval && python run_search_eval.py all                     # keyword vs meaning vs hybrid
```

**Keyword-only score: 7 / 10 (hit@5).** The 3 misses are the questions that share no words with the product:
"charge my laptop" (charging cable), "a light for my desk" (desk lamp), "put my feet up" (footrest).

## Step 4d: the Hybrid station (AI fills a form, code builds the SQL)

```
 question -> EXTRACTOR fills the form -> GROUND (real values only) -> SQL TEMPLATE (parameters, no pasted text)
          -> RUN -> best depot per product -> product cards + receipts
                    (nothing found? -> "Without the delivery-time limit, 1 option would match.")
```

| File | Job |
| --- | --- |
| `app/grounding.py` | Before trusting an empty result, check the query didn't search for invented values |
| `app/extractors/vocab.py` | The store's real vocabulary + the form checker |
| `app/extractors/rules.py` | Fills the form with patterns (no AI) |
| `app/extractors/ollama_extractor.py` | Fills the form with the local model |
| `app/extractors/combined.py` | AI first, then the rules fill any box the AI left empty |
| `app/hybrid_station.py` | Form -> SQL template -> cards, totals, averages, follow-ups |

```bash
cd engine/app  && python hybrid_station.py "40 navy mesh chairs, 4D arms, under $350, Chicago within 3 days"
cd engine/eval && python run_eval.py hybrid-rules hard      # no AI
cd engine/eval && python run_eval.py hybrid-ollama hard     # AI form-filler (Ollama running)
cd engine/eval && python run_eval.py hybrid-ollama fresh    # the fair test: phrasings nobody tuned for
cd engine/eval && python run_eval.py hybrid-both fresh      # AI first, rules fill the gaps
```

**Question sets:** `sql` (simple lookups), `hard` (maths + Elena's questions), `fresh` (7 new phrasings written after the rules, never tuned against).

| Method | hard | fresh |
| --- | --- | --- |
| AI writes the whole SQL (qwen2.5-coder:3b) | 0 / 6 (6 wrong) | not run |
| Rules fill the form (no AI) | 6 / 6 | 5 / 7 (2 wrong) |
| AI fills the form | 5 / 6 (1 wrong) | your run |
| AI fills the form + rules fill gaps (`hybrid-both`) | 6 / 6 (replay of real forms) | your run |

## Step 4e: the router and one front door

```
 question ──► ROUTER (rules first) ──┬─► handoff   angry, refund, wants a person
              │                      ├─► sql       how many, which depot, status
              │ nothing matched?     ├─► hybrid    quantities, budgets, deadlines, totals
              └─► AI picks 1 word ──►└─► search    descriptions ("Did you mean...?" if ambiguous)
```

| File | Job |
| --- | --- |
| `app/router.py` | Rules that pick a station, with a printed reason |
| `app/ai_router.py` | AI tie-breaker, used only when the rules found nothing |
| `app/engine.py` | `ask(question)`: the single front door for every question |
| `eval/run_pipeline_eval.py` | Scores router + all stations together |

```bash
cd engine/app  && python engine.py "Show me the navy shell"          # try any question (no AI)
cd engine/app  && python engine.py ai "I'd like to buy eight desks"   # with AI
cd engine/eval && python run_pipeline_eval.py no-ai                   # whole engine, rules only
cd engine/eval && python run_pipeline_eval.py ai                      # whole engine, with Ollama
```

**No-AI pipeline:** router 35 / 35 on known questions but **4 / 8 on fresh ones**; answers 26 / 35 right, 4 wrong, median 10 ms.

## Step 5: the API and the connected prototype

```
                    ┌── LIVE:     prototype/?api=http://localhost:8001  ──► FastAPI ──► engine.ask()
 Prototype widget ──┤
                    └── RECORDED: prototype/answers.json (real tickets, replayed on GitHub Pages)
```

| File | Job |
| --- | --- |
| `app/api.py` | FastAPI: `GET /health`, `POST /ask` (question + optional previous form) |
| `eval/test_api.py` | 15 automated checks: answers, memory, safety, bad requests, SQL injection |
| `app/record_demo.py` | Runs a demo conversation and saves real tickets to `prototype/answers.json` |
| `prototype/index.html` | Widget "engine mode": draws cards, chips, hand-offs and receipts from tickets |

**Setup (once):** `python -m pip install -r requirements.txt`

```bash
# A. Automated API tests
cd engine/eval && python test_api.py

# B. Record real answers for GitHub (use 'ai' for the published version)
cd engine/app  && python record_demo.py ai

# C. See the prototype with recorded answers (two terminals not needed)
cd prototype   && python -m http.server 8080
#    open http://localhost:8080/#shopper

# D. See the prototype with the LIVE engine (second terminal)
cd engine/app  && python -m uvicorn api:app --port 8001          # rules only
#    PowerShell, with AI:  $env:CARTESIAN_PRESET = "ai"; python -m uvicorn api:app --port 8001
#    open http://localhost:8080/?api=http://localhost:8001#shopper
#    API playground: http://localhost:8001/docs
```

Opening `index.html` by double-clicking still works, but browsers block it from reading `answers.json`, so it falls back to the original hand-written demo. Use the small web server (C), or GitHub Pages.

## Next

Re-record with AI, publish to GitHub Pages, then Step 1 (the design check) and the case-study write-up.
