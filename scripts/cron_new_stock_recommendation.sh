#!/bin/bash
# 신규종목추천 Cron 스크립트
# 실행 시간: 04, 07, 10, 13, 16, 18시
# 18시에는 종가 평가 모드로 실행
# 주말/공휴일에는 실행하지 않음

set -e

# 환경 설정
PROJECT_DIR="/Users/wonny/Dev/joungwon.stocks"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
HOUR=$(date '+%H')
TODAY=$(date '+%Y-%m-%d')
DAY_OF_WEEK=$(date '+%u')  # 1=월요일, 7=일요일

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 로그 파일
LOG_FILE="$LOG_DIR/cron_new_stock_$TIMESTAMP.log"

# ========== 휴장일 체크 ==========
# 1. 주말 체크 (토=6, 일=7)
if [ "$DAY_OF_WEEK" -ge 6 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 주말 - 실행 스킵" >> "$LOG_FILE"
    exit 0
fi

# Python 가상환경 활성화
source "$VENV_DIR/bin/activate"

# 2. 공휴일 체크 (pykrx 거래일 캘린더 사용)
IS_HOLIDAY=$(python -c "
from pykrx import stock
from datetime import datetime, timedelta

today = datetime.now()
today_str = today.strftime('%Y%m%d')

# 이번 달 시작일부터 오늘까지의 거래일 목록 조회
start_of_month = today.replace(day=1).strftime('%Y%m%d')
end_of_month = (today + timedelta(days=7)).strftime('%Y%m%d')

try:
    # 거래일 캘린더에서 오늘이 포함되어 있는지 확인
    trading_days = stock.get_market_ohlcv_by_date(start_of_month, end_of_month, '005930').index
    trading_days_str = [d.strftime('%Y%m%d') for d in trading_days]

    if today_str in trading_days_str:
        print('trading')
    else:
        # 장 시작 전이라 오늘 데이터가 없을 수 있음 - 요일로 추가 체크
        # 평일(월~금)이면 거래일로 간주
        if today.weekday() < 5:  # 0=월, 4=금
            # 한국 공휴일 체크 (수동 리스트)
            korean_holidays_2025 = [
                '20250101',  # 신정
                '20250128', '20250129', '20250130',  # 설날
                '20250301',  # 삼일절
                '20250505',  # 어린이날
                '20250506',  # 대체공휴일
                '20250606',  # 현충일
                '20250815',  # 광복절
                '20251003',  # 개천절
                '20251006', '20251007', '20251008',  # 추석
                '20251009',  # 한글날
                '20251225',  # 성탄절
            ]
            if today_str in korean_holidays_2025:
                print('holiday')
            else:
                print('trading')
        else:
            print('holiday')
except Exception as e:
    # 에러 시 평일이면 실행
    if today.weekday() < 5:
        print('trading')
    else:
        print('holiday')
" 2>/dev/null)

if [ "$IS_HOLIDAY" == "holiday" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 공휴일 - 실행 스킵" >> "$LOG_FILE"
    deactivate
    exit 0
fi

echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 신규종목추천 Cron 시작" >> "$LOG_FILE"
echo "실행 시간: $HOUR시 (거래일 확인 완료)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# 18시(종가 확정 시간)에는 종가 평가 모드로 실행
if [ "$HOUR" == "18" ]; then
    echo "[INFO] 18시 종가 평가 모드 실행" >> "$LOG_FILE"

    # 1. 기존 추천 종목의 종가 추적 기록
    echo "[STEP 1] 종가 추적 기록 시작..." >> "$LOG_FILE"
    python -c "
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from 신규종목추천.src.reports.daily_tracker import DailyPriceTracker
from 신규종목추천.src.utils.database import db

async def track_closing_prices():
    await db.connect()
    try:
        tracker = DailyPriceTracker()
        result = await tracker.record_daily_prices()
        print(f'종가 기록: {result[\"recorded\"]}/{result[\"total\"]}건')
        return result
    finally:
        await db.disconnect()

asyncio.run(track_closing_prices())
" >> "$LOG_FILE" 2>&1

    # 2. 추적 리포트 생성
    echo "[STEP 2] 추적 리포트 생성..." >> "$LOG_FILE"
    python -c "
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from 신규종목추천.src.reports.daily_tracker import DailyPriceTracker
from 신규종목추천.src.utils.database import db

async def generate_report():
    await db.connect()
    try:
        tracker = DailyPriceTracker()
        report_path = await tracker.save_tracking_report()
        print(f'추적 리포트: {report_path}')
        return report_path
    finally:
        await db.disconnect()

asyncio.run(generate_report())
" >> "$LOG_FILE" 2>&1

    # 3. 신규 추천 실행
    echo "[STEP 3] 신규 추천 실행..." >> "$LOG_FILE"
    python 신규종목추천/run.py >> "$LOG_FILE" 2>&1

    # 4. 성과 요약 출력
    echo "[STEP 4] 성과 요약 생성..." >> "$LOG_FILE"
    python -c "
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from 신규종목추천.src.reports.daily_tracker import DailyPriceTracker
from 신규종목추천.src.utils.database import db

async def print_summary():
    await db.connect()
    try:
        tracker = DailyPriceTracker()
        summary = await tracker.get_tracking_summary()

        print('\\n===== 등급별 성과 요약 =====')
        for row in summary:
            grade = row.get('ai_grade', 'N/A')
            count = row.get('count', 0)
            avg_ret = row.get('avg_return', 0) or 0
            winners = row.get('winners', 0)
            losers = row.get('losers', 0)
            win_rate = winners / count * 100 if count > 0 else 0
            print(f'{grade}등급: {count}종목, 평균수익 {avg_ret:+.2f}%, 승률 {win_rate:.1f}%')
    finally:
        await db.disconnect()

asyncio.run(print_summary())
" >> "$LOG_FILE" 2>&1

else
    # 일반 실행 (04, 07, 10, 13, 16시)
    echo "[INFO] 일반 추천 모드 실행" >> "$LOG_FILE"
    python 신규종목추천/run.py >> "$LOG_FILE" 2>&1
fi

echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 신규종목추천 Cron 완료" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 가상환경 비활성화
deactivate
