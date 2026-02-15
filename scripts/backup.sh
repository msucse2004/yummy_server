#!/bin/bash
# DB 백업 스크립트 - cron으로 주기 실행 권장
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PGPASSWORD="${POSTGRES_PASSWORD:-yummy_secret}" pg_dump -h localhost -U yummy -d yummy -F c -f "$BACKUP_DIR/yummy_$TIMESTAMP.dump"
echo "Backup saved: $BACKUP_DIR/yummy_$TIMESTAMP.dump"
