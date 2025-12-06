"""
Database models and engine/session setup for the Fiindo recruitment challenge.
This file defines:
- Ticker: basic instrument metadata
- TickerStats: latest calculated metrics per ticker
- TickerStatsHistory: historical snapshot of ticker metrics per ETL run
- IndustryStats: latest aggregated metrics per industry
- IndustryStatsHistory: historical snapshot of industry metrics
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# SQLite file in the project root
DATABASE_URL = "sqlite:///fiindo_challenge.db"

Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite in some envs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Ticker(Base):
    """
    Basic ticker master data coming from the Fiindo API (/symbols + /general).
    One ticker can have many stats rows in history and exactly one
    current stats row (from the latest ETL run).
    """
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    company = Column(String, nullable=True)
    industry = Column(String, index=True, nullable=True)
    exchange = Column(String, nullable=True)
    stats = relationship("TickerStats", back_populates="ticker", lazy="select")
    stats_history = relationship(
        "TickerStatsHistory", back_populates="ticker", lazy="select"
    )

class TickerStats(Base):
    """
    Latest calculated metrics per ticker (current snapshot).
    Will be cleared before each ETL run and re-populated.
    Metrics:
    - pe_ratio: P/E ratio from last quarter
    - revenue_growth: QoQ revenue growth (Q-1 vs Q-2)
    - net_income_ttm: trailing 12 months net income
    - debt_ratio: debt-to-equity ratio from last year
    - latest_revenue: revenue of the last reported quarter
    """
    __tablename__ = "ticker_stats"
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), index=True, nullable=False)
    pe_ratio = Column(Float)
    revenue_growth = Column(Float)
    net_income_ttm = Column(Float)
    debt_ratio = Column(Float)
    latest_revenue = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    ticker = relationship("Ticker", back_populates="stats")

class TickerStatsHistory(Base):
    """
    Historical snapshot of ticker metrics per ETL run.
    This table is append-only and never cleared, so you can later
    analyse how the metrics evolved over time.
    """
    __tablename__ = "ticker_stats_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), index=True, nullable=False)
    pe_ratio = Column(Float)
    revenue_growth = Column(Float)
    net_income_ttm = Column(Float)
    debt_ratio = Column(Float)
    latest_revenue = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    ticker = relationship("Ticker", back_populates="stats_history")

class IndustryStats(Base):
    """
    Latest aggregated metrics per industry (current snapshot).
    Metrics:
    - avg_pe_ratio: mean P/E ratio across all tickers in industry
    - avg_revenue_growth: mean revenue growth across all tickers
    - sum_revenue: sum of latest revenue across all tickers
    """
    __tablename__ = "industry_stats"
    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String, index=True, nullable=False)
    avg_pe_ratio = Column(Float)
    avg_revenue_growth = Column(Float)
    sum_revenue = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class IndustryStatsHistory(Base):
    """
    Historical snapshot of industry metrics per ETL run.
    This table is append-only and never cleared.
    """
    __tablename__ = "industry_stats_history"
    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String, index=True, nullable=False)
    avg_pe_ratio = Column(Float)
    avg_revenue_growth = Column(Float)
    sum_revenue = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db() -> None:
    """Create all tables in the SQLite database if they don’t exist yet."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database tables created (if necessary).")
