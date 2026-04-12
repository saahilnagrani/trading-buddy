#!/usr/bin/env bash
# Database backup script
# Usage: ./scripts/backup_db.sh
# Set DATABASE_URL or individual PG* env vars before running.
# Backups older than 30 days are automatically pruned.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="trading_buddy_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

if [ -n "${DATABASE_URL:-}" ]; then
  pg_dump "$DATABASE_URL" | gzip > "${BACKUP_DIR}/${FILENAME}"
else
  PGHOST="${PGHOST:-localhost}"
  PGPORT="${PGPORT:-5432}"
  PGUSER="${PGUSER:-trading}"
  PGDATABASE="${PGDATABASE:-trading_buddy}"
  pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" | gzip > "${BACKUP_DIR}/${FILENAME}"
fi

echo "Backup saved: ${BACKUP_DIR}/${FILENAME}"

# Prune backups older than 30 days
find "$BACKUP_DIR" -name "trading_buddy_*.sql.gz" -mtime +30 -delete 2>/dev/null || true
echo "Old backups pruned."
