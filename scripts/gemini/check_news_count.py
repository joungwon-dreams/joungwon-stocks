import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db

async def main():
    await db.connect()
    try:
        count = await db.fetchval("SELECT count(*) FROM collected_data WHERE data_type LIKE '%news%'")
        print(f"News count: {count}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
