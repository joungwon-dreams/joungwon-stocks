import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.gemini.daum.price import DaumPriceFetcher
from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.naver.news import NaverNewsFetcher
# from scripts.gemini.naver.peers import NaverPeersFetcher

async def main():
    stock_code = "015760" # KEPCO
    print(f"🚀 Testing Fetchers for {stock_code}...\n")
    
    # 1. Daum Price
    print("--- Daum Price ---")
    price = DaumPriceFetcher()
    quote = await price.fetch_quote(stock_code)
    history = await price.fetch_history(stock_code, days=5)
    print(f"Quote: {quote.get('tradePrice')} (Change: {quote.get('changeRate')}%)")
    print(f"History (Last 5): {len(history)} items")
    if history: print(f"Latest: {history[-1]}")
    print()
    
    # 2. Daum Supply
    print("--- Daum Supply ---")
    supply = DaumSupplyFetcher()
    trends = await supply.fetch_history(stock_code, days=5)
    print(f"Trends (Last 5): {len(trends)} items")
    if trends: print(f"Latest: {trends[-1]}")
    print()
    
    # 3. Daum Financials
    print("--- Daum Financials ---")
    fin = DaumFinancialsFetcher()
    data = await fin.fetch_ratios(stock_code)
    print(f"Ratios: {data.get('ratios')}")
    print(f"Peers: {data.get('peers')}")
    
    # statements = await fin.fetch_statements(stock_code) # Skipping statements for now as endpoint might be tricky
    # print(f"Yearly Statements: {len(statements['yearly'])}")
    # print(f"Quarterly Statements: {len(statements['quarterly'])}")
    # if statements['yearly']: print(f"Latest Year: {statements['yearly'][-1]}")
    print()
    
    # 4. Naver Consensus
    print("--- Naver Consensus ---")
    cons = NaverConsensusFetcher()
    c_data = await cons.fetch_consensus(stock_code)
    print(f"Consensus: {c_data}")
    print()
    
    # 5. Naver Peers (Removed, using Daum)
    # print("--- Naver Peers ---")
    # peers = NaverPeersFetcher()
    # p_list = await peers.fetch_peers(stock_code)
    # print(f"Peers: {p_list}")
    # print()
    
    # 6. Naver News
    print("--- Naver News ---")
    news = NaverNewsFetcher()
    n_list = await news.fetch_news(stock_code)
    print(f"News (Top 5): {len(n_list)}")
    for n in n_list[:2]:
        print(f"- [{n['collected_at']}] {n['title']}")
    print()

if __name__ == "__main__":
    asyncio.run(main())
