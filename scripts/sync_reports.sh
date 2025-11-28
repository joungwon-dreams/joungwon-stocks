#!/bin/bash
#
# reports 폴더 양방향 동기화 스크립트
# fswatch를 이용하여 두 폴더를 실시간 동기화
#

DIR1="/Users/wonny/Dev/joungwon.stocks/reports"
DIR2="/Users/wonny/Dev/joungwon.stocks.report/reports"
LOG="/Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log"
LOCK_FILE="/tmp/sync_reports.lock"
SYNC_CACHE="/tmp/sync_reports_cache"

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
rm -f "$SYNC_CACHE"

cleanup() {
    log "동기화 종료 중..."
    rm -f "$LOCK_FILE" "$SYNC_CACHE"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 최근 동기화 여부 확인 (파일 기반)
was_recently_synced() {
    local filename="$1"
    local cache_file="$SYNC_CACHE"

    if [ ! -f "$cache_file" ]; then
        return 1
    fi

    local current_time=$(date +%s)
    while IFS=: read -r cached_file cached_time; do
        if [ "$cached_file" = "$filename" ]; then
            local diff=$((current_time - cached_time))
            if [ $diff -lt 3 ]; then
                return 0
            fi
        fi
    done < "$cache_file"
    return 1
}

mark_synced() {
    local filename="$1"
    local current_time=$(date +%s)
    echo "$filename:$current_time" >> "$SYNC_CACHE"

    # 캐시 정리 (100줄 이상이면 최근 50줄만 유지)
    if [ $(wc -l < "$SYNC_CACHE" 2>/dev/null || echo 0) -gt 100 ]; then
        tail -50 "$SYNC_CACHE" > "$SYNC_CACHE.tmp" && mv "$SYNC_CACHE.tmp" "$SYNC_CACHE"
    fi
}

log "=========================================="
log "Reports 양방향 동기화 시작"
log "=========================================="

# 초기 동기화
log "초기 동기화 중..."
rsync -av --delete "$DIR1/" "$DIR2/" >> "$LOG" 2>&1
log "초기 동기화 완료"

log "양방향 감시 시작..."

# 두 디렉토리를 동시에 감시
/usr/local/bin/fswatch -0 -r -l 2 -e ".*\.DS_Store" -e ".*~$" "$DIR1" "$DIR2" | while IFS= read -r -d '' changed_file; do
    # 파일명 추출
    filename=$(basename "$changed_file")

    # 최근 동기화된 파일인지 확인
    if was_recently_synced "$filename"; then
        continue
    fi

    # 변경된 파일이 어느 디렉토리에서 왔는지 확인
    if [[ "$changed_file" == "$DIR1"* ]]; then
        rel_path="${changed_file#$DIR1/}"
        target_file="$DIR2/$rel_path"
        if [ -f "$changed_file" ]; then
            mkdir -p "$(dirname "$target_file")"
            cp "$changed_file" "$target_file" 2>/dev/null
            mark_synced "$filename"
            log "SYNC: $rel_path → joungwon.stocks.report"
        fi
    elif [[ "$changed_file" == "$DIR2"* ]]; then
        rel_path="${changed_file#$DIR2/}"
        target_file="$DIR1/$rel_path"
        if [ -f "$changed_file" ]; then
            mkdir -p "$(dirname "$target_file")"
            cp "$changed_file" "$target_file" 2>/dev/null
            mark_synced "$filename"
            log "SYNC: $rel_path → joungwon.stocks"
        fi
    fi
done
