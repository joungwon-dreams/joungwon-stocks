"""
Test script for Orchestrator
Tests data collection across multiple sites with rate limiting and concurrency control
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import Orchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_orchestrator_basic():
    """Test basic orchestrator functionality"""
    logger.info("=" * 60)
    logger.info("Testing Orchestrator - Basic Functionality")
    logger.info("=" * 60)

    # Create orchestrator with limited concurrency
    orchestrator = Orchestrator(max_concurrent=5)

    try:
        # Initialize
        await orchestrator.initialize()

        logger.info(f"Initialized with {len(orchestrator.fetchers)} fetchers")
        logger.info(f"Rate limiters configured: {len(orchestrator.rate_limiters.limiters)}")

        # Test with single ticker
        tickers = ["005930"]  # Samsung Electronics
        logger.info(f"\nFetching data for: {tickers}")

        await orchestrator.run(tickers)

        logger.info("\n" + "=" * 60)
        logger.info("✅ Orchestrator test completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Orchestrator test failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


async def test_orchestrator_scheduled():
    """Test scheduled orchestrator (run once)"""
    logger.info("=" * 60)
    logger.info("Testing Orchestrator - Scheduled Mode")
    logger.info("=" * 60)

    orchestrator = Orchestrator(max_concurrent=5)

    try:
        await orchestrator.initialize()

        # Run scheduled mode with run_once=True
        tickers = ["005930", "035720"]  # Samsung, Kakao
        await orchestrator.run_scheduled(
            interval_minutes=60,
            tickers=tickers,
            run_once=True  # Only run once for testing
        )

        logger.info("\n" + "=" * 60)
        logger.info("✅ Scheduled orchestrator test completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Scheduled test failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


async def test_orchestrator_single_site():
    """Test single site execution"""
    logger.info("=" * 60)
    logger.info("Testing Orchestrator - Single Site")
    logger.info("=" * 60)

    orchestrator = Orchestrator(max_concurrent=5)

    try:
        await orchestrator.initialize()

        # Test KRX fetcher (site_id=1)
        if 1 in orchestrator.fetchers:
            logger.info("Testing KRX fetcher (site_id=1)...")
            result = await orchestrator.run_single_site(site_id=1, ticker="005930")
            logger.info(f"Result: {result}")
        else:
            logger.warning("KRX fetcher not found")

        # Test Naver fetcher (site_id=6)
        if 6 in orchestrator.fetchers:
            logger.info("\nTesting Naver fetcher (site_id=6)...")
            result = await orchestrator.run_single_site(site_id=6, ticker="005930")
            logger.info(f"Result: {result}")
        else:
            logger.warning("Naver fetcher not found")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Single site test completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Single site test failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


async def test_orchestrator_concurrent():
    """Test concurrent execution with multiple tickers"""
    logger.info("=" * 60)
    logger.info("Testing Orchestrator - Concurrent Execution")
    logger.info("=" * 60)

    # Use smaller max_concurrent to observe rate limiting
    orchestrator = Orchestrator(max_concurrent=3)

    try:
        await orchestrator.initialize()

        # Test with multiple tickers
        tickers = ["005930", "035720", "005380", "051910"]  # Samsung, Kakao, Hyundai, LG
        logger.info(f"Fetching data for {len(tickers)} tickers: {tickers}")
        logger.info(f"Max concurrent: {orchestrator.max_concurrent}")

        await orchestrator.run(tickers)

        logger.info("\n" + "=" * 60)
        logger.info("✅ Concurrent execution test completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Concurrent test failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


async def main():
    """Main test runner"""
    print("\n" + "=" * 60)
    print("Orchestrator Test Suite")
    print("=" * 60)

    choice = input("\nSelect test:\n"
                   "1. Basic functionality (single ticker)\n"
                   "2. Scheduled mode (run once)\n"
                   "3. Single site execution\n"
                   "4. Concurrent execution (multiple tickers)\n"
                   "5. Run all tests\n"
                   "Enter choice (1-5): ")

    if choice == "1":
        await test_orchestrator_basic()
    elif choice == "2":
        await test_orchestrator_scheduled()
    elif choice == "3":
        await test_orchestrator_single_site()
    elif choice == "4":
        await test_orchestrator_concurrent()
    elif choice == "5":
        await test_orchestrator_basic()
        await test_orchestrator_scheduled()
        await test_orchestrator_single_site()
        await test_orchestrator_concurrent()
    else:
        print("Invalid choice")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
