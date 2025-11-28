"""
pykrx를 사용하여 전체 종목의 OHLCV 데이터 수집 (단순 순차 처리)
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pykrx import stock
import sys

async def collect_ohlcv_simple():
    """전체 종목 OHLCV 데이터 수집"""

    # DB 연결
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='stock_investment_db',
        user='wonny'
    )

    # 날짜 범위 (최근 60일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    print(f"OHLCV 수집 기간: {start_str} ~ {end_str}", flush=True)

    # 활성 종목 목록 (숫자만)
    existing_codes = await conn.fetch("""
        SELECT stock_code FROM stocks
        WHERE is_delisted = FALSE AND market IN ('KOSPI', 'KOSDAQ')
          AND stock_code ~ '^[0-9]+$'
    """)
    stock_codes = [r['stock_code'] for r in existing_codes]
    print(f"대상 종목: {len(stock_codes)}개", flush=True)

    total_inserted = 0
    total_updated = 0
    errors = 0

    for idx, code in enumerate(stock_codes):
        try:
            df = stock.get_market_ohlcv(start_str, end_str, code)

            if df.empty:
                continue

            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                result = await conn.execute("""
                    INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (stock_code, date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low = EXCLUDED.low, close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """, code, date_str,
                    int(row['시가']), int(row['고가']), int(row['저가']),
                    int(row['종가']), int(row['거래량']))

                if 'INSERT' in result:
                    total_inserted += 1
                else:
                    total_updated += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  에러 ({code}): {e}", flush=True)
            continue

        # 진행 상황 출력
        if (idx + 1) % 100 == 0:
            print(f"진행: {idx+1}/{len(stock_codes)} ({(idx+1)*100//len(stock_codes)}%) - "
                  f"신규:{total_inserted}, 업데이트:{total_updated}, 에러:{errors}", flush=True)

    print(f"\n완료! 신규:{total_inserted}, 업데이트:{total_updated}, 에러:{errors}", flush=True)

    # 결과 확인
    count = await conn.fetchval("""
        SELECT COUNT(DISTINCT stock_code) FROM daily_ohlcv
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
    """)
    print(f"최근 5일 OHLCV 데이터 보유 종목: {count}개", flush=True)

    await conn.close()

if __name__ == '__main__':
    asyncio.run(collect_ohlcv_simple())
