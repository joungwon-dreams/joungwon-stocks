"""
Test script to verify all three fixes:
1. execution_status check constraint fix
2. DART XML parsing error recovery
3. FDR preferred stock handling
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


async def main():
    """Test fixes with specific tickers"""
    logger.info("=" * 60)
    logger.info("Testing Fixes")
    logger.info("=" * 60)

    # Test tickers:
    # - 005930: Normal stock (Samsung)
    # - 000050: Had DART XML parsing errors
    # - 0004Y0: Preferred stock (FDR 404)
    test_tickers = ["005930", "000050", "0004Y0"]

    orchestrator = Orchestrator(max_concurrent=5)

    try:
        # Initialize
        logger.info("Initializing orchestrator...")
        await orchestrator.initialize()

        logger.info(f"Testing with {len(test_tickers)} tickers: {test_tickers}")
        logger.info("")

        # Run data collection
        await orchestrator.run(tickers=test_tickers)

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Test completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
