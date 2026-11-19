# Design ↔ Engine Findings Log

Real results from building the engine, and what each one means for the design. This log feeds the "Design ↔ Engine" chapter of the case study. Numbers here are measured, not estimated.

## Run 1 — Text-to-SQL station, 11 SQL-route questions (2026-11-12)

| Writer | Right | Hand-off (safe) | Wrong (dangerous) | Median time |
| --- | --- | --- | --- | --- |
| Baseline (hand-written rules, no AI) | 6 / 11 | 5 | 0 | 6 ms |
| Local AI model via Ollama, on Dex's PC | 10 / 11 as first marked; 11 / 11 after fixing the marking (see E2) | 0 | 0 | 7,889 ms |

Cold start (first question after the model loads): 62.4 s.

### E1. Answers take about 8 seconds, not 1.2

- **Measured:** median 7.9 s per question; range 6.3–12.5 s. The database part is 1–4 ms. Over 99.9% of the wait is the AI writing the SQL.
- **Design budget was:** 1.2 s total.
- **What it means for the design:**
  - The loading state is not a brief flicker. It is a place people stay for 6–12 seconds, so it must show progress in stages ("Understanding your question… Writing the query… Checking stock…").
  - Send disabled + skeleton cards alone would feel broken at 8 s.
  - Prompt chips and remembered answers matter more: a tapped chip with a saved answer can be instant.
- **Engine options to test:** a smaller model, a PC with a graphics card, or a hosted model.

### E2. "Zero" and "nothing found" are two honest ways to say no

- **What happened:** for "Are black AeroTask chairs in stock in Columbus?" the model filtered for stock above zero and got an empty result. That is a correct "No". The marking script expected a row saying `available = 0` and marked it WRONG.
- **Fix:** the answer key now accepts both shapes for that question. The test was wrong, not the model.
- **What it means for the design:** the widget needs a proper "No" answer for yes/no stock questions, ideally with an alternative ("None in Columbus. 22 in Indianapolis."), instead of the generic "nothing matches".
- **Rule we follow:** change the test only when the engine's answer was true. Never change it to hide a real error.

### E3. Cold start is a full minute

- **Measured:** 62.4 s for the first question, while the model loads into memory.
- **Fix:** the eval now warms the model up first and reports the cold start separately. The engine asks Ollama to keep the model loaded for 30 minutes.
- **What it means for the design:** a real deployment keeps the model warm; the first visitor of the day must never pay that minute.

### E4. The contract grew twice because of testing

- `table` (raw result rows) was added so answers can be marked without reading prose.
- `trace` (the SQL, number of tries, which writer) was added because a query that returns no rows left no receipt, so the miss could not be diagnosed.
- **Lesson:** "can we debug it?" is a design requirement too.

### E5. The guard and the answer key catch different things

- The guard stops **harmful** SQL (deleting, unknown tables).
- Only the answer key catches **mistaken** SQL (safe query, wrong question).
- Both are needed. Neither replaces the other.

### E6. Duplicate rows made a correct answer look vague

- "What does the AeroTask Pro Mesh cost?" returned 320, 320, 320 (one per colour) and the message said "Found 3 rows".
- **Fix:** the station now removes identical rows, so the message reads "unit_price: 320.0".

## Run 2 — Text-to-SQL with qwen2.5-coder:3b, after fixes (2026-11-12)

| Writer | Right | Hand-off | Wrong | Median time | Model load | First question |
| --- | --- | --- | --- | --- | --- | --- |
| qwen2.5-coder:3b via Ollama | 11 / 11 | 0 | 0 | 7,802 ms | 13.6 s | 39.1 s |

### E7. The first question is slow even after the model is loaded

- **Measured:** the model loaded in 13.6 s, yet the first real question still took 39.1 s. Later questions took 6–11 s.
- **Why:** the first question is when the model reads the long prompt (rules + schema card + examples) for the first time. Ollama then remembers that unchanging part, so later questions only add the new sentence.
- **Fix:** the warm-up now sends the real prompt, so the "reading the rulebook" cost is paid before any user asks anything.
- **What it means for the design:** prompt length has a real cost. Every table or example added to the schema card makes cold starts slower.

### E8. A small model was enough for simple SQL

