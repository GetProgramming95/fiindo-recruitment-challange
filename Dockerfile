# Use a slim Python base image
FROM python:3.10-slim

# Ensure we see logs directly and no .pyc clutter
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install system dependencies (if needed in the future, keep here)
# For now it's intentionally minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Entry point that runs migrations + ETL
CMD ["bash", "entrypoint.sh"]
