-- =====================================================================
-- 02_portfolio_summary.sql
-- Headline portfolio KPIs by grade, with weighted-average rates and
-- charge-off rate to date. Uses a single CTE chain — readable, no joins
-- by the application layer needed.
-- =====================================================================

WITH latest_status AS (
    -- Most-recent monthly observation per loan
    SELECT p.loan_id,
           p.status                                       AS current_status,
           p.remaining_balance                            AS current_balance
    FROM   payments p
    JOIN  (SELECT loan_id, MAX(payment_date) AS last_date
           FROM payments GROUP BY loan_id) last
      ON  last.loan_id   = p.loan_id
     AND  last.last_date = p.payment_date
),
joined AS (
    SELECT l.grade,
           l.loan_amount,
           l.interest_rate,
           ls.current_status,
           ls.current_balance,
           CASE WHEN ls.current_status = 'charged_off' THEN 1 ELSE 0 END AS is_charged_off
    FROM loans l
    JOIN latest_status ls USING (loan_id)
)
SELECT
    grade,
    COUNT(*)                                                                       AS n_loans,
    ROUND(SUM(loan_amount) / 1e6, 2)                                                AS originated_usd_m,
    ROUND(SUM(current_balance) / 1e6, 2)                                            AS outstanding_usd_m,
    ROUND(SUM(loan_amount * interest_rate) / NULLIF(SUM(loan_amount), 0), 2)        AS wavg_rate_pct,
    SUM(is_charged_off)                                                             AS charged_off_loans,
    ROUND(100.0 * SUM(is_charged_off) / COUNT(*), 2)                                AS charge_off_rate_pct
FROM joined
GROUP BY grade
ORDER BY grade;
