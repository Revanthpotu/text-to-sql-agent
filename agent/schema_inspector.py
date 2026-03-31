"""Database schema introspection utilities.

Provides helpers that give the LLM context about the structure of the
target database: table names, column types, sample rows, and row counts.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def list_tables(engine: Engine) -> list[str]:
    """Return a list of all user table names in the database.

    Args:
        engine: A SQLAlchemy ``Engine``.

    Returns:
        Sorted list of table names.
    """
    inspector = inspect(engine)
    return sorted(inspector.get_table_names())


def get_columns(engine: Engine, table_name: str) -> list[dict[str, Any]]:
    """Return column metadata for *table_name*.

    Each dict contains at least ``name`` and ``type`` keys.

    Args:
        engine: A SQLAlchemy ``Engine``.
        table_name: Name of the table to inspect.

    Returns:
        List of column info dicts.
    """
    inspector = inspect(engine)
    return [
        {"name": col["name"], "type": str(col["type"])}
        for col in inspector.get_columns(table_name)
    ]


def get_sample_rows(
    engine: Engine,
    table_name: str,
    limit: int = 3,
) -> pd.DataFrame:
    """Return the first *limit* rows from *table_name* as a DataFrame.

    Args:
        engine: A SQLAlchemy ``Engine``.
        table_name: Name of the table to sample.
        limit: Maximum number of rows to return.

    Returns:
        A ``pandas.DataFrame`` with sample data.
    """
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT :lim"), {"lim": limit})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def get_row_count(engine: Engine, table_name: str) -> int:
    """Return the total row count for *table_name*.

    Args:
        engine: A SQLAlchemy ``Engine``.
        table_name: Name of the table.

    Returns:
        Integer row count.
    """
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return int(result.scalar())


def get_schema_summary(engine: Engine) -> str:
    """Build a human-readable schema summary suitable for an LLM prompt.

    The summary includes table names, column names & types, row counts,
    and a few sample rows per table.

    Args:
        engine: A SQLAlchemy ``Engine``.

    Returns:
        Multi-line string describing the full database schema.
    """
    tables = list_tables(engine)
    parts: list[str] = []
    for table in tables:
        columns = get_columns(engine, table)
        count = get_row_count(engine, table)
        col_lines = "\n".join(
            f"    - {c['name']} ({c['type']})" for c in columns
        )
        sample = get_sample_rows(engine, table, limit=3)
        sample_str = sample.to_string(index=False) if not sample.empty else "    (empty)"
        parts.append(
            f"Table: {table}  ({count} rows)\n"
            f"  Columns:\n{col_lines}\n"
            f"  Sample rows:\n{sample_str}"
        )
    return "\n\n".join(parts)
