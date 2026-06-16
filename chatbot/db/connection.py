from functools import lru_cache
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase
from .config import get_sqlalchemy_url


@lru_cache(maxsize=1)
def get_engine():
    """SQLAlchemy engine — created once and reused."""
    url = get_sqlalchemy_url()
    return create_engine(url)


@lru_cache(maxsize=1)
def get_sql_database() -> SQLDatabase:
    """LangChain SQLDatabase wrapper — used by the Text-to-SQL chain."""
    return SQLDatabase(get_engine())


def check_connection() -> bool:
    """Returns True if the DB is reachable, False otherwise."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
