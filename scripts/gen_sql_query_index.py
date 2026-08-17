"""
Regenerates docs/sql_query_index.md — an index of every direct-SQL call site in
the app (dbq() calls in views.py/auth_backend.py/audit.py, and _query() calls in
the analytics/RAG-chat layer).

For the app layer (masters/listings/auth/audit), also reconstructs the actual SQL
text and runs it through the real dialect translator (chatbot/db/sql.py ::
translate_mssql) to show the equivalent SQL Server table names + query — not a
hand-derived guess, the same code path the app itself uses at runtime.

Usage:
    python scripts/gen_sql_query_index.py
Needs Django set up (imports chatbot.db.sql) but no live DB connection.
"""
import ast
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "docs" / "sql_query_index.md"

sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "serosIS.settings")
import django  # noqa: E402

django.setup()

from chatbot.db.sql import translate_mssql  # noqa: E402

# (file, call_function_name, sql_arg_index)
TARGETS = [
    ("chatbot/views.py", "dbq", 1),
    ("chatbot/auth_backend.py", "dbq", 1),
    ("chatbot/audit.py", "dbq", 1),
    ("chatbot/analytics/tools.py", "_query", 0),
    ("chatbot/analytics/rigs.py", "_query", 0),
    ("chatbot/analytics/listings.py", "_query", 0),
    ("chatbot/analytics/hse.py", "_query", 0),
    ("chatbot/analytics/router.py", "_query", 0),
]

APP_LAYER_FILES = {
    "chatbot/views.py": "Masters, listings, admin, and page views",
    "chatbot/auth_backend.py": "AD + local login authentication",
    "chatbot/audit.py": "Audit trail row snapshotting",
}
ANALYTICS_LAYER_FILES = {
    "chatbot/analytics/tools.py": "RAG-chat tool functions (rig/HSE/finance/etc. lookups)",
    "chatbot/analytics/rigs.py": "RAG-chat rig-specific analytics",
    "chatbot/analytics/listings.py": "RAG-chat listing/table-building queries",
    "chatbot/analytics/hse.py": "RAG-chat HSE/hazard analytics",
    "chatbot/analytics/router.py": "RAG-chat tool router (rig-name cache)",
}

TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_.{}]*)", re.IGNORECASE)
OP_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)

# Distinctive placeholder used to feed translate_mssql()'s LIMIT-value inlining
# (it pops real ints off `params`, which we don't have statically). Swapped back
# to a readable marker in the output — see _clean_translated().
_PARAM_SENTINEL = 999999
_SENTINEL_PARAMS = (_PARAM_SENTINEL,) * 12


def enclosing_function(tree, target_node):
    best = None
    stack = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node):
            is_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_func:
                stack.append(node.name)
            if node is target_node:
                nonlocal best
                best = stack[-1] if stack else "(module level)"
            super().generic_visit(node)
            if is_func:
                stack.pop()

    Visitor().visit(tree)
    return best


def enclosing_function_node(tree, target_node):
    """Same walk as enclosing_function(), but returns the innermost
    FunctionDef/AsyncFunctionDef node itself (or None at module level) so
    reconstruct_sql() can look back at sibling statements for variable
    assignments."""
    best = None
    stack = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node):
            is_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_func:
                stack.append(node)
            if node is target_node:
                nonlocal best
                best = stack[-1] if stack else None
            super().generic_visit(node)
            if is_func:
                stack.pop()

    Visitor().visit(tree)
    return best


def _resolve_simple_var(name, func_node, before_line, full_src):
    """Look back within the enclosing function for a variable that's SAFE to
    inline: assigned with `=` exactly once, and never touched by `+=` anywhere
    in the function (that would mean its value depends on runtime branches —
    e.g. a conditionally-built WHERE clause — and inlining just the base
    assignment would be actively misleading, not just incomplete)."""
    if func_node is None:
        return None
    assigns, augassigns = [], False
    for n in ast.walk(func_node):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name:
            assigns.append(n)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == name:
            augassigns = True
    if augassigns or len(assigns) != 1 or assigns[0].lineno >= before_line:
        return None
    return reconstruct_sql(assigns[0].value, full_src, func_node)


