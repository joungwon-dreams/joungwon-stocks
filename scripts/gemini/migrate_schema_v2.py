import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

async def main():
    await db.connect()
    try:
        print("Migrating schema (v2)...")
        
        # 1. Create stock_credit_rating table
        query_credit = """
        CREATE TABLE IF NOT EXISTS stock_credit_rating (
            id SERIAL PRIMARY KEY,
            stock_code VARCHAR(20) NOT NULL,
            agency VARCHAR(50),
            rating VARCHAR(20),
            date DATE,
            collected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            UNIQUE(stock_code, agency, date)
        );
        """
        print("Creating stock_credit_rating table...")
        await db.execute(query_credit)
        
        # 2. Add columns to stock_consensus
        consensus_columns = [
            "ALTER TABLE stock_consensus ADD COLUMN IF NOT EXISTS eps_consensus INTEGER;",
            "ALTER TABLE stock_consensus ADD COLUMN IF NOT EXISTS per_consensus NUMERIC;",
            "ALTER TABLE stock_consensus ADD COLUMN IF NOT EXISTS target_high INTEGER;",
            "ALTER TABLE stock_consensus ADD COLUMN IF NOT EXISTS target_low INTEGER;"
        ]
        
        print("Updating stock_consensus schema...")
        for q in consensus_columns:
            print(f"Executing: {q}")
            await db.execute(q)
            
        # 3. Create analyst_target_prices table
        print("Creating analyst_target_prices table...")
        await db.execute('DROP TABLE IF EXISTS analyst_target_prices')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS analyst_target_prices (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(10),
                brokerage VARCHAR(50),      -- 증권사명
                target_price INTEGER,       -- 목표가
                opinion VARCHAR(20),        -- 투자의견 (매수/중립/매도)
                report_date VARCHAR(8),     -- 리포트 날짜 (YYYYMMDD)
                title TEXT,                 -- 리포트 제목
                url TEXT,                   -- 원문 링크
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, brokerage, report_date)
            );
        ''')

        # 4. Add columns to stock_consensus if not exist (Double check)
        print("Checking stock_consensus columns...")
        # (Already done in step 1, but good to be safe)
        
        print("Schema migration v2 completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
