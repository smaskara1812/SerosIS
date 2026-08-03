#!/usr/bin/env python3
"""
mssql_to_mysql.py  —  MSSQL T-SQL dump → MySQL dump converter

Handles SSMS-generated scripts (the exact format produced by
"Generate Scripts" in SQL Server Management Studio).

Usage:
    python mssql_to_mysql.py input.sql output.sql
    python mssql_to_mysql.py input.sql output.sql --db Seros_Data
    python mssql_to_mysql.py input.sql output.sql --ddl-only
    python mssql_to_mysql.py input.sql output.sql --rows 100 --date-col Cr_Dt

Options:
    --db         Target MySQL database name  (default: Seros_Data)
    --ddl-only   Convert CREATE TABLE only, skip INSERT statements
    --rows N     Limit INSERT rows per table to N  (default: unlimited)
    --date-col   Column name to use for date-range ordering when --rows is set
                 (uses most-recent N rows by that column)
"""

import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# ── Data type mapping ──────────────────────────────────────────────────────────

_SIMPLE_TYPES = {
    'bigint':           'BIGINT',
    'int':              'INT',
    'smallint':         'SMALLINT',
    'tinyint':          'TINYINT',
    'bit':              'TINYINT(1)',
    'money':            'DECIMAL(19,4)',
    'smallmoney':       'DECIMAL(10,4)',
    'float':            'DOUBLE',
    'real':             'FLOAT',
    'datetime':         'DATETIME',
    'datetime2':        'DATETIME(6)',
    'smalldatetime':    'DATETIME',
    'date':             'DATE',
    'time':             'TIME(6)',
    'datetimeoffset':   'DATETIME(6)',
    'text':             'LONGTEXT',
    'ntext':            'LONGTEXT',
    'image':            'LONGBLOB',
    'uniqueidentifier': 'CHAR(36)',
    'xml':              'LONGTEXT',
    'sql_variant':      'TEXT',
    'geography':        'TEXT',
    'geometry':         'TEXT',
    'hierarchyid':      'VARCHAR(900)',
    # MSSQL timestamp = rowversion (binary counter), NOT a date
    'timestamp':        'BIGINT',
    'rowversion':       'BIGINT',
}


def _map_type(type_name: str, size: str | None) -> str:
    """Return the MySQL equivalent for a given MSSQL type name + optional size."""
    t = type_name.lower()

    if t in _SIMPLE_TYPES:
        return _SIMPLE_TYPES[t]

    # VARCHAR / NVARCHAR
    if t in ('varchar', 'nvarchar'):
        if size and size.lower() == 'max':
            return 'LONGTEXT'
        return f'VARCHAR({size})' if size else 'VARCHAR(255)'

    # VARBINARY
    if t == 'varbinary':
        if size and size.lower() == 'max':
            return 'LONGBLOB'
        return f'VARBINARY({size})' if size else 'VARBINARY(255)'

    # CHAR / NCHAR
    if t in ('char', 'nchar'):
        return f'CHAR({size})' if size else 'CHAR(1)'

    # BINARY
    if t == 'binary':
        return f'BINARY({size})' if size else 'BINARY(1)'

    # DECIMAL / NUMERIC
    if t in ('decimal', 'numeric'):
        return f'DECIMAL({size})' if size else 'DECIMAL(18,0)'

    # Unknown — preserve but warn
    sys.stderr.write(f'[WARN] Unrecognised MSSQL type: {type_name!r} — kept as-is\n')
    return type_name.upper()


# ── Statement converters ───────────────────────────────────────────────────────

# Column line pattern:  [name] [type](size) IDENTITY(1,1) NOT NULL,
_COL_RE = re.compile(
    r'^\s*\[([^\]]+)\]\s+\[(\w+)\](\([^)]*\))?\s*'   # name  type  (size)
    r'(IDENTITY\s*\(\s*\d+\s*,\s*\d+\s*\))?\s*'   # IDENTITY(a,b)
    r'(NOT\s+NULL|NULL)?\s*,?\s*$',
    re.IGNORECASE,
)


