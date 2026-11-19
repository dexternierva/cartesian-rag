"""Check that Ollama is installed, running, and has the model we need.

Run this FIRST, before run_eval.py:

    python check_ollama.py
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from writers.ollama_writer import OLLAMA_MODEL, OLLAMA_URL, write_sql  # noqa: E402

print(f"1. Looking for Ollama at {OLLAMA_URL} ...")
try:
    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as response:
        models = [m["name"] for m in json.loads(response.read().decode("utf-8")).get("models", [])]
except (urllib.error.URLError, OSError):
    raise SystemExit("   NOT FOUND. Open the Ollama app (or run 'ollama serve') and try again.")
print("   OK, Ollama is running.")

print(f"2. Looking for the model '{OLLAMA_MODEL}' ...")
print("   Models on this computer:", ", ".join(models) or "(none yet)")
if not any(m == OLLAMA_MODEL or m.startswith(OLLAMA_MODEL + ":") for m in models):
    raise SystemExit(f"   NOT DOWNLOADED. Run:  ollama pull {OLLAMA_MODEL}")
print("   OK, model is downloaded.")

print("3. Asking it one question (the first answer can take a minute while the model loads) ...")
question = "How many black Duo Monitor Arms are in Chicago?"
print("   Question:", question)
print("   Reply:   ", write_sql(question))
print("\nAll good. Next:  cd ../eval  &&  python run_eval.py ollama")
