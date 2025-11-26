import asyncio
import sys
import json
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from scripts.gemini.naver.financials import NaverFinancialsFetcher

async def main():
    fetcher = NaverFinancialsFetcher()
    stock_code = "015760" # KEPCO
    
    print(f"Fetching financials for {stock_code} from Naver...")
    data = await fetcher.fetch_statements(stock_code)
    
    print("\n--- Yearly ---")
    for item in data['yearly']:
        print(item)
        
    print("\n--- Quarterly ---")
    for item in data['quarterly']:
        print(item)

if __name__ == "__main__":
    asyncio.run(main())