def _convert_col_line(line: str) -> str | None:
    """Convert one column definition line. Returns None if not a column line."""
    m = _COL_RE.match(line)
    if not m:
        return None
    col_name, type_name, size_paren, identity, nullability = m.groups()
    col_name = col_name.strip()
    size = size_paren.strip('()').strip() if size_paren else None
    mysql_type = _map_type(type_name, size)

    parts = [f'  `{col_name}` {mysql_type}']
    if identity:
        parts.append('AUTO_INCREMENT')
    if nullability:
        parts.append(nullability.upper().replace('  ', ' '))
    return ' '.join(parts)


def convert_create_table(stmt: str) -> str | None:
    """
    Convert a full CREATE TABLE T-SQL statement to MySQL syntax.
    Returns None if the statement cannot be parsed.
    """
    # ── Table name ─────────────────────────────────────────────────────────
    # Use [^\]]+ to match any character inside brackets (including $ and .)
    # For non-dbo schemas prefix the table name: hr.Employee → hr_Employee
    tm = re.search(
        r'CREATE\s+TABLE\s+\[([^\]]+)\]\.\[([^\]]+)\]',
        stmt, re.IGNORECASE
    )
    if not tm:
        tm2 = re.search(r'CREATE\s+TABLE\s+\[([^\]]+)\]', stmt, re.IGNORECASE)
        if not tm2:
            return None
        raw_name = tm2.group(1)
        schema = 'dbo'
    else:
        schema, raw_name = tm.group(1), tm.group(2)

    # Sanitize for MySQL: replace $ . spaces and other invalid chars with _
    safe_name = re.sub(r'[^\w]', '_', raw_name).strip('_')
    table_name = safe_name if schema.lower() == 'dbo' else f'{schema}_{safe_name}'

    # ── Extract PRIMARY KEY columns ────────────────────────────────────────
    # Pattern spans multiple lines:
    #   CONSTRAINT [name] PRIMARY KEY CLUSTERED
    #   (
    #       [col] ASC
    #   )WITH (...)  ON [...]
    pk_cols = []
    pk_m = re.search(
        r'PRIMARY\s+KEY\s+\w+\s*\(([^)]+)\)',
        stmt, re.IGNORECASE | re.DOTALL
    )
    if pk_m:
        pk_cols = re.findall(r'\[([^\]]+)\]', pk_m.group(1))

    # ── Extract column body ────────────────────────────────────────────────
    # Everything between the opening ( of CREATE TABLE and either
    # the CONSTRAINT block or the closing ) ON [filegroup]
    body_m = re.search(
        r'CREATE\s+TABLE[^\(]+\((.+?)'
        r'(?:CONSTRAINT\s*\[|\)\s*(?:WITH\s*\(|ON\s*\[|TEXTIMAGE_ON))',
        stmt, re.IGNORECASE | re.DOTALL
    )
    if not body_m:
        # Table with no constraints and no filegroup (rare) — grab to last )
        body_m = re.search(
            r'CREATE\s+TABLE[^\(]+\((.+)\)',
            stmt, re.IGNORECASE | re.DOTALL
        )
    if not body_m:
        return None

    # ── Parse column definitions ───────────────────────────────────────────
    col_defs = []
    for line in body_m.group(1).splitlines():
        converted = _convert_col_line(line)
        if converted:
            col_defs.append(converted)

    if not col_defs:
        return None

    # ── Find AUTO_INCREMENT column (if any) ───────────────────────────────
    ai_col = None
    for col in col_defs:
        m = re.match(r'\s*`(\w+)`.*AUTO_INCREMENT', col, re.IGNORECASE)
        if m:
            ai_col = m.group(1)
            break

    # MySQL rule: AUTO_INCREMENT column MUST be a key.
    # If it's already in pk_cols → fine.
    # If pk_cols is empty → make it the PRIMARY KEY.
    # If pk_cols exists but doesn't include it → add a standalone KEY.
    extra_key = None
    if ai_col:
        if not pk_cols:
            pk_cols = [ai_col]
        elif ai_col not in pk_cols:
            extra_key = ai_col

    # ── Assemble MySQL CREATE TABLE ────────────────────────────────────────
    has_trailer = bool(pk_cols or extra_key)
    out = [f'DROP TABLE IF EXISTS `{table_name}`;',
           f'CREATE TABLE `{table_name}` (']
    for i, col in enumerate(col_defs):
        comma = ',' if (i < len(col_defs) - 1 or has_trailer) else ''
        out.append(col + comma)
    if pk_cols:
        pk_str = ', '.join(f'`{c}`' for c in pk_cols)
        out.append(f'  PRIMARY KEY ({pk_str})' + (',' if extra_key else ''))
    if extra_key:
        out.append(f'  KEY `idx_{extra_key}` (`{extra_key}`)')
    out.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci')

    return '\n'.join(out)


