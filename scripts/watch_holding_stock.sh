#!/bin/bash
# FSWatch: holding_stock 폴더 변경 감시 및 복사
# 소스: /Users/wonny/Dev/joungwon.stocks/reports/holding_stock
# 대상: /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock

SOURCE_DIR="/Users/wonny/Dev/joungwon.stocks/reports/holding_stock"
TARGET_DIR="/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock"
LOG_FILE="/Users/wonny/Dev/joungwon.stocks/logs/watch_holding_stock.log"

# 로그 디렉토리 생성
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$TARGET_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

sync_files() {
    if [ -d "$SOURCE_DIR" ]; then
        rsync -av --delete "$SOURCE_DIR/" "$TARGET_DIR/"
        log "✅ 동기화 완료: $SOURCE_DIR → $TARGET_DIR"
    else
        log "⚠️ 소스 디렉토리 없음: $SOURCE_DIR"
    fi
}

log "🚀 FSWatch 시작: $SOURCE_DIR 감시 중..."

# 초기 동기화
sync_files

# fswatch로 디렉토리 변경 감시
fswatch -o "$SOURCE_DIR" | while read -r event; do
    log "📝 파일 변경 감지"
    sleep 1  # 파일 쓰기 완료 대기
    sync_files
done
