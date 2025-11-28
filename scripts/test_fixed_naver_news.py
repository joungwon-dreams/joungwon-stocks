"""
수정된 Naver News Fetcher 테스트
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier4_browser_automation.naver_stock_news_fetcher import NaverStockNewsFetcher

async def test_naver_news():
    print("="*60)
    print("수정된 Naver News Fetcher 테스트")
    print("="*60)

    # Fetcher 생성
    config = {
        'headless': True,
        'viewport': {'width': 1920, 'height': 1080}
    }

    fetcher = NaverStockNewsFetcher(site_id=999, config=config)

    try:
        # 브라우저 초기화
        await fetcher.initialize()
        print("✅ 브라우저 초기화 완료\n")

        # 한국전력 뉴스 수집
        ticker = '015760'
        print(f"한국전력 ({ticker}) 뉴스 수집 중...")

        data = await fetcher.fetch_data(ticker)

        if data:
            print(f"\n✅ 뉴스 수집 성공!")
            print(f"   총 {data['news_count']}건")

            print("\n" + "="*60)
            print("수집된 뉴스 (처음 10건)")
            print("="*60)

            for i, news in enumerate(data['news_list'][:10], 1):
                print(f"\n뉴스 {i}:")
                print(f"  제목: {news.get('title', 'N/A')}")
                print(f"  출처: {news.get('source', 'N/A')}")
                print(f"  날짜: {news.get('date', 'N/A')}")
                print(f"  감성: {news.get('sentiment', 'N/A')}")
                print(f"  URL: {news.get('url', 'N/A')[:80]}...")

        else:
            print("❌ 뉴스 수집 실패")

    finally:
        # 브라우저 종료
        await fetcher.close()
        print("\n✅ 브라우저 종료")

asyncio.run(test_naver_news())
