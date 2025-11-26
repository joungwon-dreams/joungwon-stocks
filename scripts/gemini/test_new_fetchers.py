"""
Test newly added fetcher methods:
1. DaumFinancialsFetcher.fetch_statements() - 분기별 재무제표
2. NaverConsensusFetcher.fetch_analyst_reports() - 증권사별 리포트
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher

async def main():
    stock_code = "015760"  # 한국전력
    print(f"🚀 Testing new fetcher methods for {stock_code}...\n")

    # 1. Test Daum Financial Statements
    print("=" * 60)
    print("1. Daum Financial Statements (분기별 재무제표)")
    print("=" * 60)
    daum_fin = DaumFinancialsFetcher()
    statements = await daum_fin.fetch_statements(stock_code)

    print(f"\n📊 Yearly Statements: {len(statements['yearly'])} records")
    for stmt in statements['yearly'][:3]:  # Show first 3
        print(f"   {stmt['date']}: 매출 {stmt['revenue']:,.0f}억, "
              f"영업이익 {stmt['operating_profit']:,.0f}억, "
              f"순이익 {stmt['net_income']:,.0f}억")

    print(f"\n📊 Quarterly Statements: {len(statements['quarterly'])} records")
    for stmt in statements['quarterly'][:3]:  # Show first 3
        print(f"   {stmt['date']}: 매출 {stmt['revenue']:,.0f}억, "
              f"영업이익 {stmt['operating_profit']:,.0f}억, "
              f"순이익 {stmt['net_income']:,.0f}억")

    # 2. Test Naver Analyst Reports
    print("\n" + "=" * 60)
    print("2. Naver Analyst Reports (증권사별 리포트)")
    print("=" * 60)
    naver_cons = NaverConsensusFetcher()
    reports = await naver_cons.fetch_analyst_reports(stock_code)

    print(f"\n📰 Analyst Reports: {len(reports)} recent reports")
    for report in reports:
        print(f"\n   [{report['date']}] {report['firm']}")
        print(f"   제목: {report['title']}")
        print(f"   투자의견: {report['opinion']}")
        print(f"   목표가: {report['target_price']}")
        if report['url']:
            print(f"   URL: {report['url']}")

    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
