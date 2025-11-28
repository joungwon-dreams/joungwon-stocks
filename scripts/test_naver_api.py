import asyncio
import aiohttp
import sys

async def main():
    stock_code = "034230" # 파라다이스
    # Try finding the correct list endpoint
    # Option 1: searchUrl (based on network inspection of similar sites)
    url = f"https://m.stock.naver.com/api/research/company/list?itemCode={stock_code}&page=1&pageSize=10"
    
    # Option 2: Maybe under /stock/{code}/research?
    # url = f"https://m.stock.naver.com/api/stock/{stock_code}/research/list"
    
    params = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)',
        'Referer': 'https://m.stock.naver.com/'
    }
    
    print(f"Testing URL: {url}")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                try:
                    data = await resp.json()
                    print(f"Data type: {type(data)}")
                    if isinstance(data, list) and len(data) > 0:
                        print("First item:", data[0])
                    else:
                        print("Data:", data)
                except Exception as e:
                    print(f"JSON Parse Error: {e}")
                    print("Text:", await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
