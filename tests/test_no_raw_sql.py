"""
Guard rail: fails if any app module runs raw cursor.execute()/cur.execute() SQL
without going through the dialect translator (chatbot/db/sql.py :: maybe_translate).

Why this exists: on MySQL, raw execute() "just works" — but on SQL Server it would
silently run MySQL-flavoured SQL (wrong table names, wrong date functions, LIMIT
instead of OFFSET/FETCH, ...). See docs/sqlserver_migration_plan.md.

The two legitimate places a raw execute() is allowed are the translator's own
choke points:
  - chatbot/db/sql.py       :: dbq()    — the app-wide helper everything else uses
  - chatbot/analytics/tools.py :: _query() — the analytics layer's own equivalent

Every other module must call dbq(cursor, sql, params) instead of
cursor.execute(sql, params) directly.

Usage:
    python tests/test_no_raw_sql.py
Exits 0 if clean, 1 (with the offending file:line list) if a raw call is found.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "chatbot"

# The translator's own choke points — raw execute() is expected (and required) here.
ALLOWED_FILES = {
    APP_DIR / "db" / "sql.py",
    APP_DIR / "analytics" / "tools.py",
}


def _is_sqlalchemy_text_call(node: ast.Call) -> bool:
    """True for `conn.execute(text(...))` — SQLAlchemy's own dialect-agnostic API
    (used only for plain connectivity pings), structurally different from a
    DB-API `cursor.execute(sql_string, params)` call. Not a translator concern."""
    return bool(
        node.args
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Name)
        and node.args[0].func.id == "text"
    )


def find_raw_execute_calls(path: Path):
    """Return [(lineno, source_snippet), ...] for any `<name>.execute(...)` call
    in the file, where <name> is a simple identifier (cursor/cur/conn-style) —
    i.e. NOT a call to the dbq() wrapper, and not a SQLAlchemy text() ping."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        return [(e.lineno or 0, f"SyntaxError: {e}")]

    hits = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and isinstance(node.func.value, ast.Name)
            and not _is_sqlalchemy_text_call(node)
        ):
            hits.append((node.lineno, f"{node.func.value.id}.execute(...)"))
    return hits


def main():
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path in ALLOWED_FILES:
            continue
        if "/migrations/" in str(path):
            continue
        for lineno, snippet in find_raw_execute_calls(path):
            offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {snippet}")

    if offenders:
        print("FAIL — raw SQL execute() found outside the dialect translator.")
        print("Use dbq(cursor, sql, params) from chatbot.db.sql instead.\n")
        print("\n".join(offenders))
        sys.exit(1)

    print(f"OK — no raw execute() calls outside {sorted(f.name for f in ALLOWED_FILES)}.")
    sys.exit(0)


if __name__ == "__main__":
    main()
