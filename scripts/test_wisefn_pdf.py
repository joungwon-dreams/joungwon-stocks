"""
Test WISEfn PDF Generation with Database Integration
1. Scrapes analyst reports and saves to database
2. Retrieves from database and generates PDF
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper
from scripts.gemini.wisefn.pdf_generator import DaumReportPDFGenerator
from src.config.database import db

async def main():
    # Test stock: 한국전력 (015760)
    stock_name = "한국전력"
    stock_code = "015760"

    print(f"=== Testing WISEfn Database Integration for {stock_name} ({stock_code}) ===\n")

    # Step 1: Fetch and save to database
    print("Step 1: Scraping analyst reports from WISEfn and saving to database...")
    scraper = WISEfnReportsScraper()

    # Initialize database connection
    await db.connect()

    # Fetch and save
    reports = await scraper.fetch_and_save(stock_code)

    if not reports:
        print("❌ No reports found!")
        await db.disconnect()
        return

    print(f"✅ Scraped and saved {len(reports)} reports to database\n")

    # Step 2: Retrieve from database
    print("Step 2: Retrieving reports from database...")
    db_reports = await WISEfnReportsScraper.get_from_db(stock_code, limit=10)
    print(f"✅ Retrieved {len(db_reports)} reports from database\n")

    # Display first 3 reports from database
    print("Preview of first 3 reports from database:")
    print("-" * 80)
    for i, report in enumerate(db_reports[:3], 1):
        print(f"{i}. {report['date']} | {report['brokerage']} | {report['target_price']:,}원")
        print(f"   {report['opinion']} | {report['title'][:50]}...")
        print()

    # Step 3: Generate PDF using database data
    print("Step 3: Generating PDF with Daum Finance design using database data...")
    generator = DaumReportPDFGenerator()
    pdf_path = generator.generate_report(stock_name, stock_code, db_reports)

    print(f"\n✅ Success! PDF created at:")
    print(f"   {pdf_path}")
    print(f"\nTo open: open '{pdf_path}'")

    # Cleanup
    await db.disconnect()
    print("\n✅ Database connection closed")

if __name__ == '__main__':
    asyncio.run(main())
