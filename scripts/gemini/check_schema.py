import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

async def main():
    await db.connect()
    try:
        query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'stock_financials'"
        rows = await db.fetch(query)
        print("Columns in stock_financials:")
        for row in rows:
            print(f"- {row['column_name']} ({row['data_type']})")
            
        query_reports = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'analyst_reports'"
        rows_reports = await db.fetch(query_reports)
        print("\nColumns in analyst_reports:")
        for row in rows_reports:
            print(f"- {row['column_name']} ({row['data_type']})")

        query_cons = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'stock_consensus'"
        rows_cons = await db.fetch(query_cons)
        print("\nColumns in stock_consensus:")
        for row in rows_cons:
            print(f"- {row['column_name']} ({row['data_type']})")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
