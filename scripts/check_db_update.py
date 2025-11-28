import asyncio
import asyncpg
import os
from datetime import datetime

# DB 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

async def check_latest_ohlcv():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # 1. 전체 종목 중 가장 최근 날짜 확인
        row = await conn.fetchrow("SELECT MAX(date) as last_date FROM daily_ohlcv")
        last_date = row['last_date']
        print(f"📅 DB 상 가장 최근 OHLCV 날짜: {last_date}")

        # 2. 한국전력(015760)의 최근 5일 데이터 확인
        print("\n🔍 한국전력(015760) 최근 5일 데이터:")
        rows = await conn.fetch("""
            SELECT date, close, volume 
            FROM daily_ohlcv 
            WHERE stock_code = '015760' 
            ORDER BY date DESC 
            LIMIT 5
        """)
        for r in rows:
            print(f"   - {r['date']}: 종가 {int(r['close']):,}원, 거래량 {int(r['volume']):,}")

        # 3. 업데이트가 필요한지 판단
        today = datetime.now().date()
        # 어제 날짜 (평일 기준, 간단히 하루 전으로 계산)
        yesterday = today  # 오늘이 27일이므로 
        # (주의: 휴일 로직은 복잡하므로 생략하고 날짜만 비교)
        
        print(f"\n✅ 확인 결과:")
        if str(last_date) == '2025-11-26':
            print("   어제(11/26) 데이터가 업데이트 되어 있습니다.")
        else:
            print(f"   어제(11/26) 데이터가 아직 없습니다. (최신: {last_date})")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_latest_ohlcv())
