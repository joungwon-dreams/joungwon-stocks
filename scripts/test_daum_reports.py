"""
Test Daum Finance Reports API
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.daum.reports import DaumReportsFetcher

async def main():
    fetcher = DaumReportsFetcher()

    # Test with 한국전력 (015760)
    print("Fetching Daum reports for 한국전력 (015760)...")
    reports = await fetcher.fetch_reports('015760')

    print(f"\n✅ Found {len(reports)} reports\n")

    for i, report in enumerate(reports[:6], 1):
        print(f"Report {i}:")
        print(f"  날짜: {report.get('date', 'N/A')}")
        print(f"  목표가: {report.get('target_price', 0):,}원")
        print(f"  증권사: {report.get('firm', 'N/A')}")
        print(f"  투자의견: {report.get('opinion', 'N/A')}")
        print(f"  제목: {report.get('title', 'N/A')[:50]}...")
        print(f"  URL: {report.get('url', 'N/A')}")
        print()

if __name__ == '__main__':
    asyncio.run(main())
