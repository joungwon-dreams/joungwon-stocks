import aiohttp
import asyncio
import json

async def main():
    stock_code = "005930" # Samsung Electronics
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.stock.naver.com/'
    }
    
    # 7. Test Naver Consensus Detail
    print("\n--- Naver Consensus Detail ---")
    url_consensus = f"https://m.stock.naver.com/api/stock/{stock_code}/consensus"
    print(f"Testing URL: {url_consensus}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_consensus) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Consensus Keys: {data.keys()}")
                if isinstance(data, list) and len(data) > 0:
                     print(f"Consensus Data Sample: {json.dumps(data[0], ensure_ascii=False)}")
                elif isinstance(data, dict):
                     print(f"Consensus Data Sample: {json.dumps(data, ensure_ascii=False)[:500]}")
            else:
                print(f"Naver Consensus Detail Error: {resp.status}")

    # 10. Test Naver Consensus Trend/Finance Endpoints
    print("\n--- Naver Consensus Trend/Finance Endpoints ---")
    urls_to_test = [
        f"https://m.stock.naver.com/api/stock/{stock_code}/consensus/trend",
        f"https://m.stock.naver.com/api/stock/{stock_code}/finance/consensus",
        f"https://m.stock.naver.com/front-api/stock/{stock_code}/consensus/prices",
        f"https://m.stock.naver.com/front-api/stock/{stock_code}/consensus/earnings"
    ]
    
    for url in urls_to_test:
        print(f"Testing URL: {url}")
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        print(f"Data Keys: {data.keys()}")
                        print(f"Sample: {json.dumps(data, ensure_ascii=False)[:200]}")
                    except:
                        print("Response is not JSON")
    
    print("\n--- News API (Analyst Reports Proxy Check) ---")
    # Fetch 50 items to be sure
    url_news = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize=50&page=1"
    print(f"Testing URL: {url_news}")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_news) as resp:
            if resp.status == 200:
                data = await resp.json()
                all_items = []
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict):
                            all_items.extend(entry.get('items', []))
                elif isinstance(data, dict):
                    all_items = data.get('items', [])
                
                print(f"Found {len(all_items)} news items.")
                keywords = ['목표가', '투자의견', '리포트', '상향', '하향', '유지', '매수']
                print(f"Filtering with keywords: {keywords}")
                
                found_count = 0
                for i, item in enumerate(all_items):
                    title = item.get('title', '')
                    is_match = any(k in title for k in keywords)
                    match_mark = "✅ MATCH" if is_match else "❌"
                    if is_match: found_count += 1
                    print(f"[{i+1}] {match_mark} {title}")
                
                print(f"\nTotal Matches: {found_count}")
            else:
                print(f"News API Error: {resp.status}")

if __name__ == "__main__":
    asyncio.run(main())
