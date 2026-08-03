"""
Standalone MySQL connection test — no Django required.

Tests both databases:
  DB 1  Operational data  (MYSQL_* vars)
  DB 2  Chat history      (CHAT_MYSQL_* vars)

Usage:
    python test_mysql_connections.py
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


def test_connection(label, host, port, user, password, database):
    print(f"\n{'─'*55}")
    print(f"  {label}")
    print(f"  Host     : {host}:{port}")
    print(f"  User     : {user}")
    print(f"  Database : {database}")
    print(f"{'─'*55}")

    try:
        import pymysql
    except ImportError:
        print("  [FAIL] pymysql is not installed — run: pip install pymysql")
        return False

    t0 = time.perf_counter()
    try:
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=10,
        )
    except pymysql.OperationalError as exc:
        elapsed = time.perf_counter() - t0
        print(f"  [FAIL] Connection refused after {elapsed:.2f}s")
        print(f"         {exc}")
        return False
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False

    elapsed = time.perf_counter() - t0

    with conn.cursor() as cur:
        # Server version
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]

        # List tables
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]

    conn.close()

    print(f"  [OK]   Connected in {elapsed*1000:.1f} ms")
    print(f"  Server : MySQL {version}")
    if tables:
        print(f"  Tables ({len(tables)}): {', '.join(tables[:10])}", end="")
        print(" …" if len(tables) > 10 else "")
    else:
        print("  Tables : (none — database is empty)")

    return True


def main():
    print("=" * 55)
    print("  Seros — MySQL Connection Test")
    print("=" * 55)

    results = {}

    # ── DB 1: Operational data ──────────────────────────────
    results["DB 1 Operational"] = test_connection(
        label    = "DB 1 — Operational Data  (read-only, Phase 2)",
        host     = _get("MYSQL_HOST", "127.0.0.1"),
        port     = _get("MYSQL_PORT", "3306"),
        user     = _get("MYSQL_USER", "root"),
        password = _get("MYSQL_PASSWORD", ""),
        database = _get("MYSQL_DB", ""),
    )

    # ── DB 2: Chat history ──────────────────────────────────
    results["DB 2 Chat History"] = test_connection(
        label    = "DB 2 — Chat History  (cb_conversations, cb_messages)",
        host     = _get("CHAT_MYSQL_HOST", "127.0.0.1"),
        port     = _get("CHAT_MYSQL_PORT", "3306"),
        user     = _get("CHAT_MYSQL_USER", "root"),
        password = _get("CHAT_MYSQL_PASSWORD", ""),
        database = _get("CHAT_MYSQL_DB", ""),
    )

    # ── Summary ─────────────────────────────────────────────
    print(f"\n{'═'*55}")
    print("  Summary")
    print(f"{'═'*55}")
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
