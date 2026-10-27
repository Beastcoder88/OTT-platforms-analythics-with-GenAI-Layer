import sqlite3
import time

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

# ---------- Setup ----------
client = genai.Client()          # reads GEMINI_API_KEY from .env
MODEL = "gemini-3.8-flash"       # keep the model name that worked for you

# ---------- Practice database (lives in memory) ----------
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE sales (region TEXT, amount INTEGER)")
conn.executemany(
    "INSERT INTO sales VALUES (?, ?)",
    [("Delhi", 500), ("Mumbai", 300), ("Delhi", 700), ("Chennai", 200), ("Mumbai", 450)],
)

# ---------- What the model is told ----------
SCHEMA = "Table: sales(region TEXT, amount INTEGER)"

SYSTEM = (
    "You are a SQL assistant for a SQLite database. "
    "Output exactly one valid SELECT query. "
    "No explanation, no markdown, no comments. "
    "Use only the tables and columns given in the schema."
)


# ---------- Question -> SQL ----------
def question_to_sql(question):
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=f"{SCHEMA}\n\nQuestion: {question}",
                config=types.GenerateContentConfig(system_instruction=SYSTEM),
            )
            text = response.text
            if not text:
                print("Model returned no text")
                return None
            # remove ```sql fences if the model adds them anyway
            return text.replace("```sql", "").replace("```", "").strip()

        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print("Rate limit hit, waiting 30 seconds...")
                time.sleep(30)
            else:
                print("API error:", str(e)[:300])
                return None


# ---------- Safety check ----------
def is_safe(sql):
    cleaned = sql.strip().rstrip(";").lower()
    if not cleaned.startswith("select"):
        return False
    if ";" in cleaned:        # blocks multiple statements like "SELECT ...; DROP ..."
        return False
    return True


# ---------- Run one question end to end ----------
def run_question(question):
    print("Q:", question)

    sql = question_to_sql(question)
    if sql is None:
        print()
        return

    print("SQL:", sql)

    if not is_safe(sql):
        print("Blocked: only a single SELECT query is allowed\n")
        return

    try:
        rows = conn.execute(sql).fetchall()
        print("Result:", rows, "\n")
    except Exception as e:
        print("SQL error:", e, "\n")


# ---------- Questions to test ----------
# Free-tier limits are low, so test only a few at a time.
# Uncomment more when you need them.
QUESTIONS = [
    "Which region has the highest total amount?",
    "Show regions with total amount above 500.",
    # "Rank regions by total amount.",
    # "How many orders were placed in Delhi?",
    # "Delete all rows from sales.",          # guardrail test
    # "Who is doing best?",                   # vague question test
    # "Show total amount by customer.",       # missing column test
]

if __name__ == "__main__":
    for q in QUESTIONS:
        run_question(q)
        time.sleep(5)    # pause between calls to avoid rate limits