def convert_insert(stmt: str) -> str:
    """Convert an INSERT T-SQL statement to MySQL syntax."""
    # Strip SET IDENTITY_INSERT lines that may be bundled in the same GO block
    stmt = re.sub(r'^SET\s+IDENTITY_INSERT\s+.*$', '', stmt, flags=re.MULTILINE | re.IGNORECASE).strip()
    if not stmt:
        return ''
    # Remove N'' unicode prefix from string literals
    stmt = re.sub(r"\bN'", "'", stmt)
    # Escape backslashes so MySQL doesn't treat \' as an escaped quote
    stmt = stmt.replace('\\', '\\\\')

    # Add INTO: INSERT [schema].[table] → INSERT INTO `table`
    # Must handle schema prefix the same way as CREATE TABLE
    def _replace_insert_table(m):
        schema = m.group(1).lower() if m.group(1) else 'dbo'
        raw_name = m.group(2)
        safe_name = re.sub(r'[^\w]', '_', raw_name).strip('_')
        table_name = safe_name if schema == 'dbo' else f'{schema}_{safe_name}'
        return f'INSERT IGNORE INTO `{table_name}`'

    stmt = re.sub(
        r'INSERT\s+\[([^\]]+)\]\.\[([^\]]+)\]',
        _replace_insert_table,
        stmt, flags=re.IGNORECASE
    )
    # Fallback: INSERT [table] with no schema
    def _replace_insert_notbl(m):
        safe = re.sub(r'[^\w]', '_', m.group(1)).strip('_')
        return f'INSERT IGNORE INTO `{safe}`'
    stmt = re.sub(r'INSERT\s+\[([^\]]+)\]', _replace_insert_notbl, stmt, flags=re.IGNORECASE)

    # Convert CAST('...' AS Date/DateTime/DateTime2) → plain quoted string
    # Also normalise ISO datetime: 2015-05-14T14:16:00.000 → 2015-05-14 14:16:00
    def _fix_cast(m):
        val = m.group(1)
        # Replace T separator and strip fractional seconds
        val = re.sub(r'T(\d{2}:\d{2}:\d{2})(\.\d+)?', r' \1', val)
        return f"'{val}'"
    stmt = re.sub(
        r"CAST\('([^']+)'\s+AS\s+(?:Date(?:Time(?:2|Offset)?)?)\s*\)",
        _fix_cast, stmt, flags=re.IGNORECASE
    )

    # Convert any remaining [identifier] → `identifier` (allow spaces, trim)
    stmt = re.sub(r'\[([^\]]+)\]', lambda m: f'`{m.group(1).strip()}`', stmt)
    return stmt


_SKIP_PREFIXES = (
    'USE ',
    'SET ANSI_NULLS',
    'SET QUOTED_IDENTIFIER',
    'SET ANSI_PADDING',
    'SET NOCOUNT',
    'EXEC ',
    'EXECUTE ',
    'SET IDENTITY_INSERT',
    'CREATE NONCLUSTERED INDEX',
    'CREATE UNIQUE NONCLUSTERED',
    'CREATE CLUSTERED INDEX',
    'CREATE UNIQUE CLUSTERED',
    'ALTER TABLE',
    'CREATE PROCEDURE',
    'CREATE FUNCTION',
    'CREATE TRIGGER',
    'CREATE VIEW',
    'CREATE SCHEMA',
    'PRINT ',
    'IF ',
    'BEGIN',
    'END',
)


