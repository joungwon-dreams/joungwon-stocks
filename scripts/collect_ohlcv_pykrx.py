"""
pykrx를 사용하여 전체 종목의 OHLCV 데이터 수집 (최근 60일)
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd
import time

async def collect_ohlcv():
    """전체 종목 OHLCV 데이터 수집"""

    # DB 연결
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='stock_investment_db',
        user='wonny'
    )

    # 날짜 범위 설정 (최근 60일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    print(f"OHLCV 데이터 수집: {start_str} ~ {end_str}")

    # stocks 테이블에서 활성 종목 가져오기
    existing_codes = await conn.fetch("""
        SELECT stock_code FROM stocks
        WHERE is_delisted = FALSE AND market IN ('KOSPI', 'KOSDAQ')
    """)
    stock_codes = [r['stock_code'] for r in existing_codes]
    print(f"대상 종목: {len(stock_codes)}개")

    # 배치 처리
    batch_size = 100
    total_inserted = 0
    total_updated = 0

    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i+batch_size]
        print(f"\n배치 {i//batch_size + 1}/{(len(stock_codes)-1)//batch_size + 1}: {len(batch)}개 종목...")

        for code in batch:
            try:
                # pykrx로 OHLCV 데이터 가져오기
                df = stock.get_market_ohlcv(start_str, end_str, code)

                if df.empty:
                    continue

                # 데이터 저장
                for date_idx, row in df.iterrows():
                    date_str = date_idx.strftime('%Y-%m-%d')

                    result = await conn.execute("""
                        INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (stock_code, date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """, code, date_str,
                        int(row['시가']), int(row['고가']), int(row['저가']),
                        int(row['종가']), int(row['거래량']))

                    if 'INSERT' in result:
                        total_inserted += 1
                    else:
                        total_updated += 1

            except Exception as e:
                print(f"  {code} 오류: {e}")
                continue

        print(f"  누적: {total_inserted} 신규, {total_updated} 업데이트")
        time.sleep(0.5)  # Rate limit

    print(f"\n완료! 총 {total_inserted} 신규, {total_updated} 업데이트")

    # 결과 확인
    count = await conn.fetchval("""
        SELECT COUNT(DISTINCT stock_code) FROM daily_ohlcv
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
    """)
    print(f"최근 5일 OHLCV 데이터 보유 종목: {count}개")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(collect_ohlcv())
