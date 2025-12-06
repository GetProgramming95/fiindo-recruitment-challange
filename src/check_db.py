"""
Small helper script to inspect the SQLite database content.
It prints:
- Number and preview of tickers
- Number and preview of ticker stats
- Number and preview of industry stats
- Basic sanity checks (duplicates, missing industries)
"""
from sqlalchemy import func
from src.models import (
    SessionLocal,
    Ticker,
    TickerStats,
    TickerStatsHistory,
    IndustryStats,
    IndustryStatsHistory,
)

def query_table(session, model):
    return session.query(model).all()

def preview_table(session, model, limit: int = 5):
    return session.query(model).limit(limit).all()

def run_checks() -> None:
    session = SessionLocal()
    # 1) Ticker master data
    print("STARTING DB CHECK\n")
    print("Ticker table (master data)")
    tickers = query_table(session, Ticker)
    print(f"Number of tickers: {len(tickers)}")
    for t in preview_table(session, Ticker):
        print(f"- {t.symbol} | {t.company} | {t.industry} | {t.exchange}")
    print()

    # 2) TickerStats (current snapshot)
    print("TickerStats (current metrics)")
    stats = query_table(session, TickerStats)
    print(f"Number of TickerStats rows: {len(stats)}")
    for s in preview_table(session, TickerStats):
        # use Session.get() instead of Query.get() to avoid legacy warning
        ticker = session.get(Ticker, s.ticker_id)
        sym = ticker.symbol if ticker else f"id={s.ticker_id}"
        print(
            f"- {sym} | PE={s.pe_ratio} | RevGrowth={s.revenue_growth} "
            f"| NetIncomeTTM={s.net_income_ttm} | DebtRatio={s.debt_ratio}"
        )
    print()

    # 3) IndustryStats (current snapshot)
    print("IndustryStats (industry aggregates)")
    ind = query_table(session, IndustryStats)
    print(f"Number of industries (IndustryStats): {len(ind)}")
    for i in preview_table(session, IndustryStats):
        print(
            f"- {i.industry} | AvgPE={i.avg_pe_ratio} | "
            f"AvgRevGrowth={i.avg_revenue_growth} | TotalRevenue={i.sum_revenue}"
        )
    print()

    # 4) History tables
    print("History tables")
    print(f"TickerStatsHistory: {session.query(TickerStatsHistory).count()} rows")
    print(f"IndustryStatsHistory: {session.query(IndustryStatsHistory).count()} rows")
    print()

    # 5) Extra sanity checks
    print("Extra checks")

    # 5.1 No duplicate TickerStats per ticker_id
    duplicates = (
        session.query(TickerStats.ticker_id)
        .group_by(TickerStats.ticker_id)
        .having(func.count() > 1)
        .all()
    )
    if duplicates:
        print("Duplicate TickerStats rows for ticker_ids:", duplicates)
    else:
        print("No duplicate TickerStats rows per ticker")

    # 5.2 All target industries present
    EXPECTED_INDUSTRIES = {
        "Banks - Diversified",
        "Software - Application",
        "Consumer Electronics",
    }

    found_industries = {i.industry for i in ind}
    missing = EXPECTED_INDUSTRIES - found_industries
    if missing:
        print("Industries missing in IndustryStats:", missing)
    else:
        print("All target industries present in IndustryStats")

    session.close()
    print("DB check completed!")

if __name__ == "__main__":
    run_checks()
