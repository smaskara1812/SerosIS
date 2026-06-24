"""
SQL dialect bridge: lets the analytics queries stay MySQL-flavored while
running on SQL Server when USE_MSSQL is on.

Why a translator and not per-query rewrites:
  - The analytics layer has ~30 queries totalling >2000 lines of SQL.
  - Hand-porting every one risks subtle bugs (DATEDIFF arg order, INTERVAL
    syntax, LIMIT param ordering).
  - A single translator keeps the analytics code readable and lets both
    engines share one source of truth.

What it translates (MySQL → MSSQL):
    eos_TableName              →  eos.TableName
    CURDATE()                  →  CAST(GETDATE() AS DATE)
    NOW()                      →  GETDATE()
    DATE(x)                    →  CAST(x AS DATE)
    DATE_FORMAT(x, '%Y-%m')    →  CONVERT(VARCHAR(7), x, 120)   [fast path]
    DATE_FORMAT(x, '%Y-%m-%d') →  CONVERT(VARCHAR(10), x, 120)  [fast path]
    DATE_FORMAT(x, '%Y')       →  CAST(YEAR(x) AS VARCHAR(4))   [fast path]
    DATE_FORMAT(x, other)      →  FORMAT(x, 'mssql-fmt')        [fallback]
    DATE_SUB(x, INTERVAL n u)  →  DATEADD(u, -n, x)
    DATE_ADD(x, INTERVAL n u)  →  DATEADD(u, n, x)
    CURDATE() + INTERVAL n u   →  DATEADD(u, n, CURDATE())      (then CURDATE → ...)
    DATEDIFF(a, b)             →  DATEDIFF(day, b, a)            (note arg flip)
    IF(cond, t, f)             →  IIF(cond, t, f)                (IFNULL excluded)
    (col IS NULL)              →  CASE WHEN col IS NULL THEN 1 ELSE 0 END
    (col IS NOT NULL)          →  CASE WHEN col IS NOT NULL THEN 1 ELSE 0 END
    CAST(x AS CHAR)            →  CAST(x AS VARCHAR(50))
    AS open/type/key/...       →  AS [open]/[type]/[key]/...     (reserved word aliases)
    LIMIT n                    →  OFFSET 0 ROWS FETCH NEXT n ROWS ONLY
    LIMIT %s                   →  OFFSET 0 ROWS FETCH NEXT <n> ROWS ONLY  (param inlined)
    LIMIT %s OFFSET %s         →  OFFSET <m> ROWS FETCH NEXT <n> ROWS ONLY (params inlined)

Param inlining for LIMIT: MSSQL's FETCH NEXT can accept parameters, but the
order of LIMIT vs OFFSET params is flipped vs the FETCH clause, and propagating
that all the way up to every caller is more disruption than the inline is
worth. The values are pagination ints we control, so inlining is safe.

Translation only runs when USE_MSSQL is true. On MySQL the SQL passes through
unchanged.
"""

import re

from chatbot.db.config import USE_MYSQL, USE_MSSQL


# ── Balanced-paren helpers ────────────────────────────────────────────────────

def _find_matching_close(s: str, open_idx: int) -> int:
    """Given the index of '(' in s, return the index of the matching ')'."""
    depth = 0
    i = open_idx
    n = len(s)
    while i < n:
        c = s[i]
        if c == "'":
            # skip string literal
            i += 1
            while i < n and s[i] != "'":
                i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_top_level_args(args_str: str) -> list[str]:
    """Split a function arg list by top-level commas (ignore commas inside parens)."""
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    i = 0
    n = len(args_str)
    while i < n:
        c = args_str[i]
        if c == "'":
            buf.append(c)
            i += 1
            while i < n and args_str[i] != "'":
                buf.append(args_str[i]); i += 1
            if i < n:
                buf.append(args_str[i])
        elif c == "(":
            depth += 1; buf.append(c)
        elif c == ")":
            depth -= 1; buf.append(c)
        elif c == "," and depth == 0:
            out.append("".join(buf).strip()); buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        out.append("".join(buf).strip())
    return out


