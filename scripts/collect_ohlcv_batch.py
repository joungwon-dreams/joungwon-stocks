"""
pykrx를 사용하여 전체 종목의 OHLCV 데이터 수집
개별 종목별로 수집 (병렬 처리)
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pykrx import stock
import concurrent.futures
import time

def fetch_ohlcv_single(code: str, start_str: str, end_str: str):
    """단일 종목 OHLCV 수집 (동기 함수)"""
    # 우선주 코드 (알파벳 포함) 스킵
    if not code.isdigit():
        return code, []

    try:
        df = stock.get_market_ohlcv(start_str, end_str, code)
        if df.empty:
            return code, []

        records = []
        for date_idx, row in df.iterrows():
            records.append({
                'code': code,
                'date': date_idx.strftime('%Y-%m-%d'),
                'open': int(row['시가']),
                'high': int(row['고가']),
                'low': int(row['저가']),
                'close': int(row['종가']),
                'volume': int(row['거래량'])
            })
        return code, records
    except Exception as e:
        return code, []

async def collect_ohlcv_batch():
    """전체 종목 OHLCV 데이터 배치 수집"""

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

    # 활성 종목 목록
    existing_codes = await conn.fetch("""
        SELECT stock_code FROM stocks
        WHERE is_delisted = FALSE AND market IN ('KOSPI', 'KOSDAQ')
    """)
    stock_codes = [r['stock_code'] for r in existing_codes]
    print(f"대상 종목: {len(stock_codes)}개", flush=True)

    # 병렬 수집 (ThreadPoolExecutor)
    total_inserted = 0
    total_updated = 0
    batch_size = 50

    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(stock_codes) - 1) // batch_size + 1

        print(f"\n배치 {batch_num}/{total_batches} 처리 중... ({len(batch)}개 종목)", flush=True)

        # ThreadPoolExecutor로 병렬 수집
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_ohlcv_single, code, start_str, end_str): code
                for code in batch
            }

            for future in concurrent.futures.as_completed(futures):
                code, records = future.result()

                if not records:
                    continue

                # DB에 저장
                for rec in records:
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
                        """, rec['code'], rec['date'],
                            rec['open'], rec['high'], rec['low'],
                            rec['close'], rec['volume'])

                        if 'INSERT' in result:
                            total_inserted += 1
                        else:
                            total_updated += 1
                    except:
                        continue

        print(f"  누적: {total_inserted}신규 / {total_updated}업데이트", flush=True)
        time.sleep(1)  # Rate limit

    print(f"\n완료! 총 {total_inserted} 신규, {total_updated} 업데이트")

    # 결과 확인
    count = await conn.fetchval("""
        SELECT COUNT(DISTINCT stock_code) FROM daily_ohlcv
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
    """)
    print(f"최근 5일 OHLCV 데이터 보유 종목: {count}개")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(collect_ohlcv_batch())
