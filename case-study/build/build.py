"""Builds the CartesianRAG case-study pages: one shared shell, eight pages of content.

    python build.py        (run from case-study/build/; Python 3.8 or newer)

The home page tells the story as a loop (Design -> Build -> Measure -> Redesign).
The other pages are an appendix for readers who want the detail.
Real data is read from the repository, never typed in:
    prototype/answers.json                    -> the live "anatomy of an answer" panel
    engine/eval/results/pipeline-*.json       -> the dot scoreboard
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1]        # case-study/
REPO = OUT.parent                                        # the repository root
DEMO = "../prototype/"
SITE = "https://dexternnierva.github.io/cartesian-rag/"   # the live site (GitHub Pages)
GITHUB = "https://github.com/dexternnierva/cartesian-rag"
REPO_FILE = GITHUB + "/blob/main/"                       # Markdown opens formatted on GitHub, not as raw text

# The loop, on the home page
STEPS = [("design", "1", "Design"), ("build", "2", "Build"), ("measure", "3", "Measure"), ("redesign", "4", "Redesign")]
# The appendix pages: (file, number, short label, title)
PAGES = [
    ("appendix.html", "A", "Appendix", "Appendix"),
    ("research.html", "A1", "Research", "Research &amp; Discovery"),
    ("ia.html", "A2", "IA", "Information Architecture"),
    ("engine.html", "A3", "Engine", "Design ↔ Engine"),
    ("evaluation.html", "A4", "Evaluation", "Evaluation"),
    ("system.html", "A5", "System", "Design System"),
    ("ui.html", "A6", "UI", "High‑Fidelity UI"),
]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E"
           "%3Crect x=%224%22 y=%224%22 width=%2224%22 height=%2224%22 rx=%226%22 fill=%22%232f6b3b%22/%3E"
           "%3Ccircle cx=%2222%22 cy=%2210%22 r=%224%22 fill=%22%23c8452b%22/%3E%3C/svg%3E")
FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700"
         "&amp;family=Figtree:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap")
# Applies a saved theme before the page paints, so it never flashes the wrong one.
THEME_BOOT = ("<script>try{var t=localStorage.getItem('crcs-theme');if(t==='dark'||t==='light')"
              "document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>")


# ----------------------------------------------------------------- real data
def load_tickets():
    """Four real tickets from the 19 Nov recording, trimmed to what the panel shows."""
    data = json.loads((REPO / "prototype" / "answers.json").read_text(encoding="utf-8"))
    by_q = {a["question"]: a for a in data["answers"] if not a.get("drop")}
    picks = [
        ("Elena’s 40 chairs", "Need 40 ergonomic mesh chairs with 4D armrests in navy, under $350 each, delivered to Chicago within 3 days."),
        ("Nothing matches", "40 navy mesh chairs with 4D armrests under $300 delivered to Chicago within 2 days"),
        ("A lookup", "How many navy AeroTask Pro Mesh chairs are available in Indianapolis?"),
        ("An upset customer", "My order is 4 days late and I want a refund right now!"),
    ]
    out = []
    for label, q in picks:
        t = by_q[q]["ticket"]
        slim = {"state": t["state"], "message": t["message"]}
        if t.get("constraints"):
            slim["constraints"] = {k: v for k, v in t["constraints"].items() if k != "follow_up"}
        if t.get("relax"):
            slim["relax"] = t["relax"]
        if t.get("subject"):
            slim["subject"] = t["subject"]
        if t.get("table") and t["state"] == "answer" and t.get("subject"):
            slim["table"] = {"columns": t["table"]["columns"], "rows": t["table"]["rows"][:1]}
        comps = []
        for c in t.get("components", [])[:2]:
            if c["type"] == "product_card":
                comps.append({"type": "product_card", "sku": c["sku"], "name": c["name"], "color": c["color"],
                              "unit_price": c["unit_price"], "citation_ids": c["citation_ids"],
                              "stock": {"available": c["stock"]["available"], "depot_name": c["stock"]["depot_name"]}})
            elif c["type"] == "handoff":
                comps.append({"type": "handoff", "reason": c.get("reason")})
        if comps:
            slim["components"] = comps
        if t.get("citations"):
            c0 = t["citations"][0]
            slim["citations"] = [{"id": c0["id"], "table": c0["table"], "row_key": c0.get("row_key")}, "…"] \
                if len(t["citations"]) > 1 else [{"id": c0["id"], "table": c0["table"], "row_key": c0.get("row_key")}]
        slim["timing_ms"] = {"total": t["timing_ms"]["total"]}
        out.append({"label": label, "question": q, "ticket": slim})
    return out, data["recorded_at"][:10]


def load_scores():
    """Per-question outcomes from the two whole-pipeline runs."""
    res = REPO / "engine" / "eval" / "results"
    rows = {}
    for key, f in (("rules", "pipeline-no-ai.json"), ("ai", "pipeline-ai.json")):
        d = json.loads((res / f).read_text(encoding="utf-8"))
        rows[key] = [(r["id"], r["outcome"], r["ticket"]["question"]) for r in d["results"]]
    return rows


# ----------------------------------------------------------------- shell
def head(title, desc, scripts=(), file="index.html"):
    url = SITE + "case-study/" + ("" if file == "index.html" else file)
    js = "".join(f'<script src="js/{s}" defer></script>\n' for s in ("menu-dismiss.js", "lightbox.js", "theme.js") + tuple(scripts))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Dex">
<meta name="theme-color" content="#faf6ef">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:site_name" content="CartesianRAG case study by Dex">
<meta property="og:url" content="{url}">
<link rel="canonical" href="{url}">
<meta property="og:image" content="{SITE}case-study/images/og-card.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="CartesianRAG: the engine got the answers right before the screens were ready for them.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
{THEME_BOOT}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="styles.css">
{js}</head>
<body>
<div class="page">
<a class="skip" href="#content">Skip to content</a>
"""


