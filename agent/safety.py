"""SQL safety validator — blocks destructive operations before execution."""

from __future__ import annotations

import re

# Statements that must never be executed
_BLOCKED_KEYWORDS: list[str] = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "REPLACE",
    "CALL",
]

# Pre-compiled pattern: match any blocked keyword as a whole word (case-insensitive)
_BLOCKED_PATTERN: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(_BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """Check whether *sql* is safe to run.

    Only ``SELECT`` statements (and ``WITH … SELECT`` CTEs) are allowed.

    Args:
        sql: The SQL string to validate.

    Returns:
        A ``(is_safe, reason)`` tuple.  ``is_safe`` is ``True`` when the
        query may be executed; otherwise ``reason`` explains why it was
        blocked.
    """

    if not sql or not sql.strip():
        return False, "Empty query."

    cleaned = sql.strip().rstrip(";").strip()

    # Check for blocked keywords
    match = _BLOCKED_PATTERN.search(cleaned)
    if match:
        keyword = match.group(1).upper()
        return False, f"Blocked: '{keyword}' statements are not allowed."

    # Must start with SELECT or WITH (for CTEs)
    first_word = cleaned.split()[0].upper()
    if first_word not in ("SELECT", "WITH", "EXPLAIN"):
        return False, (
            f"Only SELECT queries are allowed. Got '{first_word}' statement."
        )

    return True, "Query is safe."
