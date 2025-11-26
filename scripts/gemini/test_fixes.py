"""
Test fixed fetchers:
1. Daum Supply - investor trends (fixed field names)
2. Naver Consensus - analyst reports (now uses news API)
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher

async def main():
    stock_code = "015760"  # 한국전력
    print(f"🚀 Testing FIXED fetchers for {stock_code}...\n")

    # 1. Test Fixed Daum Supply (Investor Trends)
    print("=" * 60)
    print("1. Daum Investor Trends (투자자 매매동향) - FIXED")
    print("=" * 60)
    supply = DaumSupplyFetcher()
    trends = await supply.fetch_history(stock_code, days=5)

    print(f"\n📈 Investor Trends (Last 5 days): {len(trends)} records")
    for trend in trends:
        print(f"\n   날짜: {trend['date']}")
        print(f"   외국인: {trend['foreign']:,.0f}주")
        print(f"   기관: {trend['institutional']:,.0f}주")
        print(f"   개인: {trend['individual']:,.0f}주")

    # 2. Test Fixed Naver Analyst Reports (News-based)
    print("\n" + "=" * 60)
    print("2. Naver Analyst Reports (뉴스 기반) - FIXED")
    print("=" * 60)
    cons = NaverConsensusFetcher()
    reports = await cons.fetch_analyst_reports(stock_code)

    print(f"\n📰 Report-related News: {len(reports)} records")
    if not reports:
        print("   ⚠️ No recent report-related news found (this is OK if there are no recent analyst reports)")
    else:
        for i, report in enumerate(reports[:5], 1):  # Show first 5
            print(f"\n   [{i}] {report['date']} - {report['firm']}")
            print(f"       제목: {report['title']}")
            print(f"       URL: {report['url']}")

    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
