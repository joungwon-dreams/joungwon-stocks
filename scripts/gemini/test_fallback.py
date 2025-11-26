"""
Test Daum->Naver Fallback for Financial Statements
Simulates Daum failure to verify Naver fallback works
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.naver.financials import NaverFinancialsFetcher

# Mock Daum fetcher that returns empty data
class FailingDaumFetcher(DaumFinancialsFetcher):
    async def fetch_statements(self, stock_code: str):
        print("   [MOCK] Daum returning empty data...")
        return {'yearly': [], 'quarterly': []}

async def test_fallback(stock_code: str):
    """Test fallback logic"""
    print(f"🧪 Testing Daum->Naver fallback for {stock_code}...\n")

    # 1. Try Daum first (will fail intentionally)
    daum_fin = FailingDaumFetcher()
    statements = await daum_fin.fetch_statements(stock_code)
    source = "Daum"

    print(f"   📊 Daum result: yearly={len(statements['yearly'])}, quarterly={len(statements['quarterly'])}")

    # 2. Fallback to Naver if Daum is empty
    if not statements['yearly'] and not statements['quarterly']:
        print(f"   ⚠️ Daum financials empty, trying Naver...")
        naver_fin = NaverFinancialsFetcher()
        statements = await naver_fin.fetch_statements(stock_code)
        source = "Naver"

        print(f"   📊 Naver result: yearly={len(statements['yearly'])}, quarterly={len(statements['quarterly'])}")

    if not statements['yearly'] and not statements['quarterly']:
        print(f"   ❌ FAILED: No financial statements available (Daum & Naver)")
        return False

    print(f"   ✅ SUCCESS: Fetched financials from {source}")

    # Show sample data
    if statements['yearly']:
        print(f"\n   Sample Yearly Data (from {source}):")
        stmt = statements['yearly'][0]
        print(f"   - Date: {stmt['date']}")
        print(f"   - Revenue: {stmt['revenue']/100000000:,.0f}억원")

    return True

async def main():
    stock_code = "015760"  # 한국전력

    result = await test_fallback(stock_code)

    print("\n" + "=" * 60)
    if result:
        print("✅ Fallback test PASSED - Naver backup works!")
    else:
        print("❌ Fallback test FAILED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
