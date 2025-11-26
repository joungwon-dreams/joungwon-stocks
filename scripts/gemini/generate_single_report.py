"""
Generate Single AI Investment Report
Generates a PDF report for a specific stock (e.g., KEPCO) and saves it to the download directory.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.gemini.client import GeminiClient
from src.gemini.generator import ReportGenerator
from scripts.gemini.daum.price import DaumPriceFetcher
from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.naver.news import NaverNewsFetcher
from src.utils.data_validator import validate_and_log_missing_data
from src.utils.data_retry import DataRetryManager

async def fetch_stock_assets(stock_name: str):
    """Fetch stock asset info from database"""
    query = '''
        SELECT
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            (current_price - avg_buy_price) * quantity as profit_loss,
            ROUND((current_price - avg_buy_price)::numeric / avg_buy_price * 100, 2) as profit_rate,
            avg_buy_price * quantity as total_cost,
            current_price * quantity as total_value
        FROM stock_assets
        WHERE stock_name = $1
    '''
    return await db.fetchrow(query, stock_name)

async def fetch_collected_data(stock_code):
    """Fetch collected data (news, reports) from database"""
    query = '''
        SELECT DISTINCT ON (data_type)
            data_type,
            data_content,
            site_id,
            domain_id,
            collected_at
        FROM collected_data
        WHERE ticker = $1
        ORDER BY data_type, collected_at DESC
    '''
    rows = await db.fetch(query, stock_code)
    return [dict(row) for row in rows]

async def fetch_ohlcv_history(stock_code: str, days: int = 365):
    """Fetch OHLCV history from database"""
    query = '''
        SELECT date, open, high, low, close, volume
        FROM daily_ohlcv
        WHERE stock_code = $1
        ORDER BY date DESC
        LIMIT $2
    '''
    rows = await db.fetch(query, stock_code, days)
    # Return in ascending order for charting and convert Decimals to float
    history = []
    for row in reversed(rows):
        d = dict(row)
        d['open'] = float(d['open'])
        d['high'] = float(d['high'])
        d['low'] = float(d['low'])
        d['close'] = float(d['close'])
        d['volume'] = float(d['volume'])
        history.append(d)
    return history

# ... (existing code) ...

import argparse

async def main():
    parser = argparse.ArgumentParser(description='Generate Single AI Investment Report')
    parser.add_argument('--code', type=str, default='015760', help='Target stock code')
    parser.add_argument('--name', type=str, default='한국전력', help='Target stock name')
    parser.add_argument('--shares', type=int, default=0, help='Number of shares held')
    parser.add_argument('--avg_price', type=float, default=0.0, help='Average buy price')
    args = parser.parse_args()

    target_stock_code = args.code
    target_stock_name = args.name
    output_dir = "/Users/wonny/Dev/joungwon.stocks/download"
    
    print(f"🚀 Starting AI Report Generation for {target_stock_name} ({target_stock_code})...")
    
    # Initialize components
    await db.connect()
    gemini = GeminiClient()
    generator = ReportGenerator(output_dir=output_dir)
    
    # Initialize Modular Fetchers
    daum_price = DaumPriceFetcher()
    daum_supply = DaumSupplyFetcher()
    daum_fin = DaumFinancialsFetcher()
    naver_consensus = NaverConsensusFetcher()
    naver_news = NaverNewsFetcher()
    
    try:
        # 1. Fetch Stock Asset Info (or use args)
        stock = await fetch_stock_assets(target_stock_name)
        
        # Override with args if provided
        if args.shares > 0 or args.avg_price > 0:
            current_price = 0 # Will be updated later
            stock = {
                'stock_code': target_stock_code,
                'stock_name': target_stock_name,
                'quantity': args.shares,
                'avg_buy_price': args.avg_price,
                'current_price': 0,
                'profit_loss': 0,
                'profit_rate': 0.0,
                'total_cost': args.shares * args.avg_price,
                'total_value': 0
            }
        elif not stock:
            print(f"❌ Stock '{target_stock_name}' not found in assets. Creating dummy asset data for report.")
            stock = {
                'stock_code': target_stock_code,
                'stock_name': target_stock_name,
                'quantity': 0,
                'avg_buy_price': 0,
                'current_price': 0,
                'profit_loss': 0,
                'profit_rate': 0.0,
                'total_cost': 0,
                'total_value': 0
            }
            
        stock_code = stock['stock_code'] # Should match target_stock_code
            
        stock_code = stock['stock_code']
        print(f"🔄 Processing {target_stock_name} ({stock_code})...")
        
        # 2. Collect Data
        # DB Data
        db_data = await fetch_collected_data(stock_code)
        
        # Historical Data (365 days)
        print("   📉 Fetching 365 days OHLCV history...")
        history_data = await fetch_ohlcv_history(stock_code, 365)
        
        # Fallback to Daum if DB empty
        if not history_data:
            print("   ⚠️ No DB history found. Fetching from Daum Finance...")
            history_data = await daum_price.fetch_history(stock_code, 365)
            
        # Investor Trends (365 days for chart)
        print("   📉 Fetching Investor Trends...")
        investor_data = await daum_supply.fetch_history(stock_code, 365)
        
        # Real-time Data
        print("   📊 Fetching Daum Finance data (Price & Financials)...")
        quote = await daum_price.fetch_quote(stock_code)
        fin_data = await daum_fin.fetch_ratios(stock_code)
        
        # Construct Daum Data structure compatible with ReportGenerator
        daum_data = {
            'quotes': quote,
            'financials': fin_data.get('ratios', {}),
            'peers': fin_data.get('peers', []),
            'investor_trends': [investor_data[-1]] if investor_data else [] # Latest trend for summary
        }
        
        print("   📊 Fetching Naver Finance data (Consensus)...")
        consensus = await naver_consensus.fetch_consensus(stock_code)
        
        # Construct Naver Data structure
        naver_data = {
            'consensus': consensus,
            'peers': [] # Peers now come from Daum
        }
        
        print("   📰 Fetching Real-time News...")
        news_data = await naver_news.fetch_news(stock_code)
        
        # Combine Real-time Data
        realtime_data = {
            'daum': daum_data,
            'naver': naver_data
        }
        
        # 3.5. Validate collected data and log missing items
        print("   🔍 Validating collected data...")
        missing_data = validate_and_log_missing_data(
            stock_code, target_stock_name,
            realtime_data, history_data, investor_data, news_data
        )

        # 3.6. Retry missing data if any
        if missing_data:
            print(f"   🔄 Retrying {len(missing_data)} missing data items...")
            retry_manager = DataRetryManager()
            retried_data = await retry_manager.retry_missing_data(
                stock_code, target_stock_name, missing_data
            )

            # Merge retried data
            if retried_data['realtime_data']:
                # Merge Daum data
                if retried_data['realtime_data'].get('daum'):
                    for key, value in retried_data['realtime_data']['daum'].items():
                        if value:  # Only update if not empty
                            realtime_data['daum'][key] = value

                # Merge Naver data
                if retried_data['realtime_data'].get('naver'):
                    for key, value in retried_data['realtime_data']['naver'].items():
                        if value:
                            realtime_data['naver'][key] = value

            # Use retried data if original was empty
            if retried_data['history_data'] and not history_data:
                history_data = retried_data['history_data']

            if retried_data['investor_data'] and not investor_data:
                investor_data = retried_data['investor_data']

            if retried_data['news_data'] and not news_data:
                news_data = retried_data['news_data']

        print("   🧠 Running Gemini AI analysis...")
        ai_input_news = news_data if news_data else db_data
        ai_analysis = await gemini.analyze_stock(target_stock_name, ai_input_news, realtime_data, history_data)

        # 4. Generate PDF
        print("   📄 Generating PDF report...")
        pdf_path = generator.generate_pdf(stock_code, dict(stock), ai_input_news, realtime_data, ai_analysis, history_data, investor_data)

        print(f"   ✅ Report saved: {pdf_path}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.disconnect()
        print("\n✨ All Done!")

if __name__ == '__main__':
    asyncio.run(main())
