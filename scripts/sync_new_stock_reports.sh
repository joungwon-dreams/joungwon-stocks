#!/bin/bash
# 신규종목추천 PDF 파일 동기화 스크립트
# fswatch를 이용해 파일 생성/수정 시 자동 복사

SOURCE_DIR="/Users/wonny/Dev/joungwon.stocks/reports/new_stock/daily"
TARGET_DIR="/Users/wonny/Dev/joungwon.stocks.report/research_report/new_stock"

# 타겟 디렉토리 생성 (없으면)
mkdir -p "$TARGET_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting fswatch for new_stock reports..."
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"

# 기존 파일 먼저 복사
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Syncing existing files..."
for file in "$SOURCE_DIR"/*.pdf; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        cp "$file" "$TARGET_DIR/"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Initial sync: $filename"
    fi
done

# fswatch로 모니터링 (모든 변경 이벤트)
fswatch -0 "$SOURCE_DIR" | while read -d "" file; do
    if [[ "$file" == *.pdf ]] && [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Detected: $filename"
        cp "$file" "$TARGET_DIR/"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Copied to: $TARGET_DIR/$filename"
    fi
done