- The 3b model answered all 11 SQL questions correctly. These are single-step lookups, sorts and counts.
- **Caution:** 11 questions is a small test. Elena's multi-rule question (hybrid route) is much harder and not yet tested.

## Run 3 — Search station, keyword only, 10 search questions (2026-11-12)

| Mode | hit@5 | Median time |
| --- | --- | --- |
| Keyword (BM25, no AI) | 7 / 10 | 4 ms |
| Meaning (nomic-embed-text via Ollama) | 8 / 10 | 2,293 ms |
| Hybrid (both, fused with RRF) | 9 / 10 | 2,360 ms |

Measured on Dex's PC, before the two improvements in E13 and E14.

### E9. Keyword search fails exactly where words differ

- **Missed:** "Something to charge my laptop" (product says *charging cable*), "A light for my desk" (*desk lamp*), "Somewhere to put my feet up under the desk" (*footrest*).
- **Found:** everything that shared at least one distinctive word, including "Water-resistant trail shell" (matched on *trail* and *shell*, not on meaning).
- **What it means for the design:** this is the "vocabulary mismatch" pain point from discovery, now reproduced with real data. It is the case for adding meaning-based search.

### E10. Test notes must never sit in searchable text

- The trap notes ("[TRAP: over the $350 budget]") were inside product descriptions. Search would have matched words like "budget" and scored better than it deserved.
- **Fix:** notes moved to their own `test_note` column, which search never reads.
- **Lesson:** keep the answer sheet out of the exam paper.

### E11. Hybrid beat both detectives, because they fail on different questions

| Question | Keyword | Meaning | Hybrid | What happened |
| --- | --- | --- | --- | --- |
| "Stackable chairs for a waiting room" | 1st | missed (6th) | 1st | Meaning saw "chairs" and returned office chairs; it lost the detail "stackable". Keyword caught the exact word. |
| "Something to charge my laptop" | missed | 1st | 1st | No shared words with "charging cable". Meaning understood it. |
| "A light for my desk" | missed | 1st | 4th | Meaning put the lamp first. Fusion pulled it down because keyword pushed every "desk" up. |
| "Somewhere to put my feet up under the desk" | missed | missed | missed | Both were distracted by "desk"; the footrest's description was nearly empty (see E13). |

- **Lesson:** keyword is precise about rare words; meaning is good at ideas. Each covers the other's blind spot.
- **Cost of fusion:** when one detective is confidently right and the other is noisy, the right answer can slide down (lamp: 1st to 4th). Equal weighting is a starting point, not the final answer.

### E12. Meaning search costs about 2.3 s per question; keyword costs 4 ms

- The 2.3 s is the embedding model turning the question into coordinates on a CPU.
- **Design idea:** show keyword results immediately, then refine when the meaning results arrive.

### E13. Search is only as good as the product text

- Filler products had descriptions like "Rest Footrest in black." There was nothing for meaning search to understand.
- **Fix:** each product type now has a catalog-style description, written without copying words from the test questions.
- **What it means for the design/business:** catalog content quality is a search feature. Thin descriptions cap what any search engine can do.

### E14. The same product in three colours took three of the five slots

- "AeroTask Pro Mesh" in black, navy and grey filled ranks 1 to 3, pushing other products out.
- **Fix:** results are grouped by product family. One slot per product; colours become the variant buttons on the card. The engine now matches the card design.
- **Effect on keyword-only:** 7 / 10 became 8 / 10 (the desk lamp moved up to 4th).

### E15. "Navy shell" returns three different things with almost equal scores

- Top 3 for "Show me the navy shell": a side chair, a jacket and an office chair, each from a different category, with scores within 3% of each other.
- **What it means for the design:** this is a measurable trigger for the "Did you mean...?" chips: several top results, close scores, different categories.

## Run 4 — Baseline on the hard set (maths + Elena's questions)

| Writer | Right | Hand-off | Wrong |
| --- | --- | --- | --- |
| Baseline (rules, no AI) | 0 / 6 | 5 | 1 |

### E16. The first genuinely wrong answer

- "What would 40 navy AeroTask Pro Mesh chairs cost in total?" The baseline saw the word "cost" and answered **320.0** (the price of one chair). The truth is 12,800.
- This is the dangerous outcome: a confident, plausible, wrong number, with a real citation attached.
- **Lesson:** a citation proves where a number came from, not that it answers the question that was asked.

## Run 5 — Search after the two improvements (E13, E14), on Dex's PC

| Mode | hit@5 before | hit@5 after | Median time |
| --- | --- | --- | --- |
| Keyword (BM25) | 7 / 10 | 8 / 10 | 2 ms |
| Meaning (nomic-embed-text) | 8 / 10 | **10 / 10** | 2,250 ms |
| Hybrid (RRF fusion) | 9 / 10 | **10 / 10** | 2,141 ms |

### E17. Better product text fixed what a better algorithm couldn't

- "Somewhere to put my feet up under the desk": not found by any method before; meaning found the footrest 3rd, hybrid 5th, once its description said what a footrest is for.
- "A light for my desk": hybrid moved from 4th to 3rd.
- No search code changed between these runs except grouping colours (E14). The rest of the gain came from the data.

## Run 6 — Hard set, the AI writes the whole SQL (qwen2.5-coder:3b)

| Method | Right | Hand-off | Wrong | Median time |
| --- | --- | --- | --- | --- |
| Baseline SQL rules | 0 / 6 | 5 | 1 | 2 ms |
| AI writes whole SQL | 0 / 6 | 0 | **6** | 16,585 ms |

### E18. Three kinds of mistake in the model's SQL

| Mistake | Example from the run | Questions |
| --- | --- | --- |
| Invented a product name | `p.name = 'Mesh Chair'` (no such product) | Q13, Q15, Q16 |
| Exact match on descriptive text | `material = 'Mesh'` (real values: 'Breathable mesh', 'Elastomer mesh') | Q12 |
| Used the wrong table | `FROM orders` (past orders) instead of stock | Q11, Q13, Q14 |

### E19. A confident "No" is the most expensive failure

- All six answers said "No. Nothing in the store matches that." For Elena, that means being told the store has no chairs while 48 sit in Indianapolis: a lost sale, delivered with confidence.
- **Fix 1 (safety net):** a grounding check. When a query returns nothing, every exact value it searched for is checked against the real database. Invented values trigger a retry with hints, then a hand-off. "Pink" (nothing like it exists) is still allowed as an honest "No".
- **Replay of the six real queries through the check:** 4 of 6 became hand-offs (Q12, Q13, Q15, Q16). Q11 and Q14 still slip through: every value was real, only the TABLE was wrong.
- **Design consequence:** for a complex question, "nothing matches" must never be the end of the conversation (see E22).

### E20. Split the job: the AI fills in a form, code builds the SQL

- New hybrid station: an extractor fills in a form (`quantity`, `color`, `max_unit_price`, `destination_city`...), every value is grounded against the real vocabulary, then tested code builds parameterised SQL from a template.
- The form is the contract's `constraints` field: the design already had a place for it.
- **Rules-based form filler on the hard set: 6 / 6 right, 0 wrong, 12 ms.**

### E21. Overfitting: 6 / 6 on known questions, 5 / 7 on new ones

- The rules were written after seeing the six hard questions. On 7 new phrasings written afterwards (rules unchanged), they scored 5 / 7.
- Q30 "How much for 25 grey AeroTask chairs?": no "total" or "cost" word, so it was treated as a product search.
- Q35 "forty navy mesh chairs": numbers written as words are invisible to the rules. The quantity silently became 1 and three chairs were returned, including one with only 25 in stock.
- **Lesson:** a score on questions you designed for is not a score. Keep a "fresh" set you never tune against.
- **Design consequence:** a missing number should never be silently assumed. If the form has no quantity for a bulk-sounding request, ask.

### E22. "Nothing matches" can offer the nearest way out

- When no product passes every rule, the station now tries removing one rule at a time and reports the first that would give results, e.g. "Nothing matches all of those rules right now. Without the delivery-time limit, 1 option would match."
- **Design consequence:** the no-results state becomes guided recovery, a chip such as "Show options that arrive in 4 days", instead of a dead end.

### E23. Conversation memory = carrying the form forward

- "Same chairs, but within 2 days" (Q14) and "Same thing but leather only" (Q34) are answered by starting from the previous question's form and changing one field.
- Both pass with the rules extractor. Memory needed no new idea, only the `constraints` field that was already in the contract.

