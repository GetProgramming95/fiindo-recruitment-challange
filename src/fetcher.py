"""
Symbol fetching and filtering.
Steps:
1) Download all symbols from /symbols (single request)
2) For each symbol, call /general in parallel
3) Filter by the three target industries
4) Store ticker master data in the database
"""
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from src.api_client import FiindoAPI
from src.models import SessionLocal, Ticker

logger = logging.getLogger(__name__)
TARGET_INDUSTRIES = {
    "Banks - Diversified",
    "Software - Application",
    "Consumer Electronics",
}

def _int_from_env(env_name: str, default: int) -> int:
    """Helper: read an int from environment with a safe fallback."""
    raw = os.getenv(env_name)
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default

# How many workers may call /general in parallel
DEFAULT_FETCH_WORKERS = 5
MAX_FETCH_WORKERS = _int_from_env("MAX_FETCH_WORKERS", DEFAULT_FETCH_WORKERS)


class SymbolFetcher:
    """
    Fetches all symbols from the Fiindo API and filters those
    that belong to the three target industries.
    """

    def __init__(self) -> None:
        # This API client is only used for the /symbols call
        self.api = FiindoAPI()
        self.db = SessionLocal()

    def fetch_and_filter_symbols(self) -> List[Dict]:
        """
        Download all symbols, fetch /general in parallel,
        return only those belonging to the target industries.
        Also persists basic ticker metadata in the database.
        """
        symbols = self.api.get_symbols()
        logger.info("Fetched %d symbols from /symbols", len(symbols))

        if not symbols:
            return []

        def process_symbol(symbol: str) -> Optional[Dict]:
            """Worker function to fetch /general for a single symbol."""
            try:
                api = FiindoAPI()
                general = api.get_general(symbol)
                if not general:
                    return None

                fundamentals = general.get("fundamentals", {})
                profile_list = fundamentals.get("profile", {}).get("data", [])
                if not profile_list:
                    return None

                info = profile_list[0]
                industry = info.get("industry")
                company = info.get("companyName")
                exchange = info.get("exchange")

                if industry not in TARGET_INDUSTRIES:
                    return None
                logger.info("Symbol %s is relevant (industry=%s)", symbol, industry)
                return {
                    "symbol": symbol,
                    "company": company,
                    "industry": industry,
                    "exchange": exchange,
                }
            except Exception as exc:
                logger.exception("Error while processing /general for %s: %s", symbol, exc)
                return None

        logger.info(
            "Starting parallel /general fetch with %d worker(s)...",
            MAX_FETCH_WORKERS,
        )
        valid: List[Dict] = []
        with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
            futures = {executor.submit(process_symbol, s): s for s in symbols}

            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    valid.append(res)
        logger.info("Found %d relevant symbols after industry filter", len(valid))

        # Persist ticker master data (single DB session, serial writes)
        for entry in valid:
            self._store_ticker(
                entry["symbol"],
                entry["company"],
                entry["industry"],
                entry["exchange"],
            )

        self.db.commit()
        return valid

    def _store_ticker(self, symbol: str, company: str, industry: str, exchange: str) -> None:
        """Insert ticker master data if it does not exist yet."""
        existing = (
            self.db.query(Ticker)
            .filter(Ticker.symbol == symbol)
            .one_or_none()
        )

        if existing:
            return

        t = Ticker(
            symbol=symbol,
            company=company,
            industry=industry,
            exchange=exchange,
        )
        self.db.add(t)
        logger.info("Inserted new ticker: %s (%s)", symbol, industry)

if __name__ == "__main__":
    from src.logging_setup import setup_logging
    setup_logging()
    fetcher = SymbolFetcher()
    data = fetcher.fetch_and_filter_symbols()
    logger.info("Relevant symbols: %d", len(data))
