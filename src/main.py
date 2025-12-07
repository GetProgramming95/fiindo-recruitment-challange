"""
Entry point for the Fiindo ETL pipeline.
High-level steps:
1) Enable optional speed boost
2) Fetch and filter symbols for the three target industries
3) Compute ticker-level metrics in parallel
4) Persist metrics to SQLite
5) Aggregate industry-level metrics
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
from src.api_client import enable_speedboost


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
    Detailed steps + errors still go into the log files.
    """
    setup_logging()

    logger.warning("Initializing ETL run...")

    # Step 0: Optional Speed Boost activation
    enable_speedboost()

    logger.warning("STARTING ETL PIPELINE")

    fetcher = SymbolFetcher()
    writer = DBWriter()

    # Step 1: Clear current snapshot tables
    logger.warning("Step 1: Clearing current snapshot tables...")
    writer.clear_current_tables()
    logger.warning("Step 1 completed.")

    # Step 2: Fetch & filter symbols
    logger.warning("Step 2: Fetching and filtering symbols...")
    symbols: List[Dict] = fetcher.fetch_and_filter_symbols()
    logger.warning("Step 2 completed: %d symbols match the target industries.", len(symbols))

    if not symbols:
        logger.error("No relevant symbols found — aborting ETL run.")
        logger.warning("ETL PIPELINE ABORTED.")
        return

    # Step 3: Parallel calculations
    logger.warning(
        "Step 3: Starting calculations for %d symbols using up to %d worker threads...",
        len(symbols),
        MAX_WORKERS,
    )

    def process_symbol(entry: Dict) -> Tuple[str, Dict]:
        """Worker function executed by each thread."""
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
        "Step 3 completed: %d/%d tickers calculated successfully.",
        len(results),
        len(symbols),
    )

    if not results:
        logger.error("No metrics successfully calculated — aborting.")
        logger.warning("ETL PIPELINE ABORTED.")
        return

    # Step 4: Persist calculations
    logger.warning("Step 4: Persisting ticker metrics to SQLite...")
    for symbol, stats in results:
        writer.save_ticker_stats(symbol, stats)
    logger.warning("Step 4 completed: %d rows saved.", len(results))

    # Step 5: Industry aggregation
    logger.warning("Step 5: Aggregating industry-level metrics...")
    writer.aggregate_industries()
    logger.warning("Step 5 completed.")

    # FINISHED
    logger.warning(
        "ETL PIPELINE COMPLETED (symbols=%d, successful calculations=%d)",
        len(symbols),
        len(results),
    )


if __name__ == "__main__":
    run_etl()
