"""The API: the pass-through window between the screens and the kitchen.

    Prototype (browser)  ── POST /ask {"question": "..."} ──►  API  ──► engine.ask()
                         ◄────────── ticket (the contract) ──────────

WHAT AN API IS
    A restaurant's pass-through window. The dining room never walks into the
    kitchen; it hands an order through the window and gets a plate back.
    Here the "window" is a web address the browser can call.

RUN IT (from the engine/app folder)
    python -m pip install fastapi uvicorn
    python -m uvicorn api:app --port 8000

    Then open http://localhost:8000/docs  -> FastAPI draws a page where you
    can try every endpoint by clicking "Try it out".

MEMORY WITHOUT A MEMORY
    The API remembers nothing between requests ("stateless"). For a follow-up
    like "Same chairs, but within 2 days", the browser sends back the previous
    ticket's form ("constraints") with the new question. Like showing your
    receipt at the counter: the shop doesn't need to remember you.
"""
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import engine

PRESET = os.environ.get("CARTESIAN_PRESET", "no-ai")
if PRESET not in engine.PRESETS:
    raise SystemExit(f"CARTESIAN_PRESET must be one of: {', '.join(engine.PRESETS)}")

app = FastAPI(
    title="CartesianRAG API",
    version="0.1",
    description="Ask a shopping or support question; get back an answer ticket that follows the contract.",
)

# CORS = which websites may call this API from a browser. Browsers block calls
# between different addresses unless the API says it's fine. For a local demo
# we allow any address. (A real deployment would list its own website only.)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


class AskRequest(BaseModel):
    """What the browser sends. FastAPI checks it automatically (wrong shape -> error 422)."""
    question: str = Field(..., min_length=1, max_length=500,
                          examples=["Need 40 navy mesh chairs with 4D armrests under $350, Chicago within 3 days."])
    previous: Optional[dict] = Field(None, description="The previous ticket's 'constraints', for follow-up questions.")
    drop: Optional[str] = Field(None, max_length=40,
                                description="One requirement to remove from 'previous' (a chip's x). Needs 'previous'.")


_started_at = time.time()


@app.get("/health")
def health():
    """'Is the kitchen open?' The prototype calls this to decide: live answers or recorded ones."""
    return {"status": "ok", "preset": PRESET, "uptime_s": round(time.time() - _started_at)}


@app.post("/ask")
def ask(request: AskRequest):
    """Answer one question with a contract ticket."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="The question is empty.")
    try:
        return engine.ask(question, request.previous, PRESET, drop=request.drop)
    except ValueError as err:            # e.g. dropping something that isn't a requirement
        raise HTTPException(status_code=422, detail=str(err))
    except SystemExit as err:            # e.g. Ollama isn't running
        raise HTTPException(status_code=503, detail=str(err))
