"""
Test Naver Financials Fetcher (Fallback for Daum)
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.naver.financials import NaverFinancialsFetcher

async def main():
    stock_code = "015760"  # 한국전력
    print(f"🚀 Testing Naver Financials Fetcher for {stock_code}...\n")

    print("=" * 60)
    print("Naver Financial Statements (Fallback)")
    print("=" * 60)

    naver_fin = NaverFinancialsFetcher()
    statements = await naver_fin.fetch_statements(stock_code)

    print(f"\n📊 Yearly Statements: {len(statements['yearly'])} records")
    for i, stmt in enumerate(statements['yearly'][:3], 1):  # Show first 3
        print(f"   [{i}] {stmt['date']}")
        print(f"       매출: {stmt['revenue']/100000000:,.0f}억원")
        print(f"       영업이익: {stmt['operating_profit']/100000000:,.0f}억원")
        print(f"       순이익: {stmt['net_income']/100000000:,.0f}억원")

    print(f"\n📊 Quarterly Statements: {len(statements['quarterly'])} records")
    for i, stmt in enumerate(statements['quarterly'][:3], 1):  # Show first 3
        print(f"   [{i}] {stmt['date']}")
        print(f"       매출: {stmt['revenue']/100000000:,.0f}억원")
        print(f"       영업이익: {stmt['operating_profit']/100000000:,.0f}억원")
        print(f"       순이익: {stmt['net_income']/100000000:,.0f}억원")

    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
