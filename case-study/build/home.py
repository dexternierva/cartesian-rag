"""The home page (the story as a loop) and the appendix hub."""
import json


def build_home(g):
    sec, fig, grid, card, stat, table, page, PILLS, DEMO, REPO = (
        g["sec"], g["fig"], g["grid"], g["card"], g["stat"], g["table"], g["page"], g["PILLS"], g["DEMO"], g["REPO_FILE"])
    m, r, s, a = PILLS["m"], PILLS["r"], PILLS["s"], PILLS["a"]
    tickets, recorded = g["load_tickets"]()
    import datetime

    def nice(iso):
        d = datetime.date(*map(int, iso.split("-")))
        return f"{d.day} {d.strftime('%b %Y')}"
    scores = g["load_scores"]()

    FACTS = [("Designer", "Dex"), ("Product", "Tabular RAG assistant · B2B e‑commerce"),
             ("Built with", "Python · SQLite · Ollama · a 3B local model"), ("Scope", "Design → Engine → Hi‑fi UI")]

    loop = """<ol class="loop" aria-label="The loop this case study follows">
<li><a href="#design"><span class="mono">Step 1</span><b>Design</b><span class="d">Personas, an answer contract, wireframes.</span></a></li>
<li><a href="#build"><span class="mono">Step 2</span><b>Build</b><span class="d">A working engine, smaller than the plan.</span></a></li>
<li><a href="#measure"><span class="mono">Step 3</span><b>Measure</b><span class="d">An answer key, a stopwatch, the misses.</span></a></li>
<li><a href="#redesign"><span class="mono">Step 4</span><b>Redesign</b><span class="d">12 review fixes and high‑fidelity UI.</span></a></li>
</ol>
<p class="loop-back">… and the redesign changed what the engine sends back, so the loop went round again.</p>"""

    # ---- dot scoreboard (real, per question)
    def dots(rows):
        cls = {"RIGHT": "r", "handoff": "h", "WRONG": "w"}
        word = {"RIGHT": "right", "handoff": "safe hand‑off", "WRONG": "wrong"}
        return "<ol>" + "".join(
            f'<li class="{cls[o]}" title="{i} · {word[o]} · {q.replace(chr(34), "")}"><span class="visually-hidden">{i} {word[o]}</span></li>'
            for i, o, q in rows) + "</ol>"

    def count(rows, o):
        return sum(1 for _, x, _ in rows if x == o)

    rr, ai = scores["rules"], scores["ai"]
    scoreboard = f"""<div class="dots" role="group" aria-label="One dot per answer-key question">
<div class="row"><span class="mono">Rules only</span>{dots(rr)}<span class="sc">{count(rr, "RIGHT")}<small style="font-size:.55em;color:var(--muted)">/{len(rr)}</small></span></div>
<div class="row"><span class="mono">With AI</span>{dots(ai)}<span class="sc">{count(ai, "RIGHT")}<small style="font-size:.55em;color:var(--muted)">/{len(ai)}</small></span></div>
<div class="legend"><span><i style="background:var(--forest);border-radius:50%"></i>Right</span><span><i style="border:2.5px solid var(--warn);border-radius:50%;background:transparent"></i>Safe hand‑off to a person</span><span><i style="background:var(--bad);border-radius:50%"></i>Wrong (the dangerous kind)</span><span>Hover a dot for its question.</span></div>
</div>
<div class="body" style="margin-top:16px"><p style="font-size:14px">With AI, {count(ai, "WRONG")} answers were wrong: a grey‑chair count (a column the safety check didn’t cover) and a follow‑up that lost its requirements after a speed fix. Both were fixed and confirmed by replaying the AI’s real answers; a fresh live run is still to do (E37, E38).</p></div>"""

    budget = """<div class="budget" role="group" aria-label="Planned wait against measured waits, drawn to the same scale">
<div class="b"><span>Design budget</span><div class="track"><div class="fill plan" style="width:2.97%"></div></div><span class="v">1.2 s</span></div>
<div class="b"><span>Median answer (Run 12)</span><div class="track"><div class="fill" style="width:17.4%"></div></div><span class="v">7.0 s</span></div>
<div class="b"><span>Elena’s question (19 Nov)</span><div class="track"><div class="fill" style="width:22.2%"></div></div><span class="v">9.0 s</span></div>
<div class="b"><span>Slowest (18 Nov)</span><div class="track"><div class="fill" style="width:100%"></div></div><span class="v">40.4 s</span></div>
<span class="mono" style="text-transform:none;letter-spacing:0">Drawn to scale. Over 99.9% of a lookup’s wait is the AI writing; the database takes milliseconds. <a class="link" href="engine.html#where-the-time-goes">Replay a real wait →</a></span>
</div>"""

    fails = [
        ("Right number, wrong question", "“What would 40 chairs cost?” → <s>$320.00</s>", "40 × $320.00 = <b>$12,800.00</b>",
         "The rules saw “cost” and returned one chair’s price, with a perfectly real receipt. A receipt proves where a number came from, not that it answers the question.", "E16"),
        ("The confident “No”", "<s>“Nothing in the store matches that.”</s>", "<b>48</b> matching chairs sat in Indianapolis",
         "The AI wrote SQL with invented product names. A grounding check now treats invented values as a reason to hand off, not to say no.", "E19"),
        ("Right for the wrong reason", "Navy asked for → receipt for the <s>black</s> chair", "Same price, so the total was right; the citation wasn’t",
         "With no colour in the form, the engine silently picked one. Now it says “any colour, same price” and cites every colour.", "E25"),
        ("An upset customer, shown a catalog", "“This is ridiculous, nobody answers my emails” → <s>product list</s>", "Hand‑off to a person",
         "The rules router scored 35/35 on its own questions and 4/8 on fresh ones. A one‑word AI tie‑breaker fixed all four.", "E32"),
    ]
    fail_html = '<div class="fails">' + "".join(
        f'''<article class="fail"><span class="mono">{e}</span><h3 class="h">{t}</h3>
<div class="said"><span class="mono">It said</span>{said}</div><div class="truth"><span class="mono">The truth</span>{truth}</div><p>{fix}</p></article>'''
        for t, said, truth, fix, e in fails) + "</div>"

    decisions = [
        ("Let the AI fill a form, not write SQL", "Considered: a bigger model writing whole queries.", "<b>0/6 → 5/6</b> with the same model. Code builds the SQL from checked values."),
        ("Rules first, AI only for the leftovers", "Considered: AI on every question.", "Known questions stay instant; the AI writes one word for the rest. Fresh routing <b>4/8 → 8/8</b>."),
        ("Remove a requirement without asking the AI again", "Considered: re‑sending a reworded question.", "The form minus one box goes straight to the database: <b>1–4 ms</b>, and it can’t mishear."),
        ("Replay real recordings on GitHub Pages", "Considered: hand‑written demo answers, or a paid server.", "Free and honest: every demo answer came out of the engine, and the status line says when."),
        ("Keep status colours out of the brand", "Considered: brand green for “in stock”.", "Lake blue + shape + word, so stock never depends on telling red from green."),
    ]
    dec_html = grid([f'<div class="mono">Decision {i}</div><h3 class="h">{t}</h3><p class="alt">{alt}</p><p class="why">{why}</p>' for i, (t, alt, why) in enumerate(decisions, 1)], 280, "dec")

    glossary = [
        ("RAG", "Retrieval‑augmented generation", "Look things up first, then answer from what you found.", "An open‑book exam: the answer must come from the book on the desk."),
        ("Router", "Which desk handles this?", "Rules recognise most questions; an AI picks one word for the rest.", "A receptionist who knows most visitors by sight."),
        ("BM25 + embeddings", "Two kinds of search", "Keyword search matches rare words; meaning search matches ideas.", "Two detectives with different blind spots."),
        ("RRF", "Reciprocal Rank Fusion", "Each search gives a product 1 / (60 + its rank); the scores are added.", "Two judges’ rankings combined into one."),
        ("Grounding check", "Is that value real?", "Before saying “no”, every value a query searched for is checked against the database.", "A librarian who checks your spelling before saying “we don’t have it”."),
        ("Contract", "The answer ticket", "Every answer follows one JSON shape: rows, receipts, requirements, timing.", "A receipt the screen knows how to read."),
    ]
    gl_html = grid([f'<div class="k"><span class="mono">{k}</span><span class="mono">{sub}</span></div><p style="color:var(--ink)">{what}</p><p class="an">{an}</p>' for k, sub, what, an in glossary], 260, "gl")

    tickets_json = json.dumps(tickets, ensure_ascii=False).replace("</", "<\\/")

    home = f"""
<section class="hero">
<div class="eyebrow mono"><span class="pip" aria-hidden="true"></span>UX &amp; design engineering case study · Tabular RAG</div>
<h1 class="title">CartesianRAG<span class="spark">.</span></h1>
<p class="thesis">The engine got the answers right <em>before the screens were ready for them</em>.</p>
<p class="lead" style="margin-top:20px">I designed an assistant that answers a camp‑to‑desk store’s questions from its own tables, with a receipt for every number. Then I built the engine behind it, measured it, and let what I measured redesign the screens.</p>
<div class="cta"><a class="btn primary" href="{DEMO}">Try the demo →</a><a class="btn" href="#design">Read the story</a></div>
<div class="facts">{''.join(f'<div><div class="mono">{k}</div><div class="v">{v}</div></div>' for k, v in FACTS)}</div>
{loop}
</section>

<section class="sec" id="anatomy-sec">
<div class="lab"><div class="mono"><span>Start here</span></div></div>
<div class="con">
<h2 class="big">One answer, two ways: the data, and the screen it becomes.</h2>
<div class="body" style="margin-top:20px"><p>Pick a real answer the engine gave. Point at a field on the left to see what it draws on the right, or point at the screen to find its data.</p></div>
<div class="evid">{m}<span class="mono" style="text-transform:none;letter-spacing:0;align-self:center">Recorded {nice(recorded)} · qwen2.5‑coder:3b</span></div>
<div class="anat" id="anatomy" hidden>
<div class="seg" role="group" aria-label="Pick a recorded answer"></div>
<div class="panes"><pre class="json" aria-label="The ticket the engine returned"></pre><div class="screen" aria-label="What the shopper sees"></div></div>
<p class="hint">Only fields with a match on the screen are highlighted. The full ticket also carries the SQL, the timing and every citation.</p>
</div>
<div id="anatomy-fallback">{fig("hifi-elena", "Assistant answering Elena with requirement chips and product cards", "Elena’s answer, drawn from its ticket", "", eager=True)}</div>
<script type="application/json" id="tickets">{tickets_json}</script>
</div>
</section>

{sec("", "Design", "Two people, one rule: show your working.", f'''
<div class="evid">{a}</div>
{grid([card("Storefront", "Elena Rostova", "B2B facilities buyer. “Tell me if you have forty ergonomic mesh chairs with 4D armrests in navy, under $350 each, delivered to Chicago by Tuesday.”"),
       card("Console", "Marcus Vance", "Tier‑1 support specialist. “If a tool suggests an action, I need to see the exact database row it came from.”")], 280)}
<div class="body"><p>The design’s one big idea was a <b>contract</b>: every answer is a ticket with the rows it used, a receipt for each number, and the requirements it understood. Screens draw from the ticket, never from loose text. Marcus’s console was designed but is still a hand‑built prototype; only Elena’s half was built for real.</p></div>
{fig("s1-storefront-widget", "Low-fidelity wireframe of the storefront with the assistant and two product cards", "Wireframe S1 — the plan, greyscale on purpose", "", 2000, 1562)}
''', "research.html", "design", "1")}

{sec("", "Build", "The smallest engine that could test the design.", f'''
<div class="evid">{m}</div>
<pre class="diagram" aria-label="Diagram: the router sends each question to one of four stations; answers pass a grounding check and become a ticket">
 Question ─► ROUTER: rules first ─► (no rule? the AI picks ONE word)
                │
   ┌────────────┼─────────────┬──────────────┬─────────────┐
   HAND‑OFF     SQL           HYBRID         SEARCH
   0–1 ms       AI writes a   AI fills a     keyword + meaning,
                SELECT        form; code     fused (RRF)
                              builds SQL
   └────────────┴─────────────┴──────┬───────┴─────────────┘
                                     ▼
        grounding check: does every searched value really exist?
                                     ▼
        TICKET: message · cards · rows · receipts · requirements · timing
</pre>
<h3 class="sub">Decisions I’d defend</h3>
{dec_html}
''', "engine.html", "build", "2")}

{sec("", "Measure", "An answer key, a stopwatch, and the misses left in.", f'''
<div class="evid">{m}</div>
<div class="body" style="margin-top:20px"><p>35 questions with proven answers, run through the whole engine (Runs 11 and 12, 12 Nov 2026). Each dot is one question.</p></div>
{scoreboard}
<h3 class="sub">The wait the design planned for, and the one it got</h3>
{budget}
<h3 class="sub">Failure gallery</h3>
{fail_html}
''', "engine.html", "measure", "3")}

{sec("", "Redesign", "Twelve review findings, none of them about wrong data.", f'''
<div class="evid">{r}{m}</div>
{grid([stat("3", "Major: Task A couldn’t be finished; the close button was hidden on phones; the wait was misrepresented."),
       stat("5", "Minor: invisible memory, a hint you couldn’t tap, a number with no subject, fake buttons, engine words."),
       stat("12<small>/12</small>", "Fixed. Three needed the engine to send <b>data</b> instead of sentences.")], 220)}
<div class="ba"><span class="before">“Without the delivery‑time limit, 1 option would match.”</span><span class="arrow" aria-hidden="true">→</span><span class="after">[ Show 1 option without the delivery‑time limit ]</span><span class="mono note">A sentence can only be read. The same fact as data (relax: field, label, matches) can be a button. That one change answers in 1–4 ms, with no AI.</span></div>
{fig("hifi-nomatch", "High-fidelity assistant: nothing matches, with one button per requirement that would give results if dropped", "High fidelity — ways out you can tap", f"Recorded {nice(recorded)}", 2000, 1344)}
<div class="swatches" style="margin-top:32px">
<div class="sw"><div class="chip" style="background:#2f6b3b;color:#fff">Forest</div><div class="meta">Primary</div></div>
<div class="sw"><div class="chip" style="background:#f2c14e;color:#2b2118">Lantern</div><div class="meta">Secondary · ways out</div></div>
<div class="sw"><div class="chip" style="background:#c8452b;color:#fff">Campfire</div><div class="meta">Rare accent</div></div>
<div class="sw"><div class="chip" style="background:#2b2118;color:#f3ece3">Bark</div><div class="meta">Text</div></div>
<div class="sw"><div class="chip" style="background:#1d6782;color:#fff">Lake</div><div class="meta">Status: in stock</div></div>
</div>
''', "evaluation.html", "redesign", "4")}

{sec("", "What I learned about RAG", "Six ideas, in plain words.", gl_html)}

{sec("", "Limits &amp; how I worked", "What this case study can’t claim, and who did what.", f'''
{grid([card("Not yet tested", "No real participants", "The usability round was simulated and the expert review had one reviewer. Next: 2–3 informal Task A sessions, one on a phone."),
       card("Not yet built", "Marcus’s console", "The operations console is styled but hand‑built; it doesn’t talk to the engine yet."),
       card("How I worked", "Tools", "Python, SQLite and Ollama on a home PC. An AI assistant (Claude) helped write and review code, ran the heuristic review, and drafted copy that I edited. The design calls, the evaluation plan and the runs on my PC are mine.")], 260)}
<div class="evid" style="margin-top:24px">{m}{r}{s}{a}<span class="mono" style="text-transform:none;letter-spacing:0;align-self:center">Every claim on these pages carries one of these labels.</span></div>
''')}
"""
    page("index.html", "CartesianRAG — UX &amp; Design Engineering Case Study",
         "Case study by Dex: CartesianRAG, an assistant that answers from a store's own tables with a receipt for every number. Designed, built, measured, then redesigned from what the measurements showed.",
         home, ("anatomy.js",))

    # ---------------------------------------------------------------- APPENDIX HUB
    rows = "".join(f'<li><a href="{f}"><span class="n">{n}</span><span class="t">{t}</span><span aria-hidden="true">→</span></a></li>' for f, n, _, t in g["PAGES"][1:])
    ap = f"""
<section class="hero sub">
<div class="eyebrow mono crumbs"><a href="index.html">Case study</a><span aria-hidden="true">/</span><span class="here">Appendix</span></div>
<h1 class="title">Appendix<span class="spark">.</span></h1>
<p class="lead">The home page tells the story in about three minutes. These pages hold the detail behind each step, for readers who want to check the working.</p>
</section>
{sec("", "Contents", "Six detail pages.", f'<ol class="toc">{rows}</ol>')}
{sec("", "Evidence labels", "Every claim says where it came from.", table(["Label", "What it means"], [
        [m, "Produced by running the engine and checking every answer against an answer key"],
        [r, "One reviewer checked the prototype against Nielsen’s 10 heuristics"],
        [s, "Predicted behaviour of synthetic participants. No real people took part"],
        [a, "Design‑time hypotheses about users and the market"]]) + '<div class="body" style="margin-top:24px"><p>Earlier drafts gave precise percentages for discovery research and a 500‑query benchmark. Neither study was run, so these pages leave those numbers out.</p></div>')}
{sec("", "Source files", "Everything behind these pages is in the repository.", grid([
        card("Write‑up", "Case study v4", f'The full written case study. <a href="{REPO}cartesian-rag-enterprise-case-study-v4.md">Read it on GitHub</a>'),
        card("Engine", "Findings log E1–E47", f'Every measured result, with what it meant for the design. <a href="{REPO}engine/FINDINGS.md">Read it on GitHub</a>'),
        card("Design system", "Tokens and components", f'27 colours, 9 text styles and 16 components. <a href="{REPO}design-system/README.md">Read it on GitHub</a>')], 240))}
"""
    page("appendix.html", "Appendix — CartesianRAG Case Study", "Appendix to the CartesianRAG case study: research, IA, engine, evaluation, design system and UI detail pages, plus evidence labels and source files.", ap)
