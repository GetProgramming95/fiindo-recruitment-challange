### Fiindo Recruitment Challenge – ETL Pipeline

This repository contains my solution for the **Fiindo technical recruitment challenge**.

The application implements a complete **ETL pipeline** that:
- Fetches financial and market data from the Fiindo API  
- Computes several **ticker-level metrics**
- Aggregates results at the **industry level**
- Stores all processed data in a **SQLite** database
- Provides **unit tests**, **logging**, **data validation**, and an optional **Docker setup**

The codebase is structured, testable, and built around clean separation of concerns.

> **Note:**  
> All commands in this README assume you run them from the **project root directory**  
> (the folder containing `README.md`, `docker-compose.yml`, etc.).

---

### Recommended: Run the Project via Docker

The easiest and fully reproducible way to run the ETL pipeline is through the  
provided **Docker setup**.

Running `docker compose up` will automatically:
- install all dependencies  
- run Alembic migrations  
- create or update the SQLite database (`fiindo_challenge.db`)  
- create the `logs/` directory with timestamped log files  
- execute the full ETL pipeline  

> **Note:**  
> This repository *includes* a pre-generated `fiindo_challenge.db` and example  
> log files inside `logs/` so that reviewers can directly inspect the final ETL  
> output (ticker metrics, industry aggregations, history tables, and error logs).  
> When running via Docker, these files will be automatically updated or overwritten.
> Just ensure your `.env` file is filled in before starting Docker.

---

### Project Structure

    .
    ├─ src/
    │  ├─ main.py                  # ETL orchestration (entry point)
    │  ├─ api_client.py            # Fiindo API wrapper (auth, retries, speedboost, error handling)
    │  ├─ fetcher.py               # Fetch symbols & filter industries
    │  ├─ calculations.py          # Compute per-ticker metrics
    │  ├─ db_writer.py             # Save ticker + industry results into SQLite
    │  ├─ models.py                # SQLAlchemy models
    │  ├─ logging_setup.py         # Unified logging configuration
    │  ├─ check_db.py              # CLI tool to inspect DB contents
    │  ├─ analyze_logs.py          # Summaries of ETL log output
    │  └─ debug_missing_tickers.py # Helper to inspect tickers without metrics via /debug
    │
    ├─ fiindo_challenge.db         # SQLite database (example ETL output)
    ├─ tests/
    │  ├─ conftest.py
    │  ├─ test_calculations.py
    │  └─ test_db_writer.py
    │
    ├─ alembic/
    ├─ logs/
    │  └─ etl_*.log                # ETL log files (timestamped)
    ├─ alembic.ini
    ├─ Dockerfile
    ├─ docker-compose.yml
    ├─ requirements.txt
    ├─ .env.example
    └─ README.md




               +----------------+
               |   Fiindo API   |
               +--------+-------+
                        |
                        v
+------------+    +------------+    +--------------+
|  fetcher   | -> | calculator | -> |  db_writer   |
+------------+    +------------+    +--------------+
        \                |                 |
         \               |                 |
          +----------------------------------------+
                           Database


---

### Prerequisites

- Python **3.10+**
- SQLite (built-in)
- Optional: Docker & docker-compose

---

### ETL Overview

#### 1. Extract

The pipeline calls Fiindo endpoints:

- `/symbols`
- `/general/{symbol}`
- `/financials/{symbol}/income_statement`
- `/financials/{symbol}/balance_sheet_statement`
- `/eod/{symbol}`

Only tickers from these industries are processed:

- `Banks - Diversified`
- `Software - Application`
- `Consumer Electronics`

Ticker master data is stored in the `tickers` table.

---

#### 2. Transform (Calculations)

The pipeline computes:

**PE Ratio**

    latest_price / last_quarter_eps

**Revenue Growth (QoQ)**

    (Q1_revenue - Q2_revenue) / Q2_revenue

**NetIncomeTTM**

    sum of netIncome for the last four quarters

**Debt Ratio**

    totalDebt / totalEquity

**Latest Revenue**  
Used for industry-level total revenue aggregation.

Parallel processing is implemented via `ThreadPoolExecutor`.  
Thread counts are configurable via `.env`.

