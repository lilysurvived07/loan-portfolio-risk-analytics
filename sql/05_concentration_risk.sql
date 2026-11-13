-- =====================================================================
-- 05_concentration_risk.sql
-- How concentrated is exposure? Top 10% of loans by outstanding balance,
-- their share of total book, and their charge-off rate to date.
-- Demonstrates NTILE and conditional aggregation.
-- =====================================================================

WITH latest AS (
    SELECT p.loan_id,
           p.status,
           p.remaining_balance
    FROM payments p
    JOIN (SELECT loan_id, MAX(payment_date) AS last_date
          FROM payments GROUP BY loan_id) lp
      ON lp.loan_id = p.loan_id AND lp.last_date = p.payment_date
),
ranked AS (
    SELECT loan_id, status, remaining_balance,
           NTILE(10) OVER (ORDER BY remaining_balance DESC) AS decile
    FROM latest
)
SELECT
    decile,
    COUNT(*)                                                              AS n_loans,
    ROUND(SUM(remaining_balance) / 1e6, 2)                                 AS outstanding_usd_m,
    ROUND(100.0 * SUM(remaining_balance) /
          (SELECT SUM(remaining_balance) FROM latest), 2)                  AS pct_of_book,
    ROUND(100.0 * SUM(CASE WHEN status = 'charged_off' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                             AS charge_off_rate_pct
FROM ranked
GROUP BY decile
ORDER BY decile;
