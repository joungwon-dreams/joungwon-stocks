#!/bin/bash
#
# reports 폴더 양방향 동기화 스크립트
# fswatch를 이용하여 두 폴더를 실시간 동기화
# 폴더 생성/삭제/이름변경도 rsync로 처리
#

DIR1="/Users/wonny/Dev/joungwon.stocks/reports"
DIR2="/Users/wonny/Dev/joungwon.stocks.report/reports"
LOG="/Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log"
LOCK_FILE="/tmp/sync_reports.lock"
SYNC_LOCK="/tmp/sync_reports_syncing"

mkdir -p "$(dirname "$LOG")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

# 이미 실행 중인지 확인
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "Already running with PID $OLD_PID"
        exit 0
    fi
fi

echo $$ > "$LOCK_FILE"

cleanup() {
    log "동기화 종료 중..."
    rm -f "$LOCK_FILE" "$SYNC_LOCK"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# rsync 기반 전체 동기화 (삭제 포함)
full_sync() {
    local source="$1"
    local target="$2"
    local direction="$3"

    # 동기화 중 플래그
    touch "$SYNC_LOCK"

    rsync -a --delete "$source/" "$target/" 2>/dev/null
    local result=$?

    rm -f "$SYNC_LOCK"

    if [ $result -eq 0 ]; then
        log "RSYNC: $direction 완료"
    fi
}

log "=========================================="
log "Reports 양방향 동기화 시작"
log "=========================================="

# 초기 동기화 (DIR1 → DIR2)
log "초기 동기화 중..."
rsync -av --delete "$DIR1/" "$DIR2/" >> "$LOG" 2>&1
log "초기 동기화 완료"

log "양방향 감시 시작..."

# 마지막 동기화 시간 추적
LAST_SYNC_TIME=0

# 두 디렉토리를 동시에 감시
/usr/local/bin/fswatch -0 -r -l 1 -e ".*\.DS_Store" -e ".*~$" "$DIR1" "$DIR2" | while IFS= read -r -d '' changed_file; do
    # 동기화 중이면 스킵
    if [ -f "$SYNC_LOCK" ]; then
        continue
    fi

    # 1초 내 중복 이벤트 무시
    current_time=$(date +%s)
    if [ $((current_time - LAST_SYNC_TIME)) -lt 2 ]; then
        continue
    fi
    LAST_SYNC_TIME=$current_time

    # 변경 감지된 디렉토리 확인 후 rsync 실행
    if [[ "$changed_file" == "$DIR1"* ]]; then
        full_sync "$DIR1" "$DIR2" "DIR1→DIR2"
    elif [[ "$changed_file" == "$DIR2"* ]]; then
        full_sync "$DIR2" "$DIR1" "DIR2→DIR1"
    fi
done
