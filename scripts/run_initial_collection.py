"""
Run initial data collection
Collects data for top 100 stocks from all active fetchers
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
    """Run initial data collection"""
    logger.info("=" * 60)
    logger.info("Initial Data Collection")
    logger.info("=" * 60)

    # Create orchestrator with moderate concurrency
    orchestrator = Orchestrator(max_concurrent=10)

    try:
        # Initialize
        logger.info("Initializing orchestrator...")
        await orchestrator.initialize()

        logger.info(f"Created {len(orchestrator.fetchers)} fetchers")
        logger.info(f"Loaded {len(orchestrator.sites)} active sites")
        logger.info(f"Max concurrent: {orchestrator.max_concurrent}")
        logger.info("")

        # Run data collection (loads top 100 stocks from database)
        logger.info("Starting data collection for top 100 stocks...")
        logger.info("This may take 5-10 minutes depending on API response times...")
        logger.info("")

        await orchestrator.run(tickers=None)  # None = load from database

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Initial data collection completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Data collection failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