---

#### 3. Load (SQLite)

Snapshot vs. history tables:

| Table                     | Purpose                          |
|---------------------------|----------------------------------|
| `tickers`                 | Master data                      |
| `ticker_stats`            | Latest ticker metrics            |
| `ticker_stats_history`    | Full metric history              |
| `industry_stats`          | Latest industry aggregation      |
| `industry_stats_history`  | Full aggregation history         |

Before each ETL run:
- snapshot tables are cleared  
- history tables accumulate all runs  

---

### Industry Aggregation

For each industry, the ETL computes:
- Average PE Ratio  
- Average Revenue Growth  
- Total Latest Revenue  

Results are written to snapshot and history tables.

---

### Installation

#### 1. Install dependencies

    pip install -r requirements.txt

#### 2. Create `.env`

    cp .env.example .env

Fill it:

    # Authentication for Fiindo API
    FIRST_NAME=YourFirstName
    LAST_NAME=YourLastName

    # Optional performance tuning (thread pool sizes)
    # Threads calculating ticker metrics
    MAX_WORKERS=5

    # Threads fetching ticker / general info
    MAX_FETCH_WORKERS=5

    # Optional: Override API base URL (default: https://api.test.fiindo.com/api/v1)
    FIINDO_API_BASE_URL=https://api.test.fiindo.com/api/v1

    # Optional: Enable Fiindo Speedboost (recommended during development)
    FIINDO_ENABLE_SPEEDBOOST=true

    # Optional override for the speedboost URL
    # If empty → automatically derived from FIINDO_API_BASE_URL
    # Fallback → https://api.test.fiindo.com/api/v1/speedboost
    FIINDO_SPEEDBOOST_URL=https://api.test.fiindo.com/api/v1/speedboost

    # Retry / timeout configuration for FiindoAPI
    # Maximum retry attempts for retryable HTTP errors
    FIINDO_MAX_RETRIES=3

    # Seconds to wait between retries (backoff)
    FIINDO_RETRY_BACKOFF=30

    # Per-request timeout in seconds (recommended: 60–90 seconds)
    FIINDO_API_TIMEOUT=90

    # Comma-separated HTTP status codes that should trigger a retry
    FIINDO_RETRY_STATUS_CODES=429,500

> **Spec Note**  
> The original challenge text contains a typo in the HTTP header name  
> (`Auhtorization` instead of `Authorization`).  
> However, the real Fiindo test API only accepts the correct  
> `Authorization: Bearer FIRST.LAST` header.  
>  
> This implementation therefore uses the working, correct header name so that the
> ETL pipeline can successfully communicate with the actual API, while still
> acknowledging the typo in the challenge description.

---

### Environment Variables: API Base URL & Retry / Timeout Settings

In addition to worker settings, the Fiindo API client supports configurable  
**API base URL**, **HTTP timeout**, **retry behavior**, and **speedboost control**.

#### API Base URL

Default:

    FIINDO_API_BASE_URL=https://api.test.fiindo.com/api/v1

Can be overridden for testing, mocks, or staging environments.

#### Retry / Timeout Settings

| Variable                  | Default   | Description                                           |
|---------------------------|-----------|-------------------------------------------------------|
| `FIINDO_MAX_RETRIES`      | `3`       | Max retry attempts for retryable HTTP errors         |
| `FIINDO_RETRY_BACKOFF`    | `30`      | Seconds to wait between retries                      |
| `FIINDO_API_TIMEOUT`      | `90`      | Per-request HTTP timeout in seconds                  |
| `FIINDO_RETRY_STATUS_CODES` | `429,500` | Status codes that should trigger retries           |

These values aim for a balance between robustness and API-friendliness.

---

### Speedboost (Hidden Fiindo Feature)

The Fiindo API exposes a hidden endpoint that can temporarily speed up responses:

    POST https://api.test.fiindo.com/api/v1/speedboost
    Body: { "first_name": FIRST_NAME, "last_name": LAST_NAME }

This project supports that endpoint directly from `api_client.py`.

Control via `.env`:

    FIINDO_ENABLE_SPEEDBOOST=true

