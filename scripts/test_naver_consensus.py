import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from scripts.gemini.naver.consensus import NaverConsensusFetcher

async def main():
    fetcher = NaverConsensusFetcher()
    stock_code = "034230" # 파라다이스
    
    print(f"Fetching Consensus for {stock_code}...")
    data = await fetcher.fetch_consensus(stock_code)
    print("Consensus:", data)
    
    print("\nFetching Analyst Reports...")
    reports = await fetcher.fetch_analyst_reports(stock_code)
    print(f"Found {len(reports)} reports:")
    for r in reports:
        print(r)

if __name__ == "__main__":
    asyncio.run(main())
