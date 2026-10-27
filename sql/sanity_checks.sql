USE ott_analytics;

-- Row counts
SELECT 'users' AS tbl, COUNT(*) AS n FROM users
UNION ALL SELECT 'content', COUNT(*) FROM content
UNION ALL SELECT 'viewership', COUNT(*) FROM viewership;

-- Watch events before signup (must be 0)
SELECT COUNT(*) AS before_signup
FROM viewership v JOIN users u ON u.user_id = v.user_id
WHERE v.watch_date < u.signup_date;

-- Watch events after cancellation (must be 0)
SELECT COUNT(*) AS after_cancel
FROM viewership v JOIN users u ON u.user_id = v.user_id
WHERE u.cancel_date IS NOT NULL AND v.watch_date > u.cancel_date;

-- Overall churn rate
SELECT ROUND(100 * SUM(CASE WHEN cancel_date IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_pct
FROM users;

-- Date range and watch-minute sanity
SELECT MIN(watch_date), MAX(watch_date), MIN(watch_minutes), MAX(watch_minutes), ROUND(AVG(watch_minutes), 1)
FROM viewership;

-- Does the cricket spike show up in SQL?
SELECT watch_date, SUM(watch_minutes) AS total_minutes
FROM viewership
WHERE watch_date BETWEEN '2025-04-01' AND '2025-05-05'
GROUP BY watch_date
ORDER BY watch_date;

-- A join across all three tables: top genres by watch time
SELECT c.genre, SUM(v.watch_minutes) AS total_minutes
FROM viewership v JOIN content c ON c.content_id = v.content_id
GROUP BY c.genre
ORDER BY total_minutes DESC;