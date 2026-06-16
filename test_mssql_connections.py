"""
Standalone MSSQL connection test — no Django required.

Tests both databases:
  DB 1  Operational data  (MSSQL_* vars)
  DB 2  Chat history      (CHAT_MSSQL_* vars)

Requires pyodbc and the ODBC driver named in MSSQL_ODBC_DRIVER.
Check installed drivers with:
    odbcinst -q -d            (Linux / macOS)
    Get-OdbcDriver            (Windows PowerShell)

Usage:
    python test_mssql_connections.py
"""

import os
import sys
import time
from pathlib import Path

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    print("[WARN] python-dotenv not installed — reading env vars from shell only\n")


def _get(key, default=""):
    return os.getenv(key, default)


def _build_conn_str(host, port, user, password, database, driver):
    """Build a pyodbc connection string.

    Supports both SQL Server auth (user/password) and Windows Integrated auth
    (leave MSSQL_USER blank to use Trusted_Connection=yes).
    """
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={host},{port}",
        f"DATABASE={database}",
    ]
    if user:
        parts += [f"UID={user}", f"PWD={password}"]
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts)


def test_connection(label, host, port, user, password, database, driver):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"  Host     : {host}:{port}")
    print(f"  User     : {user or '(Windows Integrated Auth)'}")
    print(f"  Database : {database}")
    print(f"  Driver   : {driver}")
    print(f"{'─'*60}")

    try:
        import pyodbc
    except ImportError:
        print("  [FAIL] pyodbc is not installed — run: pip install pyodbc")
        return False

    # Check driver is available
    available = [d for d in pyodbc.drivers() if driver.lower() in d.lower()]
    if not available:
        all_drivers = pyodbc.drivers()
        print(f"  [FAIL] ODBC driver not found: '{driver}'")
        if all_drivers:
            print(f"         Available drivers: {', '.join(all_drivers)}")
        else:
            print("         No ODBC drivers installed.")
        return False

    conn_str = _build_conn_str(host, port, user, password, database, driver)

    t0 = time.perf_counter()
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
    except pyodbc.OperationalError as exc:
        elapsed = time.perf_counter() - t0
        print(f"  [FAIL] Connection refused after {elapsed:.2f}s")
        print(f"         {exc}")
        return False
    except pyodbc.InterfaceError as exc:
        print(f"  [FAIL] Interface error (check driver / server name)")
        print(f"         {exc}")
        return False
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False

    elapsed = time.perf_counter() - t0

    with conn.cursor() as cur:
        # Server version
        cur.execute("SELECT @@VERSION")
        full_version = cur.fetchone()[0]
        # Shorten to first line only
        version = full_version.splitlines()[0].strip()

        # List user tables
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        )
        tables = [row[0] for row in cur.fetchall()]

    conn.close()

    print(f"  [OK]   Connected in {elapsed*1000:.1f} ms")
    print(f"  Server : {version}")
    if tables:
        print(f"  Tables ({len(tables)}): {', '.join(tables[:10])}", end="")
        print(" …" if len(tables) > 10 else "")
    else:
        print("  Tables : (none — database is empty)")

    return True


def main():
    print("=" * 60)
    print("  Seros — MSSQL Connection Test")
    print("=" * 60)

    results = {}

    # ── DB 1: Operational data ──────────────────────────────────
    results["DB 1 Operational"] = test_connection(
        label    = "DB 1 — Operational Data  (read-only, Phase 2)",
        host     = _get("MSSQL_HOST", "localhost"),
        port     = _get("MSSQL_PORT", "1433"),
        user     = _get("MSSQL_USER", ""),
        password = _get("MSSQL_PASSWORD", ""),
        database = _get("MSSQL_DB", ""),
        driver   = _get("MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server"),
    )

    # ── DB 2: Chat history ──────────────────────────────────────
    results["DB 2 Chat History"] = test_connection(
        label    = "DB 2 — Chat History  (cb_conversations, cb_messages)",
        host     = _get("CHAT_MSSQL_HOST", "localhost"),
        port     = _get("CHAT_MSSQL_PORT", "1433"),
        user     = _get("CHAT_MSSQL_USER", ""),
        password = _get("CHAT_MSSQL_PASSWORD", ""),
        database = _get("CHAT_MSSQL_DB", ""),
        driver   = _get("CHAT_MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server"),
    )

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  Summary")
    print(f"{'═'*60}")
    all_ok = True
    for name, ok in results.items():
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if not ok:
            all_ok = False

    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
