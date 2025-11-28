import asyncio
import asyncpg
import os

# DB 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

async def check_wisefn():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        print("Checking WISEfn reports for 034230 (Paradise)...")
        rows = await conn.fetch("""
            SELECT * FROM wisefn_analyst_reports WHERE stock_code = '034230'
        """)
        
        if rows:
            print(f"Found {len(rows)} reports:")
            for r in rows:
                print(r)
        else:
            print("No reports found for 034230.")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_wisefn())