_SKIP_TABLES = {
    'Audit_DDL_Changes',
}


def _should_skip(stmt: str) -> bool:
    upper = stmt.strip().upper()
    return any(upper.startswith(p) for p in _SKIP_PREFIXES)


def _split_inserts(block: str) -> list[str]:
    """Split a GO block into individual INSERT statements.

    Tracks single-quote depth so INSERT keywords inside string literal values
    (e.g. stored-procedure source stored in an audit table) are not treated as
    statement boundaries. Top-level INSERTs always start at column 0 (no
    leading whitespace); code inside strings is indented.
    """
    parts: list[str] = []
    in_string = False
    start = 0
    i = 0
    n = len(block)
    while i < n:
        c = block[i]
        if c == "'":
            if in_string and i + 1 < n and block[i + 1] == "'":
                i += 2  # '' is an escaped quote — stay in string
                continue
            in_string = not in_string
        elif c == '\n' and not in_string:
            # Only split when INSERT appears immediately after \n (column 0).
            # Indented INSERT (inside stored-proc text) won't match.
            if block[i + 1: i + 7].upper() == 'INSERT':
                parts.append(block[start:i])
                start = i + 1
        i += 1
    parts.append(block[start:])
    return [p.strip() for p in parts if p.strip()]


# ── File converter ─────────────────────────────────────────────────────────────

