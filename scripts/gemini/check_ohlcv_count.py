import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db

async def main():
    stock_code = '015760' # KEPCO
    print(f"🔍 Checking daily_ohlcv for {stock_code}...")
    
    await db.connect()
    try:
        count = await db.fetchval("SELECT count(*) FROM daily_ohlcv WHERE stock_code = $1", stock_code)
        print(f"OHLCV count: {count}")
        
        if count > 0:
            latest = await db.fetchval("SELECT MAX(date) FROM daily_ohlcv WHERE stock_code = $1", stock_code)
            print(f"Latest date: {latest}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
