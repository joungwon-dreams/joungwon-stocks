"""
단일 종목 종합 리포트 테스트 (한국전력)
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.generate_comprehensive_holdings_report import (
    fetch_holdings_from_db,
    generate_comprehensive_report
)
import os

async def main():
    # 출력 디렉토리
    output_dir = '/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock'
    temp_dir = '/tmp/stock_charts'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    # 보유종목 조회
    holdings = await fetch_holdings_from_db()

    # 한국전력만 테스트
    stock_code = '015760'
    if stock_code in holdings:
        holding_data = holdings[stock_code]
        print(f"📝 {holding_data['name']} ({stock_code}) 테스트 리포트 생성 중...")

        report_path = await generate_comprehensive_report(
            stock_code,
            holding_data,
            output_dir,
            temp_dir
        )

        print(f"✅ 리포트 생성 완료: {report_path}")
    else:
        print(f"❌ 한국전력({stock_code})을 찾을 수 없습니다.")

if __name__ == '__main__':
    asyncio.run(main())
