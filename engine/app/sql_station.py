"""The Text-to-SQL station: question in, contract ticket out.

    question -> WRITER -> GUARD -> RUN -> PACK -> ticket

The WRITER is passed in as a function, so we can swap a rule-based writer
for an AI writer without touching anything else here.

    writer(question) -> {"sql": "...", "confidence": 0.9}   or   None
"""
import time
import uuid
from datetime import datetime, timezone

from db import connect
from grounding import explain, subject_of, ungrounded_values
from sql_guard import GuardError, check_sql, tables_used

MAX_CITED_ROWS = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _handoff_ticket(question, reason_text, started, routing_ms):
    """When we can't answer safely, we say so and pass to a human. Never guess."""
    return {
        "contract_version": "0.1",
        "query_id": "q_" + uuid.uuid4().hex[:10],
        "question": question,
        "route": "handoff",
        "state": "handoff",
        "confidence": 0.3,
        "message": "I couldn't answer that reliably, so I'm connecting you to a specialist.",
        "components": [{"type": "handoff", "reason": "low_confidence", "summary": reason_text}],
        "citations": [],
        "timing_ms": {"generation": round(routing_ms, 1),
                      "total": round((time.perf_counter() - started) * 1000, 1)},
    }


def _is_empty(columns, rows) -> bool:
    """'Empty' = no rows came back, the only cell is NULL, or a COUNT(*) said 0.

    Careful: "available: 0" is NOT empty. "No, none in Columbus" is a real answer.
    """
    single = rows[0][0] if len(rows) == 1 and len(rows[0]) == 1 else "n/a"
    return (not rows) or single is None or (single == 0 and columns[0].lower().startswith("count"))


def answer_with_sql(question: str, writer) -> dict:
    started = time.perf_counter()

    # 1-3. WRITER -> GUARD -> RUN, with one second chance.
    # If the SQL is blocked or crashes, a writer that "can_retry" gets to see
    # the error and try again, like a student correcting a marked mistake.
    max_tries = 2 if getattr(writer, "can_retry", False) else 1
    sql, columns, rows, problem, previous = None, None, None, None, None
    writing_ms = retrieval_ms = 0.0
    tries = 0
    for tries in range(1, max_tries + 1):
        t0 = time.perf_counter()
        draft = writer(question) if tries == 1 else writer(question, previous_sql=previous, error=problem)
        writing_ms += (time.perf_counter() - t0) * 1000
        if not draft or not draft.get("sql"):
            problem = "The SQL writer could not turn this question into a query."
            break                                   # nothing to fix: the writer declined
        previous = draft["sql"]
        try:
            sql = check_sql(draft["sql"])           # 2. GUARD
        except GuardError as err:
            problem, sql = f"Query blocked by the guard: {err}", None
            continue
        t0 = time.perf_counter()
        con = connect()
        try:
            cursor = con.execute(sql)               # 3. RUN (read-only)
            columns = [d[0] for d in cursor.description]
            rows = [list(r) for r in cursor.fetchall()]
            problem = None
            # 3b. GROUNDING: an empty answer is a claim ("we don't have it").
            # Before believing it, check the query didn't search for invented values.
            if _is_empty(columns, rows):
                issues = ungrounded_values(sql, con)
                if issues:
                    problem, sql = explain(issues), None
        except Exception as err:                    # e.g. a column that doesn't exist
            problem, sql = f"Query failed to run: {err}", None
        finally:
            con.close()
        retrieval_ms += (time.perf_counter() - t0) * 1000
        if problem is None:
            break

    if problem is not None or sql is None:
        return _handoff_ticket(question, problem or "No query was produced.", started, writing_ms)
    read_at = _now_iso()

    # Drop exact duplicate rows (e.g. the same price listed once per colour),
    # so "320, 320, 320" becomes one clear answer instead of "Found 3 rows".
    unique = []
    for row in rows:
        if row not in unique:
            unique.append(row)
    rows = unique

    # 4. PACK: build the ticket the screens understand
    tables = tables_used(sql)
    empty = _is_empty(columns, rows)
    citations = [
        {
            "id": f"c{i + 1}",
            "kind": "db_row",
            "database": "store.db",
            "table": ", ".join(tables),
            "row_key": {"result_row": i + 1},
            "fields": dict(zip(columns, row)),
            "sql": sql,
            "read_at": read_at,
            "confidence": 1.0,   # the database doesn't guess: a row is a row
        }
        for i, row in enumerate(rows[:MAX_CITED_ROWS])
    ]

    con = connect()
    subject = subject_of(sql, con)
    con.close()

    if empty:
        message = "No. Nothing in the store matches that right now."
    elif len(rows) == 1:
        message = "; ".join(f"{c}: {v}" for c, v in zip(columns, rows[0]))
    else:
        message = f"Found {len(rows)} rows."

    return {
        "contract_version": "0.1",
        "query_id": "q_" + uuid.uuid4().hex[:10],
        "question": question,
        "route": "sql",
        "state": "no_results" if empty else "answer",
        "confidence": float(draft.get("confidence", 0.9)),
        "message": message,
        "components": [],            # product cards arrive with the hybrid station
        "citations": citations,
        "table": {"columns": columns, "rows": rows},
        **({"subject": subject} if subject else {}),
        "trace": {"sql": sql, "tries": tries, "writer": getattr(writer, "label", "unknown")},
        "timing_ms": {
            "generation": round(writing_ms, 1),   # time the writer took (the AI, later)
            "retrieval": round(retrieval_ms, 1),   # time the database took
            "total": round((time.perf_counter() - started) * 1000, 1),
        },
    }
