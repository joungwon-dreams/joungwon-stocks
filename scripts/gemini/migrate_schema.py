import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

async def main():
    await db.connect()
    try:
        print("Migrating schema...")
        
        # Add columns to stock_fundamentals
        queries = [
            "ALTER TABLE stock_fundamentals ADD COLUMN IF NOT EXISTS sector TEXT;",
            "ALTER TABLE stock_fundamentals ADD COLUMN IF NOT EXISTS dividend_yield NUMERIC;",
            "ALTER TABLE stock_fundamentals ADD COLUMN IF NOT EXISTS company_summary TEXT;"
        ]
        
        for q in queries:
            print(f"Executing: {q}")
            await db.execute(q)
            
        print("Schema migration completed.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
