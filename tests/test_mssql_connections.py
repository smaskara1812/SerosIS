"""
Standalone MSSQL connection test — no Django required.

Tests both databases:
  DB 1  Operational data  (MSSQL_* vars)
  DB 2  Chat history      (CHAT_MSSQL_* vars)

Requires:
    pip install pyodbc python-dotenv
"""

import os
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────
# Load .env
# ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    print("[WARN] python-dotenv not installed — using system env only\n")


def _get(key, default=""):
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else value


# ─────────────────────────────────────────────
# Build connection string (FIXED)
# ─────────────────────────────────────────────
def _build_conn_str(host, port, user, password, database, driver):
    """
    Supports:
    - Named instance: 172.24.33.59\\QAserver
    - Default instance: 172.24.33.59,1433
    - SQL auth + Windows auth
    """

    parts = [f"DRIVER={{{driver}}}"]

    host = host.strip()

    # IMPORTANT FIX:
    # If named instance exists → NEVER append port
    if "\\" in host:
        parts.append(f"SERVER={host}")
    else:
        port = (port or "").strip()

        if port:
            parts.append(f"SERVER={host},{port}")
        else:
            parts.append(f"SERVER={host}")

    if database:
        parts.append(f"DATABASE={database}")

    if user:
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")
    else:
        parts.append("Trusted_Connection=yes")

    conn_str = ";".join(parts)

    # DEBUG (VERY IMPORTANT)
    print("\n[DEBUG] Connection string:")
    print(conn_str)
    print()

    return conn_str


# ─────────────────────────────────────────────
# Test single connection
# ─────────────────────────────────────────────
def test_connection(label, host, port, user, password, database, driver):

    print(f"\n{'─'*70}")
    print(f"{label}")
    print(f"Host     : {host}")
    print(f"Port     : {port}")
    print(f"User     : {user or '(Windows Auth)'}")
    print(f"Database : {database}")
    print(f"Driver   : {driver}")
    print(f"{'─'*70}")

    try:
        import pyodbc
    except ImportError:
        print("[FAIL] pyodbc not installed → pip install pyodbc")
        return False

    # Validate driver
    drivers = pyodbc.drivers()
    if not any(driver.lower() in d.lower() for d in drivers):
        print(f"[FAIL] ODBC driver not found: {driver}")
        print("Available drivers:", drivers)
        return False

    conn_str = _build_conn_str(host, port, user, password, database, driver)

    t0 = time.perf_counter()

    try:
        conn = pyodbc.connect(conn_str, timeout=10)
    except Exception as e:
        print(f"[FAIL] Connection error: {type(e).__name__}")
        print(e)
        return False

    elapsed = time.perf_counter() - t0

    try:
        cur = conn.cursor()

        cur.execute("SELECT @@VERSION")
        version = cur.fetchone()[0].splitlines()[0]

        cur.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [r[0] for r in cur.fetchall()]

        conn.close()

    except Exception as e:
        print("[FAIL] Query error:", e)
        return False

    print(f"[OK] Connected in {elapsed*1000:.1f} ms")
    print("Server :", version)
    print(f"Tables : {len(tables)}")

    return True


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    print("=" * 70)
    print("        MSSQL CONNECTION TEST (FIXED)")
    print("=" * 70)

    results = {}

    results["DB1"] = test_connection(
        "DB 1 — Operational",
        _get("MSSQL_HOST", "localhost"),
        _get("MSSQL_PORT", "1433"),
        _get("MSSQL_USER", ""),
        _get("MSSQL_PASSWORD", ""),
        _get("MSSQL_DB", ""),
        _get("MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server"),
    )

    results["DB2"] = test_connection(
        "DB 2 — Chat History",
        _get("CHAT_MSSQL_HOST", "localhost"),
        _get("CHAT_MSSQL_PORT", "1433"),
        _get("CHAT_MSSQL_USER", ""),
        _get("CHAT_MSSQL_PASSWORD", ""),
        _get("CHAT_MSSQL_DB", ""),
        _get("CHAT_MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server"),
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for k, v in results.items():
        print(f"{k}: {'OK' if v else 'FAIL'}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()