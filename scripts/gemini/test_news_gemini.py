import asyncio
from naver.news import NaverNewsFetcher

async def test():
    fetcher = NaverNewsFetcher()
    news = await fetcher.fetch_news('015760')
    print(f'Total news fetched: {len(news)}\n')

    for i, item in enumerate(news[:3], 1):
        print(f'{i}. {item["title"]}')
        print(f'   Sentiment: {item.get("sentiment", "N/A")}')
        summary = item.get("summary", "N/A")
        if summary and summary != "N/A":
            print(f'   Summary: {summary[:150]}...')
        else:
            print(f'   Summary: {summary}')
        print(f'   Source: {item.get("source", "N/A")}')
        print(f'   Date: {item.get("collected_at", "N/A")}')
        print()

asyncio.run(test())
