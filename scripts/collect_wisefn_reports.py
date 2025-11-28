"""
Collect WISEfn Analyst Reports for Stock Assets
Fetches analyst reports and saves to database for all stocks in stock_assets
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper
from src.config.database import db

async def collect_reports_for_stock(stock_code: str, stock_name: str):
    """Collect WISEfn reports for a single stock"""
    print(f"\n📊 Collecting reports for {stock_name} ({stock_code})...")

    scraper = WISEfnReportsScraper()

    try:
        # Fetch and save to database
        reports = await scraper.fetch_and_save(stock_code)

        if reports:
            print(f"   ✅ Saved {len(reports)} reports to database")
            return len(reports)
        else:
            print(f"   ⚠️  No reports found")
            return 0

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0

async def main():
    """Main function to collect reports for all stock assets"""
    print("=" * 80)
    print("WISEfn Analyst Reports Collection")
    print("=" * 80)

    # Connect to database
    await db.connect()

    # Get all stocks from stock_assets with quantity > 0
    query = """
        SELECT sa.stock_code, s.stock_name
        FROM stock_assets sa
        JOIN stocks s ON sa.stock_code = s.stock_code
        WHERE sa.quantity > 0
        ORDER BY sa.stock_code
    """

    stock_assets = await db.fetch(query)

    if not stock_assets:
        print("\n❌ No stock assets found in database")
        await db.disconnect()
        return

    print(f"\n📈 Found {len(stock_assets)} stocks with holdings")
    print("-" * 80)

    total_reports = 0
    successful_stocks = 0
    failed_stocks = 0

    for i, stock in enumerate(stock_assets, 1):
        stock_code = stock['stock_code']
        stock_name = stock['stock_name']

        print(f"\n[{i}/{len(stock_assets)}] Processing {stock_name} ({stock_code})...")

        try:
            num_reports = await collect_reports_for_stock(stock_code, stock_name)

            if num_reports > 0:
                total_reports += num_reports
                successful_stocks += 1
            else:
                failed_stocks += 1

            # Add delay to avoid rate limiting (3 seconds between requests)
            if i < len(stock_assets):
                print("   ⏳ Waiting 3 seconds...")
                await asyncio.sleep(3)

        except Exception as e:
            print(f"   ❌ Failed to collect reports: {e}")
            failed_stocks += 1
            continue

    # Summary
    print("\n" + "=" * 80)
    print("Collection Summary")
    print("=" * 80)
    print(f"Total stocks processed: {len(stock_assets)}")
    print(f"Successful collections: {successful_stocks}")
    print(f"Failed collections: {failed_stocks}")
    print(f"Total reports saved: {total_reports}")
    print("=" * 80)

    # Cleanup
    await db.disconnect()
    print("\n✅ Database connection closed")

if __name__ == '__main__':
    asyncio.run(main())