Optional custom URL (otherwise auto-generated from `FIINDO_API_BASE_URL`):

    FIINDO_SPEEDBOOST_URL=https://api.test.fiindo.com/api/v1/speedboost

How it works internally:

- At ETL startup, `enable_speedboost()` is called from `main.py`
- If `FIINDO_ENABLE_SPEEDBOOST` is true:
  - the client sends the POST request with `FIRST_NAME` / `LAST_NAME`
  - success or failure is logged
  - the ETL **always continues**, even if speedboost fails

This improves:
- latency
- stability under parallel load
- behavior when using higher worker counts

---

### Database Setup (Alembic)

Initialize / upgrade the schema:

    alembic upgrade head

Alternative: create tables directly from SQLAlchemy models (without Alembic):

    python -m src.models

This creates or updates `fiindo_challenge.db`.

---

### Running the ETL

    python -m src.main

Logs are written to:

- `logs/etl_YYYYMMDD_HHMMSS.log` (one file per run)

---

### Running Helper Scripts

#### 1. Database overview

    python -m src.check_db

Outputs:
- Row counts  
- Sample rows  
- Duplicate checks  
- Validation of required industries  
- Extra checks to ensure no duplicate ticker symbols in the master table  

#### 2. Log analysis

    python -m src.analyze_logs

Shows:
- Error log lines  
- HTTP failures (401, 404, 429, 500, …)  
- Tickers missing metrics  
- Uses the **latest** `logs/etl_*.log` automatically  

#### 3. Debug missing tickers

    python -m src.debug_missing_tickers

This helper:

- finds all symbols that exist in `Ticker` but have **no row** in `TickerStats`
- calls `/debug/{symbol}` for each of them
- prints `is_valid` and the message from the debug response

This is useful to show that “problematic” tickers are valid, but the underlying
financial endpoints may still return missing data or repeated 500 errors.

---

### Tests

Run all tests:

    pytest

Included tests:

- `test_calculations.py`  
  - validates revenue growth, PE ratio, debt ratio, net income TTM, latest revenue  
  - uses deterministic fake data  

- `test_db_writer.py`  
  - runs against in-memory SQLite  
  - validates industry aggregation, averages, sums  

- `conftest.py`  
  - ensures `src/` is importable and test setup is reliable  

---

### Docker (Optional)

This project includes a full Docker setup to run the ETL in an isolated environment.

#### Build

    docker compose build

#### Run

    docker compose up

The container performs:

1. Install dependencies from `requirements.txt`  
2. Load `.env`  
3. Run Alembic migrations (`alembic upgrade head`)  
4. Optionally request Fiindo speedboost (if enabled)  
5. Execute ETL (`python -m src.main`)  
6. Write timestamped logs into `logs/`  
7. Write `fiindo_challenge.db` next to the code  

It runs **once** and then exits. You can restart it any time.

---

### Rebuilding after code changes

    docker compose down
    docker compose build
    docker compose up

---

### Where logs and the database go

- Logs:  
  `logs/etl_YYYYMMDD_HHMMSS.log`

- SQLite database:  
  `fiindo_challenge.db`

Both are persisted via bind mounts of the project directory.

---

### Troubleshooting

**Too many API requests → 429 errors**

- Lower workers in `.env`:

      MAX_WORKERS=2
      MAX_FETCH_WORKERS=2

**Docker cannot start (Windows)**

- Ensure virtualization is enabled in BIOS (SVM / IOMMU / Hyper-V).

**Full reset**

    docker compose down -v
    docker compose build
    docker compose up

---

### Summary

This project provides:

- Clean, modular ETL architecture  
- Parallel computation with configurable worker pools  
- Strong retry and error-handling mechanisms  
- Snapshot + history schema in SQLite  
- Automatic Alembic migrations  
- Unit-tested calculation and aggregation logic  
- Detailed timestamped logs with analysis helpers  
- Support for Fiindo’s hidden speedboost endpoint  
- Docker setup for fully reproducible runs  

Together, these components form a robust, maintainable ETL workflow that can be
extended or integrated into larger systems.

**Ready for review and discussion.**
