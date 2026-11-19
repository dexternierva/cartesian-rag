# CartesianRAG

A UX and design-engineering case study: an assistant for a "camp-to-desk" store that answers shopping and support questions **from the store's own tables**, with a receipt for every number.

I designed it, then built a working engine behind the design to find out which design ideas survive real data and a real AI model.

**Live:** [Case study](https://dexternnierva.github.io/cartesian-rag/case-study/) · [Demo](https://dexternnierva.github.io/cartesian-rag/prototype/)

| | |
| :--- | :--- |
| **Try the demo** | [Open the prototype](prototype/) (replays real answers the engine gave) |
| **Read the case study** | [Case study website](case-study/) · [Full write-up (v4)](cartesian-rag-enterprise-case-study-v4.md) |
| **Design system** | [Tokens, 16 components and the brand book](design-system/) |
| **The engine** | [Python engine, answer contract and evaluation](engine/) · [Findings log, E1–E47](engine/FINDINGS.md) |

## What's in the demo

Open **Task A** and ask the assistant for 40 navy mesh chairs. Every answer in the online demo is a real ticket recorded from the engine (AI preset, `qwen2.5-coder:3b`). GitHub Pages can't run Python, so the answers are replayed. The status line in the assistant says so.

## Numbers, measured on a home PC

- **33 of 35** answer-key questions right with AI (26 with rules only); 2 wrong.
- Router: **8 of 8** fresh questions placed correctly (4 of 8 with rules only).
- **5 to 40 s** per AI answer, depending on the question and the day: the main design challenge.
- API tests: **23 of 23** pass.

## How this was evaluated

- **Measured:** every engine number above, checked against an answer key.
- **Expert review:** one reviewer against Nielsen's 10 heuristics; all 12 findings fixed.
- **Simulated:** an early usability round with synthetic participants, clearly labelled.
- **Not yet done:** sessions with real people.

## Run it yourself

See [`engine/README.md`](engine/README.md). In short:

```bash
cd engine && python -m pip install -r requirements.txt
cd eval && python run_pipeline_eval.py no-ai      # whole engine, no AI, about a second
```

*Author: Dex · November 2026*
