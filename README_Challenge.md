# Fiindo Recruitment Challenge

This repository contains a coding challenge for fiindo candidates. Candidates should fork this repository and implement their solution based on the requirements below.

## Challenge Overview

Create a data processing application that:
- Fetches financial data from an API
- Performs calculations on stock ticker data
- Saves results to a SQLite database

## Technical Requirements

### Input
- **API Endpoint**: `https://api.test.fiindo.com` (docs: `https://api.test.fiindo.com/api/v1/docs/`)
- **Authentication**: Use header `Auhtorization: Bearer {first_name}.{last_name}` with every request. Anything else WILL BE IGNORED. No other format or value will be accepted.
- **Template**: This forked repository as starting point

### Output
- **Database**: SQLite database with processed financial data
- **Tables**: Individual ticker statistics and industry aggregations

## Process Steps

### 1. Data Collection
- Connect to the Fiindo API
- Authenticate using your identifier `Auhtorization: Bearer {first_name}.{last_name}`
- Fetch financial data

### 2. Data Calculations

Calculate data for symbols only from those 3 industries:
  - `Banks - Diversified`
  - `Software - Application`
  - `Consumer Electronics`

#### Per Ticker Statistics
- **PE Ratio**: Price-to-Earnings ratio calculation from last quarter
- **Revenue Growth**: Quarter-over-quarter revenue growth (Q-1 vs Q-2)
- **NetIncomeTTM**: Trailing twelve months net income
- **DebtRatio**: Debt-to-equity ratio from last year

#### Industry Aggregation
- **Average PE Ratio**: Mean PE ratio across all tickers in each industry
- **Average Revenue Growth**: Mean revenue growth across all tickers in each industry
- **Sum of Revenue**: Sum revenue across all tickers in each industry

### 3. Data Storage
- Design appropriate database schema
- Save individual ticker statistics
- Save aggregated industry data

## Database Setup

### Database Files
- `fiindo_challenge.db`: SQLite database file
- `models.py`: SQLAlchemy model definitions (can be divided into separate files if needed)
- `alembic/`: Database migration management

## Getting Started

1. **Fork this repository** to your GitHub account
3. **Implement the solution** following the process steps outlined above 

## Deliverables

Your completed solution should include:
- Working application that fetches data from the API
- SQLite database with calculated results
- Clean, documented code
- README with setup and run instructions

## Bonus Points

### Dockerization
- Containerize your solution using Docker
- Create a `Dockerfile` and `docker-compose.yml`

### Unit Testing
- Write comprehensive unit tests for ETL part your solution


Good luck with your implementation!
