"""
Simple helper that scans the latest ETL log file and summarizes errors.
It:
- picks the newest logs/etl_YYYYMMDD_HHMMSS.log file (by filename)
- prints all ERROR lines
- counts HTTP status codes (e.g. 401, 429, 500)
- counts all symbols where metrics could NOT be calculated
  (including those failing due to API errors)
"""
import os
import glob
import re
from collections import Counter

LOG_DIR = "logs"
LOG_PATTERN = "etl_*.log"
FALLBACK_LOG_FILE = os.path.join(LOG_DIR, "etl.log")

# Match our own API error log:
API_STATUS_RE = re.compile(r"Unexpected status (\d+)\b")

# Match HTTPError:
HTTPERROR_RE = re.compile(r"Server Error: (\d{3})")

# Match our warning:
NO_METRICS_RE = re.compile(r"No metrics could be calculated for (\S+)")

# Match symbol inside API URLs:
# .../financials/WDI.SW/income_statement
SYMBOL_IN_URL_RE = re.compile(r"/financials/([A-Z0-9\.\-]+)/income_statement")


def find_latest_log_file() -> str:
    """
    Find the newest ETL log file in logs/, based on the filename.
    Looks for logs/etl_YYYYMMDD_HHMMSS.log and returns the lexicographically
    largest one. Falls back to logs/etl.log if no timestamped file exists.
    Raises FileNotFoundError if nothing is found.
    """
    pattern = os.path.join(LOG_DIR, LOG_PATTERN)
    candidates = glob.glob(pattern)

    if candidates:
        # filenames are like etl_20251206_123712.log, so lexicographic max = newest
        latest = max(candidates, key=lambda p: os.path.basename(p))
        return latest

    # Fallback to old single-file logging, if it exists
    if os.path.exists(FALLBACK_LOG_FILE):
        return FALLBACK_LOG_FILE

    raise FileNotFoundError("No ETL log file found in 'logs/' directory.")


def analyze_logs() -> None:
    log_file = find_latest_log_file()
    print(f"Analyzing log file: {log_file}\n")

    errors = []
    api_status_counts = Counter()
    no_metrics_counts = Counter()

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            # 1) Collect ERROR lines + extract HTTP codes
            if "ERROR" in line:
                errors.append(line)

                status_code = None

                m1 = API_STATUS_RE.search(line)
                if m1:
                    status_code = m1.group(1)

                m2 = HTTPERROR_RE.search(line)
                if m2:
                    status_code = m2.group(1)

                if status_code:
                    api_status_counts[status_code] += 1

                # Extract symbol from problematic API URL
                m3 = SYMBOL_IN_URL_RE.search(line)
                if m3:
                    symbol = m3.group(1)
                    no_metrics_counts[symbol] += 1

            # 2) Collect symbols where metrics are missing
            m4 = NO_METRICS_RE.search(line)
            if m4:
                symbol = m4.group(1)
                no_metrics_counts[symbol] += 1

    # OUTPUT
    print("ERROR SUMMARY")
    print(f"{len(errors)} errors detected.\n")

    for err in errors:
        print(err)

    print("\nAPI ERROR CODES")
    if api_status_counts:
        for code, cnt in sorted(api_status_counts.items()):
            print(f"{code}: {cnt} occurrence(s)")
    else:
        print("No HTTP errors detected.")

    print("\nTICKERS WITHOUT METRICS")
    total_symbols = len(no_metrics_counts)
    total_events = sum(no_metrics_counts.values())
    print(f"{total_symbols} unique symbols, {total_events} total event(s).\n")

    for symbol, cnt in sorted(no_metrics_counts.items()):
        print(f"{symbol}: {cnt} time(s) with no metrics")


if __name__ == "__main__":
    analyze_logs()
