"""
Text-to-SQL Agent — Streamlit UI

A web interface for asking natural-language questions of a database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()

from agent.safety import validate_sql
from agent.schema_inspector import (
    get_full_schema_context,
    list_tables,
    schema_to_dataframe,
)
from agent.sql_agent import QueryResult, ask
from database.connection import get_engine, test_connection

# ── Page configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon="🔍",
    layout="wide",
)

# ── Session state defaults ───────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history: list[QueryResult] = []


# ── Sidebar — database settings ─────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    use_sample = st.toggle(
        "Use sample SQLite database",
        value=os.getenv("USE_SAMPLE_DB", "true").lower() in ("true", "1", "yes"),
        help="Toggle off to connect to a PostgreSQL database instead.",
    )

    if not use_sample:
        st.subheader("PostgreSQL Connection")
        db_host = st.text_input("Host", value=os.getenv("DB_HOST", "localhost"))
        db_port = st.text_input("Port", value=os.getenv("DB_PORT", "5432"))
        db_name = st.text_input("Database", value=os.getenv("DB_NAME", "ecommerce"))
        db_user = st.text_input("User", value=os.getenv("DB_USER", "postgres"))
        db_password = st.text_input(
            "Password",
            value=os.getenv("DB_PASSWORD", ""),
            type="password",
        )
        # Push values into env so connection.py picks them up
        os.environ["DB_HOST"] = db_host
        os.environ["DB_PORT"] = db_port
        os.environ["DB_NAME"] = db_name
        os.environ["DB_USER"] = db_user
        os.environ["DB_PASSWORD"] = db_password

    st.divider()

    st.subheader("LLM Backend")
    llm_choice = st.radio(
        "Model provider",
        ["Ollama (local)", "OpenAI"],
        index=0,
        help="Ollama is free and runs locally. OpenAI requires an API key.",
    )
    if llm_choice == "Ollama (local)":
        ollama_model = st.text_input(
            "Ollama model",
            value=os.getenv("OLLAMA_MODEL", "llama3.2"),
        )
        os.environ["OLLAMA_MODEL"] = ollama_model
        os.environ.pop("OPENAI_API_KEY", None)
    else:
        openai_key = st.text_input(
            "OpenAI API key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
        )
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key

    st.divider()

    st.subheader("💡 Example Questions")
    example_questions: list[str] = [
        "How many customers do we have?",
        "What are the top 5 products by revenue?",
        "Show orders from New York customers",
        "What is the average order value by status?",
        "Which category has the most products?",
        "List customers who spent more than $200",
        "How many orders were placed each month in 2024?",
        "What are the top 3 cities by number of customers?",
    ]
    for q in example_questions:
        if st.button(q, key=f"ex_{q}", use_container_width=True):
            st.session_state["prefill_question"] = q

# ── Main content ─────────────────────────────────────────────────────
st.title("🔍 Text-to-SQL Agent")
st.caption(
    "Ask questions about your database in plain English. "
    "The agent converts your question to SQL, runs it safely, "
    "and explains the results."
)

# ── Connect to database ─────────────────────────────────────────────
try:
    engine = get_engine(use_sample_db=use_sample)
    ok, msg = test_connection(engine)
except Exception as exc:
    ok, msg = False, str(exc)

if not ok:
    st.error(f"**Database connection failed**\n\n{msg}")
    st.stop()

# ── Schema overview (expandable) ────────────────────────────────────
with st.expander("📊 Database Schema", expanded=False):
    try:
        schema_df = schema_to_dataframe(engine)
        st.dataframe(schema_df, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"Could not load schema: {exc}")

# ── Question input ───────────────────────────────────────────────────
prefill = st.session_state.pop("prefill_question", "")
question = st.text_input(
    "Ask a question about your data:",
    value=prefill,
    placeholder="e.g. What are the top 5 customers by total spend?",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 Run", type="primary", use_container_width=True)
with col2:
    explain_toggle = st.toggle("Generate explanation", value=True)

# ── Run agent ────────────────────────────────────────────────────────
if run_btn and question.strip():
    with st.spinner("Thinking…"):
        result = ask(question, engine, explain=explain_toggle)
        st.session_state.history.insert(0, result)

    if result.error:
        st.error(result.error)
    else:
        # SQL query (expandable)
        with st.expander("🧾 Generated SQL", expanded=True):
            st.code(result.sql_query, language="sql")

        # Results table
        if not result.results_df.empty:
            st.subheader("📋 Results")
            st.dataframe(result.results_df, use_container_width=True, hide_index=True)
            st.caption(f"{len(result.results_df)} row(s) returned")
        else:
            st.info("The query returned no rows.")

        # Explanation
        if result.explanation:
            st.subheader("💬 Explanation")
            st.markdown(result.explanation)

elif run_btn:
    st.warning("Please enter a question first.")

# ── Query history ────────────────────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.subheader("📜 Query History")
    for i, past in enumerate(st.session_state.history[:10]):
        with st.expander(f"{'❌' if past.error else '✅'} {past.question}", expanded=False):
            if past.sql_query:
                st.code(past.sql_query, language="sql")
            if past.error:
                st.error(past.error)
            elif not past.results_df.empty:
                st.dataframe(past.results_df.head(5), use_container_width=True, hide_index=True)
