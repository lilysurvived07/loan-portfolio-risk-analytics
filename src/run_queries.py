"""
Run every SQL file in /sql against the SQLite database produced by
generate_data.py, save the results as CSV, and render a few of the
classic portfolio-analytics charts.
"""

from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)
DB = DATA_DIR / "portfolio.db"
sns.set_theme(style="whitegrid", palette="deep")


def _strip_sql_comments(text: str) -> str:
    """Remove --line comments from each line so we can detect SELECT/WITH."""
    out = []
    for line in text.splitlines():
        # strip everything after `--` outside of strings (simple heuristic)
        if "--" in line:
            line = line.split("--", 1)[0]
        out.append(line)
    return "\n".join(out)


def run_query_file(conn, sql_path: Path) -> pd.DataFrame | None:
    raw = sql_path.read_text(encoding="utf-8")
    cleaned = _strip_sql_comments(raw)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    # The "schema" file has DDL only — execute every statement, no rows back.
    if sql_path.name.startswith("01_"):
        for stmt in statements:
            conn.execute(stmt)
        conn.commit()
        return None
    # Otherwise the last SELECT/WITH is the result query.
    select_stmt = next(
        (s for s in reversed(statements)
         if s.upper().lstrip().startswith(("WITH", "SELECT"))),
        None,
    )
    if not select_stmt:
        return None
    return pd.read_sql_query(select_stmt, conn)


def plot_portfolio_summary(df: pd.DataFrame) -> None:
    fig, ax1 = plt.subplots(figsize=(8.5, 5))
    ax2 = ax1.twinx()
    sns.barplot(data=df, x="grade", y="outstanding_usd_m", color="steelblue", ax=ax1)
    ax1.set_ylabel("Outstanding (USD millions)", color="steelblue")
    ax2.plot(df["grade"], df["charge_off_rate_pct"], "o-", color="crimson", lw=2.5,
             label="Charge-off rate")
    ax2.set_ylabel("Charge-off rate (%)", color="crimson")
    ax2.set_ylim(0, max(df["charge_off_rate_pct"]) * 1.4)
    plt.title("Portfolio by credit grade — exposure vs charge-off rate")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "portfolio_summary.png", dpi=130)
    plt.close()


def plot_vintage(df: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 6))
    for vintage, sub in df.groupby("vintage"):
        plt.plot(sub["months_on_book"], sub["dq_rate_pct"], "-", label=str(vintage), alpha=0.8)
    plt.xlabel("Months on book")
    plt.ylabel("Delinquency rate (%)")
    plt.title("Vintage delinquency curves")
    plt.legend(title="Vintage", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "vintage_curves.png", dpi=130)
    plt.close()


def plot_migration(df: pd.DataFrame) -> None:
    order = ["current", "30dpd", "60dpd", "90dpd", "charged_off", "paid_off"]
    pivot = (df.pivot(index="from_status", columns="to_status", values="pct_of_origin")
               .reindex(index=order, columns=order)
               .fillna(0))
    plt.figure(figsize=(8, 6))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues",
                cbar_kws={"label": "% of origin status"})
    plt.title("Roll-rate matrix — status (month T) → status (month T+1)")
    plt.xlabel("To status (T+1)")
    plt.ylabel("From status (T)")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "migration_matrix.png", dpi=130)
    plt.close()


def main() -> None:
    if not DB.exists():
        print("Database not found — run src/generate_data.py first.")
        return
    conn = sqlite3.connect(DB)

    print("Running SQL files in order...\n")
    results: dict[str, pd.DataFrame] = {}
    for sql_path in sorted(SQL_DIR.glob("*.sql")):
        out = run_query_file(conn, sql_path)
        if out is None:
            print(f"  - {sql_path.name}: schema applied")
            continue
        results[sql_path.stem] = out
        csv_path = OUT_DIR / f"{sql_path.stem}.csv"
        out.to_csv(csv_path, index=False)
        print(f"  - {sql_path.name}: {len(out):,} rows -> {csv_path.name}")
        print(out.head(8).to_string(index=False), "\n")

    conn.close()

    if "02_portfolio_summary" in results:
        plot_portfolio_summary(results["02_portfolio_summary"])
    if "03_vintage_curve" in results:
        plot_vintage(results["03_vintage_curve"])
    if "04_status_migration" in results:
        plot_migration(results["04_status_migration"])
    print("Charts saved to:", OUT_DIR)


if __name__ == "__main__":
    main()
