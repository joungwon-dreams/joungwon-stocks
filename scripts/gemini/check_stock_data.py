import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db

async def main():
    target_name = "한국전력"
    print(f"🔍 Checking database for '{target_name}'...")
    
    await db.connect()
    try:
        # 1. Find Stock Code
        query_stock = "SELECT stock_code, stock_name FROM stock_assets WHERE stock_name = $1"
        stock = await db.fetchrow(query_stock, target_name)
        
        if not stock:
            print(f"❌ Stock '{target_name}' not found in stock_assets table.")
            # Try finding by code if name fails, but user said name.
            # Let's try partial match just in case
            query_partial = "SELECT stock_code, stock_name FROM stock_assets WHERE stock_name LIKE $1"
            stock = await db.fetchrow(query_partial, f"%{target_name}%")
            if not stock:
                print("❌ Stock not found even with partial match.")
                return

        stock_code = stock['stock_code']
        stock_name = stock['stock_name']
        print(f"✅ Found Stock: {stock_name} ({stock_code})")
        
        # 2. Check Collected Data
        print(f"\n📊 Checking 'collected_data' table for {stock_name}...")
        
        query_data = '''
            SELECT 
                data_type, 
                COUNT(*) as count, 
                MAX(collected_at) as latest_date
            FROM collected_data 
            WHERE ticker = $1 
            GROUP BY data_type
            ORDER BY data_type
        '''
        rows = await db.fetch(query_data, stock_code)
        
        if not rows:
            print("⚠️ No collected data found.")
        else:
            print(f"{'Data Type':<30} | {'Count':<5} | {'Latest Date':<20}")
            print("-" * 65)
            for row in rows:
                d_type = row['data_type']
                count = row['count']
                latest = row['latest_date']
                print(f"{d_type:<30} | {count:<5} | {latest}")
                
        # 3. Show a sample of recent data content (optional)
        print(f"\n📝 Recent Data Samples (Top 3):")
        query_sample = '''
            SELECT data_type, data_content, collected_at 
            FROM collected_data 
            WHERE ticker = $1 
            ORDER BY collected_at DESC 
            LIMIT 3
        '''
        samples = await db.fetch(query_sample, stock_code)
        for s in samples:
            content = s['data_content'][:100].replace('\n', ' ') + "..." if s['data_content'] else "No Content"
            print(f"[{s['collected_at']}] [{s['data_type']}] {content}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
