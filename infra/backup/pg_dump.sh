#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=${BACKUP_DIR:-/tmp/backups}
S3_BUCKET=${BACKUP_S3_BUCKET:-retromind-backups}
PG_URL=${DATABASE_URL:-postgresql://retromind:retromind@localhost:5432/retromind}
RETENTION_DAYS=${RETENTION_DAYS:-30}

mkdir -p "$BACKUP_DIR"

FILENAME="pg_dump_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

echo "Starting PostgreSQL backup at $(date)"
pg_dump "$PG_URL" --no-owner --no-acl | gzip > "$FILEPATH"

FILESIZE=$(stat -f%z "$FILEPATH" 2>/dev/null || stat -c%s "$FILEPATH" 2>/dev/null)
echo "Backup size: $FILESIZE bytes"

if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  echo "Uploading to S3 bucket: $S3_BUCKET"
  aws s3 cp "$FILEPATH" "s3://${S3_BUCKET}/postgresql/${FILENAME}" --no-progress
  echo "Upload complete"

  # Clean old backups (retain daily for RETENTION_DAYS days)
  echo "Cleaning backups older than $RETENTION_DAYS days"
  aws s3 ls "s3://${S3_BUCKET}/postgresql/" | while read -r line; do
    DATE=$(echo "$line" | awk '{print $1" "$2}')
    FILE=$(echo "$line" | awk '{print $4}')
    if [ -n "$DATE" ] && [ "$(date -d "$DATE" +%s)" -lt "$(date -d "-${RETENTION_DAYS} days" +%s)" ]; then
      aws s3 rm "s3://${S3_BUCKET}/postgresql/${FILE}"
      echo "Deleted old backup: $FILE"
    fi
  done
fi

echo "Backup completed successfully"
