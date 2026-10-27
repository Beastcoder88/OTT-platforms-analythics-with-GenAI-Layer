# OTT Viewership & Subscriber Analytics, with a plain-English query assistant

> Independent student project. Not affiliated with or endorsed by any streaming company. All data is simulated.

![demo](docs/demo.gif)

## What this is
A case study of the analytics a streaming platform's business team needs: who watches what,
who churns, and how a live cricket event changes behavior. Inspired by large Indian OTT platforms.

## Highlights
- Star schema in MySQL: users, content, viewership ([N] users, [N] watch sessions)
- 2-page Power BI dashboard: Overview, and Subscribers & Churn
- Streamlit question box: Gemini writes SQL, a validator and a read-only database user protect the data
- Checked against hand-written SQL: [N of N] test questions correct (docs/ai_test_log.md)

## Architecture
```text
Python generators -> MySQL (star schema) -> Power BI dashboard
question -> Gemini -> SQL -> validator -> read-only DB user -> table/chart (Streamlit)
```

## The data (simulated by design)
Generated with Python. I built in: churn that depends on subscription tier, a two-week
cricket-event spike in watch time, and event-window signups who churn faster.
The findings below exist because I designed them. They demonstrate the workflow, not real-world facts.
Integrity rules (no viewing before signup or after cancellation) are checked in SQL.

## Findings
- Overall churn [N]%; highest tier [tier] ([N]%), lowest [tier] ([N]%)
- Daily watch time in the event window was [N]x normal days
- Event-window signups churned within 60 days at [N]% vs [N]% for other signups

## The AI layer and its safety
1. Prompt rules: one SELECT only, or CANNOT_ANSWER
2. Validator: blocks multiple statements, comments, and dangerous keywords
3. Read-only MySQL user, read-only session, 10-second timeout, 500-row cap
Known limits: AI can write valid but wrong SQL (so the app shows the SQL), the validator is a
keyword filter, and free-tier API quota is small.

## Run it yourself
1. `pip install -r requirements.txt`, copy `.env.example` to `.env` and fill it in
2. Create the MySQL database and tables: `sql/01_create_tables.sql`
3. `python scripts/generate_users.py`, then `generate_content.py`, `generate_viewership.py`, `load_to_db.py`
4. Create the read-only user (`GRANT SELECT` only)
5. `streamlit run app/streamlit_app.py`

## Limitations and next steps
Simulated data; no scheduled refresh; runs locally; live matches have no individual dates.
Next: scheduled pipeline, data-quality alerts, monitoring of AI answers.
