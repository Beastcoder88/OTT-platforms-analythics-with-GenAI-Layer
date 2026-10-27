"""Turn a plain-English question into a safe MySQL SELECT, run it, and return a table."""
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL

from ai_layer.schema import build_schema

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")   # use the model name that worked for you
MAX_ROWS = 500
MAX_QUESTION_CHARS = 300
REPAIR_ON_ERROR = True    # one extra model call if the first query fails to run

SYSTEM_PROMPT = """You are a careful data analyst who writes MySQL 8 queries.
Convert the user's question into exactly ONE read-only query.

Rules:
- Output only the SQL. No explanation, no markdown fences, no comments.
- The query must start with SELECT or WITH.
- Use only the tables and columns in the schema, and the exact category spellings listed.
- Never use CURDATE(), NOW() or CURRENT_DATE. Follow the date rules in the schema.
- Never use the word rank as a column alias (it is reserved in MySQL 8). Use names like genre_rank.
- Give result columns readable aliases and round decimals to at most 2 places.
- Percentages are numbers from 0 to 100, not fractions.
- If the question cannot be answered from this schema (weather, other companies,
  or a request to change or delete data), output exactly: CANNOT_ANSWER
"""

EXAMPLES = """\
EXAMPLES

Question: Which subscription tier has the highest churn rate?
SQL:
SELECT subscription_tier, ROUND(100 * AVG(cancel_date IS NOT NULL), 1) AS churn_rate_pct
FROM users
GROUP BY subscription_tier
ORDER BY churn_rate_pct DESC

Question: Total watch hours by region
SQL:
SELECT u.region, ROUND(SUM(v.watch_minutes) / 60, 1) AS watch_hours
FROM viewership v
JOIN users u ON u.user_id = v.user_id
GROUP BY u.region
ORDER BY watch_hours DESC

Question: How did watch time change month by month?
SQL:
SELECT DATE_FORMAT(watch_date, '%Y-%m') AS watch_month, SUM(watch_minutes) AS total_minutes
FROM viewership
GROUP BY watch_month
ORDER BY watch_month

Question: What are the top 3 genres in each region?
SQL:
WITH region_genre AS (
    SELECT u.region, c.genre, SUM(v.watch_minutes) AS minutes
    FROM viewership v
    JOIN users u ON u.user_id = v.user_id
    JOIN content c ON c.content_id = v.content_id
    GROUP BY u.region, c.genre
),
ranked AS (
    SELECT region, genre, minutes,
           RANK() OVER (PARTITION BY region ORDER BY minutes DESC) AS genre_rank
    FROM region_genre
)
SELECT region, genre, minutes, genre_rank
FROM ranked
WHERE genre_rank <= 3
ORDER BY region, genre_rank

Question: How much higher was daily watch time during the cricket event than on normal days?
SQL:
WITH daily AS (
    SELECT watch_date, SUM(watch_minutes) AS minutes
    FROM viewership
    GROUP BY watch_date
)
SELECT
    ROUND(AVG(CASE WHEN watch_date BETWEEN '2025-04-10' AND '2025-04-24' THEN minutes END)) AS event_avg_daily_minutes,
    ROUND(AVG(CASE WHEN watch_date NOT BETWEEN '2025-04-10' AND '2025-04-24' THEN minutes END)) AS normal_avg_daily_minutes
FROM daily
"""

# Words that should never appear in a read-only analytics query.
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|replace|rename|call|"
    r"load_file|outfile|dumpfile|into|sleep|benchmark|lock|handler|"
    r"information_schema|performance_schema|mysql)\b",
    re.IGNORECASE,
)

_engine = None
_client = None
_schema = None

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "sql_cache.json"


def _load_cache():
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache():
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(_sql_cache, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


_sql_cache = _load_cache()


def _remember(question, sql):
    _sql_cache[question] = sql
    _save_cache()


def _forget(question):
    if _sql_cache.pop(question, None) is not None:
        _save_cache()


# ---------- Connections ----------
def get_engine():
    """Connect with the READ-ONLY MySQL user. This is the real safety net."""
    global _engine
    if _engine is None:
        user = os.getenv("AI_DB_USER")
        password = os.getenv("AI_DB_PASSWORD")
        if not user or not password:
            raise RuntimeError("AI_DB_USER and AI_DB_PASSWORD are missing in .env (use the read-only MySQL user).")
        if user.lower() == "root":
            raise RuntimeError("Do not use root here. Create and use the read-only user (pbi_reader).")
        url = URL.create(
            "mysql+pymysql",
            username=user,
            password=password,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "ott_analytics"),
            query={"charset": "utf8mb4"},
        )
        engine = create_engine(url, pool_pre_ping=True)

        @event.listens_for(engine, "connect")
        def _restrict_session(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("SET SESSION TRANSACTION READ ONLY")
            cur.execute("SET SESSION MAX_EXECUTION_TIME=10000")   # 10 seconds
            cur.close()

        _engine = engine
    return _engine


def get_schema():
    global _schema
    if _schema is None:
        _schema = build_schema(get_engine())
    return _schema


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()     # reads GEMINI_API_KEY from the environment
    return _client


# ---------- Model call ----------
def _call_model(prompt):
    from google.genai import types

    client = _get_client()
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0),
            )
            return (response.text or "").strip()
        except Exception as e:
            message = str(e)
            # Daily quota errors generally will not be fixed by a short retry.
            if "PerDay" in message:
                raise
            if "429" in message and attempt < 2:
                time.sleep(15 * (attempt + 1))    # retry transient per-minute limits
                continue
            raise


