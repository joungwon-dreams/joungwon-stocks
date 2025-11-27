#!/bin/bash
# DB 백업 스크립트

BACKUP_DIR="/Users/wonny/Dev/joungwon.stocks/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="stock_investment_db"

# 전체 백업 (데이터 포함)
pg_dump -U wonny -Fc $DB_NAME > "$BACKUP_DIR/full_backup_$DATE.dump"

# 스키마만 백업 (Git용)
pg_dump -U wonny --schema-only $DB_NAME > "$BACKUP_DIR/schema_latest.sql"

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "full_backup_*.dump" -mtime +7 -delete

echo "✅ 백업 완료: $BACKUP_DIR/full_backup_$DATE.dump"
ls -lh $BACKUP_DIR/*.dump 2>/dev/null | tail -5
