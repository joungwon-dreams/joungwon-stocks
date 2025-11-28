"""
collected_data의 현재가 정보를 stock_assets 테이블에 업데이트
"""
import asyncio
import sys

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def update_current_prices():
    """collected_data의 price 데이터를 stock_assets에 반영"""

    await db.connect()

    try:
        print("=" * 80)
        print("현재가 업데이트 시작")
        print("=" * 80)
        print()

        # collected_data에서 최신 price 데이터 조회
        query = '''
            WITH latest_prices AS (
                SELECT DISTINCT ON (ticker)
                    ticker,
                    (data_content->>'current_price')::numeric as current_price,
                    collected_at
                FROM collected_data
                WHERE data_type = 'price'
                  AND data_content->>'current_price' IS NOT NULL
                ORDER BY ticker, collected_at DESC
            )
            UPDATE stock_assets sa
            SET
                current_price = lp.current_price,
                updated_at = NOW()
            FROM latest_prices lp
            WHERE sa.stock_code = lp.ticker
            RETURNING sa.stock_code, sa.stock_name, sa.current_price, sa.avg_buy_price
        '''

        updated_rows = await db.fetch(query)

        print(f"✅ {len(updated_rows)}개 종목 현재가 업데이트 완료:")
        print()

        for row in updated_rows:
            print(f"{row['stock_name']} ({row['stock_code']})")
            print(f"  - 평균매수가: {row['avg_buy_price']:,}원")
            print(f"  - 현재가: {row['current_price']:,}원")
            profit_loss_rate = ((row['current_price'] - row['avg_buy_price']) / row['avg_buy_price'] * 100) if row['avg_buy_price'] > 0 else 0
            print(f"  - 손익률: {profit_loss_rate:.2f}%")
            print()

        print("=" * 80)
        print("업데이트 완료")
        print("=" * 80)

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(update_current_prices())