def clean_sql(raw):
    sql = (raw or "").strip()
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()
    if sql.lower().startswith("sql:"):
        sql = sql[4:].strip()
    return sql.rstrip(";").strip()


def generate_sql(question):
    if question in _sql_cache:
        return _sql_cache[question]
    prompt = f"{get_schema()}\n{EXAMPLES}\nQuestion: {question}\nSQL:"
    sql = clean_sql(_call_model(prompt))
    _remember(question, sql)
    return sql


def repair_sql(question, bad_sql, error_message):
    prompt = (
        f"{get_schema()}\n{EXAMPLES}\nQuestion: {question}\n"
        f"This query failed in MySQL:\n{bad_sql}\nError: {error_message}\n"
        "Write a corrected query. Output only the SQL.\nSQL:"
    )
    return clean_sql(_call_model(prompt))


# ---------- Safety check ----------
def validate_sql(sql):
    """Return (True, '') if the query looks like a single safe SELECT, else (False, reason)."""
    if not sql:
        return False, "the model returned an empty query."
    if not re.match(r"^\s*(select|with)\b", sql, re.IGNORECASE):
        return False, "only SELECT queries are allowed."
    if ";" in sql:
        return False, "multiple statements are not allowed."
    if "--" in sql or "/*" in sql or "#" in sql:
        return False, "comments are not allowed."
    bad = FORBIDDEN.search(sql)
    if bad:
        return False, f"the query uses a blocked keyword ({bad.group(0)})."
    return True, ""


# ---------- Run the query ----------
def run_query(sql):
    """Execute a validated SELECT. Returns (DataFrame, was_truncated)."""
    with get_engine().connect() as conn:
        result = conn.execute(text(sql.replace(":", r"\:")))   # escape colons so they are not read as parameters
        rows = result.fetchmany(MAX_ROWS + 1)
        columns = list(result.keys())
    truncated = len(rows) > MAX_ROWS
    df = pd.DataFrame([tuple(r) for r in rows[:MAX_ROWS]], columns=columns)
    for col in df.columns:            # MySQL returns Decimal numbers; convert them for charts
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df, truncated


# ---------- The whole pipeline ----------
def ask(question):
    """Run question -> SQL -> checks -> database. Never raises; returns a dict for the UI."""
    q = (question or "").strip()
    result = {"question": q, "sql": None, "df": None, "truncated": False,
              "error": None, "refused": False, "repaired": False, "detail": None}

    if not q:
        result["error"] = "Please type a question."
        return result
    if len(q) > MAX_QUESTION_CHARS:
        result["error"] = f"Please keep the question under {MAX_QUESTION_CHARS} characters."
        return result

    try:
        get_schema()     # check the database login first, so database and AI failures are told apart
    except Exception as e:
        result["error"] = ("The database could not be reached. Check that MySQL is running and that "
                           "AI_DB_USER and AI_DB_PASSWORD in .env are correct.")
        result["detail"] = f"{type(e).__name__}: {str(e)[:1500]}"
        return result

    try:
        sql = generate_sql(q)
    except Exception as e:
        if "PerDay" in str(e):
            result["error"] = ("The free daily limit for this AI model has been used up. Try again after "
                               "it resets, or set a different GEMINI_MODEL in .env.")
        else:
            result["error"] = ("The AI service could not be reached. If the details mention 429, "
                               "you hit the free-tier limit: wait a minute and try again.")
        result["detail"] = f"{type(e).__name__}: {str(e)[:1500]}"
        return result

    if sql.strip().upper() == "CANNOT_ANSWER":
        result["refused"] = True
        result["error"] = ("I can't answer that from this dataset. Try a question about watch time, "
                           "subscribers, churn, genres, regions or devices.")
        return result

    result["sql"] = sql
    ok, reason = validate_sql(sql)
    if not ok:
        _forget(q)
        result["error"] = f"Blocked for safety: {reason}"
        return result

    try:
        result["df"], result["truncated"] = run_query(sql)
        return result
    except Exception as e:
        msg = str(e).splitlines()[0][:300] if str(e) else type(e).__name__
        result["detail"] = f"{type(e).__name__}: {msg}"

    if REPAIR_ON_ERROR:                      # one self-correction attempt
        try:
            fixed = repair_sql(q, sql, result["detail"])
            ok, _ = validate_sql(fixed)
            if ok:
                result["df"], result["truncated"] = run_query(fixed)
                result["sql"], result["repaired"] = fixed, True
                _remember(q, fixed)
                return result
        except Exception as e:
            result["detail"] += f" | repair failed: {type(e).__name__}"

    _forget(q)
    result["error"] = "The query could not be run. Try rephrasing the question."
    return result