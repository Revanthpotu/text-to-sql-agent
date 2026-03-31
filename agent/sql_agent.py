"""Core Text-to-SQL agent powered by LangChain.

The public entry point is :func:`ask_question`, which accepts a natural
language question and a database URL, then returns a dict with the
generated SQL, a results DataFrame, and a plain-English explanation.
"""

from __future__ import annotations

import re
import traceback
from typing import Any

import pandas as pd
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text

from agent.llm_config import get_llm
from agent.prompts import SQL_AGENT_PREFIX
from agent.safety import validate_sql
from agent.schema_inspector import get_schema_summary


def _extract_sql(agent_output: str) -> str:
    """Best-effort extraction of a SQL query from the agent's text output.

    The agent may wrap the SQL in markdown code fences or return it inline.
    This helper strips formatting and returns the raw SQL.

    Args:
        agent_output: Raw text output from the LangChain agent.

    Returns:
        Cleaned SQL string (may be empty if nothing found).
    """

    # Try to find SQL in a code fence
    fence_match = re.search(
        r"```(?:sql)?\s*\n?(.*?)```", agent_output, re.DOTALL | re.IGNORECASE
    )
    if fence_match:
        return fence_match.group(1).strip()

    # Try to find a SELECT/WITH statement
    sql_match = re.search(
        r"((?:SELECT|WITH)\b.*?;)",
        agent_output,
        re.DOTALL | re.IGNORECASE,
    )
    if sql_match:
        return sql_match.group(1).strip()

    # Fallback: try without trailing semicolon
    sql_match = re.search(
        r"((?:SELECT|WITH)\b[^;]+)",
        agent_output,
        re.DOTALL | re.IGNORECASE,
    )
    if sql_match:
        return sql_match.group(1).strip()

    return ""


def ask_question(
    question: str,
    db_url: str,
) -> dict[str, Any]:
    """Convert a natural language *question* into SQL and execute it.

    This is a simplified, robust pipeline that:
    1. Inspects the database schema.
    2. Sends the schema + question to the LLM.
    3. Extracts the SQL from the LLM's response.
    4. Validates the SQL with the safety checker.
    5. Executes the query and returns results.

    Args:
        question: Natural language question from the user.
        db_url: SQLAlchemy database URL.

    Returns:
        A dict with keys ``sql_query``, ``results_df``, ``explanation``,
        and ``error`` (``None`` when successful).
    """

    result: dict[str, Any] = {
        "sql_query": "",
        "results_df": pd.DataFrame(),
        "explanation": "",
        "error": None,
    }

    try:
        engine = create_engine(db_url)
        schema_summary = get_schema_summary(engine)
    except Exception as exc:
        result["error"] = f"Could not connect to the database: {exc}"
        return result

    # Build the prompt
    try:
        llm = get_llm()
    except Exception as exc:
        result["error"] = str(exc)
        return result

    system_message = (
        f"{SQL_AGENT_PREFIX}\n\n"
        f"DATABASE SCHEMA:\n{schema_summary}\n\n"
        "Given the schema above, generate a SQL query that answers the "
        "user's question. Return ONLY:\n"
        "1. The SQL query inside a ```sql code fence.\n"
        "2. A brief explanation of the query and the expected results.\n"
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=question),
        ]
        response = llm.invoke(messages)
        raw_output = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        result["error"] = f"LLM error: {exc}"
        return result

    # Extract SQL
    sql_query = _extract_sql(raw_output)
    result["sql_query"] = sql_query

    if not sql_query:
        # The LLM might have answered directly without SQL
        result["explanation"] = raw_output
        return result

    # Safety check
    is_safe, reason = validate_sql(sql_query)
    if not is_safe:
        result["error"] = f"Query blocked by safety validator: {reason}"
        result["explanation"] = reason
        return result

    # Execute
    try:
        with engine.connect() as conn:
            query_result = conn.execute(text(sql_query))
            rows = query_result.fetchall()
            columns = list(query_result.keys())
            result["results_df"] = pd.DataFrame(rows, columns=columns)
    except Exception as exc:
        result["error"] = f"SQL execution error: {exc}"
        return result

    # Build explanation — use the LLM's own explanation from raw_output
    # Remove the SQL fence from the explanation
    explanation = re.sub(
        r"```(?:sql)?\s*\n?.*?```", "", raw_output, flags=re.DOTALL
    ).strip()
    if not explanation:
        row_count = len(result["results_df"])
        explanation = f"The query returned {row_count} row(s)."
    result["explanation"] = explanation

    return result
