# Schema Design: OTT Viewership & Subscriber Analytics

Simulated data, modeled on a large Indian streaming platform. Not real company data.

## Star schema
users (1) ---- (M) viewership (M) ---- (1) content

## Tables

### users
| Column | Type | Notes |
|---|---|---|
| user_id | INT PK | |
| region | VARCHAR(30) | |
| preferred_language | VARCHAR(20) | |
| subscription_tier | VARCHAR(20) | Free / Mobile / Standard / Premium (simulated) |
| signup_date | DATE | |
| cancel_date | DATE | NULL = still active |

### content
| Column | Type | Notes |
|---|---|---|
| content_id | INT PK | |
| title | VARCHAR(150) | |
| genre | VARCHAR(40) | includes Sports |
| language | VARCHAR(20) | |
| content_type | VARCHAR(20) | Movie / Series / Live Sport |
| release_year | INT | |

### viewership
| Column | Type | Notes |
|---|---|---|
| view_id | INT PK | |
| user_id | INT FK -> users | |
| content_id | INT FK -> content | |
| watch_date | DATE | |
| watch_minutes | INT | |
| device | VARCHAR(20) | Mobile / Smart TV / Laptop |

## Data rules
- Users: 5,000
- Viewership rows: about 50,000
- Date range: (your dates)
- Cricket spike window: (your dates), effect: (your numbers)
- Churn target: (your %)
- Tier split: (your numbers)

## Integrity rules
- No viewership before signup_date
- No viewership after cancel_date
- Free tier watches less than Premium