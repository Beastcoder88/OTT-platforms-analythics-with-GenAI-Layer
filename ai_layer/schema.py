"""Builds the text description of the database that is sent to the AI model."""
from sqlalchemy import text

# Columns whose allowed values are read from the database, so the prompt stays
# correct if the data changes (for example after swapping in real titles).
CATEGORICAL_COLUMNS = {
    "users": ["region", "preferred_language", "subscription_tier"],
    "content": ["genre", "language", "content_type"],
    "viewership": ["device"],
}

BASE_SCHEMA = """\
DATABASE: MySQL 8, schema ott_analytics. SIMULATED data for a streaming platform.

TABLE users  -- one row per subscriber
  user_id             INT  (primary key)
  region              VARCHAR
  preferred_language  VARCHAR
  subscription_tier   VARCHAR
  signup_date         DATE
  cancel_date         DATE, NULL when the user is still active

TABLE content  -- one row per title
  content_id    INT  (primary key)
  title         VARCHAR
  genre         VARCHAR
  language      VARCHAR
  content_type  VARCHAR
  release_year  INT

TABLE viewership  -- one row per watch session (fact table)
  view_id        INT  (primary key)
  user_id        INT  (foreign key -> users.user_id)
  content_id     INT  (foreign key -> content.content_id)
  watch_date     DATE
  watch_minutes  INT
  device         VARCHAR

JOINS
  viewership.user_id = users.user_id
  viewership.content_id = content.content_id

BUSINESS RULES
  - A user is churned when users.cancel_date IS NOT NULL, and active when it IS NULL.
  - Churn rate = churned users / all users, as a percentage from 0 to 100.
  - Watch time = SUM(viewership.watch_minutes). Divide by 60 for hours.
  - All data covers 2025-01-01 to 2025-12-31. Treat 2025-12-31 as "today".
    NEVER use CURDATE(), NOW() or CURRENT_DATE. "Last month" means December 2025,
    "this year" means 2025, "last quarter" means Q4 2025.
  - The cricket event window is 2025-04-10 to 2025-04-24. Cricket and live matches
    are content with content_type = 'Live Sport'.
  - Round averages and percentages to at most 2 decimals and use readable column names.
"""


def build_schema(engine, max_values=40):
    """Return the schema text plus the allowed values of each category column."""
    lines = ["ALLOWED VALUES (use these exact spellings):"]
    with engine.connect() as conn:
        for table, columns in CATEGORICAL_COLUMNS.items():
            for col in columns:
                rows = conn.execute(
                    text(f"SELECT DISTINCT {col} FROM {table} ORDER BY 1 LIMIT {max_values}")
                ).fetchall()
                values = ", ".join(str(r[0]) for r in rows)
                lines.append(f"  {table}.{col}: {values}")
    return BASE_SCHEMA + "\n" + "\n".join(lines) + "\n"