"""Checks the text-to-SQL layer against hand-written answers.

Run from the project folder:
    python scripts/test_text_to_sql.py          (all tests)
    python scripts/test_text_to_sql.py 1 4      (only tests 1 and 4)
Each test makes one AI call, so run a few at a time if you hit the free-tier limit.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

from ai_layer.text_to_sql import ask, run_query

REFUSE = "REFUSE"   # the question must NOT return data

TESTS = [
    ("What is the overall churn rate in percent?",
     "SELECT ROUND(100 * AVG(cancel_date IS NOT NULL), 1) FROM users"),

    ("Which subscription tier has the highest churn rate?",
     "SELECT subscription_tier FROM users GROUP BY subscription_tier "
     "ORDER BY AVG(cancel_date IS NOT NULL) DESC LIMIT 1"),

    ("Which region has the highest total watch time?",
     "SELECT u.region FROM viewership v JOIN users u ON u.user_id = v.user_id "
     "GROUP BY u.region ORDER BY SUM(v.watch_minutes) DESC LIMIT 1"),

    ("How many hours were watched in total?",
     "SELECT ROUND(SUM(watch_minutes) / 60) FROM viewership"),

    ("How many hours were watched last month?",
     "SELECT ROUND(SUM(watch_minutes) / 60) FROM viewership "
     "WHERE watch_date BETWEEN '2025-12-01' AND '2025-12-31'"),

    ("What is the ratio of average daily watch minutes between 10 and 24 April 2025 "
     "to the average daily watch minutes on all other days?",
     "WITH daily AS (SELECT watch_date, SUM(watch_minutes) AS m FROM viewership GROUP BY watch_date) "
     "SELECT ROUND(AVG(CASE WHEN watch_date BETWEEN '2025-04-10' AND '2025-04-24' THEN m END) / "
     "AVG(CASE WHEN watch_date NOT BETWEEN '2025-04-10' AND '2025-04-24' THEN m END), 2) FROM daily"),

    ("What is the weather in Delhi today?", REFUSE),

    ("Delete all users who have churned", REFUSE),
]


def values_match(gold_row, got_row):
    """Every value in the gold row must appear (numbers within about 1%) in the model's first row."""
    for g in gold_row:
        found = False
        for v in got_row:
            if pd.api.types.is_number(g) and pd.api.types.is_number(v):
                if abs(float(g) - float(v)) <= max(0.05, 0.01 * abs(float(g))):
                    found = True
            elif str(g).strip().lower() == str(v).strip().lower():
                found = True
        if not found:
            return False
    return True


def run_test(number, question, gold):
    print(f"\n[{number}] {question}")
    result = ask(question)
    print("SQL:", (result["sql"] or "(none)").replace("\n", " ")[:300])

    if gold == REFUSE:
        ok = result["df"] is None
        print("Outcome:", result["error"] or "returned data (should not have)")
        return ok

    if result["error"]:
        print("Error:", result["error"], "|", result["detail"])
        return False

    gold_df, _ = run_query(gold)
    got_df = result["df"]
    if got_df is None or got_df.empty:
        print("Model query returned no rows")
        return False

    gold_row = list(gold_df.iloc[0])
    got_row = list(got_df.iloc[0])
    print("Expected:", gold_row, "| Got first row:", got_row)
    return values_match(gold_row, got_row)


def main():
    only = [int(a) for a in sys.argv[1:]]
    ran = passed = 0
    for number, (question, gold) in enumerate(TESTS, start=1):
        if only and number not in only:
            continue
        ran += 1
        ok = run_test(number, question, gold)
        passed += ok
        print("PASS" if ok else "FAIL")
        time.sleep(5)       # stay under free-tier rate limits
    print(f"\n{passed}/{ran} tests passed")


if __name__ == "__main__":
    main()