## Run 7 — Hard set, the AI fills the FORM (qwen2.5-coder:3b), on Dex's PC

| Method | Right | Hand-off | Wrong | Median time |
| --- | --- | --- | --- | --- |
| AI writes the whole SQL | 0 / 6 | 0 | 6 | 16,585 ms |
| Rules fill the form (no AI) | 6 / 6 | 0 | 0 | 12 ms |
| **AI fills the form** | **5 / 6** | 0 | 1 | 14,301 ms |
| AI fills the form + rules fill gaps (replay of the run's real forms) | 6 / 6 | 0 | 0 | not timed (replay) |

Model load (warm-up) took 52.9 s.

### E24. Same model, easier job: 0 / 6 became 5 / 6

- The model, the questions and the database were identical. Only the job changed: from writing SQL to filling in a form with allowed values.
- **Lesson:** before reaching for a bigger model, make the model's job smaller.

### E25. "Right for the wrong reason"

- Q11 asked for NAVY chairs. The model left the colour out of the form, the engine picked the first colour alphabetically (Black), and the total was still correct because every colour costs $320. The marking script said RIGHT. The receipt pointed at the wrong chair.
- **Fix (marking):** questions can now name an `expected_sku`; the receipts must include it.
- **Fix (engine):** with no colour given, the engine never silently picks one. Same price for every colour: it says "any colour: Black, Grey, Navy, same price" and cites every colour. Different prices: it asks "Which colour?" with chips.
- **Design consequence:** the audit drawer is only as honest as the row the engine chose to cite.

### E26. The AI forgets things the rules never forget

- Q16 says "don't mind which warehouses". The model left `single_depot` empty; the engine assumed one warehouse, and two qualifying chairs disappeared.
- The rules caught that phrase every time. They miss unusual phrasing ("forty", "how much for") but never forget a pattern they know.
- **Fix:** the AI fills the form first; the rules fill any box the AI left empty. Replaying the run's real forms through this merge: 6 / 6.
- Same lesson as hybrid search (E11): two methods with different blind spots beat either one.

### E27. Assumptions must be visible

- When the question doesn't say whether units may come from several warehouses, the engine assumes one (the stricter rule) and now says what it would change: "Found 2 products that pass every rule. 1 more qualifies if the units can come from several warehouses."
- **Design consequence:** a candidate chip, "Allow several warehouses", that re-runs the search with one rule changed.

## Run 8 — Fresh set (7 phrasings nobody tuned for), on Dex's PC

| Method | Right | Wrong | Median time |
| --- | --- | --- | --- |
| Rules fill the form (no AI) | 5 / 7 | 2 | 21 ms |
| **AI fills the form (qwen2.5-coder:3b)** | **7 / 7** | 0 | 16,944 ms |
| AI + rules fill gaps (replay of the run's real forms) | 7 / 7 | 0 | not timed (replay) |

### E28. On new phrasings, the AI beat the rules

- The AI read "forty" as 40 and understood "How much for 25 grey AeroTask chairs?" as a total: the two questions the rules got wrong.
- Every answer was right for the right reason: re-graded with `expected_sku`, the receipts point at the correct products.
- The AI also correctly left boxes EMPTY: Q33 names no material, so no material rule was added and the leather chair was correctly included.
- **Overall picture:** rules are fast and never forget a pattern; the AI handles phrasing nobody anticipated. Team-up results across both sets: hard 6 / 6 and fresh 7 / 7 (both from replays of real forms; to confirm with a live run).

### E29. Speed is now the biggest gap: about 17 s against a 1.2 s budget

- Accuracy problems are largely solved for Task A. Every second of the wait is the model filling in the form; the database adds milliseconds.
- **Next run measures where the seconds go:** the eval now records how many tokens the model READS (the prompt) and WRITES (the form), and how long each takes.

## Run 9 — AI + rules team-up, live, fresh set, with the stopwatch

| Method | Right | Wrong | Median time |
| --- | --- | --- | --- |
| AI + rules fill gaps (`hybrid-both`), live | **7 / 7** | 0 | 14,834 ms |

Where the model's time went (average of 7 calls):

| Step | Tokens | Time | Speed |
| --- | --- | --- | --- |
| Reading the prompt | 937 | 1.8 s | 518 tokens/s |
| Writing the form | 85 | 10.9 s | 8 tokens/s |

### E30. Writing is slow, reading is fast: make the model write less

- On a CPU, this model reads about 65 times faster than it writes. Writing took three-quarters of the wait.
- About two-thirds of each form was empty boxes (`"material": null`), written token by token for nothing.
- **Fix:** the model now writes only the boxes it fills in; missing boxes count as empty. An example form shrank from 265 to 92 characters.
- **Prediction to check in the next run:** writing time falls roughly in proportion to the tokens written.
- **Design-engineering lesson:** measure first. Shortening the prompt (the obvious guess) would have saved at most 1.8 s; shortening the output targets the 10.9 s.

## Run 10 — Same team-up, form with only the filled boxes

| | Tokens written | Writing time | Median total | Right |
| --- | --- | --- | --- | --- |
| Before (every box, nulls included) | 85 | 10.9 s | 14.8 s | 7 / 7 |
| **After (filled boxes only)** | **50** | **5.8 s** | **11.0 s** | **7 / 7** |

### E31. The prediction held: less writing, proportionally less waiting

- 41% fewer tokens written, 47% less writing time, accuracy unchanged.
- Short forms are fast and long forms are slow: Q31 (3 boxes) took 4.9 s, Q35 (9 boxes) 12.0 s.
- **Design consequence:** the wait grows with how detailed the request is. The loading state should expect 5 to 12 s for detailed requests on this hardware.

## Run 11 — The whole pipeline (router + every station), no AI

| Score | Result |
| --- | --- |
| Router, questions it was written for | 35 / 35 |
| **Router, 8 fresh questions written afterwards** | **4 / 8** |
| Answers | 26 / 35 right, 5 hand-offs, 4 wrong |
| Median time | 10 ms |

### E32. The router overfitted too, and every miss landed in the default bucket

| Fresh question | Should go | Went |
| --- | --- | --- |
| "Can someone call me back about a damaged chair?" | handoff | search |
| "What's the priciest chair you sell?" | sql | search |
| "I'd like to buy eight standing desks" | hybrid | search |
| "This is ridiculous, nobody answers my emails" | handoff | search |

- When no rule matches, the router falls through to "search". All four misses landed there.
- **The two handoff misses are the worst kind of error:** an upset customer would be shown a product list instead of a person.

### E33. Rules first, AI only for the leftovers

- In the `ai` preset, the rules still decide everything they recognise (microseconds). Only questions that fall through to the default are sent to the AI, which answers with ONE word out of four.
- Writing one word is the cheapest job a model can do (E30), so the tie-breaker costs little and only when needed.
- Any label the AI invents outside the four is rejected; the rules' choice stands.
- **Design consequence:** most questions stay fast; only unusual ones pay for AI.

### E34. "Did you mean...?" now has a concrete trigger

- If the distinctive words of a question appear in the names of several products from DIFFERENT categories, the engine asks instead of guessing. "Show me the navy shell" matches a shell office chair, a shell guest chair and a shell jacket, so three chips appear.
- **Caution:** this rule was written knowing that question. It needs fresh ambiguous questions before it can be trusted.

### E35. Where the no-AI pipeline goes wrong

- 4 wrong: two keyword-search misses ("charge my laptop", "feet up under the desk") and two form-filling misses ("how much for", "forty").
- Each was fixed by AI in the station tests (search hybrid 10 / 10; AI + rules form 7 / 7), so the `ai` preset should recover them. To confirm with a live run.

## Run 12 — The whole pipeline with AI (`ai` preset), on Dex's PC

| Score | No AI (Run 11) | **With AI** |
| --- | --- | --- |
| Router, fresh questions | 4 / 8 | **8 / 8** |
| Answers right | 26 / 35 | **33 / 35** |
| Wrong (danger) | 4 | 2 |
| Median time | 10 ms | 7,028 ms |

| Station | Right | Median time |
| --- | --- | --- |
| search | 10 / 10 | 6,180 ms |
| sql | 10 / 11 | 7,866 ms |
| hybrid | 12 / 13 | 10,922 ms |
| handoff | 1 / 1 | 0 ms |

### E36. The AI tie-breaker fixed every router miss

- All four fresh questions that fell through the rules were placed correctly by the one-word AI tie-breaker, including both upset customers ("This is ridiculous...", "call me back about a damaged chair").
- Questions the rules recognised never called the AI, so the 1-in-35 safety handoff still took 0 ms.

### E37. A gap in the safety net: a column the grounding check didn't cover

- Q06 ("How many grey AeroTask chairs are left?") was answered "No". The model wrote `p.family = 'AeroTask Pro Mesh'`, but `family` holds codes like 'AT'. The grounding check only covered a hand-picked list of columns, and `family` wasn't on it.
- **Fix:** the check now covers EVERY text column in the database automatically, with names and codes (family, sku, order_id...) treated as strict.
- **Side effect, accepted:** "status of order NX-99999" (an order that doesn't exist) now goes to a person instead of "No such order". For an order the system can't find, a person is the right answer.
- The same model answered Q06 correctly in Run 2. Temperature 0 makes answers very repeatable, not perfectly identical: small differences (for example, what was cached from earlier prompts) can flip a borderline answer. **Lesson:** one run is evidence, not proof. Important numbers should be measured more than once.

### E38. My speed fix broke conversation memory (a regression)

- Q14 ("Same chairs, but they must arrive in Chicago within 2 days") lost Q13's quantity and budget, so the $365 trap chair got through.
- Cause: after "write only the filled boxes" (E30), the AI stopped writing `"follow_up": true`, and the team-up code ignored the rules' follow-up signal. The old form was never merged.
- **Fix:** follow-ups are detected by the AI's flag OR plain words ("same", "those", "but"...). Replay of the AI's real Q14 form: RIGHT.
- **Lesson:** a change that improves one number (speed) can quietly break another (memory). This is why the whole eval runs after every change: a REGRESSION test.

### E39. Self-repair worked, at double the cost, and with a caveat

- Q05 ("Are black AeroTask chairs in stock in Columbus?") needed 2 tries: the first query was rejected, the model saw the error and fixed it. Result: RIGHT ("available: 0"), but it took 20.9 s, the slowest question in the run.
- **Caveat:** the repaired query filtered on `category = 'Office chairs' AND color = 'Black'` and left out the product name. It was right because no other black office chair happens to be in Columbus. Another day, with different stock, the same query would be wrong.
- **Design consequence:** retries are a safety feature, but they double the wait. The loading state should be able to say "Double-checking…".
- **Eval consequence:** the SQL station's receipts don't name the product, so `expected_sku` can't catch this yet. A future fix: make SQL answers include the sku.

## Run 13 — Step 5: API, recorded answers, connected prototype

| Check | Result |
| --- | --- |
| API automated tests (`test_api.py`) | 15 / 15 pass |
| Demo answers recorded (rules-only preset) | 12 real tickets in `prototype/answers.json` |
| Prototype, recorded mode, clicked through in a real browser | cards, receipts drawer, follow-up, "Did you mean...?", totals, unknown questions: all work |
| Prototype, live mode against a stand-in API | answers shown; the follow-up sent the previous form |

### E40. Memory without a memory

- The API is stateless: it remembers nothing between requests. For "Same chairs, but within 2 days", the browser sends back the previous ticket's form (`constraints`) with the new question.
- Test: the same follow-up WITHOUT the form does not invent old rules (passes).
- **Design consequence:** conversation memory lives in the screen, in the ticket the screen already holds. A page refresh forgets the conversation unless the screen saves it.

### E41. SQL answers come out as raw facts

- The SQL station returns messages like "available: 48". Correct, but not a sentence a shopper expects.
- **For now:** the widget tidies it ("Available: 48") and shows the result as a small fact table with its receipt.
- **Later:** a writing step that turns facts into a sentence, with the same rule as the contract: no number may appear that isn't in a cited field.

### E42. The first table design hid the answer

- The fact table showed only the first four columns. For a total-cost answer, the fifth column was the total itself.
- **Fix:** drop the code column (sku) when a readable name exists, and keep the LAST four columns, where the answer usually is.
- **Lesson:** a generic layout rule should be checked against the data it will show, not only against a sketch.

### E43. A recording is evidence of the engine you ran

- The first recording used the rules-only preset, so "Something to charge my laptop" shows "nothing matches" (the keyword-search blind spot from E9). The widget's status line says which preset and model produced the answers.
- **For the published demo:** record with the `ai` preset, so the demo shows the engine at its best and still says honestly what produced it.

## Run 14 — Demo recorded with AI (`record_demo.py ai`, qwen2.5-coder:3b), 2026-11-18

All 12 recorded answers are correct. "Something to charge my laptop" now finds the charging cable (the rules-only recording found nothing).

| Answer type | Total time |
| --- | --- |
| Hybrid (Elena's questions, follow-up, total) | 11.6 to 20.4 s |
| SQL lookup | 17.0 s |
| Search (descriptions) | 21.5 to 40.4 s for the first ones; 5.7 to 7.3 s once warm |
| Hand-off | 1 ms |

### E44. A setting that lives in one window caused a 3-minute hang

- `$env:OLLAMA_MODEL` only lasts for one PowerShell window. In a new window the code fell back to its default (the bigger 7b model), which was too slow to load: the warm-up timed out after 180 s with a long, unhelpful traceback.
- **Fixes:** the default is now the 3b model (the one that measured best); every script prints which model it uses before warming up; a timeout now explains the three usual causes in plain words.
- **Lesson:** an error message is part of the design. "TimeoutError: timed out" sent the user to ask for help; a sentence naming the model would have solved it in seconds.

### E45. "Rules first, AI for the leftovers" means every search pays for AI

- Descriptions ("A breathable chair...") match no rule, so they always fall into the router's default bucket, and the AI tie-breaker runs every time, before the search even starts.
- The first search also loaded the embedding model, which the warm-up didn't cover: 40 s for "Show me the navy shell".
- **Ideas to test:** warm up the embedding model too; run the tie-breaker and the search at the same time and keep the search result unless the tie-breaker says "handoff"; skip the tie-breaker when the question has no complaint or problem words.
- **Slower than Thursday:** the same hybrid questions took 18 to 20 s instead of about 11 s. Same model and code, so the PC's state (just restarted, other apps, memory) matters. Another reason to measure more than once.

## Run 15 — Review fixes R4–R6 in the engine, 2026-11-19

| Check | Result |
| --- | --- |
| API tests (`test_api.py`) | **23 / 23** pass (15 old + 8 new) |
| Whole pipeline, no AI (regression) | unchanged: router 35 / 35 and 4 / 8 fresh, answers 26 / 35, contract 35 / 35 valid |
| Demo recording (rules only, test run) | 37 answers, including every one-tap removal, each in 6–10 ms |

### E46. Three review findings needed the contract to grow, not the screen

- **R4, visible memory:** `POST /ask` takes `drop` (one requirement to remove). The previous form minus that box goes straight to the hybrid station. No AI re-reads anything, so it takes milliseconds and can't mishear.
- **R5, ways out:** "nothing matches" tickets carry `relax`: each single requirement whose removal gives results (`field`, `label`, `matches`). The screen turns each into a button that sends `drop`.
- **R6, say what the number is about:** SQL tickets carry `subject`, read from the query's own exact filters and checked against the database, the same check as grounding. "available: 48" becomes "48 navy AeroTask Pro Mesh available at Indianapolis Regional" without the AI writing a word of it. When product and colour name exactly one SKU, `subject.sku` is filled, which starts to close E39's gap.
- **Shopper words (R8):** "pass every rule" became "match everything you asked for".
- **Lesson:** a sentence is a dead end for a screen. A hint written as words can only be read; the same hint as data can become a button.

### E47. The AI re-recording: same answers, half the wait

- Re-recorded with `qwen2.5-coder:3b` on 19 Nov: all 12 answers correct again, and the recorded lookup came back with a full `subject` (product, colour, warehouse, SKU), from SQL the AI wrote.
- Questions took **5.0 to 10.8 s**, against 11.6 to 40.4 s on 18 Nov. Same model and same code for the AI steps. The 25 one-tap removals took 1 to 4 ms each.
- **Lesson:** the PC's state still moves the numbers by 2× or more (see E45). Speed claims need several runs, on the same day and on different days.
