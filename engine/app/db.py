"""One place that knows where the pantry (store.db) is and how to open it safely."""
import sqlite3
from pathlib import Path

DB_PATH = (Path(__file__).parent.parent / "data" / "store.db").resolve()


def connect() -> sqlite3.Connection:
    """Open store.db READ-ONLY.

    immutable=1 means: "this file will not change while I read it, and I
    promise not to write to it". Even if a bad query slipped past the
    guard, the database itself would refuse to change anything.
    That's two locks on the door instead of one ("defence in depth").
    """
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?immutable=1", uri=True)
    con.row_factory = sqlite3.Row  # lets us read columns by name
    return con
