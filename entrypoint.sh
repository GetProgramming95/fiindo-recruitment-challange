#!/usr/bin/env bash
set -e

echo ">>> Running Alembic migrations..."
alembic upgrade head

echo ">>> Starting ETL run..."
python -m src.main
