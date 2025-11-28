"""
Generate comprehensive PDF for 우리금융지주 with WISEfn data
1. Scrape WISEfn reports and save to database
2. Generate PDF from database
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper
from scripts.gemini.generate_pdf_report import PDFReportGenerator
from src.config.database import db

async def main():
    stock_code = "316140"
    stock_name = "우리금융지주"

    print("=" * 80)
    print(f"{stock_name} 종합 PDF 생성")
    print("=" * 80)

    # Connect to database
    await db.connect()

    # Step 1: Scrape and save WISEfn reports
    print(f"\n📊 Step 1: WISEfn 리포트 스크래핑 및 저장...")
    scraper = WISEfnReportsScraper()
    reports = await scraper.fetch_and_save(stock_code)

    if reports:
        print(f"   ✅ {len(reports)}개 리포트 저장 완료")
    else:
        print(f"   ⚠️  리포트 없음")

    # Step 2: Generate PDF
    print(f"\n📝 Step 2: 종합 PDF 생성...")
    generator = PDFReportGenerator(stock_code)
    await generator.fetch_all_data()
    generator.generate_charts()
    generator.generate_pdf()

    print(f"\n✅ PDF 생성 완료!")
    print(f"   파일: /Users/wonny/Dev/joungwon.stocks/reports/{stock_name}_*.pdf")

    # Disconnect
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
