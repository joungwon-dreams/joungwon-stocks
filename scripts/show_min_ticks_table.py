#!/usr/bin/env python3
"""
min_ticks 테이블 구조 및 데이터 조회
"""
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def show_table_structure():
    """min_ticks 테이블 구조 조회"""
    await db.connect()

    try:
        # 테이블 구조 조회
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'min_ticks'
            ORDER BY ordinal_position
        """

        columns = await db.fetch(query)

        print("\n" + "=" * 100)
        print(f"📋 min_ticks 테이블 구조")
        print("=" * 100)
        print()
        print(f"{'컬럼명':20s} | {'데이터 타입':20s} | {'NULL 허용':10s} | {'기본값':30s}")
        print("-" * 100)

        for col in columns:
            col_name = col['column_name']
            data_type = col['data_type']
            nullable = 'YES' if col['is_nullable'] == 'YES' else 'NO'
            default = col['column_default'] if col['column_default'] else '-'

            print(f"{col_name:20s} | {data_type:20s} | {nullable:10s} | {default:30s}")

        print()
        print("=" * 100)
        print()

        # 최근 데이터 조회
        data_query = """
            SELECT
                stock_code,
                timestamp,
                price,
                change_rate,
                volume,
                bid_price,
                ask_price,
                created_at
            FROM min_ticks
            ORDER BY timestamp DESC
            LIMIT 10
        """

        rows = await db.fetch(data_query)

        print("\n" + "=" * 140)
        print(f"📊 최근 10개 레코드 (총 {len(rows)}개)")
        print("=" * 140)
        print()

        if rows:
            print(f"{'종목코드':8s} | {'현재가':>9s} | {'등락률':>6s} | {'거래량':>11s} | "
                  f"{'매수호가':>9s} | {'매도호가':>9s} | {'시각':19s}")
            print("-" * 140)

            for row in rows:
                # Decimal 타입을 int/float로 변환
                price = int(row['price']) if row['price'] else 0
                change_rate = float(row['change_rate']) if row['change_rate'] else 0.0
                volume = int(row['volume']) if row['volume'] else 0
                bid_price = int(row['bid_price']) if row['bid_price'] else 0
                ask_price = int(row['ask_price']) if row['ask_price'] else 0

                print(f"{row['stock_code']:8s} | {price:9,d}원 | {change_rate:+6.2f}% | {volume:11,d}주 | "
                      f"{bid_price:9,d}원 | {ask_price:9,d}원 | {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("📭 데이터가 없습니다.")

        print()
        print("=" * 140)
        print()

        # 통계 정보
        stats_query = """
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT stock_code) as unique_stocks,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest
            FROM min_ticks
        """

        stats = await db.fetchrow(stats_query)

        print("\n" + "=" * 100)
        print(f"📈 데이터 통계")
        print("=" * 100)
        print()
        print(f"총 레코드 수: {stats['total_records']:,}개")
        print(f"고유 종목 수: {stats['unique_stocks']:,}개")
        if stats['earliest']:
            print(f"최초 데이터: {stats['earliest'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"최신 데이터: {stats['latest'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("=" * 100)
        print()

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(show_table_structure())
