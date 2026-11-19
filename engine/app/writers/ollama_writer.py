"""The AI SQL writer: a local model (via Ollama) turns questions into SQL.

HOW IT WORKS
    We send the model three things, called the PROMPT:
      1. Rules       - "only SELECT, answer in JSON, say null if you can't"
      2. Schema card - the map of our tables (from schema_card.py)
      3. Examples    - a few solved questions, so it copies the style
    Then the user's question. The model replies with SQL. That's all
    "Text-to-SQL" is: a well-written note to a model, plus checking its work.

SETTINGS (environment variables, both optional)
    OLLAMA_MODEL   which model to use     (default: qwen2.5-coder:7b)
    OLLAMA_URL     where Ollama listens   (default: http://localhost:11434)

No extra Python packages needed: it talks to Ollama over plain HTTP.
"""
import json
import os
import socket
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schema_card import build_schema_card  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
# Default = the small model that measured best on a home PC (11/11 SQL, 7/7 fresh forms).
# (Was 7b until 2026-11-18: a new PowerShell window forgot the 3b setting and the
#  bigger model was too slow to load, so the warm-up timed out.)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")
TIMEOUT_SECONDS = 180

RULES = """You write SQLite queries for an online store's database.

RULES
1. Reply with JSON only, in exactly this shape: {"sql": "<one SELECT query>"}
2. If the question cannot be answered from these tables, reply: {"sql": null, "reason": "<why>"}
3. Only SELECT. Never change data. Use only the tables and columns in the schema below.
4. Text values must match the listed values exactly (for example color = 'Navy', not 'navy blue').
5. For anything about stock, use stock_available.available (it is on_hand minus reserved).
6. Product names are in products.name. One product name has several SKUs (one per colour).
7. Select the columns a person would want to read (a name or id, plus the number asked for).
8. For "do you sell / do you have any ..." questions, use SELECT COUNT(*).
"""

# Few-shot examples. IMPORTANT: none of these are questions from the answer key.
# They teach the STYLE of a good answer, using different products and cities.
# Putting real test questions here would be like handing out the exam in advance.
EXAMPLES = [
    ("How many white Lift Standing Desks are in Dallas?",
     {"sql": "SELECT s.available FROM stock_available s JOIN products p USING (sku) "
             "WHERE p.name = 'Lift Standing Desk' AND p.color = 'White' AND s.depot_id = 'DAL-01'"}),
    ("Which depot holds the most Rest Footrests?",
     {"sql": "SELECT s.depot_id, SUM(s.available) AS total_available FROM stock_available s "
             "JOIN products p USING (sku) WHERE p.name = 'Rest Footrest' "
             "GROUP BY s.depot_id ORDER BY total_available DESC LIMIT 1"}),
    ("Do you sell any purple desks?",
     {"sql": "SELECT COUNT(*) FROM products WHERE category = 'Desks' AND color = 'Purple'"}),
    ("What's the most expensive desk?",
     {"sql": "SELECT name, unit_price FROM products WHERE category = 'Desks' ORDER BY unit_price DESC LIMIT 1"}),
    ("What will the weather be tomorrow?",
     {"sql": None, "reason": "Not a question about the store's data."}),
]

_SYSTEM_PROMPT = None

# A stopwatch log: one entry per call to the model. Ollama tells us how many
# "tokens" (word-pieces) it READ (the prompt) and WROTE (the answer), and how
# long each part took. run_eval.py reads and clears this list.
CALL_STATS = []


def system_prompt() -> str:
    """Rules + schema card. Built once and reused."""
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = RULES + "\nSCHEMA\n" + build_schema_card()
    return _SYSTEM_PROMPT


