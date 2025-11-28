"""
Test WISEfn Database Read and PDF Generation
Tests reading from database and generating PDF (no scraping required)
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

    print(f"=== Testing WISEfn Database Read for {stock_name} ({stock_code}) ===\n")

    # Initialize database connection
    await db.connect()

    # Step 1: Retrieve from database
    print("Step 1: Retrieving reports from database...")
    db_reports = await WISEfnReportsScraper.get_from_db(stock_code, limit=10)

    if not db_reports:
        print("❌ No reports found in database!")
        await db.disconnect()
        return

    print(f"✅ Retrieved {len(db_reports)} reports from database\n")

    # Display all reports
    print("Reports from database:")
    print("-" * 80)
    for i, report in enumerate(db_reports, 1):
        print(f"{i}. {report['date']} | {report['brokerage']:4s} | {report['target_price']:>7,}원")
        print(f"   {report['opinion']:4s} | {report['price_change']:>10s} | {report['title'][:50]}")
        print()

    # Step 2: Generate PDF using database data
    print("Step 2: Generating PDF with Daum Finance design using database data...")
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
