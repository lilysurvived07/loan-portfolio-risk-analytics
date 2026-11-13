-- =====================================================================
-- 03_vintage_curve.sql
-- Vintage / cohort analysis.
-- For each origination quarter, what share of the cohort is delinquent
-- (any status worse than 'current') at every months-on-book point?
-- This is THE classic loan-portfolio chart.
-- =====================================================================

WITH vintage AS (
    SELECT  l.loan_id,
            CAST(strftime('%Y', l.origination_date) AS INTEGER)            AS orig_year,
            CAST(((CAST(strftime('%m', l.origination_date) AS INTEGER) - 1) / 3) + 1
                 AS INTEGER)                                                AS orig_q
    FROM loans l
),
labelled AS (
    SELECT  p.loan_id,
            p.months_on_book,
            v.orig_year,
            v.orig_q,
            CASE WHEN p.status IN ('30dpd','60dpd','90dpd','charged_off') THEN 1 ELSE 0 END
                                                                            AS is_dq
    FROM payments p
    JOIN vintage v USING (loan_id)
)
SELECT
    orig_year || '-Q' || orig_q          AS vintage,
    months_on_book,
    COUNT(*)                              AS n_obs,
    ROUND(100.0 * AVG(is_dq), 2)          AS dq_rate_pct
FROM labelled
WHERE months_on_book BETWEEN 1 AND 24
GROUP BY vintage, months_on_book
ORDER BY vintage, months_on_book;
