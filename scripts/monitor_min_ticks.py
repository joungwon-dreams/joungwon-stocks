#!/usr/bin/env python3
"""
1분마다 min_ticks 테이블 데이터 모니터링
현재가 데이터 실시간 확인
"""
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def show_min_ticks():
    """min_ticks 테이블의 최근 데이터 조회"""
    await db.connect()

    try:
        # 각 종목별 최신 tick 데이터 조회
        query = """
            WITH latest_ticks AS (
                SELECT DISTINCT ON (stock_code)
                    stock_code,
                    timestamp,
                    price,
                    change_rate,
                    volume,
                    bid_price,
                    ask_price
                FROM min_ticks
                ORDER BY stock_code, timestamp DESC
            )
            SELECT
                sa.stock_name,
                lt.stock_code,
                lt.price AS current_price,
                lt.change_rate,
                lt.volume,
                lt.bid_price,
                lt.ask_price,
                lt.timestamp,
                sa.avg_buy_price,
                sa.quantity
            FROM latest_ticks lt
            JOIN stock_assets sa ON lt.stock_code = sa.stock_code
            WHERE sa.quantity > 0
            ORDER BY sa.total_value DESC
        """

        ticks = await db.fetch(query)

        # 출력
        print("\n" + "=" * 140)
        print(f"🕐 실시간 현재가 데이터 (min_ticks) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 140)
        print()

        if not ticks:
            print("📭 min_ticks 테이블에 데이터가 없습니다.")
            print()
            print("=" * 140)
            return

        # 헤더
        print(f"{'종목명':10s} | {'종목코드':8s} | {'현재가':>10s} | {'등락률':>8s} | "
              f"{'거래량':>12s} | {'매수호가':>10s} | {'매도호가':>10s} | "
              f"{'평단가':>10s} | {'손익률':>8s} | {'최종시각':19s}")
        print("-" * 140)

        # 데이터 출력
        for t in ticks:
            current_price = float(t['current_price'])
            avg_price = float(t['avg_buy_price'])
            profit_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

            # 색상 표시용 기호
            profit_mark = "🔴" if profit_rate > 0 else "🔵" if profit_rate < 0 else "⚪"

            print(f"{t['stock_name']:10s} | {t['stock_code']:8s} | "
                  f"{current_price:10,.0f}원 | "
                  f"{t['change_rate']:+7.2f}% | "
                  f"{t['volume']:12,}주 | "
                  f"{t['bid_price']:10,.0f}원 | "
                  f"{t['ask_price']:10,.0f}원 | "
                  f"{avg_price:10,.0f}원 | "
                  f"{profit_mark}{profit_rate:+6.2f}% | "
                  f"{t['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

        print("-" * 140)
        print(f"📊 총 {len(ticks)}개 종목")
        print("=" * 140)
        print()

    finally:
        await db.disconnect()


async def monitor_loop():
    """1분마다 반복 실행"""
    print("\n🔄 1분마다 min_ticks 모니터링 시작 (Ctrl+C로 종료)\n")

    try:
        while True:
            await show_min_ticks()
            print("⏳ 60초 대기 중...\n")
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n\n⏹️  모니터링 종료")


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='min_ticks 테이블 모니터링')
    parser.add_argument('--once', action='store_true', help='1회만 실행')
    parser.add_argument('--loop', action='store_true', help='1분마다 반복 실행')

    args = parser.parse_args()

    if args.loop:
        await monitor_loop()
    else:
        # 기본: 1회 실행
        await show_min_ticks()


if __name__ == '__main__':
    asyncio.run(main())
