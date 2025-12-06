"""
Database writer for ticker- and industry-level metrics.
Responsibilities:
- Clear current snapshot tables before each ETL run
- Insert latest ticker metrics into TickerStats
- Append all ticker metrics to TickerStatsHistory
- Aggregate per industry and write IndustryStats / IndustryStatsHistory
"""
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy import delete
from src.models import (
    SessionLocal,
    Ticker,
    TickerStats,
    TickerStatsHistory,
    IndustryStats,
    IndustryStatsHistory,
)

logger = logging.getLogger(__name__)

class DBWriter:
    """
    Handles all "Load" logic of the ETL pipeline.
    Important:
    - TickerStats and IndustryStats are the “current snapshot” tables.
      They are cleared before each run.
    - TickerStatsHistory and IndustryStatsHistory are append-only.
    """

    def __init__(self) -> None:
        self.db = SessionLocal()

    # Clear current tables

    def clear_current_tables(self) -> None:
        """
        Remove all rows from:
        - TickerStats
        - IndustryStats
        History tables are never touched.
        """
        logger.info("Clearing current snapshot tables (TickerStats & IndustryStats)...")
        self.db.execute(delete(TickerStats))
        self.db.execute(delete(IndustryStats))
        self.db.commit()
        logger.info("Successfully cleared TickerStats & IndustryStats.")

    # Ticker metrics
    def save_ticker_stats(self, symbol: str, stats: Dict) -> None:
        """
        Persist calculated metrics for a single ticker.
        - Insert into TickerStats (current snapshot)
        - Insert into TickerStatsHistory (append-only)
        """
        ticker = (
            self.db.query(Ticker)
            .filter(Ticker.symbol == symbol)
            .one_or_none()
        )

        if not ticker:
            logger.warning("Ticker %s not found in DB (did the fetcher run?)", symbol)
            return
        now = datetime.utcnow()

        # Current snapshot
        current = TickerStats(
            ticker_id=ticker.id,
            pe_ratio=stats.get("pe_ratio"),
            revenue_growth=stats.get("revenue_growth"),
            net_income_ttm=stats.get("net_income_ttm"),
            debt_ratio=stats.get("debt_ratio"),
            latest_revenue=stats.get("latest_revenue"),
            calculated_at=now,
        )
        self.db.add(current)

        # History row
        history = TickerStatsHistory(
            ticker_id=ticker.id,
            pe_ratio=stats.get("pe_ratio"),
            revenue_growth=stats.get("revenue_growth"),
            net_income_ttm=stats.get("net_income_ttm"),
            debt_ratio=stats.get("debt_ratio"),
            latest_revenue=stats.get("latest_revenue"),
            created_at=now,
        )
        self.db.add(history)
        self.db.commit()
        logger.info("Saved stats for %s (ticker_id=%s)", symbol, ticker.id)

    # Industry aggregates
    def aggregate_industries(self) -> None:
        """
        Aggregate metrics per industry based on TickerStats:
        - Average P/E ratio across all tickers
        - Average revenue growth across all tickers
        - Sum of latest revenue
        """
        now = datetime.utcnow()
        industries = [
            row[0]
            for row in self.db.query(Ticker.industry).distinct().all()
            if row[0] is not None
        ]
        logger.info("Aggregating industry stats for %d industries", len(industries))
        for industry in industries:
            stats = (
                self.db.query(TickerStats)
                .join(Ticker, TickerStats.ticker_id == Ticker.id)
                .filter(Ticker.industry == industry)
                .all()
            )
            if not stats:
                logger.info("No stats for industry %s – skipping", industry)
                continue

            valid_pe = [t.pe_ratio for t in stats if t.pe_ratio is not None]
            valid_rg = [t.revenue_growth for t in stats if t.revenue_growth is not None]
            valid_rev = [t.latest_revenue for t in stats if t.latest_revenue is not None]
            avg_pe = sum(valid_pe) / len(valid_pe) if valid_pe else None
            avg_rg = sum(valid_rg) / len(valid_rg) if valid_rg else None
            sum_rev = sum(valid_rev) if valid_rev else None

            # Current snapshot: always re-insert after clear_current_tables()
            current = IndustryStats(
                industry=industry,
                avg_pe_ratio=avg_pe,
                avg_revenue_growth=avg_rg,
                sum_revenue=sum_rev,
                calculated_at=now,
            )
            self.db.add(current)

            # History row
            history = IndustryStatsHistory(
                industry=industry,
                avg_pe_ratio=avg_pe,
                avg_revenue_growth=avg_rg,
                sum_revenue=sum_rev,
                created_at=now,
            )
            self.db.add(history)

            logger.info(
                "Aggregated industry %s: avg_pe=%s, avg_rg=%s, sum_rev=%s",
                industry,
                avg_pe,
                avg_rg,
                sum_rev,
            )

        self.db.commit()
        logger.info("Industry aggregation completed.")
