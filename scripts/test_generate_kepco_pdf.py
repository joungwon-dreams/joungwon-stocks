"""
Generate comprehensive PDF for 한국전력 with WISEfn database integration
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.generate_pdf_report import PDFReportGenerator
from src.config.database import db

async def main():
    print("=" * 80)
    print("한국전력 종합 PDF 생성 (WISEfn DB 통합)")
    print("=" * 80)

    # Connect to database
    await db.connect()

    # Generate PDF
    generator = PDFReportGenerator('015760')
    await generator.fetch_all_data()
    generator.generate_charts()
    generator.generate_pdf()

    print(f"\n✅ PDF 생성 완료: {generator.pdf_path}")
    print(f"\nTo open: open '{generator.pdf_path}'")

    # Disconnect
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
