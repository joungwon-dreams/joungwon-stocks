"""
Initialize stocks table with KRX stock list
Fetches all Korean stocks from KRX and inserts into database
"""
import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pykrx import stock
from src.config.database import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_krx_stocks(target_date: str = None) -> List[Dict[str, Any]]:
    """
    Fetch all stocks from KRX.

    Args:
        target_date: Date in YYYYMMDD format (default: today)

    Returns:
        List of stock dictionaries
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y%m%d")

    logger.info(f"Fetching stock list from KRX for date: {target_date}")

    stocks_data = []

    # Get stocks from each market
    markets = {
        'KOSPI': 'KOSPI',
        'KOSDAQ': 'KOSDAQ',
        'KONEX': 'KONEX'
    }

    for market_name, market_code in markets.items():
        try:
            logger.info(f"Fetching {market_name} stocks...")
            tickers = stock.get_market_ticker_list(target_date, market=market_code)

            for ticker in tickers:
                try:
                    # Get stock name
                    name = stock.get_market_ticker_name(ticker)

                    stocks_data.append({
                        'stock_code': ticker,
                        'stock_name': name,
                        'market': market_name,
                        'is_delisted': False
                    })

                except Exception as e:
                    logger.warning(f"Failed to get name for ticker {ticker}: {e}")
                    continue

            logger.info(f"Fetched {len(tickers)} stocks from {market_name}")

        except Exception as e:
            logger.error(f"Failed to fetch {market_name} stocks: {e}")
            continue

    logger.info(f"Total stocks fetched: {len(stocks_data)}")
    return stocks_data


async def insert_stocks(stocks_data: List[Dict[str, Any]]) -> int:
    """
    Insert stocks into database.

    Args:
        stocks_data: List of stock dictionaries

    Returns:
        Number of stocks inserted
    """
    query = """
        INSERT INTO stocks (
            stock_code,
            stock_name,
            market,
            is_delisted,
            created_at,
            updated_at
        ) VALUES ($1, $2, $3, $4, NOW(), NOW())
        ON CONFLICT (stock_code) DO UPDATE SET
            stock_name = EXCLUDED.stock_name,
            market = EXCLUDED.market,
            is_delisted = EXCLUDED.is_delisted,
            updated_at = NOW()
    """

    inserted_count = 0

    for stock_data in stocks_data:
        try:
            await db.execute(
                query,
                stock_data['stock_code'],
                stock_data['stock_name'],
                stock_data['market'],
                stock_data['is_delisted']
            )
            inserted_count += 1

            if inserted_count % 100 == 0:
                logger.info(f"Inserted {inserted_count}/{len(stocks_data)} stocks...")

        except Exception as e:
            logger.error(f"Failed to insert {stock_data['stock_code']}: {e}")
            continue

    logger.info(f"Successfully inserted/updated {inserted_count} stocks")
    return inserted_count


async def initialize_stock_assets():
    """
    Initialize stock_assets table for top 100 stocks by market cap.
    This allows orchestrator to run immediately.
    """
    logger.info("Initializing stock_assets for top stocks...")

    # Get top 100 stocks by market cap from KOSPI
    query = """
        INSERT INTO stock_assets (
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            is_active,
            auto_trading,
            created_at,
            updated_at
        )
        SELECT
            stock_code,
            stock_name,
            0,  -- quantity
            0,  -- avg_buy_price
            0,  -- current_price
            TRUE,  -- is_active
            FALSE,  -- auto_trading
            NOW(),
            NOW()
        FROM stocks
        WHERE is_delisted = FALSE
            AND market IN ('KOSPI', 'KOSDAQ')
        ORDER BY stock_code
        LIMIT 100
        ON CONFLICT (stock_code) DO NOTHING
    """

    result = await db.execute(query)
    logger.info(f"Initialized stock_assets: {result}")


async def main():
    """Main initialization function"""
    logger.info("=" * 60)
    logger.info("Stock List Initialization")
    logger.info("=" * 60)

    try:
        # Connect to database
        await db.connect()
        logger.info("Connected to database")

        # Check current stock count
        result = await db.fetch("SELECT COUNT(*) as count FROM stocks")
        current_count = result[0]['count']
        logger.info(f"Current stocks in database: {current_count}")

        # Fetch stocks from KRX
        stocks_data = await fetch_krx_stocks()

        if not stocks_data:
            logger.error("No stocks fetched from KRX")
            sys.exit(1)

        # Insert stocks
        inserted_count = await insert_stocks(stocks_data)

        # Initialize stock_assets for top 100
        await initialize_stock_assets()

        # Verify
        result = await db.fetch("SELECT COUNT(*) as count FROM stocks WHERE is_delisted = FALSE")
        active_count = result[0]['count']

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ Initialization Complete!")
        logger.info(f"Total stocks: {inserted_count}")
        logger.info(f"Active stocks: {active_count}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
