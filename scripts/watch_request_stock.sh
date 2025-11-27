#!/bin/bash
# FSWatch: request_stock.md 변경 감시 및 복사
# 소스: /Users/wonny/Dev/joungwon.stocks.report/research_report/request_stock/request_stock.md
# 대상: /Users/wonny/Dev/joungwon.stocks/reports/request_stock/

SOURCE_FILE="/Users/wonny/Dev/joungwon.stocks.report/research_report/request_stock/request_stock.md"
TARGET_DIR="/Users/wonny/Dev/joungwon.stocks/reports/request_stock"
LOG_FILE="/Users/wonny/Dev/joungwon.stocks/logs/watch_request_stock.log"

# 로그 디렉토리 생성
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$TARGET_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

copy_file() {
    if [ -f "$SOURCE_FILE" ]; then
        cp "$SOURCE_FILE" "$TARGET_DIR/"
        log "✅ 복사 완료: request_stock.md → $TARGET_DIR/"
    else
        log "⚠️ 소스 파일 없음: $SOURCE_FILE"
    fi
}

log "🚀 FSWatch 시작: $SOURCE_FILE 감시 중..."

# 초기 복사
copy_file

# fswatch로 파일 변경 감시
fswatch -o "$SOURCE_FILE" | while read -r event; do
    log "📝 파일 변경 감지"
    sleep 1  # 파일 쓰기 완료 대기
    copy_file
done
