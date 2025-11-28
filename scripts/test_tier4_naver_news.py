"""
Tier 4 Naver Stock News Playwright Fetcher 테스트

한국전력 뉴스 데이터로 Naver Stock News Playwright fetcher 테스트
"""
import sys
import asyncio
import json
from datetime import datetime

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier4_browser_automation.naver_stock_news_fetcher import NaverStockNewsFetcher
from src.config.database import db

# 한국전력 종목코드
KEPCO_CODE = '015760'


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("Tier 4 Naver Stock News Playwright Fetcher 테스트")
    print("=" * 80)
    print()
    print(f"대상 종목: 한국전력 ({KEPCO_CODE})")
    print()

    try:
        await db.connect()

        # Naver Stock News fetcher 생성
        config = {
            'site_id': 54,  # Naver Stock News site ID
            'domain_id': 1,
            'headless': False,  # 디버깅을 위해 브라우저 표시
            'timeout': 30000,
            'data_type': 'stock_news'
        }

        fetcher = NaverStockNewsFetcher(site_id=54, config=config)

        print("🌐 네이버 증권 뉴스 페이지 접속 중...")
        print()

        # 데이터 수집
        result = await fetcher.fetch(KEPCO_CODE)

        if result:
            print("✅ 데이터 수집 성공")
            print()
            print("=" * 80)
            print("수집된 데이터:")
            print("=" * 80)
            print()

            data = result.get('data', {})

            # 뉴스 개수
            print(f"📰 수집된 뉴스: {data.get('news_count', 0)}건")
            print()

            # 뉴스 목록 (최대 10개)
            news_list = data.get('news_list', [])
            if news_list:
                print("📋 뉴스 목록 (최근 10건):")
                for i, news in enumerate(news_list[:10], 1):
                    print(f"\n{i}. {news.get('title', 'N/A')}")
                    print(f"   언론사: {news.get('source', 'N/A')}")
                    print(f"   날짜: {news.get('date', 'N/A')}")
                    print(f"   감성: {news.get('sentiment', 'neutral')}")
                    if news.get('url'):
                        print(f"   링크: {news.get('url')}")
                print()

            # 감성 분석 요약
            if news_list:
                sentiment_counts = {
                    'positive': sum(1 for n in news_list if n.get('sentiment') == 'positive'),
                    'negative': sum(1 for n in news_list if n.get('sentiment') == 'negative'),
                    'neutral': sum(1 for n in news_list if n.get('sentiment') == 'neutral')
                }
                print("📊 감성 분석 요약:")
                print(f"   호재: {sentiment_counts['positive']}건")
                print(f"   악재: {sentiment_counts['negative']}건")
                print(f"   중립: {sentiment_counts['neutral']}건")
                print()

            # 전체 JSON 출력 (디버깅용)
            print("=" * 80)
            print("전체 데이터 (JSON):")
            print("=" * 80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print()

        else:
            print("❌ 데이터 수집 실패")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
