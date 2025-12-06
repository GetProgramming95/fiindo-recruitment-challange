import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src import models
import src.db_writer as db_writer

def create_test_session():
    """
    Create an in-memory SQLite DB and return a SessionLocal bound to it.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    models.Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestSessionLocal

def test_aggregate_industries(monkeypatch):
    """
    Given a couple of tickers and ticker_stats rows,
    DBWriter.aggregate_industries should compute the expected aggregates.
    """
    # 1) In-memory SessionLocal
    TestSessionLocal = create_test_session()

    # 2) Monkeypatch db_writer.SessionLocal so DBWriter uses our test DB
    monkeypatch.setattr(db_writer, "SessionLocal", TestSessionLocal)

    # 3) Create DBWriter + get session
    writer = db_writer.DBWriter()
    session = writer.db

    # 4) Insert some test tickers (same industry)
    t1 = models.Ticker(
        symbol="AAA",
        company="Company A",
        industry="Banks - Diversified",
        exchange="X",
    )
    t2 = models.Ticker(
        symbol="BBB",
        company="Company B",
        industry="Banks - Diversified",
        exchange="X",
    )
    session.add_all([t1, t2])
    session.commit()

    # 5) Insert TickerStats for these tickers
    s1 = models.TickerStats(
        ticker_id=t1.id,
        pe_ratio=10.0,
        revenue_growth=0.10,
        latest_revenue=100.0,
    )
    s2 = models.TickerStats(
        ticker_id=t2.id,
        pe_ratio=20.0,
        revenue_growth=0.30,
        latest_revenue=300.0,
    )
    session.add_all([s1, s2])
    session.commit()

    # 6) Run aggregation
    writer.aggregate_industries()

    # 7) Check result in IndustryStats
    industries = session.query(models.IndustryStats).all()
    assert len(industries) == 1
    row = industries[0]
    assert row.industry == "Banks - Diversified"

    # avg_pe = (10 + 20) / 2 = 15
    assert row.avg_pe_ratio == pytest.approx(15.0)

    # avg_rev_growth = (0.10 + 0.30) / 2 = 0.20
    assert row.avg_revenue_growth == pytest.approx(0.20)

    # sum_revenue = 100 + 300 = 400
    assert row.sum_revenue == pytest.approx(400.0)
