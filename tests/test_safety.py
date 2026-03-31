"""Tests for the SQL safety validator."""

from __future__ import annotations

import pytest

from agent.safety import validate_sql


class TestValidateSQL:
    """Ensure the safety validator blocks dangerous queries."""

    # ---- blocked queries ------------------------------------------------

    @pytest.mark.parametrize(
        "sql",
        [
            "DROP TABLE customers;",
            "drop table customers;",
            "DROP   TABLE IF EXISTS customers",
            "DELETE FROM orders WHERE id = 1;",
            "delete from orders",
            "UPDATE customers SET name = 'x' WHERE id = 1;",
            "update customers set name='x'",
            "INSERT INTO customers (name) VALUES ('test');",
            "insert into customers (name) values ('test')",
            "TRUNCATE TABLE orders;",
            "truncate table orders",
            "ALTER TABLE customers ADD COLUMN age INT;",
            "CREATE TABLE evil (id INT);",
            "GRANT ALL ON customers TO public;",
            "REVOKE SELECT ON customers FROM public;",
        ],
    )
    def test_blocks_dangerous_queries(self, sql: str) -> None:
        is_safe, reason = validate_sql(sql)
        assert is_safe is False, f"Should have blocked: {sql}"
        assert "Blocked" in reason or "not allowed" in reason.lower()

    # ---- allowed queries ------------------------------------------------

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM customers;",
            "select * from customers",
            "SELECT COUNT(*) FROM orders WHERE status = 'completed';",
            "WITH cte AS (SELECT id FROM products) SELECT * FROM cte;",
            "SELECT c.name, SUM(o.total_amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name;",
            "EXPLAIN SELECT * FROM customers;",
        ],
    )
    def test_allows_safe_queries(self, sql: str) -> None:
        is_safe, reason = validate_sql(sql)
        assert is_safe is True, f"Should have allowed: {sql} — {reason}"

    # ---- edge cases -----------------------------------------------------

    def test_empty_query(self) -> None:
        is_safe, reason = validate_sql("")
        assert is_safe is False

    def test_whitespace_query(self) -> None:
        is_safe, reason = validate_sql("   ")
        assert is_safe is False

    def test_non_select_statement(self) -> None:
        is_safe, reason = validate_sql("SHOW TABLES;")
        assert is_safe is False

    def test_mixed_case_drop(self) -> None:
        is_safe, _ = validate_sql("DrOp TaBlE customers;")
        assert is_safe is False

    def test_subquery_with_delete(self) -> None:
        """A SELECT that contains a DELETE subquery should be blocked."""
        sql = "SELECT * FROM customers WHERE id IN (DELETE FROM orders RETURNING customer_id);"
        is_safe, _ = validate_sql(sql)
        assert is_safe is False