def _replace_func(sql: str, name_regex: str, transform) -> str:
    """
    Find every call `<name>(...)` (with balanced parens) and replace it with
    transform(list_of_args). `name_regex` is the raw regex for the function name.
    """
    pattern = re.compile(r"\b" + name_regex + r"\s*\(", re.IGNORECASE)
    out: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        m = pattern.search(sql, i)
        if not m:
            out.append(sql[i:])
            break
        out.append(sql[i : m.start()])
        open_idx = m.end() - 1
        close_idx = _find_matching_close(sql, open_idx)
        if close_idx == -1:
            out.append(sql[i:])
            break
        args_str = sql[open_idx + 1 : close_idx]
        args = _split_top_level_args(args_str)
        out.append(transform(args))
        i = close_idx + 1
    return "".join(out)


# ── Individual transforms ─────────────────────────────────────────────────────

def _tx_if(args: list[str]) -> str:
    # MySQL: IF(condition, true_val, false_val) — scalar function.
    # MSSQL: IIF(condition, true_val, false_val) — same semantics, SQL Server 2012+.
    if len(args) == 3:
        return f"IIF({args[0]}, {args[1]}, {args[2]})"
    return f"IF({', '.join(args)})"


def _tx_datediff(args: list[str]) -> str:
    # MySQL: DATEDIFF(end, start) returns days.
    # MSSQL: DATEDIFF(datepart, start, end) — note arg order flip.
    if len(args) == 2:
        return f"DATEDIFF(day, {args[1]}, {args[0]})"
    # already 3-arg or unexpected — leave alone
    return f"DATEDIFF({', '.join(args)})"


def _tx_date(args: list[str]) -> str:
    if len(args) == 1:
        return f"CAST({args[0]} AS DATE)"
    return f"DATE({', '.join(args)})"


def _tx_trim(args: list[str]) -> str:
    # TRIM(x) added in SQL Server 2017; older builds need LTRIM(RTRIM(x)).
    if len(args) == 1:
        return f"LTRIM(RTRIM({args[0]}))"
    return f"TRIM({', '.join(args)})"


def _tx_concat_ws(args: list[str]) -> str:
    """
    CONCAT_WS was only added to SQL Server in 2017. On older builds we have to
    emulate it. The MySQL semantics we need: join with the separator, skip NULLs
    and empty strings.
    """
    if len(args) < 2:
        return f"CONCAT_WS({', '.join(args)})"
    sep = args[0]
    pieces = [f"ISNULL({sep} + NULLIF({v}, ''), '')" for v in args[1:]]
    return f"LTRIM({' + '.join(pieces)})"


def _tx_date_format(args: list[str]) -> str:
    if len(args) != 2:
        return f"DATE_FORMAT({', '.join(args)})"
    expr, fmt = args[0], args[1].strip()
    # fmt comes in with surrounding quotes, e.g. "'%Y-%m'"  or  "'%%Y-%%m'"
    # The double-% form appears when the original SQL was an f-string in
    # Python — by the time we see it here, Python's f-string has run, so it's
    # actually still "'%%Y-%%m'" (the %% is preserved because % is not special
    # in f-strings; it's escaped for the DB driver which does its own %s
    # substitution). Normalize both.
    fmt_clean = fmt.strip("'").replace("%%", "%")

    # Fast paths: CONVERT is 10-50× faster than FORMAT() in SQL Server for
    # common date-to-string patterns (FORMAT uses CLR internally).
    if fmt_clean == "%Y-%m":
        # style 120 = 'YYYY-MM-DD HH:MI:SS'; VARCHAR(7) truncates to 'YYYY-MM'
        return f"CONVERT(VARCHAR(7), {expr}, 120)"
    if fmt_clean == "%Y-%m-%d":
        return f"CONVERT(VARCHAR(10), {expr}, 120)"
    if fmt_clean == "%Y":
        return f"CAST(YEAR({expr}) AS VARCHAR(4))"

    # Fallback: FORMAT() for any other pattern
    mssql_fmt = (
        fmt_clean
        .replace("%Y", "yyyy")
        .replace("%m", "MM")
        .replace("%d", "dd")
        .replace("%H", "HH")
        .replace("%i", "mm")
        .replace("%s", "ss")
    )
    return f"FORMAT({expr}, '{mssql_fmt}')"