def convert_file(
    input_path: Path,
    output_path: Path,
    target_db: str,
    ddl_only: bool = False,
    max_rows: int | None = None,
    date_col: str | None = None,
):
    total_bytes = input_path.stat().st_size
    processed   = 0
    tables_ok   = 0
    tables_skip = 0
    inserts_ok  = 0
    row_counts: dict[str, int] = defaultdict(int)   # table → rows written so far

    # Detect encoding from BOM
    with open(input_path, 'rb') as _f:
        bom = _f.read(4)
    if bom[:2] in (b'\xff\xfe', b'\xfe\xff'):
        encoding = 'utf-16'       # SSMS UTF-16 LE/BE
    elif bom[:3] == b'\xef\xbb\xbf':
        encoding = 'utf-8-sig'    # UTF-8 with BOM
    else:
        encoding = 'utf-8'        # plain UTF-8 or ASCII

    with open(input_path, encoding=encoding, errors='replace') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:

        # ── Header ────────────────────────────────────────────────────────
        fout.write(f'-- Converted from MSSQL by mssql_to_mysql.py\n')
        fout.write(f'-- Source : {input_path.name}\n\n')
        fout.write(
            f'CREATE DATABASE IF NOT EXISTS `{target_db}`\n'
            f'  DEFAULT CHARACTER SET utf8mb4\n'
            f'  COLLATE utf8mb4_unicode_ci;\n\n'
        )
        fout.write(f'USE `{target_db}`;\n\n')
        fout.write('SET FOREIGN_KEY_CHECKS = 0;\n')
        fout.write("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';\n")
        fout.write('SET NAMES utf8mb4;\n\n')

        # ── Process statements (split on GO) ───────────────────────────────
        buf = []

        for raw in fin:
            processed += len(raw.encode('utf-8', errors='replace'))
            line = raw.rstrip('\n\r')

            if line.strip() == 'GO':
                stmt = '\n'.join(buf).strip()
                buf = []

                if not stmt or _should_skip(stmt):
                    continue

                upper = stmt.upper().lstrip()

                # ── Check skip-tables ─────────────────────────────────────
                tbl_match = re.search(r'\[([^\]]+)\]\.\[([^\]]+)\]', stmt)
                if not tbl_match:
                    tbl_match = re.search(r'\[([^\]]+)\]', stmt)
                _raw_tbl = (tbl_match.group(2) if tbl_match and tbl_match.lastindex >= 2
                            else tbl_match.group(1) if tbl_match else '')
                if _raw_tbl in _SKIP_TABLES:
                    continue

                # ── CREATE TABLE ──────────────────────────────────────────
                if upper.startswith('CREATE TABLE'):
                    converted = convert_create_table(stmt)
                    if converted:
                        fout.write(converted + ';\n\n')
                        tables_ok += 1
                    else:
                        first_line = stmt.splitlines()[0]
                        fout.write(f'-- [FAILED TO CONVERT] {first_line}\n\n')
                        sys.stderr.write(f'[WARN] Could not convert: {first_line}\n')
                        tables_skip += 1

                # ── INSERT ────────────────────────────────────────────────
                elif not ddl_only and upper.startswith('INSERT'):
                    # A single GO block may contain multiple INSERT statements.
                    # Split on lines that start with INSERT *outside* string
                    # literals — top-level INSERTs are at column 0 (no leading
                    # whitespace). Stored-procedure code inside VALUES strings
                    # is always indented, so we never split there.
                    individual = _split_inserts(stmt)
                    for single in individual:
                        single = single.strip()
                        if not single:
                            continue
                        if _should_skip(single):
                            continue
                        if max_rows is not None:
                            tbl_m = re.search(
                                r'INSERT\s+(?:INTO\s+)?(?:\[[^\]]+\]\.)?[\[`]?(\w+)[\]`]?',
                                single, re.IGNORECASE
                            )
                            tbl = tbl_m.group(1) if tbl_m else '__unknown__'
                            if row_counts[tbl] >= max_rows:
                                continue
                            row_counts[tbl] += 1

                        converted = convert_insert(single)
                        if not converted:
                            continue
                        fout.write(converted + ';\n')
                        inserts_ok += 1

                # Progress every ~25 MB
                if processed % (25 * 1024 * 1024) < 2000:
                    pct = processed / total_bytes * 100
                    print(
                        f'  {pct:5.1f}%  |  {tables_ok} tables  |  {inserts_ok} inserts',
                        end='\r', flush=True
                    )
            else:
                buf.append(line)

        # ── Footer ────────────────────────────────────────────────────────
        fout.write('\n\nSET FOREIGN_KEY_CHECKS = 1;\n')

    print(f'\n  Done.')
    print(f'  Tables  : {tables_ok} converted, {tables_skip} failed')
    print(f'  Inserts : {inserts_ok} statements written')
    if max_rows:
        print(f'  Row cap : {max_rows} rows per table')


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Convert an MSSQL (SSMS) SQL dump to MySQL syntax',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input',  help='Input .sql file (MSSQL / T-SQL)')
    parser.add_argument('output', help='Output .sql file (MySQL)')
    parser.add_argument(
        '--db', default='Seros_Data',
        help='Target MySQL database name (default: Seros_Data)'
    )
    parser.add_argument(
        '--ddl-only', action='store_true',
        help='Convert CREATE TABLE statements only — skip all INSERT data'
    )
    parser.add_argument(
        '--rows', type=int, default=None, metavar='N',
        help='Limit INSERT rows per table to N (useful for dev imports)'
    )
    parser.add_argument(
        '--date-col', default=None, metavar='COL',
        help='(Future) Column name for ordering when --rows is used'
    )
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output)

    if not inp.exists():
        print(f'Error: input file not found: {inp}')
        sys.exit(1)

    size_mb = inp.stat().st_size / 1024 / 1024
    print(f'Input  : {inp.name}  ({size_mb:.1f} MB)')
    print(f'Output : {out.name}')
    print(f'DB     : {args.db}')
    mode = 'DDL only' if args.ddl_only else f'DDL + data{f" (max {args.rows} rows/table)" if args.rows else ""}'
    print(f'Mode   : {mode}')
    print()

    convert_file(inp, out, args.db, args.ddl_only, args.rows, args.date_col)


if __name__ == '__main__':
    main()
