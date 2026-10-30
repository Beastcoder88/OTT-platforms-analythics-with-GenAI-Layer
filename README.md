⁷# OTT Viewership & Subscriber Analytics, with a plain-English query assistant

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
Overall churn: 16.8%. Highest tier: Free (21.2), lowest: Premium (10.1%).
Churn by region: ranges from 15% (Delhi) to 19.3% (Kolkata). No regional effect was built into the simulation, so this gap is likely random variation; churn is driven by tier, not region.
Cricket spike: avg daily minutes 24,229 in the spike window vs 8,033 on normal days (x3.02).
Live sport share of minutes: 6.4% on normal days vs 83.3% during the spike.
Spike-window signups churned within 60 days at 49.8% vs 1.5% for other signups.
Top genre overall: documentary (607,371 min), with Drama a close second (549,088 min). Engagement rises from Free to Premium: minutes per viewer 411 -> 632 -> 910 -> 1,152 (Free, Mobile, Standard, Premium); avg session 55.5 -> 72.3 min.
Caveat: data is simulated, so these effects exist because I designed them.

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
