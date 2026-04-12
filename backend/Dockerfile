FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for asyncpg and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy everything, then install
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

# Run migrations then start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
