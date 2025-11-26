"""
Test PDF generation for single stock (한국전력)
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.gemini.client import GeminiClient
from src.gemini.generator import ReportGenerator
from scripts.gemini.daum.price import DaumPriceFetcher
from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.naver.news import NaverNewsFetcher

async def fetch_stock_data(stock_code: str):
    """Fetch stock data from database"""
    query = '''
        SELECT
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            total_value,
            total_cost,
            profit_loss,
            profit_loss_rate as profit_rate,
            stop_loss_rate,
            target_profit_rate
        FROM stock_assets
        WHERE stock_code = $1
    '''
    return await db.fetchrow(query, stock_code)

async def fetch_news_data(stock_code: str):
    """Fetch news from database"""
    query = '''
        SELECT title, collected_at, summary, sentiment, source_url as url, publisher as source
        FROM stock_news
        WHERE stock_code = $1
        ORDER BY collected_at DESC
        LIMIT 20
    '''
    return await db.fetch(query, stock_code)

async def main():
    stock_code = '015760'
    stock_name = '한국전력'

    print(f"🚀 PDF 생성 테스트: {stock_name} ({stock_code})")
    print("=" * 80)

    await db.connect()

    try:
        # 1. Fetch stock data
        print("1️⃣  데이터베이스에서 종목 정보 로드...")
        stock = await fetch_stock_data(stock_code)

        if not stock:
            print(f"❌ {stock_code} 종목을 stock_assets에서 찾을 수 없습니다.")
            return

        print(f"   ✅ {stock['stock_name']}: 수량 {stock['quantity']}주")

        # 2. Fetch news
        print("\n2️⃣  뉴스 데이터 로드...")
        db_news = await fetch_news_data(stock_code)
        print(f"   ✅ 뉴스 {len(db_news)}개")

        # 3. Initialize fetchers
        print("\n3️⃣  실시간 데이터 수집...")
        daum_price = DaumPriceFetcher()
        daum_supply = DaumSupplyFetcher()
        daum_fin = DaumFinancialsFetcher()
        naver_consensus = NaverConsensusFetcher()
        naver_news = NaverNewsFetcher()

        # Daum data
        print("   📊 Daum Finance 데이터...")
        quote = await daum_price.fetch_quote(stock_code)
        fin_data = await daum_fin.fetch_ratios(stock_code)
        investor_data = await daum_supply.fetch_history(stock_code, 365)
        history_data = await daum_price.fetch_history(stock_code, 365)

        daum_data = {
            'quotes': quote,
            'financials': fin_data.get('ratios', {}),
            'peers': fin_data.get('peers', []),
            'investor_trends': [investor_data[-1]] if investor_data else []
        }
        print(f"   ✅ Daum: 시세/재무/투자자 데이터")

        # Naver data
        print("   📊 Naver Finance 데이터...")
        consensus = await naver_consensus.fetch_consensus(stock_code)
        news_data = await naver_news.fetch_news(stock_code)

        naver_data = {
            'consensus': consensus,
            'peers': []
        }
        print(f"   ✅ Naver: 컨센서스/뉴스 {len(news_data)}개")

        realtime_data = {
            'daum': daum_data,
            'naver': naver_data
        }

        # 4. AI Analysis (skip if quota exceeded)
        print("\n4️⃣  AI 분석 (Gemini)...")
        try:
            gemini = GeminiClient()
            ai_input_news = news_data if news_data else db_news
            ai_analysis = await gemini.analyze_stock(stock_name, ai_input_news, realtime_data)
            print("   ✅ AI 분석 완료")
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                print(f"   ⚠️  Gemini API 할당량 초과 - AI 분석 생략")
                ai_analysis = {
                    'summary': '(API 할당량 초과로 분석 생략)',
                    'key_points': [],
                    'recommendation': '중립',
                    'risks': [],
                    'opportunities': []
                }
            else:
                raise

        # 5. Generate PDF
        print("\n5️⃣  PDF 생성...")
        generator = ReportGenerator(output_dir='/Users/wonny/Dev/joungwon.stocks.report/research_report/gemini')

        pdf_path = generator.generate_pdf(
            stock_code,
            stock,
            news_data if news_data else db_news,
            realtime_data,
            ai_analysis,
            history_data,
            investor_data
        )

        print(f"\n✅ PDF 생성 완료!")
        print(f"📄 파일: {pdf_path}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db.disconnect()
        print("\n✨ 완료!")

if __name__ == '__main__':
    asyncio.run(main())
