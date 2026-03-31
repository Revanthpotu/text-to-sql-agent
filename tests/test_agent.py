"""Integration tests for the SQL agent using a sample SQLite database.

These tests verify the full pipeline: schema inspection -> LLM call ->
safety validation -> SQL execution.  They require a working LLM backend
(Ollama or OpenAI) and are therefore marked as integration tests.

Run with:
    pytest tests/test_agent.py -v

Skip if no LLM is configured:
    pytest tests/test_agent.py -v -k "not integration"
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Check whether an LLM backend is available
_HAS_LLM = bool(os.getenv("OLLAMA_MODEL") or os.getenv("OPENAI_API_KEY"))

skip_no_llm = pytest.mark.skipif(
    not _HAS_LLM,
    reason="No LLM configured (set OLLAMA_MODEL or OPENAI_API_KEY).",
)

# Ensure sample database exists
SAMPLE_DB = Path(__file__).resolve().parent.parent / "sample_ecommerce.db"


@pytest.fixture(autouse=True)
def _ensure_sample_db() -> None:
    """Create the sample database if it doesn't exist."""
    if not SAMPLE_DB.exists():
        from database.sample_data import create_database

        create_database(SAMPLE_DB)


DB_URL = f"sqlite:///{SAMPLE_DB}"


@skip_no_llm
class TestAskQuestion:
    """Integration tests that hit the real LLM."""

    def test_count_customers(self) -> None:
        from agent.sql_agent import ask_question

        result = ask_question("How many customers are there?", DB_URL)
        assert result["error"] is None, result["error"]
        assert result["sql_query"], "Expected a SQL query to be generated"
        assert "SELECT" in result["sql_query"].upper()

    def test_top_products_by_price(self) -> None:
        from agent.sql_agent import ask_question

        result = ask_question("What are the top 5 most expensive products?", DB_URL)
        assert result["error"] is None, result["error"]
        assert result["sql_query"], "Expected a SQL query"

    def test_total_revenue(self) -> None:
        from agent.sql_agent import ask_question

        result = ask_question("What is the total revenue from completed orders?", DB_URL)
        assert result["error"] is None, result["error"]
        assert result["sql_query"], "Expected a SQL query"


class TestSafetyIntegration:
    """Verify that destructive requests are blocked even through the agent."""

    def test_delete_blocked(self) -> None:
        """Direct safety check — doesn't need an LLM."""
        from agent.safety import validate_sql

        is_safe, _ = validate_sql("DELETE FROM customers WHERE id = 1")
        assert is_safe is False

    def test_drop_blocked(self) -> None:
        from agent.safety import validate_sql

        is_safe, _ = validate_sql("DROP TABLE customers")
        assert is_safe is False
