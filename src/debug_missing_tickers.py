"""
Helper script to inspect tickers that have no calculated metrics.
It:
- finds all tickers that exist in the master table (Ticker)
  but do NOT have a row in TickerStats
- calls the /debug/{symbol} endpoint for each of them
- prints a short summary of the debug response
"""
import logging
from typing import List
from src.api_client import FiindoAPI
from src.models import SessionLocal, Ticker, TickerStats

logger = logging.getLogger(__name__)

def find_tickers_without_stats() -> List[str]:
    """Return all symbols that have no row in TickerStats."""
    session = SessionLocal()
    try:
        rows = (
            session.query(Ticker.symbol)
            .outerjoin(TickerStats, Ticker.id == TickerStats.ticker_id)
            .filter(TickerStats.id.is_(None))
            .all()
        )
        return [r[0] for r in rows]
    finally:
        session.close()

def debug_tickers(symbols: List[str]) -> None:
    """Call /debug/{symbol} for each symbol and print a short summary."""
    api = FiindoAPI()
    for symbol in symbols:
        logger.info("Requesting /debug for %s ...", symbol)
        data = api.get_debug(symbol)
        if not data:
            print(f"{symbol}: no debug data (None or 404)")
            continue

        top_keys = list(data.keys())
        print(f"{symbol}: debug response keys = {top_keys}")

        # Show validation-related fields if present
        is_valid = data.get("is_valid")
        message = data.get("message")
        if is_valid is not None or message is not None:
            print(f"  - is_valid={is_valid}, message={message}")
        print()

def main() -> None:
    # Simple console logging for this helper (no file-based ETL logging)
    logging.basicConfig(level=logging.INFO)
    missing = find_tickers_without_stats()
    print(f"Found {len(missing)} tickers without metrics in DB.\n")
    debug_tickers(missing)

if __name__ == "__main__":
    main()
