import aiohttp
import asyncio
import json

async def main():
    stock_code = "015760"
    symbol_code = f"A{stock_code}"
    # Daum Finance uses a different endpoint structure usually.
    # Let's try the one in the code and also a common one.
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://finance.daum.net/quotes/A{stock_code}'
    }
    
    # 1. Try Daum singular 'quote' endpoint
    url1 = f"https://finance.daum.net/api/quote/A{stock_code}/financials"
    print(f"Testing Daum URL: {url1}")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url1) as resp:
            print(f"Daum Status: {resp.status}")
            if resp.status == 200:
                print("Daum Success!")
                data = await resp.json()
                print(f"Daum Keys: {data.keys()}")
                if 'data' in data:
                    content = data['data']
                    print(f"Daum Data Type: {type(content)}")
                    if isinstance(content, list):
                        print(f"Daum Data Sample: {json.dumps(content[:1], ensure_ascii=False)}")
                    else:
                        print(f"Daum Data Sample: {json.dumps(content, ensure_ascii=False)[:200]}")
            else:
                print(f"Daum Error: {resp.status}")

    print("\n--- Naver Financials API ---")
    # 2. Try Naver Financials (Annual & Quarterly)
    headers_naver = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.stock.naver.com/'
    }
    
    for period in ['annual', 'quarter']: # Trying 'quarter' based on common patterns
        url_naver = f"https://m.stock.naver.com/api/stock/{stock_code}/finance/{period}"
        print(f"Testing Naver URL: {url_naver}")
        
        async with aiohttp.ClientSession(headers=headers_naver) as session:
            async with session.get(url_naver) as resp:
                print(f"Naver {period} Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Naver {period} Keys: {data.keys()}")
                    if 'financeInfo' in data:
                        fin_info = data['financeInfo']
                        print(f"Naver {period} Finance Info Type: {type(fin_info)}")
                        if isinstance(fin_info, list) and len(fin_info) > 0:
                             print(f"First Item: {json.dumps(fin_info[0], ensure_ascii=False)}")
                        elif isinstance(fin_info, dict):
                             print(f"Finance Info Keys: {fin_info.keys()}")
                             if 'trTitleList' in fin_info:
                                 print(f"Titles: {json.dumps(fin_info['trTitleList'], ensure_ascii=False)}")
                             if 'rowList' in fin_info:
                                 print(f"Row List Sample: {json.dumps(fin_info['rowList'][:5], ensure_ascii=False)}")
    # 3. Test Supply API with KEPCO (015760)
    print("\n--- Daum Supply API (KEPCO) ---")
    kepco_code = "015760"
    url_supply = f"https://finance.daum.net/api/investor/days?symbolCode=A{kepco_code}&days=5"
    headers_supply = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://finance.daum.net/quotes/A{kepco_code}#investor'
    }
    
    async with aiohttp.ClientSession(headers=headers_supply) as session:
        async with session.get(url_supply) as resp:
            print(f"Supply Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
    # 4. Test Daum Sectors Endpoint (for Dividend & Sector)
    print("\n--- Daum Sectors API ---")
    url_sectors = f"https://finance.daum.net/api/quote/A{stock_code}/sectors"
    print(f"Testing URL: {url_sectors}")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_sectors) as resp:
            print(f"Sectors Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                if 'data' in data:
                    items = data['data']
                    print(f"Items Count: {len(items)}")
                    # Find target stock
                    target = next((item for item in items if item['symbolCode'] == f"A{stock_code}"), None)
                    if target:
                        print(f"Target Stock Data: {json.dumps(target, ensure_ascii=False)}")
                    
                    # Check if sector name is available in the response wrapper or items
                    print(f"Response Keys: {data.keys()}")
    # 5. Test Daum Quote Snapshot (for Dividend Yield)
    print("\n--- Daum Quote Snapshot ---")
    url_quote = f"https://finance.daum.net/api/quotes/A{stock_code}?summary=false&changeStatistics=true"
    print(f"Testing URL: {url_quote}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_quote) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Quote Keys: {data.keys()}")
                # Check for dividend yield (dvr or similar)
                print(f"Dividend Yield (dvr): {data.get('dvr')}")
                print(f"Dividend Yield (dividendYield): {data.get('dividendYield')}")
                
    # 6. Test Naver Company Summary (for Business Segments)
    print("\n--- Naver Company Summary ---")
    url_summary = f"https://m.stock.naver.com/api/stock/{stock_code}/basic"
    print(f"Testing URL: {url_summary}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_summary) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Summary Keys: {data.keys()}")
                if 'corporateSummary' in data:
                    print(f"Corporate Summary: {data['corporateSummary']}")
    # 7. Test Daum Consensus
    print("\n--- Daum Consensus Check ---")
    url_daum_consensus = f"https://finance.daum.net/api/quote/A{stock_code}/consensus"
    print(f"Testing URL: {url_daum_consensus}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_daum_consensus) as resp:
            print(f"Daum Consensus Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                if 'data' in data:
                    print(f"Daum Consensus Data: {json.dumps(data['data'], ensure_ascii=False)[:500]}")

    # 8. Test Daum Analyst Reports
    print("\n--- Daum Analyst Reports Check ---")
    # Try finding reports for the specific stock
    # Common pattern: /api/research/company?symbolCode=A...
    url_reports = f"https://finance.daum.net/api/research/company?symbolCode=A{stock_code}&page=1&perPage=10"
    print(f"Testing URL: {url_reports}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_reports) as resp:
            print(f"Daum Reports Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                if 'data' in data:
                    print(f"Reports Count: {len(data['data'])}")
                    if len(data['data']) > 0:
                        print(f"First Report: {json.dumps(data['data'][0], ensure_ascii=False)}")

    # 9. Test Daum Credit Rating (Corporate Info)
    print("\n--- Daum Corporate Info (Credit?) ---")
    url_corp = f"https://finance.daum.net/api/quote/A{stock_code}/corporate_info" # Guessing endpoint
    print(f"Testing URL: {url_corp}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url_corp) as resp:
            print(f"Daum Corp Info Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Corp Info Keys: {data.keys()}")

if __name__ == "__main__":
    asyncio.run(main())
