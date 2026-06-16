import requests


def check_llm() -> dict:
    from chatbot.rag.config import (
        LLM_PROVIDER, OLLAMA_BASE_URL,
        OLLAMA_CHAT_MODEL, GEMINI_API_KEY, GEMINI_CHAT_MODEL,
    )

    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            return {"ok": False, "provider": "Gemini", "model": GEMINI_CHAT_MODEL, "detail": "API key not set"}
        try:
            requests.get("https://generativelanguage.googleapis.com/", timeout=5)
            return {"ok": True, "provider": "Gemini", "model": GEMINI_CHAT_MODEL, "detail": "Endpoint reachable"}
        except Exception as e:
            return {"ok": False, "provider": "Gemini", "model": GEMINI_CHAT_MODEL, "detail": str(e)}

    # Ollama
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        installed = [m["name"] for m in r.json().get("models", [])]
        found = any(OLLAMA_CHAT_MODEL in m for m in installed)
        return {
            "ok": found,
            "provider": "Ollama",
            "model": OLLAMA_CHAT_MODEL,
            "detail": "Model ready" if found else f"Model not pulled. Installed: {', '.join(installed) or 'none'}",
        }
    except Exception as e:
        return {"ok": False, "provider": "Ollama", "model": OLLAMA_CHAT_MODEL, "detail": str(e)}


def check_embeddings() -> dict:
    from chatbot.rag.config import (
        LLM_PROVIDER, OLLAMA_BASE_URL,
        OLLAMA_EMBED_MODEL, LOCAL_EMBED_MODEL,
    )

    if LLM_PROVIDER == "gemini":
        try:
            import sentence_transformers  # noqa: F401
            return {"ok": True, "model": LOCAL_EMBED_MODEL, "detail": "sentence-transformers (local CPU)"}
        except ImportError:
            return {"ok": False, "model": LOCAL_EMBED_MODEL, "detail": "sentence-transformers not installed"}

    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        installed = [m["name"] for m in r.json().get("models", [])]
        found = any(OLLAMA_EMBED_MODEL in m for m in installed)
        return {
            "ok": found,
            "model": OLLAMA_EMBED_MODEL,
            "detail": "Model ready" if found else f"Model not pulled. Installed: {', '.join(installed) or 'none'}",
        }
    except Exception as e:
        return {"ok": False, "model": OLLAMA_EMBED_MODEL, "detail": str(e)}


def check_operational_db() -> dict:
    """DB 1 — raw Seros operational data (Django alias: default)."""
    from chatbot.db.config import USE_MYSQL, MYSQL_HOST, MYSQL_DB, MSSQL_HOST, MSSQL_DB
    from chatbot.db.connection import check_connection

    engine  = "MySQL" if USE_MYSQL else "MSSQL"
    host_db = f"{MYSQL_HOST}/{MYSQL_DB}" if USE_MYSQL else f"{MSSQL_HOST}/{MSSQL_DB}"

    try:
        ok = check_connection()
        return {"ok": ok, "engine": engine, "database": host_db, "detail": "Connected" if ok else "Could not connect"}
    except Exception as e:
        return {"ok": False, "engine": engine, "database": host_db, "detail": str(e)}


def check_chat_db() -> dict:
    """DB 2 — chat history (Django alias: chathistory, tables prefixed cb_)."""
    from chatbot.db.config import (
        USE_MYSQL,
        CHAT_MYSQL_HOST, CHAT_MYSQL_DB,
        CHAT_MSSQL_HOST, CHAT_MSSQL_DB,
    )
    from sqlalchemy import create_engine, text
    from chatbot.db.config import (
        CHAT_MYSQL_USER, CHAT_MYSQL_PASSWORD, CHAT_MYSQL_PORT,
        CHAT_MSSQL_USER, CHAT_MSSQL_PASSWORD, CHAT_MSSQL_PORT, CHAT_MSSQL_ODBC_DRIVER,
    )

    engine_name = "MySQL" if USE_MYSQL else "MSSQL"

    if USE_MYSQL:
        host_db = f"{CHAT_MYSQL_HOST}/{CHAT_MYSQL_DB}"
        url = f"mysql+pymysql://{CHAT_MYSQL_USER}:{CHAT_MYSQL_PASSWORD}@{CHAT_MYSQL_HOST}:{CHAT_MYSQL_PORT}/{CHAT_MYSQL_DB}"
    else:
        host_db = f"{CHAT_MSSQL_HOST}/{CHAT_MSSQL_DB}"
        driver = CHAT_MSSQL_ODBC_DRIVER.replace(" ", "+")
        url = f"mssql+pyodbc://{CHAT_MSSQL_USER}:{CHAT_MSSQL_PASSWORD}@{CHAT_MSSQL_HOST}:{CHAT_MSSQL_PORT}/{CHAT_MSSQL_DB}?driver={driver}"

    try:
        eng = create_engine(url)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "engine": engine_name, "database": host_db, "detail": "Connected"}
    except Exception as e:
        return {"ok": False, "engine": engine_name, "database": host_db, "detail": str(e)}


def check_vectorstore() -> dict:
    from chatbot.rag.config import VECTORSTORE_DIR, DOCSTORE_PATH

    vs_ok = VECTORSTORE_DIR.exists() and any(VECTORSTORE_DIR.iterdir())
    ds_ok = DOCSTORE_PATH.exists()

    if vs_ok and ds_ok:
        return {"ok": True, "detail": "Ready"}
    if not vs_ok and not ds_ok:
        return {"ok": False, "detail": "Not ingested — run: python manage.py ingest_manuals"}
    return {"ok": False, "detail": "Partially built — re-run: python manage.py ingest_manuals"}


def run_all() -> dict:
    return {
        "llm":            check_llm(),
        "embeddings":     check_embeddings(),
        "operational_db": check_operational_db(),
        "chat_db":        check_chat_db(),
        "vectorstore":    check_vectorstore(),
    }
