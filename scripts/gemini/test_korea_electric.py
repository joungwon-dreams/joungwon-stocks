"""
Test: Generate report for Korea Electric Power (한국전력) only
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.gemini.client import GeminiClient
from src.gemini.generator import ReportGenerator
from scripts.gemini.daum_fetcher import DaumRealtimeFetcher
from scripts.gemini.naver_fetcher import NaverRealtimeFetcher
from scripts.gemini.news_fetcher import NaverNewsFetcher

async def main():
    print("🚀 한국전력 리포트 생성 시작...")

    # Initialize
    await db.connect()
    gemini = GeminiClient()
    generator = ReportGenerator(output_dir='/Users/wonny/Dev/joungwon.stocks.report/research_report/gemini')
    daum_fetcher = DaumRealtimeFetcher()
    naver_fetcher = NaverRealtimeFetcher()
    news_fetcher = NaverNewsFetcher()

    try:
        # Fetch Korea Electric Power (015760)
        stock_code = '015760'
        stock_name = '한국전력'

        query = '''
            SELECT
                stock_code,
                stock_name,
                quantity,
                avg_buy_price,
                current_price,
                (current_price - avg_buy_price) * quantity as profit_loss,
                ROUND((current_price - avg_buy_price)::numeric / avg_buy_price * 100, 2) as profit_rate,
                avg_buy_price * quantity as total_cost,
                current_price * quantity as total_value
            FROM stock_assets
            WHERE stock_code = $1
              AND is_active = TRUE
              AND quantity > 0
        '''
        rows = await db.fetch(query, stock_code)

        if not rows:
            print(f"❌ {stock_name} ({stock_code}) 보유 정보 없음")
            return

        holding_data = dict(rows[0])
        print(f"✅ {stock_name} 보유 정보 확인")

        # Collect Data
        print("   📊 Daum Finance 데이터 수집 중...")
        daum_data = await daum_fetcher.fetch_data(stock_code)

        print("   📊 Naver Finance 데이터 수집 중...")
        naver_data = await naver_fetcher.fetch_data(stock_code)

        print("   📰 Naver 뉴스 수집 중...")
        news_data = await news_fetcher.fetch_news(stock_code)
        print(f"   ✅ 뉴스 {len(news_data)}건 수집")

        realtime_data = {
            'daum': daum_data,
            'naver': naver_data
        }

        # AI Analysis
        print("   🧠 Gemini AI 분석 중...")
        ai_analysis = await gemini.analyze_stock(stock_name, news_data, realtime_data)

        # Generate PDF
        print("   📄 PDF 생성 중...")
        pdf_path = generator.generate_pdf(stock_code, holding_data, news_data, realtime_data, ai_analysis)
        print(f"✅ 리포트 완성: {pdf_path}")

    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()
        print("\n✨ 완료!")

if __name__ == '__main__':
    asyncio.run(main())
