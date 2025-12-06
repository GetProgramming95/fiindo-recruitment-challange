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


### Recommended: Run the Project via Docker

The easiest and fully reproducible way to run the ETL pipeline is through the
provided **Docker setup**.    
Running `docker compose up` will automatically:
- install all dependencies  
- run Alembic migrations  
- create the SQLite database (`fiindo_challenge.db`)  
- create the `logs/` directory with timestamped log files  
- execute the full ETL pipeline  
No database or log files are included in the repository on purpose
(they are created dynamically at runtime).  
Just ensure your `.env` is filled in before starting Docker.


---

### Project Structure

```text
.
├─ src/
│  ├─ main.py              # ETL orchestration
│  ├─ api_client.py        # Fiindo API wrapper (auth, retries, error handling)
│  ├─ fetcher.py           # Fetch symbols & filter industries
│  ├─ calculations.py      # Compute per-ticker metrics
│  ├─ db_writer.py         # Save ticker + industry results into SQLite
│  ├─ models.py            # SQLAlchemy models
│  ├─ logging_setup.py     # Unified logging configuration
│  ├─ check_db.py          # CLI tool to inspect DB contents
│  └─ analyze_logs.py      # Summaries of ETL log output
│
├─ tests/
│  ├─ conftest.py
│  ├─ test_calculations.py
│  └─ test_db_writer.py
│
├─ alembic/
├─ logs/
│  └─ etl_*.log              # ETL log file (created at runtime)
├─ alembic.ini
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

### Prerequisites

- Python **3.10+**
- SQLite (built-in)
- Optional: Docker & docker-compose

---

### ETL Overview

### 1. Extract
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

### 2. Transform (Calculations)

The pipeline computes:

**PE Ratio**
```text
latest_price / last_quarter_eps
```

**Revenue Growth (QoQ)**
```text
(Q1_revenue - Q2_revenue) / Q2_revenue
```

**NetIncomeTTM**
```text
sum of netIncome for the last four quarters
```

**Debt Ratio**
```text
totalDebt / totalEquity
```

**Latest Revenue**
Used for industry-level total revenue aggregation.

Parallel processing is implemented via `ThreadPoolExecutor`.  
Thread counts are configurable via `.env`.

---

### 3. Load (SQLite)

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

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```bash
cp .env.example .env
```

Fill it:

```env
# Authentication for Fiindo API
FIRST_NAME=YourFirstName
LAST_NAME=YourLastName

# Optional performance tuning (thread pool sizes)
# Threads calculating ticker metrics
MAX_WORKERS=5

# Threads fetching ticker / general info
MAX_FETCH_WORKERS=10

# Optional: Override API base URL (default: https://api.test.fiindo.com/api/v1)
FIINDO_API_BASE_URL=https://api.test.fiindo.com/api/v1

# Retry / timeout configuration for FiindoAPI
# Maximum retry attempts for retryable HTTP errors
FIINDO_MAX_RETRIES=3

# Seconds to wait between retries (backoff)
FIINDO_RETRY_BACKOFF=30

# Per-request timeout in seconds (recommended: 60–90 seconds)
FIINDO_API_TIMEOUT=90

# Comma-separated HTTP status codes that should trigger a retry
FIINDO_RETRY_STATUS_CODES=429,500

