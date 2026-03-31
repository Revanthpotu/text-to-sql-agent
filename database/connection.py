"""SQLAlchemy engine factory and connection helpers."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(db_url: str | None = None) -> Engine:
    """Create and return a SQLAlchemy Engine.

    If *db_url* is not provided the function builds a PostgreSQL URL from
    the standard ``DB_*`` environment variables, falling back to a local
    SQLite sample database when ``USE_SAMPLE_DB=true``.

    Args:
        db_url: Optional explicit database URL.

    Returns:
        A configured ``sqlalchemy.engine.Engine`` with connection pooling.

    Raises:
        ValueError: When required configuration is missing.
    """

    if db_url:
        url = db_url
    elif os.getenv("USE_SAMPLE_DB", "false").lower() == "true":
        url = "sqlite:///sample_ecommerce.db"
    else:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD", "")
        if not name or not user:
            raise ValueError(
                "Database not configured. Set DB_NAME and DB_USER environment "
                "variables, or set USE_SAMPLE_DB=true to use the bundled SQLite "
                "database."
            )
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # SQLite doesn't support pool_size / max_overflow
    if url.startswith("sqlite"):
        return create_engine(url, echo=False)

    return create_engine(
        url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


def test_connection(engine: Engine) -> tuple[bool, str]:
    """Test that *engine* can reach the database.

    Args:
        engine: A SQLAlchemy ``Engine``.

    Returns:
        ``(success, message)`` tuple.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connection successful."
    except Exception as exc:
        return False, f"Connection failed: {exc}"