def reconstruct_sql(node, full_src, func_node=None):
    """Best-effort reconstruction of the actual SQL string a node evaluates to
    (not just its Python source text). Handles plain string constants (Python
    already merges adjacent literals at parse time), f-strings (dynamic {expr}
    parts become a literal `{expr_source}` placeholder — fine, since the parts
    needing dialect translation are the static table/keyword text, not these),
    simple `+` concatenation, and a safe subset of variable references (see
    _resolve_simple_var). Returns None if it can't be reconstructed (falls back
    to raw source text for the snippet, and skips translation)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                expr_src = ast.get_source_segment(full_src, v.value) or "?"
                parts.append("{" + expr_src + "}")
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = reconstruct_sql(node.left, full_src, func_node)
        right = reconstruct_sql(node.right, full_src, func_node)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.Name):
        return _resolve_simple_var(node.id, func_node, node.lineno, full_src)
    return None


def clean_snippet(src: str, maxlen=None) -> str:
    s = re.sub(r"\s+", " ", src).strip().strip('"\' \n')
    if maxlen and len(s) > maxlen:
        s = s[:maxlen].rstrip() + "…"
    return s.replace("|", "\\|")


def fmt_cell(s: str) -> str:
    """Wrap real SQL text in backticks for a code span; leave italic `*(...)*`
    explanatory messages (which may contain their own backticks) unwrapped so
    markdown doesn't choke on nested/unbalanced backticks."""
    if s.startswith("*(") and s.endswith(")*"):
        return s
    return f"`{s}`"


def translate_for_doc(sql_text: str):
    """Run the real translator; return (translated_sql, table_list) or
    (None, None) if translation fails (e.g. malformed reconstruction)."""
    try:
        out, _ = translate_mssql(sql_text, _SENTINEL_PARAMS)
    except Exception:
        return None, None
    out = out.replace(str(_PARAM_SENTINEL), "{n}")
    tables = sorted(set(m.group(1) for m in TABLE_RE.finditer(out)))
    return out, tables


def extract(file_rel, call_name, sql_arg_idx, translate: bool):
    path = ROOT / file_rel
    src = path.read_text()
    tree = ast.parse(src, filename=str(path))
    rows = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == call_name
            and len(node.args) > sql_arg_idx
        ):
            sql_node = node.args[sql_arg_idx]
            is_bare_var = isinstance(sql_node, ast.Name)
            sql_src = ast.get_source_segment(src, sql_node) or ""
            func_node = enclosing_function_node(tree, node)
            fn_name = func_node.name if func_node is not None else "(module level)"

            reconstructed = reconstruct_sql(sql_node, src, func_node)
            resolved_bare_var = is_bare_var and reconstructed is not None
            display_src = reconstructed if resolved_bare_var else sql_src

            op_match = OP_RE.match(display_src.strip('"\'f \n'))
            row = {
                "file": file_rel,
                "line": node.lineno,
                "function": fn_name,
                "op": op_match.group(1).upper() if op_match else "?",
                "tables": ", ".join(sorted(set(m.group(1) for m in TABLE_RE.finditer(display_src)))) or "—",
                "snippet": (
                    clean_snippet(reconstructed) if resolved_bare_var
                    else f"*(built dynamically in `{sql_src}` — conditional branches, see source)*"
                    if is_bare_var else clean_snippet(sql_src)
                ),
            }
            if translate:
                if reconstructed is not None:
                    mssql_sql, mssql_tables = translate_for_doc(reconstructed)
                else:
                    mssql_sql, mssql_tables = None, None
                row["mssql_tables"] = ", ".join(mssql_tables) if mssql_tables else "—"
                row["mssql_snippet"] = clean_snippet(mssql_sql) if mssql_sql else "*(not auto-translatable — see source)*"
            rows.append(row)
    rows.sort(key=lambda r: r["line"])
    return rows


