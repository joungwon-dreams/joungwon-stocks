#!/bin/bash
# 매일 저녁 DB 백업 후 Git push

set -e
cd /Users/wonny/Dev/joungwon.stocks

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d)
DB_NAME="stock_investment_db"

echo "$(date '+%Y-%m-%d %H:%M:%S') 백업 시작..."

# 1. DB 전체 백업 (압축)
pg_dump -U wonny -Fc $DB_NAME > "$BACKUP_DIR/db_$DATE.dump"

# 2. 스키마 백업 (Git용)
pg_dump -U wonny --schema-only $DB_NAME > "$BACKUP_DIR/schema_latest.sql"

# 3. 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "db_*.dump" -mtime +7 -delete

# 4. Git add & commit & push
git add "$BACKUP_DIR/schema_latest.sql"
git add "$BACKUP_DIR/db_$DATE.dump" 2>/dev/null || true

# 변경사항 있을 때만 커밋
if ! git diff --cached --quiet; then
    git commit -m "backup: Daily DB backup $DATE

🤖 Auto-generated backup"
    git push origin main
    echo "✅ Git push 완료"
else
    echo "ℹ️ 변경사항 없음, 스킵"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') 백업 완료: $BACKUP_DIR/db_$DATE.dump"
ls -lh $BACKUP_DIR/*.dump | tail -3
