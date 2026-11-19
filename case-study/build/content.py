"""The words and pictures of the CartesianRAG case study, page by page (source: case study v4)."""


def build(g):
    sec, fig, grid, card, stat, table, page, sub_hero, PILLS, DEMO, REPO = (
        g["sec"], g["fig"], g["grid"], g["card"], g["stat"], g["table"], g["page"], g["sub_hero"], g["PILLS"], g["DEMO"], g["REPO_FILE"])
    m, r, s, a = PILLS["m"], PILLS["r"], PILLS["s"], PILLS["a"]

    FACTS = [("Designer", "Dex"), ("Product", "Tabular RAG assistant · B2B e‑commerce"),
             ("Surfaces", "Storefront widget · Ops console"), ("Scope", "Research → Engine → Hi‑fi UI")]

    import home
    home.build_home(g)

    # ======================================================================= 01 RESEARCH
    rs = sub_hero("A1", "Research &amp; Discovery", "The users, pain points and constraints below are design‑time hypotheses, not findings from interviews I ran. Where the engine later tested a hypothesis, its result sits beside it.")
    rs += sec("", "Pain points", "Four hypotheses, and what the engine showed.", table(["Pain point " + a, "What the build showed " + m], [
        ["<b>Confident wrong answers on price and stock.</b> Text‑only RAG doesn’t query live tables.", "Real, and worse than expected. When an AI wrote whole SQL queries for multi‑rule questions, all 6 came back as a confident “No, nothing matches” while 48 chairs sat in a warehouse (E19)."],
        ["<b>Vocabulary mismatch in search.</b> Shoppers and catalogs use different words.", "Reproduced. Keyword search missed “something to charge my laptop” (the product says <i>charging cable</i>). Meaning search found it (E9, E11)."],
        ["<b>Swivel‑chair work for support agents.</b> Facts live in separate tools.", "Not tested. Marcus’s console is still a hand‑built prototype, not connected to the engine."],
        ["<b>Black‑box trust barrier.</b> Answers come without sources.", "Built into the contract: every card and lookup carries a receipt to its database row. Not yet tested with people."]]))
    rs += sec("", "Data freshness", "Fast data is read live. Slow data can be indexed.", grid([
        card("Fast · seconds", "Stock and orders", "Always read from the tables at question time, joined by SKU, so a search hit is never served with a stale stock number."),
        card("Medium · hours", "Prices and delivery schedules", "Also read at question time; delivery days come from a per‑warehouse, per‑city table."),
        card("Slow · months", "Specs and policies", "The only text that is pre‑indexed for keyword and meaning search.")], 240))
    rs += sec("", "Trust", "A receipt proves where a number came from. Not that it’s right.", f'''
<div class="body"><p>Three rules carried through from the first wireframes and are now enforced by the answer contract: every number has a receipt, the receipt opens in a drawer with the row and the query, and calculations show their working.</p>
<p>The build added a fourth rule nobody had planned. A rules‑only engine answered “What would 40 chairs cost?” with <b>$320</b>, the price of one chair, and attached a perfectly real citation. Correctness has to be checked separately, against an answer key.</p></div>
<div class="ba"><span class="before">“available: 48”</span><span class="arrow" aria-hidden="true">→</span><span class="after">48 navy AeroTask Pro Mesh available at Indianapolis Regional</span><span class="mono note">Match between system and the real world (Nielsen #2), built from the query’s own checked filters</span></div>
''')
    page("research.html", "Research — CartesianRAG Case Study", "Research and discovery for CartesianRAG: four pain-point hypotheses and what the working engine showed about each.", rs)

    # ======================================================================= 02 IA
    ia = sub_hero("A2", "Information Architecture", "CartesianRAG bridges loose natural‑language questions and strict, many‑column tables. The IA decides how answers are organised, labelled and reached before any screen is drawn.")
    ia += sec("", "Sitemap", "One platform, two surfaces, one source of truth.", f'''
<div class="body"><p>Think of a school building. The platform is the building. People walk into two classrooms: the <b>Storefront</b> for shoppers and the <b>Operations Console</b> for agents. Behind both sits the library, the data and governance layer, which every answer must cite.</p></div>
{fig("ia-sitemap", "Sitemap: one platform with Storefront and Operations Console and a shared Data and Governance layer", "Fig. 01 — Sitemap", "", 2000, 1650)}
''')
    ia += sec("", "Four systems", "Organised by how fast the data changes.", f'''
{grid([card("A", "Organization", "Catalog (slow), operations (fast) and governance (policies)."),
       card("B", "Labeling", "Database words become shopper words: <code>low_stock</code> becomes “Low stock · 6 left”."),
       card("C", "Navigation", "Assistant dock → widget → inline cards → receipt drawer. The console uses three panes."),
       card("D", "Search", "Natural language in; “Did you mean…?” chips when a question matches several products.")], 220)}
{fig("ia-four-systems", "The four IA systems: organization by data velocity, labeling map, navigation paths and search layers", "Fig. 02 — The four IA systems", "", 2000, 1389)}
''')
    ia += sec("", "Wireflows", "Two journeys that hand off to each other.", fig("wireflows", "Wireflows for the shopper and operations journeys, with dashed hand-offs between the two surfaces", "Fig. 03 — Wireflows", "Blue dashed arrows cross between surfaces", 2000, 1317))
    ia += sec("", "Wireframes", "Greyscale on purpose, so feedback stays on structure and words.", f'''
<div class="pair">
{fig("s1-storefront-widget", "S1 wireframe: storefront with the assistant open and two product row cards", "S1 — Storefront and assistant", "", 2000, 1562)}
{fig("s2-audit-drawer", "S2 wireframe: source audit drawer with the inventory row and the executed SQL", "S2 — Source audit drawer", "", 2000, 1406)}
{fig("s3-ops-console", "S3 wireframe: three-pane operations console with ticket queue, conversation and co-pilot", "S3 — Operations console", "", 2000, 1333)}
{fig("s4-mobile-assistant", "S4 wireframe: phone-sized assistant with a spec comparison table", "S4 — Mobile assistant", "", 780, 1688, cls="phone")}
</div>
{fig("component-states", "The assistant widget in five states: empty, streaming, disambiguation, locked with tracking, and human hand-off", "Fig. 04 — Component states, as first designed", "The engine changed three of them", 2000, 1024)}
''')
    page("ia.html", "Information Architecture — CartesianRAG Case Study", "Information architecture for CartesianRAG: sitemap, the four IA systems, wireflows and low-fidelity wireframes.", ia)

    # ======================================================================= 03 ENGINE
    stories = [
        ("The wait is a screen, not a flicker", "A 1.2 s budget, covered by skeleton cards.", "Answers take 5–40 s. Over 99.9% of that is the AI writing; the database takes milliseconds. The model reads 518 tokens/s but writes 8 (E1, E30).", "A waiting card with the real steps, a timer and an honest range. Writing only the boxes the AI fills cut writing time by 47%."),
        ("A confident “No” is the most expensive failure", "The main risk is a wrong number.", "The worst failure was a wrong absence: invented product names made all six of Elena’s questions come back “nothing matches” (E18, E19).", "A grounding check turns invented values into a hand‑off, and “nothing matches” always offers a way out (E22)."),
        ("Make the AI’s job smaller before making it bigger", "A bigger model would be needed.", "Same model, same questions. Writing whole SQL scored 0/6; filling a form of allowed values scored 5/6. AI + rules scored 6/6 and 7/7 (E24, E26).", "The form became the contract’s <code>constraints</code> field, and the screen shows it as chips."),
        ("Overfitting, twice", "Good scores on the questions I tuned for.", "Rules scored 6/6 on known questions and 5/7 on fresh ones. The router scored 35/35, then 4/8 fresh, sending two upset customers to a product list (E21, E32).", "Rules first, a one‑word AI tie‑breaker for the leftovers: 8/8 fresh (E33, E36)."),
        ("Memory without a memory", "Follow‑ups need server‑side sessions.", "“Same chairs, but within 2 days” works by sending the previous form back. A speed fix once silently broke it; the regression run caught it (E23, E38, E40).", "Requirements shown as removable chips, so a lost requirement is visible at a glance (R4)."),
        ("Right for the wrong reason", "A correct total means a correct answer.", "Elena asked for navy. The AI left colour out, the engine picked black, and the total was still right. The receipt pointed at the wrong chair (E25).", "No silent picks: “any colour, same price” with every colour cited, or “Which colour?”."),
        ("Ambiguity needs a rule, not a feeling", "Ask when unsure.", "“Navy shell” matched a chair, a guest chair and a jacket within 3% of each other (E15).", "Ask when the top matches come from different categories: “Did you mean…?” chips with category and price (E34)."),
        ("The contract grew because of testing", "The contract is finished.", "<code>table</code> was added to mark answers, <code>trace</code> to debug empty ones (E4).", "“Can we debug it?” and “can we mark it?” are design requirements too."),
        ("A sentence is a dead end for a screen", "Three review fixes are screen work.", "The screen couldn’t make a hint tappable or say what “available: 48” was about, because the engine only sent sentences (E46).", "The contract now sends <code>relax</code>, <code>drop</code> and <code>subject</code> as data. Removals answer in 1–4 ms with no AI."),
    ]
    st = "".join(f'''<div class="story"><span class="mono">{i:02d}</span><div><h3 class="h">{t}</h3><div class="flow">
<div><span class="mono">Expected</span>{e}</div><div><span class="mono">The engine showed</span>{sh}</div><div><span class="mono">Design change</span>{c}</div></div></div></div>'''
                 for i, (t, e, sh, c) in enumerate(stories, 1))
    en = sub_hero("A3", "Design ↔ Engine", "I built the engine behind the design and measured it. Each story here has the same shape: what I expected, what the engine showed, and what changed in the design.",
                  [("Model", "qwen2.5-coder:3b via Ollama"), ("Hardware", "Home PC, no graphics card"), ("Answer key", "43 questions, proven against the database"), ("Findings log", f'<a class="link" href="{REPO}engine/FINDINGS.md">E1–E47</a>')])
    en += sec("", "Built vs designed", "The smallest stack that could test the same ideas.", f'''
<pre class="diagram" aria-label="Diagram: the router sends each question to one of four stations; every answer passes a grounding check and becomes a ticket">
 Shopper's question
        │
        ▼
 ┌──────────────┐   rules match?  yes ─────────────┐
 │   ROUTER     │── no ──► AI picks ONE word ──────┤
 └──────────────┘                                  ▼
   ┌────────────┬─────────────┬───────────────┬──────────────┐
   │  HAND-OFF  │    SQL      │    HYBRID     │    SEARCH    │
   │  0–1 ms    │ AI writes a │ AI fills a    │ keyword +    │
   │            │ SELECT,     │ form, code    │ meaning,     │
   │            │ guard checks│ builds SQL    │ fused (RRF)  │
   └─────┬──────┴──────┬──────┴───────┬───────┴──────┬───────┘
         └─────────────┴──────┬───────┴──────────────┘
                              ▼
        grounding check: does every searched value exist?
                              ▼
        TICKET: message · cards · rows · receipts · constraints · trace
</pre>
{table(["Part", "Designed", "Built and measured"], [
        ["Database", "PostgreSQL, Redis, DuckDB", "SQLite, opened read‑only; 6 tables built by a script"],
        ["Router", "Intent classifier", "Rules first; one‑word AI tie‑breaker for leftovers"],
        ["Multi‑rule questions", "Sandboxed Python agent", "AI fills a form of requirements; tested code builds parameterised SQL"],
        ["Search", "Dense + BM25 + reranker", "BM25 + <code>nomic-embed-text</code>, fused with Reciprocal Rank Fusion"],
        ["Latency budget", "1,200 ms", "Median 7 s; 5–40 s by question and day"]])}
''')
    en += sec("", "Where the time goes", "Watch a real wait, replayed.", sid="where-the-time-goes", body=f'''
<div class="body"><p>Pick a recorded question. The card replays the engine’s real step timings at 4× speed, the same way the prototype’s waiting state does. The bar shows how the time splits between the <b>AI</b> and the <b>database or search</b>.</p></div>
<div class="demo-box" id="wait-demo" hidden>
<div class="seg" role="group" aria-label="Recorded question"></div>
<div class="wait" role="status" aria-live="polite"></div>
<div class="bar-track" role="img"></div>
<div class="legend"><span><i class="bar-ai"></i>AI model writing</span><span><i class="bar-db"></i>Database and search</span><span><button type="button" data-replay class="link" style="background:none;border:0;border-bottom:1px solid currentColor;padding:0;cursor:pointer">Replay</button></span></div>
</div>
{table(["Recorded question (19 Nov)", "AI", "Database / search", "Total"], [
        ["Elena: 40 navy mesh chairs…", "8.94 s", "3.2 ms", "8.97 s"],
        ["How many navy AeroTask chairs in Indianapolis?", "6.71 s", "1.1 ms", "6.74 s"],
        ["Show me the navy shell", "7.88 s", "2.97 s", "10.85 s"],
        ["Remove one requirement (any)", "none", "1–4 ms", "1–4 ms"]], (1, 2, 3))}
''')
    en += sec("", "Scoreboard", "Measured, with the misses left in.", table(["Run", "What was measured", "Result"], [
        ["1–2", "SQL station, 11 lookups", "<b>11/11</b> right · median 7.8 s"],
        ["5", "Search, 10 descriptive questions (hit in top 5)", "Keyword 8/10 · Meaning <b>10/10</b> · Hybrid <b>10/10</b>"],
        ["6", "Multi‑rule questions, AI writes whole SQL", "<b>0/6</b>, 6 wrong"],
        ["7", "Same questions, AI fills a form", "<b>5/6</b>; with rules filling gaps <b>6/6</b>"],
        ["11", "Whole pipeline, rules only", "Router fresh 4/8 · answers 26/35, 4 wrong · 8–10 ms"],
        ["12", "<b>Whole pipeline with AI</b>", "<b>Router fresh 8/8 · answers 33/35, 2 wrong · median 7.0 s</b>"],
        ["15", "Review fixes in the engine; demo re‑recorded", "API tests <b>23/23</b> · 12/12 recorded answers correct"]]))
    en += sec("", "Nine stories", "What I expected, what happened, what changed.", f'<div class="stories">{st}</div>')
    page("engine.html", "Design ↔ Engine — CartesianRAG Case Study", "What building and measuring the CartesianRAG engine changed in the design: nine stories, a scoreboard and a replay of real wait times.", en, ("wait-replay.js",))

    # ======================================================================= 04 EVALUATION
    review = [
        ("R1", "Engine-built cards had no quantity or Reserve, so Task A couldn't be finished", 3, "Stepper + “Hold 40 chairs for 15 min”, pre‑filled from the request"),
        ("R2", "On a phone, the test bar covered the assistant's close button", 3, "Assistant starts below the bar's measured height"),
        ("R3", "The waiting state didn't match the real 6–40 s wait", 3, "Real steps, timer, honest range; demo replays real timings at 4×"),
        ("R4", "Follow‑up requirements carried forward invisibly", 2, "Removable requirement chips; engine takes <code>drop</code>"),
        ("R5", "“1 option would match” hint wasn't tappable", 2, "One button per way out; engine sends <code>relax</code>"),
        ("R6", "“Available: 48” didn't say 48 of what, where", 2, "Big number + sentence; engine sends <code>subject</code>"),
        ("R7", "Colour chips looked tappable but did nothing", 2, "Plain text: “Also in Grey, Navy”"),
        ("R8", "Engine words on the shopper's screen", 2, "Shopper words; table and model names moved to Engine details"),
        ("R9", "Hand‑off message shown twice", 1, "Shown once"),
        ("R10", "Engine panel under every answer", 1, "One “Engine details” switch"),
        ("R11", "Suggestions cut off with “…”", 1, "Full text, wrapping; one on phones"),
        ("R12", "“Live inventory” claim in recorded mode", 1, "“Real answers, recorded 19 Nov 2026, replayed for this demo”"),
    ]
    rv = table(["#", "Problem", "Severity", "Fix", "Status"],
               [[i, p, f'<span class="sev s{sv}">{sv}</span>', fx, '<span class="fixed">Fixed</span>'] for i, p, sv, fx in review])
    ev = sub_hero("A4", "Evaluation", "Three kinds of evidence, each labelled: a simulated usability round, an expert review against Nielsen’s heuristics, and the engine’s own measurements. Sessions with real people are still to come.")
    ev += sec("", "Simulated round", "Ten synthetic participants, findings kept as hypotheses.", f'''
<div class="tags" style="margin-top:20px">{s}</div>
<div class="body" style="margin-top:20px"><p>Five synthetic shoppers and five synthetic support agents were walked through the first prototype, using the personas and known interaction patterns. No real people took part. Their predicted times and scores were dropped; the findings were kept as hypotheses, and several were later confirmed by the expert review.</p></div>
{table(["#", "Predicted problem", "Status"], [
        ["F1", "Shoppers don’t see the citation badge as clickable", '<span class="fixed">Fixed</span> — “✓ Verified · see source”'],
        ["F2", "“Reserve stock &amp; create PO” sounds like a charge", '<span class="fixed">Fixed</span> — “Hold 40 chairs for 15 min” + “No charge until your purchase order is approved”'],
        ["F3", "Agents can send a promise without the action", "Open (console not connected yet)"],
        ["F4", "Recommendations don’t explain why", "Open"],
        ["F6", "The 15‑minute countdown causes anxiety", '<span class="fixed">Fixed</span> — says what happens at zero']])}
''')
    ev += sec("", "Expert review", "Twelve findings against Nielsen’s heuristics. All fixed.", f'''
<div class="tags" style="margin-top:20px">{r}</div>
{grid([stat("3", "Major (fix before testing)"), stat("5", "Minor (fix soon)"), stat("4", "Cosmetic"), stat("0", "About wrong data")], 180)}
{rv}
<div class="body" style="margin-top:24px"><p><b>Limit:</b> Nielsen recommends 3 to 5 reviewers. This review had one, an AI assistant. It finds likely problems; it doesn’t replace watching people.</p></div>
''')
    ev += sec("", "Before and after", "Three major problems, fixed and checked in a browser.", f'''
<div class="pair">
{fig("review-r2-phone-before", "Before: on a phone the black test bar covers the assistant's title and close button", "R2 before — header covered", "", 390, 844, cls="phone")}
{fig("review-r2-phone-after", "After: on a phone the assistant's header and close button sit below the test bar", "R2 after — header clear", "iPhone 13 · bar ends 79 px, header starts 81 px", 1170, 1992, cls="phone")}
</div>
{fig("review-r1-hold", "Engine-built product card showing Held: 40 AeroTask Pro Mesh chairs with a 15-minute countdown and a purchase order number", "R1 — Task A can be finished again", "Before the hi‑fi restyle", 1280, 860)}
''')
    ev += sec("", "Not yet tested", "What these pages can’t claim.", grid([
        card("People", "No real participants", "Next: 2–3 informal Task A sessions, one on a phone, logged against the review findings."),
        card("Console", "Marcus’s half", "The operations console is still hand‑built, not connected to the engine."),
        card("Speed", "One PC, a few days", "The same questions ran 2× faster on one day than the day before. Speed claims need more runs.")], 240))
    page("evaluation.html", "Evaluation — CartesianRAG Case Study", "How CartesianRAG was evaluated: a labelled simulated round, an expert review against Nielsen's heuristics with all 12 findings fixed, and what is not yet tested.", ev)

    # ======================================================================= 05 SYSTEM
    def sw(name, hexv, fg, role, min_=4.5, text=None):
        return f'''<div class="sw" data-fg="{fg}" data-bg="{hexv}" data-min="{min_}"><div class="chip" style="background:{hexv};color:{fg}">{text or name}</div>
<div class="meta"><b>{name}</b><code>{hexv}</code><span>{role}</span><span class="cr" aria-live="off">{fg} on {hexv}</span></div></div>'''
    sy = sub_hero("A5", "Design System", "Built after the expert review, so the remaining fixes would follow one set of rules instead of each inventing its own. The palette brings the outdoors indoors; the rules keep it honest.",
                  [("Themes", "Daylight · Campfire night"), ("Tokens", "27 colours · 9 text styles"), ("Components", "16, mapped to the contract"), ("Files", f'<a class="link" href="{REPO}design-system/README.md">design-system/</a>')])
    sy += sec("", "Colour", "Every colour earns its contrast ratio.", f'''
<div class="body"><p>Each swatch shows a text colour on its fill. The ratio under it is calculated by your browser from the two hex values.</p></div>
<div class="swatches">
{sw("Forest", "#2f6b3b", "#ffffff", "Primary: main buttons, links, selected states")}
{sw("Lantern", "#f2c14e", "#2b2118", "Secondary: a fill, never text. Highlights and ways out")}
{sw("Campfire", "#c8452b", "#ffffff", "Rare accent: promo tags only. Never errors or stock")}
{sw("Bark", "#2b2118", "#faf6ef", "Text; the facilitator bar")}
{sw("Canvas", "#faf6ef", "#6a5847", "Page; muted text sits on it", text="Trail text")}
</div>
<h3 class="sub">Status colours: a separate set</h3>
<div class="swatches">
{sw("In stock · Lake", "#ddeef4", "#1d6782", "Solid dot + word", text="In stock")}
{sw("Low stock · Amber", "#f7ead0", "#8a5a00", "Outlined ring + word", text="Low stock")}
{sw("Out of stock · Crimson", "#f6dfe3", "#a3203f", "Dashed ring + word", text="Out of stock")}
{sw("Receipt paper", "#fffaf0", "#2b2118", "Proof: dashed edge, green tick", text="Verified · see source")}
</div>
<p class="mono" id="contrast-sum" style="margin-top:16px;text-transform:none;letter-spacing:0"></p>
<div class="body" style="margin-top:20px"><p><b>Why status isn’t the brand green:</b> about 1 in 12 men can’t easily tell red from green. “In stock” is lake blue, and every status pairs its colour with a dot shape and a word.</p></div>
''')
    sy += sec("", "Components", "Real pieces, drawn with the same CSS rules.", f'''
<div class="specimen">
<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center"><span class="ds-btn p">Hold 40 chairs for 15 min</span><span class="ds-btn s">Show 1 option without the delivery‑time limit</span><span class="ds-btn">View specs</span><span class="promo">New</span></div>
<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center"><span class="mono" style="text-transform:none;letter-spacing:0">Looking for</span><span class="req">40 units ×</span><span class="req">Navy ×</span><span class="req">Under $350 each ×</span><span class="req">Within 3 days ×</span></div>
<div style="display:flex;flex-direction:column;gap:6px"><span class="stock ok"><i></i><b>In stock</b><span class="w">· 48 at Indianapolis Regional</span></span><span class="stock warn"><i></i><b>Low stock</b><span class="w">· 6 at Columbus Hub</span></span><span class="stock bad"><i></i><b>Out of stock</b><span class="w">· Dallas Depot</span></span></div>
<span class="receipt"><span class="ck" aria-hidden="true">✓</span>Verified · see source <span class="mono">inventory · AT-NAV-4D</span></span>
</div>
{table(["The engine returns", "The screen draws"], [
        ["<code>product_card</code>", "ProductCard, with QuantityStepper, HoldNotice and ReceiptBadge"],
        ["<code>constraints</code>", "Requirement chips, each removable with <code>drop</code>"],
        ["<code>state: no_results</code> + <code>relax</code>", "NothingMatches, one button per way out"],
        ["<code>choices</code> / <code>disambiguate</code>", "ChoiceList (“Did you mean…?”)"],
        ["<code>table</code> + <code>subject</code>", "AnswerFact: big number and a sentence"],
        ["<code>citations</code>", "ReceiptBadge and ReceiptDrawer"],
        ["<code>handoff</code>", "HandoffNotice"],
        ["while waiting", "ProgressCard"]])}
''')
    sy += sec("", "Writing", "The words are part of the system.", grid([
        card("Rule", "Shopper words, not engine words", "“Found 2 chairs that match everything you asked for”, not “2 rows pass every rule”."),
        card("Rule", "Say what a number is about", "“48 navy AeroTask Pro Mesh available at Indianapolis Regional”, not “Available: 48”."),
        card("Rule", "Buttons say verb, object, consequence", "“Hold 40 chairs for 15 min”, never “Submit” or wording that sounds like a charge."),
        card("Rule", "Say no with a way out", "“Nothing matches all of that right now”, then a button for the one thing to let go of."),
        card("Rule", "Be honest about time", "“Usually 6 to 40 seconds”, with the real steps."),
        card("Rule", "Be honest about the source", "“Real answers, recorded 19 Nov 2026” in a demo; “live” only when live.")], 260))
    page("system.html", "Design System — CartesianRAG Case Study", "The CartesianRAG design system: forest, lantern, campfire and bark, separate status colours, a receipt style, 16 components mapped to the engine's answer contract.", sy, ("contrast.js",))

    # ======================================================================= 06 UI
    ui = sub_hero("A6", "High‑Fidelity UI", "The same structure as the wireframes, now in colour and driven by real engine answers. Every screen here shows a ticket the engine actually produced.")
    ui += sec("", "Elena’s answer", "Her requirements, visible and removable.", f'''
{fig("hifi-elena", "Assistant answering Elena with requirement chips, a way-out button for the one-warehouse assumption and product cards", "Fig. 01 — Requirements as chips, cards built from the contract", "Recorded 19 Nov 2026", eager=True)}
<div class="body" style="margin-top:28px"><p>The engine assumed one warehouse, the stricter rule, so it says so and offers the change. Tapping × on any chip re‑runs the same requirements minus that one. No AI runs, so the answer arrives in milliseconds.</p></div>
''')
    ui += sec("", "Ways out", "Nothing matches is never a dead end.", f'''
{fig("hifi-nomatch", "Nothing matches card with four buttons, one for each requirement that would give results if dropped", "Fig. 02 — One button per way out", "", 2000, 1344)}
''')
    ui += sec("", "Lookups", "A number with its subject.", f'''
{fig("hifi-lookup", "Lookup answer: 48 in large type, with navy AeroTask Pro Mesh available at Indianapolis Regional, and a receipt", "Fig. 03 — The sentence is built from the query’s checked filters", "", 2000, 1344)}
''')
    ui += sec("", "On a phone", "The storefront, camp to desk.", f'''
<div class="pair">
{fig("hifi-phone-store", "Storefront on a phone: Camp to desk heading and real catalog products", "Fig. 04 — Storefront, iPhone 13", "", 1170, 1992, cls="phone")}
<div class="body" style="align-self:center"><p>The products are real rows from the engine’s store. The red “New” and “Camp‑to‑desk” tags are the only place the campfire accent appears.</p>
<p><a href="{DEMO}">Open the demo</a> and ask the assistant for 40 navy mesh chairs.</p></div>
</div>
''')
    ui += sec("", "The console", "Marcus’s half, styled but not yet connected.", f'''
{fig("agent-console", "Operations console with ticket queue, the customer conversation and the co-pilot's situation analysis, policy and recommended actions", "Fig. 05 — Operations console (Task B)", "Hand‑built prototype · not connected to the engine", 1280, 860)}
''')
    page("ui.html", "High-Fidelity UI — CartesianRAG Case Study", "High-fidelity CartesianRAG screens driven by real engine answers: requirement chips, ways out, lookups with a subject, phone storefront and the operations console.", ui)
