#!/usr/bin/env python3
"""
Rebuild stock_assets and cash_balance from trading history Excel file
"""
import pandas as pd
import asyncio
import sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def main():
    excel_path = '/Users/wonny/Dev/joungwon.stocks.report/windows/999.xlsx'

    print("=" * 80)
    print("📊 거래내역 기반 보유자산 재구성")
    print("=" * 80)

    # Step 1: Read Excel
    print("\n📖 Step 1: 999.xlsx 파일 읽기...")
    df = pd.read_excel(excel_path)
    print(f"   총 {len(df)}건의 거래내역")

    # Step 2: Calculate holdings
    print("\n📊 Step 2: 보유종목 및 현금 계산...")

    holdings = defaultdict(lambda: {'quantity': 0, 'total_cost': 0.0})
    cash_balance = 0.0

    for idx, row in df.iterrows():
        trade_type = str(row['거래종류']).strip()
        stock_name = row['종목명']
        quantity = row['수량'] if pd.notna(row['수량']) else 0
        price = row['단가'] if pd.notna(row['단가']) else 0
        settlement = row['정산금액'] if pd.notna(row['정산금액']) else 0

        # Cash transactions
        if '입금' in trade_type:
            cash_balance += settlement
            print(f"   💰 {row['거래일자']} | {trade_type}: +{settlement:,.0f}원 (잔액: {cash_balance:,.0f}원)")

        elif '출금' in trade_type:
            cash_balance -= abs(settlement)
            print(f"   💸 {row['거래일자']} | {trade_type}: -{abs(settlement):,.0f}원 (잔액: {cash_balance:,.0f}원)")

        # Stock buy
        elif '매수' in trade_type:
            if pd.notna(stock_name):
                holdings[stock_name]['quantity'] += quantity
                holdings[stock_name]['total_cost'] += abs(settlement)
                cash_balance -= abs(settlement)
                print(f"   📈 {row['거래일자']} | {stock_name} 매수: {quantity}주 @ {price:,.0f}원 (정산: -{abs(settlement):,.0f}원)")

        # Stock sell
        elif '매도' in trade_type:
            if pd.notna(stock_name):
                holdings[stock_name]['quantity'] -= quantity

                # Calculate proportional cost reduction
                if holdings[stock_name]['quantity'] > 0:
                    cost_ratio = quantity / (holdings[stock_name]['quantity'] + quantity)
                    holdings[stock_name]['total_cost'] *= (1 - cost_ratio)
                elif holdings[stock_name]['quantity'] == 0:
                    holdings[stock_name]['total_cost'] = 0

                cash_balance += settlement
                print(f"   📉 {row['거래일자']} | {stock_name} 매도: {quantity}주 @ {price:,.0f}원 (정산: +{settlement:,.0f}원)")

    # Filter out zero-quantity holdings
    holdings = {name: data for name, data in holdings.items() if data['quantity'] > 0}

    print(f"\n💵 최종 예수금: {cash_balance:,.0f}원")
    print(f"\n📦 보유종목: {len(holdings)}개")
    for stock_name, data in sorted(holdings.items()):
        avg_price = data['total_cost'] / data['quantity'] if data['quantity'] > 0 else 0
        print(f"   - {stock_name}: {data['quantity']}주, 평균단가 {avg_price:,.0f}원")

    # Step 3: Get stock codes
    print("\n\n🔍 Step 3: 종목코드 조회...")
    await db.connect()

    stock_codes = {}
    for stock_name in holdings.keys():
        query = "SELECT stock_code FROM stocks WHERE stock_name = $1 LIMIT 1"
        row = await db.fetchrow(query, stock_name)
        if row:
            stock_codes[stock_name] = row['stock_code']
            print(f"   ✅ {stock_name} -> {row['stock_code']}")
        else:
            print(f"   ⚠️  {stock_name}: 종목코드 없음 (건너뜀)")

    # Step 4: Get current prices
    print("\n\n💹 Step 4: 현재가 조회...")
    current_prices = {}
    for stock_name, stock_code in stock_codes.items():
        query = "SELECT current_price FROM stock_assets WHERE stock_code = $1"
        row = await db.fetchrow(query, stock_code)
        if row and row['current_price'] > 0:
            current_prices[stock_code] = float(row['current_price'])
            print(f"   ✅ {stock_name}({stock_code}): {current_prices[stock_code]:,.0f}원")
        else:
            # Try from daily_ohlcv
            query2 = """
                SELECT close
                FROM daily_ohlcv
                WHERE stock_code = $1
                ORDER BY date DESC
                LIMIT 1
            """
            row2 = await db.fetchrow(query2, stock_code)
            if row2:
                current_prices[stock_code] = float(row2['close'])
                print(f"   ✅ {stock_name}({stock_code}): {current_prices[stock_code]:,.0f}원 (from daily_ohlcv)")
            else:
                current_prices[stock_code] = 0
                print(f"   ⚠️  {stock_name}({stock_code}): 현재가 없음 (0원으로 설정)")

    # Step 5: Clear stock_assets
    print("\n\n🗑️  Step 5: stock_assets 테이블 초기화...")
    await db.execute("UPDATE stock_assets SET quantity = 0, avg_buy_price = 0, current_price = 0")
    print("   ✅ 모든 보유수량 0으로 초기화")

    # Step 6: Insert holdings
    print("\n\n📥 Step 6: 보유종목 데이터 입력...")
    for stock_name, data in holdings.items():
        stock_code = stock_codes.get(stock_name)
        if not stock_code:
            continue

        quantity = data['quantity']
        avg_buy_price = data['total_cost'] / quantity
        current_price = current_prices.get(stock_code, 0)

        query = """
            UPDATE stock_assets
            SET quantity = $1,
                avg_buy_price = $2,
                current_price = $3,
                updated_at = CURRENT_TIMESTAMP
            WHERE stock_code = $4
        """

        await db.execute(query, quantity, avg_buy_price, current_price, stock_code)

        total_value = quantity * current_price
        profit_loss = quantity * (current_price - avg_buy_price)
        profit_loss_rate = (current_price - avg_buy_price) / avg_buy_price * 100 if avg_buy_price > 0 else 0

        print(f"   ✅ {stock_name}({stock_code})")
        print(f"      보유: {quantity}주, 평균단가: {avg_buy_price:,.0f}원")
        print(f"      현재가: {current_price:,.0f}원, 평가금액: {total_value:,.0f}원")
        print(f"      손익: {profit_loss:+,.0f}원 ({profit_loss_rate:+.2f}%)")

    # Step 7: Create/Update cash_balance table
    print("\n\n💰 Step 7: 예수금 테이블 생성 및 입력...")

    # Create table if not exists
    create_table_query = """
        CREATE TABLE IF NOT EXISTS cash_balance (
            id SERIAL PRIMARY KEY,
            balance NUMERIC(15, 2) NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    await db.execute(create_table_query)

    # Check if record exists
    row = await db.fetchrow("SELECT * FROM cash_balance LIMIT 1")

    if row:
        # Update existing
        await db.execute(
            "UPDATE cash_balance SET balance = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
            cash_balance, row['id']
        )
        print(f"   ✅ 예수금 업데이트: {cash_balance:,.0f}원")
    else:
        # Insert new
        await db.execute(
            "INSERT INTO cash_balance (balance) VALUES ($1)",
            cash_balance
        )
        print(f"   ✅ 예수금 생성: {cash_balance:,.0f}원")

    # Step 8: Final summary
    print("\n\n" + "=" * 80)
    print("📊 최종 보유자산 현황")
    print("=" * 80)

    # Get final holdings
    query = """
        SELECT
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            total_value,
            profit_loss,
            profit_loss_rate
        FROM stock_assets
        WHERE quantity > 0
        ORDER BY stock_code
    """

    holdings_db = await db.fetch(query)

    total_investment = 0
    total_valuation = 0

    print("\n보유종목:")
    print("-" * 80)
    for row in holdings_db:
        print(f"{row['stock_name']:10s} ({row['stock_code']}) | "
              f"{row['quantity']:4d}주 | "
              f"평단 {row['avg_buy_price']:8,.0f}원 | "
              f"현재 {row['current_price']:8,.0f}원 | "
              f"평가 {row['total_value']:11,.0f}원 | "
              f"손익 {row['profit_loss']:+10,.0f}원 ({row['profit_loss_rate']:+6.2f}%)")

        total_investment += row['quantity'] * row['avg_buy_price']
        total_valuation += row['total_value']

    print("-" * 80)
    print(f"\n💰 예수금:        {cash_balance:>15,.0f}원")
    print(f"📈 주식 투자금:  {float(total_investment):>15,.0f}원")
    print(f"📊 주식 평가액:  {float(total_valuation):>15,.0f}원")
    print(f"💵 총 자산:      {cash_balance + float(total_valuation):>15,.0f}원")
    total_pl = float(total_valuation) - float(total_investment)
    total_pl_rate = (total_pl / float(total_investment) * 100) if total_investment > 0 else 0
    print(f"📉 주식 손익:    {total_pl:>+15,.0f}원 ({total_pl_rate:+.2f}%)")

    await db.disconnect()
    print("\n✅ 완료!")


if __name__ == '__main__':
    asyncio.run(main())