```

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

In addition to basic worker settings, the Fiindo API client supports configurable  
**API base URL**, **HTTP timeout**, and **retry behavior** for handling unstable  
or slow endpoints.

### API Base URL

Default:
```env
FIINDO_API_BASE_URL=https://api.test.fiindo.com/api/v1
```

Can be overridden for testing, mocks, or staging environments.

---

### Retry / Timeout Settings

| Variable | Default | Description |
|----------|---------|-------------|
| **FIINDO_MAX_RETRIES** | `3` | Maximum number of retry attempts for retryable HTTP errors |
| **FIINDO_RETRY_BACKOFF** | `30` | Seconds to wait between retry attempts |
| **FIINDO_API_TIMEOUT** | `90` | Per-request HTTP timeout in seconds |
| **FIINDO_RETRY_STATUS_CODES** | `429,500` | Comma-separated HTTP status codes that trigger retries |

These values ensure robust stability with slow or rate-limited API endpoints.

---

### Database Setup (Alembic)

Initialize / upgrade the schema:

```bash
alembic upgrade head
```

Alternative: Create tables directly from models (without Alembic)
If you prefer to create the database schema directly from the SQLAlchemy models  
(e.g. for a quick local test), you can run:

```bash
python -m src.models
```

This creates or updates `fiindo_challenge.db`.

---

## Running the ETL

```bash
python -m src.main
```

Logs are written to:

- timestamped log files in `logs/etl_YYYYMMDD_HHMMSS.log` (one file per run)

---

## Running Helper Scripts

### 1. Database overview

```bash
python -m src.check_db
```

Outputs:
- Row counts  
- Sample rows  
- Duplicate checks  
- Validation of required industries  

---

### 2. Log analysis

```bash
python -m src.analyze_logs
```

Shows:
- Error log lines  
- HTTP failures (401, 404, 429, 500, …)  
- Tickers missing metrics  

---

### Tests

Run all tests:
```bash
pytest
```

### Included Tests

`test_calculations.py`
- Validates:
  - revenue growth  
  - PE ratio  
  - debt ratio  
  - net income TTM  
  - latest revenue  
- Uses a mock API client with deterministic data  

`test_db_writer.py`
- In-memory SQLite  
- Validates:
  - correct industry aggregation  
  - averages & sums  

`conftest.py`
- Ensures reliable imports during testing  

---

### Docker (Optional)

This project includes a fully working Docker setup that allows running the entire
ETL pipeline inside an isolated, reproducible environment.  
The Docker container installs all dependencies, loads environment variables,
runs Alembic migrations, executes the ETL pipeline, and keeps logs and database files persistent.


### Build:

```bash
docker compose build
```

### Run:

```bash
docker compose up
```

The container performs the following steps automatically:
1. Installs all Python dependencies from `requirements.txt`
2. Loads and exports values from `.env`
3. Runs Alembic migrations (`alembic upgrade head`)
4. Executes the ETL pipeline (`python -m src.main`)
5. Writes timestamped log files into `logs/`
6. Writes the SQLite database `fiindo_challenge.db` into the project directory
7. Keeps logs and database persistent through Docker bind-mount volumes

The container stops after the ETL completes.

---

### Required `.env` file

Docker automatically reads your `.env`.  
A valid example looks like this:

    # Authentication for Fiindo API
    FIRST_NAME=YourFirstName
    LAST_NAME=YourLastName

    # Worker configuration
    MAX_WORKERS=3
    MAX_FETCH_WORKERS=5

    # API base configuration
    FIINDO_API_BASE_URL=https://api.test.fiindo.com/api/v1

    # Retry logic
    FIINDO_MAX_RETRIES=3
    FIINDO_RETRY_BACKOFF=30
    FIINDO_API_TIMEOUT=90
    FIINDO_RETRY_STATUS_CODES=429,500


The default values in .env.example are optimized for local execution.
When using Docker, lower worker values are recommended to avoid API rate limits.
---

### Rebuilding after code changes

If you modify Python files, requirements, or migrations, use:

    docker compose down
    docker compose build
    docker compose up

---

### Where logs and the database go

- Logs are written to:  
  `logs/etl_YYYYMMDD_HHMMSS.log`
- SQLite database is written to:  
  `fiindo_challenge.db`

Both persist thanks to the mounted project directory.

---

### Notes & Behavior

- The container runs the ETL **exactly once** and then exits  
- You can start it again anytime via `docker compose up`
- Runs fully offline aside from API requests  
- Works with Docker Desktop (Windows/macOS) and native Docker on Linux
- Verified working with Docker Desktop on Windows after enabling virtualization

---

### Troubleshooting

**1. Too many API requests → 429 errors**  
Reduce worker counts inside `.env`:

    MAX_WORKERS=2
    MAX_FETCH_WORKERS=2

**2. Permissions issues**  
Ensure the project folder is not read-only.

**3. Docker cannot start on Windows**  
Ensure BIOS virtualization is enabled (`SVM`, `IOMMU`, Hyper-V).

**4. Restart with clean state**  

    docker compose down -v
    docker compose build
    docker compose up

---

### Summary

This project provides:
- A clean and modular ETL architecture  
- Parallel computation with configurable worker pools  
- Strong retry and error-handling mechanisms  
- Snapshot + history database structure using SQLite  
- Automatic Alembic migrations  
- Comprehensive unit testing for all core logic  
- Detailed timestamped logging and helper scripts for DB/log inspection  
- An optional Docker environment offering:  
  - fully self-contained execution  
  - reproducible ETL runs  
  - automatic environment loading  
  - persistent logs and database files  
  - complete isolation from the host system  

Together, these components form a reliable, maintainable, and production-ready ETL workflow suitable for further scaling or integration.

**Ready for review and discussion.**
