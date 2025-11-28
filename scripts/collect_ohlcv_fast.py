"""
pykrx를 사용하여 전체 종목의 OHLCV 데이터 빠르게 수집
get_market_ohlcv_by_date 사용 (일별 전체 종목 조회)
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd

async def collect_ohlcv_fast():
    """전체 종목 OHLCV 데이터 빠르게 수집"""

    # DB 연결
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='stock_investment_db',
        user='wonny'
    )

    # stocks 테이블에 있는 종목만 필터링용
    existing_codes = await conn.fetch("""
        SELECT stock_code FROM stocks
        WHERE is_delisted = FALSE AND market IN ('KOSPI', 'KOSDAQ')
    """)
    valid_codes = {r['stock_code'] for r in existing_codes}
    print(f"유효 종목: {len(valid_codes)}개")

    # 최근 60일 데이터 수집
    end_date = datetime.now()
    total_inserted = 0
    total_updated = 0

    for day_offset in range(60):
        target_date = end_date - timedelta(days=day_offset)
        date_str = target_date.strftime('%Y%m%d')
        date_db = target_date.strftime('%Y-%m-%d')

        try:
            # 해당 날짜의 전체 종목 OHLCV (KOSPI + KOSDAQ 따로)
            df_kospi = stock.get_market_ohlcv_by_date(date_str, date_str, "KOSPI")
            df_kosdaq = stock.get_market_ohlcv_by_date(date_str, date_str, "KOSDAQ")

            df = pd.concat([df_kospi, df_kosdaq])

            if df.empty:
                print(f"{date_str}: 데이터 없음 (휴일)")
                continue

            print(f"{date_str}: {len(df)}개 종목", end=" ")

            # DB에 저장
            inserted = 0
            updated = 0

            for code in df.index:
                if code not in valid_codes:
                    continue

                row = df.loc[code]
                try:
                    result = await conn.execute("""
                        INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (stock_code, date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """, code, date_db,
                        int(row['시가']), int(row['고가']), int(row['저가']),
                        int(row['종가']), int(row['거래량']))

                    if 'INSERT' in result:
                        inserted += 1
                    else:
                        updated += 1
                except Exception as e:
                    continue

            print(f"-> 저장: {inserted}신규, {updated}업데이트")
            total_inserted += inserted
            total_updated += updated

        except Exception as e:
            print(f"{date_str}: 오류 - {e}")
            continue

    print(f"\n완료! 총 {total_inserted} 신규, {total_updated} 업데이트")

    # 결과 확인
    count = await conn.fetchval("""
        SELECT COUNT(DISTINCT stock_code) FROM daily_ohlcv
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
    """)
    print(f"최근 5일 OHLCV 데이터 보유 종목: {count}개")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(collect_ohlcv_fast())
