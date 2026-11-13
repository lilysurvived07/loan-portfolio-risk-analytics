"""
Generate the synthetic loan-portfolio dataset.
Produces two tables:

  loans     — one row per loan (origination snapshot)
  payments  — one row per loan-month (payment performance history)

Both are written as CSVs and as a SQLite database, so the SQL files in /sql
can be executed directly with `sqlite3 portfolio.db < sql/03_...sql`.
"""

from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

RNG = np.random.default_rng(2024)


def _origination_months(n: int) -> pd.Series:
    months = pd.date_range("2022-01-01", "2025-12-01", freq="MS")
    weights = np.linspace(1, 2, len(months))  # growing book
    weights = weights / weights.sum()
    picks = RNG.choice(len(months), size=n, p=weights)
    return pd.Series(months[picks])


def generate_loans(n: int = 8_000) -> pd.DataFrame:
    grade = RNG.choice(list("ABCDE"), n, p=[.30, .30, .22, .12, .06])
    loan_amount = (RNG.lognormal(9.2, 0.7, n) * np.where(grade < "C", 1.1, 0.9)).round(2)
    term_months = RNG.choice([24, 36, 48, 60, 72], n, p=[.10, .35, .20, .25, .10])
    rate_by_grade = {"A": 6.5, "B": 9.0, "C": 12.5, "D": 17.0, "E": 23.0}
    interest_rate = np.array([rate_by_grade[g] + RNG.normal(0, 1.0) for g in grade]).round(2)
    purpose = RNG.choice(
        ["debt_consolidation", "auto", "home_improvement", "small_business",
         "credit_card", "medical", "other"],
        n, p=[.35, .15, .12, .08, .15, .07, .08],
    )
    origination_date = _origination_months(n)
    monthly_payment = (loan_amount / term_months *
                       (1 + interest_rate / 100 / 12 * term_months / 2)).round(2)

    return pd.DataFrame({
        "loan_id": np.arange(1, n + 1),
        "origination_date": origination_date.dt.strftime("%Y-%m-%d"),
        "grade": grade,
        "purpose": purpose,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "term_months": term_months,
        "monthly_payment": monthly_payment,
    })


def generate_payments(loans: pd.DataFrame, snapshot_date: str = "2026-04-01") -> pd.DataFrame:
    """Generate monthly performance rows up to snapshot_date."""
    snap = pd.Timestamp(snapshot_date)
    base_default_prob = {"A": 0.003, "B": 0.008, "C": 0.018, "D": 0.040, "E": 0.085}
    records = []

    for row in loans.itertuples(index=False):
        orig = pd.Timestamp(row.origination_date)
        # months between origination and snapshot, capped by term
        elapsed = (snap.year - orig.year) * 12 + (snap.month - orig.month)
        n_months = min(elapsed, row.term_months)
        if n_months <= 0:
            continue

        balance = row.loan_amount
        current_status = "current"  # current, 30dpd, 60dpd, 90dpd, charged_off, paid_off
        for m in range(1, n_months + 1):
            if current_status == "charged_off" or current_status == "paid_off":
                break

            # Probability of slipping to delinquency this month
            p_default = base_default_prob[row.grade]
            # Curing transitions
            if current_status == "current":
                roll = RNG.uniform()
                if roll < p_default:
                    new_status = "30dpd"
                else:
                    new_status = "current"
            elif current_status == "30dpd":
                roll = RNG.uniform()
                if roll < 0.55:
                    new_status = "current"
                elif roll < 0.95:
                    new_status = "60dpd"
                else:
                    new_status = "30dpd"
            elif current_status == "60dpd":
                roll = RNG.uniform()
                if roll < 0.25:
                    new_status = "current"
                elif roll < 0.85:
                    new_status = "90dpd"
                else:
                    new_status = "60dpd"
            elif current_status == "90dpd":
                roll = RNG.uniform()
                if roll < 0.15:
                    new_status = "current"
                elif roll < 0.70:
                    new_status = "charged_off"
                else:
                    new_status = "90dpd"

            paid = row.monthly_payment if new_status == "current" else 0.0
            balance = max(0.0, balance - paid * 0.45)  # ~45% goes to principal (rough)
            if balance <= 1 and new_status == "current":
                new_status = "paid_off"

            month_date = (orig + pd.DateOffset(months=m)).strftime("%Y-%m-%d")
            records.append((row.loan_id, month_date, m, new_status, round(paid, 2), round(balance, 2)))
            current_status = new_status

    df = pd.DataFrame.from_records(
        records,
        columns=["loan_id", "payment_date", "months_on_book", "status", "amount_paid", "remaining_balance"],
    )
    return df


def main() -> None:
    print("Generating loans...")
    loans = generate_loans(8_000)
    loans.to_csv(DATA_DIR / "loans.csv", index=False)
    print(f"  {len(loans):,} loans -> {DATA_DIR/'loans.csv'}")

    print("Generating monthly payment history (this takes ~20s)...")
    payments = generate_payments(loans)
    payments.to_csv(DATA_DIR / "payments.csv", index=False)
    print(f"  {len(payments):,} payment rows -> {DATA_DIR/'payments.csv'}")

    db_path = DATA_DIR / "portfolio.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    loans.to_sql("loans", conn, index=False)
    payments.to_sql("payments", conn, index=False)
    conn.executescript("""
        CREATE INDEX ix_loans_grade ON loans(grade);
        CREATE INDEX ix_payments_loan ON payments(loan_id);
        CREATE INDEX ix_payments_date ON payments(payment_date);
    """)
    conn.close()
    print(f"  SQLite database -> {db_path}")


if __name__ == "__main__":
    main()
