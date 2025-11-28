"""
한국전력 365일 데이터 수집 (OHLCV + 수급)

pykrx를 사용하여:
1. 일별 OHLCV (365일)
2. 외국인/기관/개인 매수/매도 데이터
3. 거래대금 및 거래량
"""
import sys
import asyncio
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db

# 한국전력 종목코드
KEPCO_CODE = '015760'
KEPCO_NAME = '한국전력'


async def collect_ohlcv_data():
    """365일 OHLCV 데이터 수집"""
    print("📊 OHLCV 데이터 수집 시작...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # pykrx로 OHLCV 조회
    df = stock.get_market_ohlcv_by_date(
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d'),
        KEPCO_CODE
    )

    if df.empty:
        print("❌ OHLCV 데이터 없음")
        return None

    # DataFrame을 dict 리스트로 변환
    records = []
    for date, row in df.iterrows():
        records.append({
            'date': date.date() if hasattr(date, 'date') else date,  # datetime to date
            'open': int(row['시가']),
            'high': int(row['고가']),
            'low': int(row['저가']),
            'close': int(row['종가']),
            'volume': int(row['거래량']),
        })

    # 데이터베이스에 저장
    await db.connect()

    # daily_ohlcv 테이블에 저장
    for record in records:
        query = '''
            INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (stock_code, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        '''
        await db.execute(
            query,
            KEPCO_CODE,
            record['date'],
            record['open'],
            record['high'],
            record['low'],
            record['close'],
            record['volume']
        )

    print(f"✅ OHLCV 데이터 {len(records)}개 저장 완료")
    return records


async def collect_trading_data():
    """365일 수급 데이터 수집 (외국인/기관/개인)"""
    print("📊 수급 데이터 수집 시작...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # pykrx로 수급 데이터 조회
    df = stock.get_market_trading_value_by_date(
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d'),
        KEPCO_CODE,
        detail=True
    )

    if df.empty:
        print("❌ 수급 데이터 없음")
        return None

    # DataFrame을 dict 리스트로 변환 (순매수량만)
    records = []
    for date, row in df.iterrows():
        records.append({
            'date': date.date() if hasattr(date, 'date') else date,  # datetime to date
            'foreigner_net': int(row.get('외국인', 0)),
            'institution_net': int(row.get('기관', 0)),
            'individual_net': int(row.get('개인', 0)),
        })

    # stock_supply_demand 테이블에 저장
    for record in records:
        query = '''
            INSERT INTO stock_supply_demand (
                stock_code, date,
                foreigner_net, institution_net, individual_net
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (stock_code, date) DO UPDATE SET
                foreigner_net = EXCLUDED.foreigner_net,
                institution_net = EXCLUDED.institution_net,
                individual_net = EXCLUDED.individual_net
        '''
        await db.execute(
            query,
            KEPCO_CODE,
            record['date'],
            record['foreigner_net'],
            record['institution_net'],
            record['individual_net']
        )

    print(f"✅ 수급 데이터 {len(records)}개 저장 완료")
    return records


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"한국전력 ({KEPCO_CODE}) 365일 데이터 수집")
    print("=" * 80)
    print()

    start_time = datetime.now()

    try:
        await db.connect()

        # OHLCV 데이터 수집
        ohlcv_data = await collect_ohlcv_data()

        # 수급 데이터 수집
        trading_data = await collect_trading_data()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 80)
        print("✅ 데이터 수집 완료")
        print("=" * 80)
        print(f"⏱️  소요 시간: {duration:.1f}초")

        if ohlcv_data:
            print(f"📊 OHLCV: {len(ohlcv_data)}개 레코드")
            print(f"   - 기간: {ohlcv_data[0]['date']} ~ {ohlcv_data[-1]['date']}")
            print(f"   - 최근 종가: {ohlcv_data[-1]['close']:,}원")

        if trading_data:
            print(f"📊 수급: {len(trading_data)}개 레코드")
            print(f"   - 기간: {trading_data[0]['date']} ~ {trading_data[-1]['date']}")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
