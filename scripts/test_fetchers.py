"""
Test script for Fetcher system
Tests Tier 1 and Tier 2 fetchers with Samsung Electronics (005930)
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import db
from src.config.settings import settings
from src.fetchers.tier1_official_libs.krx_fetcher import KRXFetcher
from src.fetchers.tier1_official_libs.dart_fetcher import DartFetcher
from src.fetchers.tier1_official_libs.fdr_fetcher import FDRFetcher
from src.fetchers.tier1_official_libs.opendart_fetcher import OpenDartFetcher
from src.fetchers.tier2_official_apis.naver_fetcher import NaverFetcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tier1_fetchers():
    """Test Tier 1 (Official Libraries) fetchers"""
    logger.info("=" * 60)
    logger.info("Testing Tier 1 Fetchers")
    logger.info("=" * 60)

    ticker = "005930"  # Samsung Electronics
    dummy_config = {"site_name_ko": "Test Site", "site_name_en": "Test Site"}

    # Test KRX
    logger.info("\n### Testing KRX Fetcher ###")
    krx = KRXFetcher(site_id=1, config=dummy_config)
    krx_data = await krx.fetch(ticker)
    logger.info(f"KRX Result: {krx_data}")

    # Test DART
    logger.info("\n### Testing DART Fetcher ###")
    dart = DartFetcher(site_id=2, config=dummy_config)
    dart_data = await dart.fetch(ticker)
    logger.info(f"DART Result (disclosures): {dart_data.get('disclosure_count', 0)} disclosures")

    # Test FDR
    logger.info("\n### Testing FinanceDataReader Fetcher ###")
    fdr = FDRFetcher(site_id=3, config=dummy_config)
    fdr_data = await fdr.fetch(ticker)
    logger.info(f"FDR Result: {fdr_data}")

    # Test OpenDART
    logger.info("\n### Testing OpenDART Fetcher ###")
    opendart = OpenDartFetcher(site_id=4, config=dummy_config)
    opendart_data = await opendart.fetch(ticker)
    logger.info(f"OpenDART Result (disclosures): {opendart_data.get('disclosure_count', 0)} disclosures")


async def test_tier2_fetchers():
    """Test Tier 2 (Official APIs) fetchers"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Tier 2 Fetchers")
    logger.info("=" * 60)

    ticker = "005930"  # Samsung Electronics
    dummy_config = {"site_name_ko": "Test Site", "site_name_en": "Test Site"}

    # Test Naver
    logger.info("\n### Testing Naver Finance Fetcher ###")
    naver = NaverFetcher(site_id=6, config=dummy_config)
    naver_data = await naver.fetch(ticker)
    logger.info(f"Naver Result: {naver_data}")


async def test_with_database():
    """Test fetchers with database integration"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing with Database Integration")
    logger.info("=" * 60)

    await db.connect()

    try:
        # Get site from database
        query = "SELECT * FROM reference_sites WHERE id = 1 LIMIT 1"
        site = await db.fetchrow(query)

        if site:
            logger.info(f"\nLoaded site from DB: {site['site_name_ko']}")

            # Create fetcher
            krx = KRXFetcher(site_id=site['id'], config=site)

            # Execute with logging
            data = await krx.execute("005930")
            logger.info(f"Data fetched: {data}")

            # Check execution log
            log_query = """
                SELECT * FROM fetch_execution_logs
                WHERE site_id = $1
                ORDER BY started_at DESC
                LIMIT 1
            """
            log = await db.fetchrow(log_query, site['id'])
            logger.info(f"Execution log: status={log['execution_status']}, duration={log['execution_time_ms']}ms")

        else:
            logger.warning("No sites found in database - run 05_insert_reference_sites.sql first")

    finally:
        await db.disconnect()


async def main():
    """Main test runner"""
    try:
        # Test without database
        await test_tier1_fetchers()
        await test_tier2_fetchers()

        # Test with database (requires reference_sites to be populated)
        logger.info("\n" + "=" * 60)
        logger.info("Note: Database tests require reference_sites to be populated")
        logger.info("Run: psql -U wonny -d stock_investment_db -f dev/sql/05_insert_reference_sites.sql")
        logger.info("=" * 60)

        response = input("\nRun database integration test? (y/n): ")
        if response.lower() == 'y':
            await test_with_database()

        logger.info("\n" + "=" * 60)
        logger.info("All tests completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