def _chat(messages) -> str:
    """Send a conversation to Ollama and return the model's reply text."""
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "30m",              # keep the model in memory between questions
        "format": "json",                 # ask Ollama to force valid JSON
        "options": {"temperature": 0},    # 0 = no creativity: same question -> same SQL
    }).encode("utf-8")
    request = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
            ns = 1e9  # Ollama reports durations in nanoseconds
            CALL_STATS.append({
                "read_tokens": data.get("prompt_eval_count", 0),
                "read_s": data.get("prompt_eval_duration", 0) / ns,
                "write_tokens": data.get("eval_count", 0),
                "write_s": data.get("eval_duration", 0) / ns,
                "load_s": data.get("load_duration", 0) / ns,
            })
            return data["message"]["content"]
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "ignore")[:200]
        raise SystemExit(f"Ollama answered with an error ({err.code}): {detail}\n"
                         f"Is the model downloaded?  Try:  ollama pull {OLLAMA_MODEL}")
    except (TimeoutError, socket.timeout):
        raise SystemExit(
            f"Ollama didn't answer within {TIMEOUT_SECONDS} s (model: {OLLAMA_MODEL}).\n"
            "Usually one of these:\n"
            "  1. The model is bigger than this PC can load quickly. Check:  echo $env:OLLAMA_MODEL\n"
            "  2. Ollama is stuck. Quit it from the system tray, reopen it, try again.\n"
            "  3. The PC is short of memory. Close heavy apps and try again.\n"
            "Test quickly with:  python check_ollama.py")
    except urllib.error.URLError as err:
        if isinstance(getattr(err, "reason", None), (TimeoutError, socket.timeout)):
            raise SystemExit(f"Ollama didn't answer within {TIMEOUT_SECONDS} s (model: {OLLAMA_MODEL}). "
                             "Try:  python check_ollama.py")
        raise SystemExit(f"Could not reach Ollama at {OLLAMA_URL}.\n"
                         "Is Ollama running? Open the Ollama app, or run:  ollama serve")


def _extract_sql(reply: str):
    """Pull the SQL out of the model's reply. Models don't always follow the format."""
    try:
        data = json.loads(reply)
        if isinstance(data, dict):
            return data.get("sql")
    except json.JSONDecodeError:
        pass
    match = re.search(r"(?is)\b(select|with)\b.+", reply)   # fallback: grab from SELECT onwards
    return match.group(0).strip().strip("`") if match else None


def write_sql(question: str, previous_sql: str = None, error: str = None):
    """Turn a question into SQL. If a first try failed, pass it back with the error."""
    messages = [{"role": "system", "content": system_prompt()}]
    for example_question, example_answer in EXAMPLES:
        messages.append({"role": "user", "content": example_question})
        messages.append({"role": "assistant", "content": json.dumps(example_answer)})
    messages.append({"role": "user", "content": question})

    if previous_sql and error:            # second chance: show the model its mistake
        messages.append({"role": "assistant", "content": json.dumps({"sql": previous_sql})})
        messages.append({"role": "user", "content":
                         f"That query failed with this error: {error}\n"
                         "Fix it and reply with the corrected JSON only."})

    sql = _extract_sql(_chat(messages))
    if not sql:
        return None
    # We do NOT ask the model how confident it is: models are bad at judging
    # themselves. A fixed value for now; later steps will calculate it from evidence.
    return {"sql": sql, "confidence": 0.85}


write_sql.can_retry = True   # tells the station this writer can fix its own mistakes
write_sql.label = f"ollama ({OLLAMA_MODEL})"


def warm_up() -> float:
    """Load the model into memory with a throwaway question. Returns seconds taken.

    The first call after Ollama starts is slow because the model file (several
    GB) is read from disk into memory: a "cold start". Like a car engine on a
    winter morning, it needs a minute before it drives normally.
    """
    import time
    t0 = time.perf_counter()
    # Use the REAL prompt (rules + schema + examples), not a tiny one. Ollama
    # remembers the unchanging start of a prompt, so after this the model only
    # has to read each new question, not the whole rulebook again.
    write_sql("How many white Basic Writing Desks are in Atlanta?")
    return time.perf_counter() - t0

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How many navy AeroTask Pro Mesh chairs are available in Indianapolis?"
    print("Model:   ", OLLAMA_MODEL)
    print("Question:", q)
    print("Reply:   ", write_sql(q))
