-- =====================================================================
-- 01_schema.sql
-- Loan portfolio analytics — table definitions.
-- Compatible with PostgreSQL and SQLite. Run once before everything else.
-- =====================================================================

CREATE TABLE IF NOT EXISTS loans (
    loan_id           INTEGER PRIMARY KEY,
    origination_date  DATE      NOT NULL,
    grade             TEXT      NOT NULL CHECK (grade IN ('A','B','C','D','E')),
    purpose           TEXT      NOT NULL,
    loan_amount       NUMERIC   NOT NULL,
    interest_rate     NUMERIC   NOT NULL,
    term_months       INTEGER   NOT NULL,
    monthly_payment   NUMERIC   NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    loan_id            INTEGER NOT NULL,
    payment_date       DATE    NOT NULL,
    months_on_book     INTEGER NOT NULL,
    status             TEXT    NOT NULL
                         CHECK (status IN ('current','30dpd','60dpd','90dpd','charged_off','paid_off')),
    amount_paid        NUMERIC NOT NULL,
    remaining_balance  NUMERIC NOT NULL,
    PRIMARY KEY (loan_id, payment_date),
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
);

CREATE INDEX IF NOT EXISTS ix_loans_grade   ON loans(grade);
CREATE INDEX IF NOT EXISTS ix_payments_loan ON payments(loan_id);
CREATE INDEX IF NOT EXISTS ix_payments_date ON payments(payment_date);
