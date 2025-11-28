"""
Test WISEfn Reports Scraper
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper

async def main():
    scraper = WISEfnReportsScraper()

    print("Testing WISEfn scraper for 한국전력 (015760)...")
    print("=" * 80)

    reports = await scraper.fetch_reports('015760')

    print(f"\n✅ Total reports: {len(reports)}\n")

    if reports:
        print("First 6 reports:")
        print("-" * 80)
        for i, report in enumerate(reports[:6], 1):
            print(f"\n{i}. {report['date']} - {report['brokerage']}")
            print(f"   목표주가: {report['target_price']:,}원")
            print(f"   아진대비: {report['price_change']}")
            print(f"   투자의견: {report['opinion']}")
            print(f"   리포트: {report['title'][:50]}...")
    else:
        print("❌ No reports found!")

if __name__ == '__main__':
    asyncio.run(main())