def header(current):
    home = "" if current == "index.html" else "index.html"
    cur = ' aria-current="page"'
    steps = "".join(f'<a href="{home}#{a}">{lab}</a>' for a, _, lab in STEPS)
    links = steps + f'<a href="appendix.html"{cur if current != "index.html" else ""}>Appendix</a>'
    menu_steps = "".join(f'<a href="{home}#{a}"><span>{lab}</span><span>{n}</span></a>' for a, n, lab in STEPS)
    menu_pages = "".join(f'<a href="{f}"><span>{t}</span><span>{n}</span></a>' for f, n, _, t in PAGES)
    toggle = '<button type="button" class="theme-btn" data-theme-toggle hidden>Night</button>'
    return f"""<header class="site-h">
<input class="menu-toggle" type="checkbox" id="menu-toggle" aria-controls="site-menu" aria-label="Case study pages menu">
<div class="m-bar">
<a class="brand" href="index.html"><span class="dot" aria-hidden="true"></span>CartesianRAG</a>
<div class="right">{toggle}<label class="menu-button" for="menu-toggle" title="Open or close the page menu"><span class="when-closed">Menu</span><span class="when-open">Close</span><svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 6h14M2 12h14"></path></svg></label></div>
</div>
<nav id="site-menu" class="m-menu" aria-label="Case study pages menu">
{menu_steps}{menu_pages}<a href="{DEMO}"><span>Try the demo</span><span>→</span></a>
</nav>
<nav class="d-nav" aria-label="Case study sections">
<a class="brand" href="index.html"><span class="dot" aria-hidden="true"></span>CartesianRAG</a>
<div class="links">{links}{toggle}<a class="demo" href="{DEMO}">Try the demo</a></div>
</nav>
</header>
"""


FOOTER = f"""<footer class="site-f">
<div class="in">
<div>
<p class="claim">Designing for an AI that can be slow, unsure and wrong, and showing its working anyway.</p>
<div class="links">
<a class="u" href="mailto:dexternierva@gmail.com">dexternierva@gmail.com</a>
<a class="u" href="{DEMO}">Try the demo</a>
<a class="u" href="{GITHUB}">Code on GitHub</a>
<a href="#content" style="color:var(--muted)">Back to top ↑</a>
</div>
</div>
<div class="mono" style="display:flex;align-items:center;gap:10px;text-transform:none;letter-spacing:0"><span class="dot" aria-hidden="true" style="width:6px;height:6px;box-shadow:none"></span>CartesianRAG · Case study by Dex · Nov 2026</div>
</div>
</footer>
</div>
</body>
</html>
"""