def main():
    data = [
        (f, extract(f, call, idx, translate=(f in APP_LAYER_FILES)))
        for f, call, idx in TARGETS
    ]
    total = sum(len(rows) for _, rows in data)
    app_total = sum(len(rows) for f, rows in data if f in APP_LAYER_FILES)
    analytics_total = sum(len(rows) for f, rows in data if f in ANALYTICS_LAYER_FILES)

    lines = [
        "# Direct SQL Query Index\n",
        "Every direct-SQL call site in the app, extracted mechanically from the source "
        "(AST scan of every `dbq(...)`/`_query(...)` call — see "
        "`docs/sqlserver_migration_plan.md` for what those wrappers do and why they "
        "exist). Regenerate anytime: `python scripts/gen_sql_query_index.py`.\n",
        f"**Total: {total} call sites** across two layers:\n",
        f"- **App layer — {app_total} sites** (masters, listings, auth, audit): "
        "routed through `chatbot/db/sql.py :: dbq()`. Each row below also shows the "
        "**equivalent SQL Server table name(s) and query** — generated by running the "
        "actual reconstructed SQL through the real translator "
        "(`translate_mssql()`), not hand-derived. Rows marked *(not "
        "auto-translatable — see source)* use a query shape (e.g. `.format()`, complex "
        "concatenation) this script's static reconstruction can't safely evaluate; the "
        "translator itself still handles them correctly at runtime.\n"
        f"- **Analytics/RAG-chat layer — {analytics_total} sites** (the chatbot's tool "
        "functions): routed through `chatbot/analytics/tools.py :: _query()`, which "
        "has called the translator directly since before this index existed. "
        "**SQL Server columns skipped here for now** (analytics wasn't in scope for "
        "this pass).\n",
        "Both choke points call `chatbot/db/sql.py :: maybe_translate()` — a no-op on "
        "MySQL, full MySQL→SQL Server translation when `USE_MSSQL=true`. "
        "`tests/test_no_raw_sql.py` enforces that no *new* raw SQL bypasses them. "
        "`{n}` in a SQL Server column marks a runtime-supplied pagination value "
        "(LIMIT/OFFSET) that isn't known statically — the translation structure "
        "(`OFFSET … ROWS FETCH NEXT … ROWS ONLY`) is real, the number is a placeholder.\n",
        "---\n",
        "## Contents\n",
        "| Layer | File | Purpose | Call sites |",
        "|---|---|---|---|",
    ]
    for file_rel, desc in {**APP_LAYER_FILES, **ANALYTICS_LAYER_FILES}.items():
        n = next(len(rows) for f, rows in data if f == file_rel)
        layer = "App" if file_rel in APP_LAYER_FILES else "Analytics"
        anchor = file_rel.replace("/", "").replace(".", "").lower()
        lines.append(f"| {layer} | [`{file_rel}`](#{anchor}) | {desc} | {n} |")
    lines += ["", "---\n"]

    counter = 0
    for file_rel, rows in data:
        is_app = file_rel in APP_LAYER_FILES
        layer = "App layer" if is_app else "Analytics/RAG-chat layer"
        desc = APP_LAYER_FILES.get(file_rel) or ANALYTICS_LAYER_FILES.get(file_rel)
        lines.append(f"## `{file_rel}`\n")
        lines.append(f"*{layer} — {desc}. {len(rows)} call sites.*\n")
        if is_app:
            lines.append(
                "| # | Line | Function | Op | MySQL Table(s) | SQL Server Table(s) | "
                "MySQL SQL | SQL Server SQL (equivalent) |"
            )
            lines.append("|---|---|---|---|---|---|---|---|")
        else:
            lines.append("| # | Line | Function | Op | Table(s) | SQL |")
            lines.append("|---|---|---|---|---|---|")
        for r in rows:
            counter += 1
            tables = r["tables"] if r["tables"] != "—" else "*(dynamic)*"
            if is_app:
                mssql_tables = r["mssql_tables"] if r["mssql_tables"] != "—" else "*(dynamic)*"
                lines.append(
                    f"| {counter} | [{r['line']}](../{file_rel}#L{r['line']}) | "
                    f"`{r['function']}` | {r['op']} | {tables} | {mssql_tables} | "
                    f"{fmt_cell(r['snippet'])} | {fmt_cell(r['mssql_snippet'])} |"
                )
            else:
                lines.append(
                    f"| {counter} | [{r['line']}](../{file_rel}#L{r['line']}) | "
                    f"`{r['function']}` | {r['op']} | {tables} | `{r['snippet']}` |"
                )
        lines.append("")

    lines.append("---\n")
    lines.append("## Regenerating this index\n")
    lines.append(
        "Generated, not hand-maintained: `python scripts/gen_sql_query_index.py`.\n"
    )

    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH} — {counter} rows across {len(data)} files.")


if __name__ == "__main__":
    main()
