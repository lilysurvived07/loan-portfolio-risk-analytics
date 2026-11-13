-- =====================================================================
-- 06_first_payment_default.sql
-- First-payment default (FPD) rate by grade and purpose.
-- FPD = loan that goes 30+ DPD within the first 3 payment cycles.
-- One of the earliest leading indicators of underwriting quality.
-- =====================================================================

WITH first_three AS (
    SELECT loan_id,
           MAX(CASE WHEN status IN ('30dpd','60dpd','90dpd','charged_off') THEN 1 ELSE 0 END)
                                                                                AS hit_dq_first_3
    FROM payments
    WHERE months_on_book <= 3
    GROUP BY loan_id
)
SELECT
    l.grade,
    l.purpose,
    COUNT(*)                                                                    AS loans,
    SUM(f.hit_dq_first_3)                                                       AS fpd_events,
    ROUND(100.0 * SUM(f.hit_dq_first_3) / COUNT(*), 2)                          AS fpd_rate_pct
FROM loans l
JOIN first_three f USING (loan_id)
GROUP BY l.grade, l.purpose
HAVING COUNT(*) >= 50
ORDER BY fpd_rate_pct DESC
LIMIT 20;
