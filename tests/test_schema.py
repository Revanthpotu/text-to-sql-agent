"""Tests for the schema inspector using an in-memory SQLite database."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from agent.schema_inspector import (
    get_columns,
    get_row_count,
    get_sample_rows,
    get_schema_summary,
    list_tables,
)


@pytest.fixture()
def engine() -> Engine:
    """Create an in-memory SQLite database with test tables."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
            )
        )
        conn.execute(
            text("INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@test.com')")
        )
        conn.execute(
            text("INSERT INTO users (id, name, email) VALUES (2, 'Bob', 'bob@test.com')")
        )
        conn.execute(
            text("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)")
        )
        conn.execute(
            text("INSERT INTO posts (id, user_id, title) VALUES (1, 1, 'Hello World')")
        )
        conn.commit()
    return eng


class TestListTables:
    def test_returns_all_tables(self, engine: Engine) -> None:
        tables = list_tables(engine)
        assert "users" in tables
        assert "posts" in tables

    def test_sorted(self, engine: Engine) -> None:
        tables = list_tables(engine)
        assert tables == sorted(tables)


class TestGetColumns:
    def test_users_columns(self, engine: Engine) -> None:
        cols = get_columns(engine, "users")
        names = [c["name"] for c in cols]
        assert "id" in names
        assert "name" in names
        assert "email" in names

    def test_column_has_type(self, engine: Engine) -> None:
        cols = get_columns(engine, "users")
        for col in cols:
            assert "type" in col


class TestGetSampleRows:
    def test_returns_dataframe(self, engine: Engine) -> None:
        df = get_sample_rows(engine, "users", limit=2)
        assert len(df) == 2
        assert "name" in df.columns

    def test_limit(self, engine: Engine) -> None:
        df = get_sample_rows(engine, "users", limit=1)
        assert len(df) == 1


class TestGetRowCount:
    def test_users_count(self, engine: Engine) -> None:
        assert get_row_count(engine, "users") == 2

    def test_posts_count(self, engine: Engine) -> None:
        assert get_row_count(engine, "posts") == 1


class TestGetSchemaSummary:
    def test_summary_contains_table_names(self, engine: Engine) -> None:
        summary = get_schema_summary(engine)
        assert "users" in summary
        assert "posts" in summary

    def test_summary_contains_columns(self, engine: Engine) -> None:
        summary = get_schema_summary(engine)
        assert "name" in summary
        assert "email" in summary

    def test_summary_contains_row_counts(self, engine: Engine) -> None:
        summary = get_schema_summary(engine)
        assert "2 rows" in summary
