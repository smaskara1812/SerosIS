import os


# ── Database engine: set exactly one to true ──────────────────────────────────
USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() == "true"
USE_MSSQL = os.getenv("USE_MSSQL", "false").lower() == "true"

# Validate — exactly one must be active
_active = [USE_MYSQL, USE_MSSQL]
if sum(_active) > 1:
    raise RuntimeError("DB config error: more than one of USE_MYSQL / USE_MSSQL is set to true.")
if sum(_active) == 0:
    raise RuntimeError("DB config error: none of USE_MYSQL / USE_MSSQL is set to true.")


# ── Operational DB — MySQL ─────────────────────────────────────────────────────
MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT     = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB       = os.getenv("MYSQL_DB", "seros")
MYSQL_USER     = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# ── Operational DB — MSSQL ────────────────────────────────────────────────────
MSSQL_HOST        = os.getenv("MSSQL_HOST", "localhost")
MSSQL_PORT        = int(os.getenv("MSSQL_PORT", "1433"))
MSSQL_DB          = os.getenv("MSSQL_DB", "seros")
MSSQL_USER        = os.getenv("MSSQL_USER", "")
MSSQL_PASSWORD    = os.getenv("MSSQL_PASSWORD", "")
MSSQL_ODBC_DRIVER = os.getenv("MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

# ── Chat History DB — MySQL ───────────────────────────────────────────────────
CHAT_MYSQL_HOST     = os.getenv("CHAT_MYSQL_HOST", "localhost")
CHAT_MYSQL_PORT     = int(os.getenv("CHAT_MYSQL_PORT", "3306"))
CHAT_MYSQL_DB       = os.getenv("CHAT_MYSQL_DB", "SerosIS")
CHAT_MYSQL_USER     = os.getenv("CHAT_MYSQL_USER", "root")
CHAT_MYSQL_PASSWORD = os.getenv("CHAT_MYSQL_PASSWORD", "")

# ── Chat History DB — MSSQL ───────────────────────────────────────────────────
CHAT_MSSQL_HOST        = os.getenv("CHAT_MSSQL_HOST", "localhost")
CHAT_MSSQL_PORT        = int(os.getenv("CHAT_MSSQL_PORT", "1433"))
CHAT_MSSQL_DB          = os.getenv("CHAT_MSSQL_DB", "SerosIS")
CHAT_MSSQL_USER        = os.getenv("CHAT_MSSQL_USER", "")
CHAT_MSSQL_PASSWORD    = os.getenv("CHAT_MSSQL_PASSWORD", "")
CHAT_MSSQL_ODBC_DRIVER = os.getenv("CHAT_MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")


def get_sqlalchemy_url() -> str:
    """SQLAlchemy URL for the operational DB (analytics queries)."""
    if USE_MYSQL:
        return (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        )
    driver = MSSQL_ODBC_DRIVER.replace(" ", "+")
    return (
        f"mssql+pyodbc://{MSSQL_USER}:{MSSQL_PASSWORD}"
        f"@{MSSQL_HOST}:{MSSQL_PORT}/{MSSQL_DB}"
        f"?driver={driver}"
    )


def get_django_db_config() -> dict:
    """Django DATABASES config for the operational DB (default)."""
    if USE_MYSQL:
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": MYSQL_DB,
            "USER": MYSQL_USER,
            "PASSWORD": MYSQL_PASSWORD,
            "HOST": MYSQL_HOST,
            "PORT": str(MYSQL_PORT),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    return {
        "ENGINE": "mssql",
        "NAME": MSSQL_DB,
        "USER": MSSQL_USER,
        "PASSWORD": MSSQL_PASSWORD,
        "HOST": MSSQL_HOST,
        "PORT": str(MSSQL_PORT),
        "OPTIONS": {"driver": MSSQL_ODBC_DRIVER},
    }


def get_chat_db_config() -> dict:
    """Django DATABASES config for the chat history DB (chathistory)."""
    if USE_MYSQL:
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": CHAT_MYSQL_DB,
            "USER": CHAT_MYSQL_USER,
            "PASSWORD": CHAT_MYSQL_PASSWORD,
            "HOST": CHAT_MYSQL_HOST,
            "PORT": str(CHAT_MYSQL_PORT),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    return {
        "ENGINE": "mssql",
        "NAME": CHAT_MSSQL_DB,
        "USER": CHAT_MSSQL_USER,
        "PASSWORD": CHAT_MSSQL_PASSWORD,
        "HOST": CHAT_MSSQL_HOST,
        "PORT": str(CHAT_MSSQL_PORT),
        "OPTIONS": {"driver": CHAT_MSSQL_ODBC_DRIVER},
    }