# ----------------------------------------------------------------- building blocks
def sub_hero(num, title, lead, facts=None):
    f = ""
    if facts:
        f = '<div class="facts">' + "".join(f'<div><div class="mono">{k}</div><div class="v">{v}</div></div>' for k, v in facts) + "</div>"
    return f"""<section class="hero sub">
<div class="eyebrow mono crumbs"><a href="index.html">Case study</a><span aria-hidden="true">/</span><a href="appendix.html">Appendix</a><span aria-hidden="true">/</span><span class="here">{num} — {title}</span></div>
<h1 class="title">{title}<span class="spark">.</span></h1>
<p class="lead">{lead}</p>
{f}
</section>
"""


def sec(num, label, h2, body, more=None, sid=None, step=None):
    link = f'<a href="{more}">Detail in the appendix →</a>' if more else ""
    badge = f'<span class="step-n" aria-hidden="true">{step}</span>' if step else ""
    num_html = f"<span>{num}</span>" if num else ""
    return f"""<section class="sec"{f' id="{sid}"' if sid else ""}>
<div class="lab">{badge}<div class="mono">{num_html}<span>{label}</span></div>{link}</div>
<div class="con">
<h2 class="big">{h2}</h2>
{body}
</div>
</section>
"""


def fig(src, alt, cap_l, cap_r="", w=2000, h=1344, cls="", eager=False):
    return f"""<figure class="{cls}">
<div class="frame"><img src="images/{src}.webp" width="{w}" height="{h}" alt="{alt}" {'fetchpriority="high"' if eager else 'loading="lazy"'} decoding="async"></div>
<figcaption><span>{cap_l}</span><span>{cap_r}</span></figcaption>
</figure>"""


def grid(cells, minw=260, cls=""):
    return f'<div class="grid {cls}" style="--min:{minw}px">' + "".join(f"<div>{c}</div>" for c in cells) + "</div>"


def card(label, title, text, right=""):
    k = f'<div class="k"><span class="mono">{label}</span><span class="mono">{right}</span></div>' if right else f'<div class="mono">{label}</div>'
    return f"{k}<h3 class=\"h\">{title}</h3><p>{text}</p>"


def stat(n, text):
    return f'<div class="stat"><div class="n">{n}</div><p>{text}</p></div>'


def table(head_cells, rows, num_cols=()):
    num = ' class="num"'
    th = "".join(f'<th{num if i in num_cols else ""}>{c}</th>' for i, c in enumerate(head_cells))
    tr = "".join("<tr>" + "".join(f'<td{num if i in num_cols else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def pn(current):
    files = [p[0] for p in PAGES]
    names = {p[0]: (p[1], p[3]) for p in PAGES}
    i = files.index(current)
    out = '<nav class="pn" aria-label="Previous and next page">'
    if i == 0:
        out += '<a href="index.html"><span class="mono">← Back</span><span class="t">The story</span></a>'
    else:
        n, t = names[files[i - 1]]
        out += f'<a href="{files[i - 1]}"><span class="mono">← Previous — {n}</span><span class="t">{t}</span></a>'
    if i + 1 < len(files):
        n, t = names[files[i + 1]]
        out += f'<a class="next" href="{files[i + 1]}"><span class="mono">Next — {n} →</span><span class="t">{t}</span></a>'
    else:
        out += f'<a class="next" href="{DEMO}"><span class="mono">Finish →</span><span class="t">Try the demo</span></a>'
    return out + "</nav>"


def page(file, title, desc, body, scripts=()):
    html = head(title, desc, scripts, file) + header(file) + f'<main id="content">\n{body}\n{"" if file == "index.html" else pn(file)}\n</main>\n' + FOOTER
    (OUT / file).write_text(html, encoding="utf-8")
    print("wrote", file, len(html))


PILLS = {
    "m": '<span class="label-pill lp-measured">Measured</span>',
    "r": '<span class="label-pill lp-review">Expert review</span>',
    "s": '<span class="label-pill lp-sim">Simulated</span>',
    "a": '<span class="label-pill lp-assumed">Assumed</span>',
}

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    import content
    old = OUT / "overview.html"          # replaced by the story on the home page and the appendix
    if old.exists():
        print("note: overview.html is no longer built; delete it if it's still in the folder")
    content.build(globals())