def _interval_to_n_unit(interval_str: str) -> tuple[str, str] | None:
    m = re.match(r"INTERVAL\s+(\d+)\s+(\w+)", interval_str.strip(), re.IGNORECASE)
    if not m:
        return None
    return m.group(1), m.group(2).upper()


def _tx_date_sub(args: list[str]) -> str:
    if len(args) != 2:
        return f"DATE_SUB({', '.join(args)})"
    parts = _interval_to_n_unit(args[1])
    if not parts:
        return f"DATE_SUB({', '.join(args)})"
    n, unit = parts
    return f"DATEADD({unit}, -{n}, {args[0]})"


def _tx_date_add(args: list[str]) -> str:
    if len(args) != 2:
        return f"DATE_ADD({', '.join(args)})"
    parts = _interval_to_n_unit(args[1])
    if not parts:
        return f"DATE_ADD({', '.join(args)})"
    n, unit = parts
    return f"DATEADD({unit}, {n}, {args[0]})"


_INLINE_INTERVAL_RE = re.compile(
    r"(CURDATE\s*\(\s*\)|NOW\s*\(\s*\)|[a-zA-Z_][a-zA-Z_0-9.]*)\s*\+\s*"
    r"INTERVAL\s+(\d+)\s+(\w+)",
    re.IGNORECASE,
)


def _translate_inline_interval(sql: str) -> str:
    """`<expr> + INTERVAL n unit`  →  `DATEADD(unit, n, <expr>)`"""
    return _INLINE_INTERVAL_RE.sub(
        lambda m: f"DATEADD({m.group(3).upper()}, {m.group(2)}, {m.group(1)})",
        sql,
    )


def _translate_eos_tables(sql: str) -> str:
    """`eos_Mst_Rig`  →  `eos.Mst_Rig`  (only when followed by uppercase letter)."""
    return re.sub(r"\beos_(?=[A-Z])", "eos.", sql)


def _translate_cast_char(sql: str) -> str:
    """`CAST(x AS CHAR)`  →  `CAST(x AS VARCHAR(50))`"""
    return re.sub(r"\bAS\s+CHAR\s*\)", "AS VARCHAR(50))", sql, flags=re.IGNORECASE)


# T-SQL reserved keywords that are safe SQL identifiers in MySQL but require
# bracket-quoting in SQL Server when used as column aliases.
# pyodbc strips the brackets from the returned column name, so Python/JS callers
# see the bare name unchanged (e.g. dict key is still 'open', not '[open]').
_RESERVED_ALIAS_RE = re.compile(
    r"\bAS\s+(open|close|type|key|file|read|fetch|full|level|user|table|index)\b",
    re.IGNORECASE,
)

def _translate_reserved_aliases(sql: str) -> str:
    """Bracket T-SQL reserved words used as column aliases: `AS open` → `AS [open]`."""
    return _RESERVED_ALIAS_RE.sub(lambda m: f"AS [{m.group(1)}]", sql)


# Matches (col IS NULL) or (col IS NOT NULL) used as a sort key — MySQL boolean
# trick for NULLS LAST / NULLS FIRST. MSSQL doesn't allow predicate expressions
# in ORDER BY, so rewrite as CASE WHEN.
# Pattern is intentionally narrow (single non-space token before IS) to avoid
# accidentally matching compound predicates inside WHERE/JOIN conditions.
_BOOL_IS_NULL_RE = re.compile(
    r"\(\s*(\S+)\s+IS\s+(NOT\s+)?NULL\s*\)", re.IGNORECASE
)

def _translate_bool_is_null(sql: str) -> str:
    """`(col IS NULL)` → `CASE WHEN col IS NULL THEN 1 ELSE 0 END`"""
    def _repl(m: re.Match) -> str:
        col     = m.group(1)
        not_kw  = (m.group(2) or "").strip()
        not_str = f"NOT " if not_kw else ""
        return f"CASE WHEN {col} IS {not_str}NULL THEN 1 ELSE 0 END"
    return _BOOL_IS_NULL_RE.sub(_repl, sql)


