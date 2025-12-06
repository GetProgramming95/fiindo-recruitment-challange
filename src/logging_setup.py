"""
Central logging configuration for the ETL pipeline.
- Writes structured logs to logs/etl.log
"""
import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Timestamped log file: logs/etl_20250206_214501.log
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"etl_{timestamp}.log")


def setup_logging(file_level: int = logging.INFO) -> None:
    """
    Configure application-wide logging.
    - Detailed logs go into the timestamped log file.
    - The console shows only warnings and errors to avoid noisy output.
    - Root logger receives everything, handlers apply filtering.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Root accepts everything, handlers filter

    # Prevent duplicate log handlers in repeated calls
    if root.handlers:
        root.handlers.clear()

    # FILE HANDLER (detailed logging: INFO, WARNING, ERROR)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # CONSOLE HANDLER (quiet: only WARNING and ERROR)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # <— Only show warnings+errors in console
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Register handlers
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Visible in console because it's WARNING level
    root.warning("Logging to file: %s", LOG_FILE)



