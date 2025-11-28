#!/usr/bin/env python3
"""
보유종목 리스트 확인 스크립트
스크린샷 기준으로 업데이트된 데이터 표시
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def main():
    await db.connect()

    # 보유종목 조회
    holdings = await db.fetch("""
        SELECT
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            total_value
        FROM stock_assets
        WHERE quantity > 0
        ORDER BY total_value DESC
    """)

    # 예수금 조회
    cash_row = await db.fetchrow("SELECT balance FROM cash_balance LIMIT 1")
    cash_balance = float(cash_row['balance']) if cash_row else 0

    # 총 자산 계산
    total_stock_value = sum(float(h['total_value']) for h in holdings)
    total_assets = cash_balance + total_stock_value

    # 출력
    print("=" * 100)
    print("📊 보유종목 리스트 (스크린샷 기준)")
    print("=" * 100)
    print()

    print(f"보유종목: {len(holdings)}개")
    print("-" * 100)
    print(f"{'종목명':12s} | {'종목코드':8s} | {'수량':>6s} | {'평균단가':>10s} | {'현재가':>10s} | {'평가금액':>14s}")
    print("-" * 100)

    for h in holdings:
        print(f"{h['stock_name']:10s} | {h['stock_code']:8s} | "
              f"{h['quantity']:6d}주 | "
              f"{h['avg_buy_price']:10,.0f}원 | "
              f"{h['current_price']:10,.0f}원 | "
              f"{h['total_value']:14,.0f}원")

    print("-" * 100)
    print()
    print(f"💰 예수금:         {cash_balance:>20,.0f}원")
    print(f"📊 주식 평가액:   {total_stock_value:>20,.0f}원")
    print(f"💵 총 자산:       {total_assets:>20,.0f}원")
    print()
    print("=" * 100)

    await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