def _translate_curdate_now(sql: str) -> str:
    sql = re.sub(r"\bCURDATE\s*\(\s*\)", "CAST(GETDATE() AS DATE)", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bNOW\s*\(\s*\)", "GETDATE()", sql, flags=re.IGNORECASE)
    return sql


# ── LIMIT translation (with param inlining) ───────────────────────────────────

_LIMIT_OFFSET_PARAM_RE = re.compile(
    r"\bLIMIT\s+%s\s+OFFSET\s+%s\s*$", re.IGNORECASE
)
_LIMIT_PARAM_RE = re.compile(r"\bLIMIT\s+%s\s*$", re.IGNORECASE)
_LIMIT_LITERAL_RE = re.compile(r"\bLIMIT\s+(\d+)\s*$", re.IGNORECASE)


def _translate_limit(sql: str, params: tuple) -> tuple[str, tuple]:
    """
    Rewrite LIMIT clauses into MSSQL OFFSET/FETCH syntax, inlining the values
    (pop them off the end of params if they were bound).

    Caller guarantees: LIMIT clauses sit at the end of a SELECT (after stripping
    trailing whitespace). All such usages in the analytics layer follow that.
    """
    stripped = sql.rstrip()
    suffix_len = len(sql) - len(stripped)
    suffix = sql[len(stripped):]

    m = _LIMIT_OFFSET_PARAM_RE.search(stripped)
    if m:
        # params tuple ends with (page_size, offset). Pop both.
        page_size = int(params[-2])
        offset    = int(params[-1])
        new_clause = f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
        new_sql = stripped[: m.start()] + new_clause + suffix
        return new_sql, params[:-2]

    m = _LIMIT_PARAM_RE.search(stripped)
    if m:
        n = int(params[-1])
        new_clause = f"OFFSET 0 ROWS FETCH NEXT {n} ROWS ONLY"
        new_sql = stripped[: m.start()] + new_clause + suffix
        return new_sql, params[:-1]

    m = _LIMIT_LITERAL_RE.search(stripped)
    if m:
        n = int(m.group(1))
        new_clause = f"OFFSET 0 ROWS FETCH NEXT {n} ROWS ONLY"
        new_sql = stripped[: m.start()] + new_clause + suffix
        return new_sql, params

    return sql, params


# ── Public entry point ────────────────────────────────────────────────────────

def translate_mssql(sql: str, params: tuple) -> tuple[str, tuple]:
    """Translate one MySQL-style SQL string + its params for MSSQL execution."""
    # 1. Inline `<expr> + INTERVAL n unit` BEFORE CURDATE() is replaced,
    #    so the regex's `CURDATE\(\)` alternative still matches.
    sql = _translate_inline_interval(sql)

    # 2. Balanced-paren function rewrites — order matters: DATE_FORMAT/_SUB/_ADD
    #    must run BEFORE DATE() because their names share the "DATE" prefix.
    #    IF() must run BEFORE any function whose name contains "IF" (none currently,
    #    but keeping it early avoids future surprises). NULLIF is excluded by \b.
    sql = _replace_func(sql, "DATE_FORMAT", _tx_date_format)
    sql = _replace_func(sql, "DATE_SUB",    _tx_date_sub)
    sql = _replace_func(sql, "DATE_ADD",    _tx_date_add)
    sql = _replace_func(sql, "DATEDIFF",    _tx_datediff)
    sql = _replace_func(sql, "DATE",        _tx_date)
    sql = _replace_func(sql, "CONCAT_WS",   _tx_concat_ws)
    sql = _replace_func(sql, "TRIM",        _tx_trim)
    sql = _replace_func(sql, r"IF(?!NULL)",  _tx_if)   # (?!NULL) skips IFNULL()

    # 3. Now-style functions.
    sql = _translate_curdate_now(sql)

    # 4. Type and identifier rewrites.
    sql = _translate_cast_char(sql)
    sql = _translate_reserved_aliases(sql)
    sql = _translate_eos_tables(sql)
    sql = _translate_bool_is_null(sql)

    # 5. LIMIT clauses (may consume trailing params).
    sql, params = _translate_limit(sql, params)

    return sql, params


def maybe_translate(sql: str, params: tuple) -> tuple[str, tuple]:
    """No-op on MySQL, full translation on MSSQL."""
    if USE_MSSQL:
        return translate_mssql(sql, params)
    return sql, params
