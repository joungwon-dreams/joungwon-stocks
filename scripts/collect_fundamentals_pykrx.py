"""
pykrx를 사용하여 전체 종목의 PBR/PER/시가총액 데이터 수집
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pykrx import stock
import time

async def collect_fundamentals():
    """전체 종목 펀더멘털 데이터 수집"""

    # DB 연결
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='stock_investment_db',
        user='wonny'
    )

    # 최근 거래일 찾기
    today = datetime.now()
    trade_date = None

    for i in range(7):
        check_date = (today - timedelta(days=i)).strftime('%Y%m%d')
        try:
            df = stock.get_market_fundamental(check_date, market="ALL")
            if len(df) > 0:
                trade_date = check_date
                print(f"거래일 확인: {trade_date}")
                break
        except:
            continue

    if not trade_date:
        print("거래일을 찾을 수 없습니다")
        return

    # KOSPI + KOSDAQ 펀더멘털 데이터 수집
    print(f"\n{trade_date} 펀더멘털 데이터 수집 중...")

    df_kospi = stock.get_market_fundamental(trade_date, market="KOSPI")
    df_kosdaq = stock.get_market_fundamental(trade_date, market="KOSDAQ")

    print(f"KOSPI: {len(df_kospi)}개, KOSDAQ: {len(df_kosdaq)}개")

    # 시가총액 데이터도 수집
    print(f"\n시가총액 데이터 수집 중...")
    df_cap_kospi = stock.get_market_cap(trade_date, market="KOSPI")
    df_cap_kosdaq = stock.get_market_cap(trade_date, market="KOSDAQ")

    # 데이터 병합
    import pandas as pd
    df_fundamental = pd.concat([df_kospi, df_kosdaq])
    df_cap = pd.concat([df_cap_kospi, df_cap_kosdaq])

    # 시가총액 병합
    df_fundamental = df_fundamental.join(df_cap[['시가총액']], how='left')

    print(f"\n총 {len(df_fundamental)}개 종목 데이터 수집 완료")
    print(f"컬럼: {df_fundamental.columns.tolist()}")
    print(df_fundamental.head())

    # stocks 테이블에 있는 종목만 가져오기
    existing_codes = await conn.fetch("SELECT stock_code FROM stocks WHERE is_delisted = FALSE")
    existing_set = {r['stock_code'] for r in existing_codes}
    print(f"stocks 테이블에 {len(existing_set)}개 종목 존재")

    # DB 업데이트
    updated = 0
    inserted = 0
    skipped = 0

    for code in df_fundamental.index:
        if code not in existing_set:
            skipped += 1
            continue
        row = df_fundamental.loc[code]

        # NaN 처리
        pbr = float(row['PBR']) if pd.notna(row['PBR']) and row['PBR'] > 0 else None
        per = float(row['PER']) if pd.notna(row['PER']) and row['PER'] > 0 else None
        eps = int(row['EPS']) if pd.notna(row['EPS']) else None
        bps = int(row['BPS']) if pd.notna(row['BPS']) else None
        dividend_yield = float(row['DIV']) if pd.notna(row.get('DIV', 0)) else None
        market_cap = int(row['시가총액']) if pd.notna(row.get('시가총액', 0)) else None

        # UPSERT
        result = await conn.execute("""
            INSERT INTO stock_fundamentals (stock_code, pbr, per, eps, bps, dividend_yield, market_cap, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (stock_code) DO UPDATE SET
                pbr = COALESCE(EXCLUDED.pbr, stock_fundamentals.pbr),
                per = COALESCE(EXCLUDED.per, stock_fundamentals.per),
                eps = COALESCE(EXCLUDED.eps, stock_fundamentals.eps),
                bps = COALESCE(EXCLUDED.bps, stock_fundamentals.bps),
                dividend_yield = COALESCE(EXCLUDED.dividend_yield, stock_fundamentals.dividend_yield),
                market_cap = COALESCE(EXCLUDED.market_cap, stock_fundamentals.market_cap),
                updated_at = NOW()
        """, code, pbr, per, eps, bps, dividend_yield, market_cap)

        if 'INSERT' in result:
            inserted += 1
        else:
            updated += 1

    print(f"\nDB 업데이트 완료: 신규 {inserted}개, 업데이트 {updated}개, 스킵 {skipped}개")

    # 결과 확인
    count = await conn.fetchval("""
        SELECT COUNT(*) FROM stock_fundamentals
        WHERE pbr IS NOT NULL AND pbr > 0
          AND per IS NOT NULL AND per > 0
    """)
    print(f"유효한 PBR/PER 데이터: {count}개 종목")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(collect_fundamentals())
