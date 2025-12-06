"""
Entry point for the Fiindo ETL pipeline.
High-level steps:
1) Fetch and filter symbols for the three target industries
2) Compute ticker-level metrics in parallel
3) Persist metrics to SQLite
4) Aggregate industry-level metrics
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple, List
from dotenv import load_dotenv
from src.fetcher import SymbolFetcher
from src.calculations import Calculator
from src.db_writer import DBWriter
from src.logging_setup import setup_logging

load_dotenv()

logger = logging.getLogger(__name__)
DEFAULT_MAX_WORKERS = 3


def _int_from_env(env_name: str, default: int) -> int:
    """Helper: read an integer from environment with a safe fallback."""
    raw = os.getenv(env_name)
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


# Number of worker threads used for calculations
MAX_WORKERS = _int_from_env("MAX_WORKERS", DEFAULT_MAX_WORKERS)


def run_etl() -> None:
    """
    Run the full ETL pipeline once.

    Console output:
    - Only high-level progress messages (WARNING level and above)
    Detailed information is still written to the log file via logging_setup.
    """
    setup_logging()

    logger.warning("STARTING ETL PIPELINE")

    fetcher = SymbolFetcher()
    writer = DBWriter()

    # Step 1: Clear current snapshot tables
    logger.warning("Step 1: Clearing current snapshot tables...")
    writer.clear_current_tables()
    logger.warning("Step 1 completed: snapshot tables cleared.")

    # Step 2: Fetch & filter symbols (three target industries)
    logger.warning("Step 2: Fetching and filtering symbols for target industries...")
    symbols: List[Dict] = fetcher.fetch_and_filter_symbols()
    logger.warning("Step 2 completed: %d relevant symbols found.", len(symbols))

    if not symbols:
        logger.error("No relevant symbols found – aborting ETL run.")
        logger.warning("ETL PIPELINE ABORTED (no symbols).")
        return

    # Step 3: Calculate metrics in parallel
    logger.warning(
        "Step 3: Starting calculations for %d symbols with up to %d worker(s)...",
        len(symbols),
        MAX_WORKERS,
    )

    def process_symbol(entry: Dict) -> Tuple[str, Dict]:
        """
        Worker function for calculations.
        Each thread uses its own Calculator / API session.
        """
        symbol = entry["symbol"]
        calculator = Calculator()
        stats = calculator.calculate_all(symbol)
        return symbol, stats

    futures = []
    results: List[Tuple[str, Dict]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for entry in symbols:
            futures.append(executor.submit(process_symbol, entry))

        for fut in as_completed(futures):
            try:
                symbol, stats = fut.result()
            except Exception as exc:
                logger.exception("Error while calculating stats for a symbol: %s", exc)
                continue
            if not stats:
                logger.warning("No metrics could be calculated for %s", symbol)
                continue
            results.append((symbol, stats))

    logger.warning(
        "Step 3 completed: metrics successfully calculated for %d ticker(s).",
        len(results),
    )

    if not results:
        logger.error("No metrics were successfully calculated – nothing to persist.")
        logger.warning("ETL PIPELINE ABORTED (no results).")
        return

    # Step 4: Persist results (single thread, single DB session)
    logger.warning("Step 4: Persisting ticker metrics to the database...")
    for symbol, stats in results:
        writer.save_ticker_stats(symbol, stats)
    logger.warning(
        "Step 4 completed: persisted metrics for %d ticker(s).",
        len(results),
    )

    # Step 5: Industry aggregation
    logger.warning("Step 5: Aggregating industry-level metrics...")
    writer.aggregate_industries()
    logger.warning("Step 5 completed: industry metrics aggregation finished.")

    logger.warning(
        "ETL PIPELINE COMPLETED (symbols=%d, successful_tickers=%d).",
        len(symbols),
        len(results),
    )


if __name__ == "__main__":
    run_etl()
