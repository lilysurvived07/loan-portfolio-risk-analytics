-- =====================================================================
-- 04_status_migration.sql
-- Roll-rate matrix — for every status in month T, what was the status
-- in month T+1? Uses LAG() so a single self-scan is enough.
-- =====================================================================

WITH ordered AS (
    SELECT  loan_id,
            payment_date,
            status,
            LAG(status) OVER (PARTITION BY loan_id ORDER BY payment_date) AS prev_status
    FROM payments
)
SELECT
    prev_status                                            AS from_status,
    status                                                 AS to_status,
    COUNT(*)                                               AS transitions,
    ROUND(100.0 * COUNT(*) /
          SUM(COUNT(*)) OVER (PARTITION BY prev_status), 2) AS pct_of_origin
FROM ordered
WHERE prev_status IS NOT NULL
GROUP BY prev_status, status
ORDER BY prev_status, to_status;
