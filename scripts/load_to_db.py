import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "generated"
DDL_FILE = ROOT / "sql" / "01_create_tables.sql"
DB_NAME = os.getenv("DB_NAME", "ott_analytics")

if not os.getenv("DB_PASSWORD"):
    raise SystemExit("DB_PASSWORD is missing in .env")


def make_url(database=None):
    return URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=database,
        query={"charset": "utf8mb4"},
    )


# 1. Create the database and empty tables (this also wipes old data)
server_engine = create_engine(make_url())
statements = [s.strip() for s in DDL_FILE.read_text(encoding="utf-8").split(";") if s.strip()]
with server_engine.begin() as conn:
    for stmt in statements:
        conn.execute(text(stmt))
print("Tables created")

# 2. Load the CSVs (parents first, because of the foreign keys)
engine = create_engine(make_url(DB_NAME))

users = pd.read_csv(DATA / "users.csv", parse_dates=["signup_date", "cancel_date"])
content = pd.read_csv(DATA / "content.csv")
views = pd.read_csv(DATA / "viewership.csv", parse_dates=["watch_date"])

for name, df in [("users", users), ("content", content), ("viewership", views)]:
    df.to_sql(name, engine, if_exists="append", index=False, chunksize=5000)
    print(f"Loaded {len(df):,} rows into {name}")

# 3. Row counts straight from the database
with engine.connect() as conn:
    for t in ["users", "content", "viewership"]:
        print(t, "->", conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar())