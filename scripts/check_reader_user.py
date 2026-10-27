import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

user = os.getenv("AI_DB_USER")
password = os.getenv("AI_DB_PASSWORD")
if not user or not password:
    raise SystemExit("AI_DB_USER or AI_DB_PASSWORD is missing in .env")

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=user,
    password=password,
    database=os.getenv("DB_NAME", "ott_analytics"),
)
cur = conn.cursor()

cur.execute("SELECT CURRENT_USER()")
print("Logged in as:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM users")
print("Users:", cur.fetchone()[0])

try:
    cur.execute("DELETE FROM users WHERE user_id = -1")
    conn.rollback()
    print("PROBLEM: the DELETE was allowed. This account is NOT read-only.")
except pymysql.MySQLError as e:
    print("Good, the DELETE was refused:", e.args)

conn.close()