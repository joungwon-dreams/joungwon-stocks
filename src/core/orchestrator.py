"""
Orchestrator - Data Collection Coordinator
Manages the data collection process across all tiers (1-4)

Features:
- Rate limiting per site
- Concurrent execution control with semaphore
- Automatic retry on transient failures
- Graceful error handling
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.config.database import db
from src.config.settings import settings
from src.core.base_fetcher import BaseFetcher
from src.core.rate_limiter import MultiRateLimiter
from src.core.retry import async_retry

# Import Tier 1 Fetchers
from src.fetchers.tier1_official_libs.krx_fetcher import KRXFetcher
from src.fetchers.tier1_official_libs.dart_fetcher import DartFetcher
from src.fetchers.tier1_official_libs.fdr_fetcher import FDRFetcher
from src.fetchers.tier1_official_libs.opendart_fetcher import OpenDartFetcher

# Import Tier 2 Fetchers
from src.fetchers.tier2_official_apis.kis_fetcher import KISFetcher
from src.fetchers.tier2_official_apis.naver_fetcher import NaverFetcher
from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher
from src.fetchers.tier2_official_apis.krx_data_fetcher import KRXDataFetcher
from src.fetchers.tier2_official_apis.kofia_fetcher import KOFIAFetcher

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Manages the data collection process across all 41 sites.

    Features:
    - Load active sites from database
    - Create appropriate fetcher for each site
    - Execute fetchers in parallel by tier
    - Rate limiting per site
    - Concurrent execution control
    - Automatic retry on failures
    - Collect and aggregate results
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize orchestrator.

        Args:
            max_concurrent: Maximum number of concurrent fetch operations
        """
        self.fetchers: Dict[int, BaseFetcher] = {}
        self.sites: List[Dict[str, Any]] = []
        self.rate_limiters = MultiRateLimiter()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent

    async def initialize(self):
        """Initialize orchestrator - connect DB and load sites"""
        await db.connect()
        self.sites = await self._load_active_sites()
        logger.info(f"Loaded {len(self.sites)} active sites")

        # Create fetchers and configure rate limits for all sites
        for site in self.sites:
            fetcher = self._create_fetcher(site)
            if fetcher:
                self.fetchers[site['id']] = fetcher

                # Configure rate limit if specified
                rate_limit = site.get('api_rate_limit_per_minute')
                if rate_limit and rate_limit > 0:
                    self.rate_limiters.set_limit(site['id'], rate_limit)
                    logger.debug(f"Set rate limit for {site['site_name_ko']}: {rate_limit} calls/min")

        logger.info(f"Created {len(self.fetchers)} fetchers")

    async def run(self, tickers: Optional[List[str]] = None):
        """
        Main execution loop - collect data for all tickers from all sites

        Args:
            tickers: List of ticker codes to fetch. If None, loads from database.
        """
        logger.info("Orchestrator started")

        try:
            # Get tickers from database if not provided
            if tickers is None:
                tickers = await self._load_active_tickers()

            logger.info(f"Fetching data for {len(tickers)} tickers from {len(self.fetchers)} sites")

            # Execute by tier for better control
            await self._execute_tier1(tickers)
            await self._execute_tier2(tickers)
            await self._execute_tier3(tickers)
            await self._execute_tier4(tickers)

            logger.info("Orchestrator completed successfully")

        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            raise

        finally:
            await db.disconnect()

    async def run_single_site(self, site_id: int, ticker: str) -> Dict[str, Any]:
        """
        Execute single site fetcher for a single ticker.
        Useful for testing and debugging.

        Args:
            site_id: Reference site ID
            ticker: Stock ticker code

        Returns:
            Fetched data dictionary
        """
        fetcher = self.fetchers.get(site_id)
        if not fetcher:
            raise ValueError(f"No fetcher found for site_id {site_id}")

        return await self._execute_with_limits(site_id, fetcher, ticker)

    async def _execute_with_limits(
        self,
        site_id: int,
        fetcher: BaseFetcher,
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """
        Execute fetcher with rate limiting and concurrency control.

        Args:
            site_id: Site ID for rate limiting
            fetcher: Fetcher instance to execute
            ticker: Stock ticker code

        Returns:
            Fetched data or None on failure
        """
        async with self.semaphore:  # Limit concurrent executions
            async with self.rate_limiters.get(site_id):  # Apply rate limit
                try:
                    return await fetcher.execute(ticker)
                except Exception as e:
                    logger.error(f"Failed to fetch {ticker} from site {site_id}: {e}")
                    return None

    async def _load_active_sites(self) -> List[Dict[str, Any]]:
        """Load active sites from database"""
        query = """
            SELECT
                rs.*,
                ssc.html_selectors,
                ssc.access_method,
                ssc.api_rate_limit_per_minute
            FROM reference_sites rs
            LEFT JOIN site_scraping_config ssc ON rs.id = ssc.site_id
            WHERE rs.is_active = TRUE
            ORDER BY rs.tier, rs.reliability_rating DESC
        """
        return await db.fetch(query)

    async def _load_active_tickers(self) -> List[str]:
        """Load active stock tickers from database"""
        query = """
            SELECT stock_code
            FROM stocks
            WHERE is_delisted = FALSE
            ORDER BY stock_code
            LIMIT 100
        """
        rows = await db.fetch(query)
        return [row['stock_code'] for row in rows]

    def _create_fetcher(self, site: Dict[str, Any]) -> Optional[BaseFetcher]:
        """
        Factory method to create appropriate fetcher based on site configuration.

        Args:
            site: Site configuration dictionary

        Returns:
            BaseFetcher instance or None
        """
        site_id = site['id']
        site_name = site.get('site_name_en', '')
        tier = site.get('tier')

        # Tier 1: Official Libraries
        if tier == 1:
            if 'Korea Exchange' in site_name or 'KRX' in site_name:
                return KRXFetcher(site_id, site)
            elif 'DART' in site_name and 'OpenDART' not in site_name:
                return DartFetcher(site_id, site)
            elif 'FinanceDataReader' in site_name:
                return FDRFetcher(site_id, site)
            elif 'OpenDART' in site_name:
                return OpenDartFetcher(site_id, site)

        # Tier 2: Official APIs
        elif tier == 2:
            if 'Korea Investment' in site_name:
                return KISFetcher(site_id, site)
            elif 'Naver Finance' in site_name:
                return NaverFetcher(site_id, site)
            elif 'Daum Finance' in site_name:
                return DaumFetcher(site_id, site)
            elif 'KRX Data' in site_name:
                return KRXDataFetcher(site_id, site)
            elif 'KOFIA' in site_name:
                return KOFIAFetcher(site_id, site)

        # Tier 3: Web Scraping
        # TODO: Implement Tier 3 fetchers

        # Tier 4: Browser Automation
        # TODO: Implement Tier 4 fetchers

        logger.warning(f"No fetcher implemented for site: {site_name} (tier {tier})")
        return None

    async def _execute_tier1(self, tickers: List[str]):
        """Execute Tier 1 (Official Libraries) fetchers with rate limiting and concurrency control"""
        tier1_fetchers = {
            sid: f for sid, f in self.fetchers.items()
            if self.sites[next(i for i, s in enumerate(self.sites) if s['id'] == sid)]['tier'] == 1
        }

        if not tier1_fetchers:
            return

        logger.info(f"Executing Tier 1: {len(tier1_fetchers)} official library fetchers")

        tasks = []
        for site_id, fetcher in tier1_fetchers.items():
            for ticker in tickers:
                tasks.append(self._execute_with_limits(site_id, fetcher, ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if isinstance(r, dict) and r)
        logger.info(f"Tier 1 completed: {success_count}/{len(results)} successful")

    async def _execute_tier2(self, tickers: List[str]):
        """Execute Tier 2 (Official APIs) fetchers with rate limiting and concurrency control"""
        tier2_fetchers = {
            sid: f for sid, f in self.fetchers.items()
            if self.sites[next(i for i, s in enumerate(self.sites) if s['id'] == sid)]['tier'] == 2
        }

        if not tier2_fetchers:
            return

        logger.info(f"Executing Tier 2: {len(tier2_fetchers)} official API fetchers")

        tasks = []
        for site_id, fetcher in tier2_fetchers.items():
            for ticker in tickers:
                tasks.append(self._execute_with_limits(site_id, fetcher, ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if isinstance(r, dict) and r)
        logger.info(f"Tier 2 completed: {success_count}/{len(results)} successful")

    async def _execute_tier3(self, tickers: List[str]):
        """Execute Tier 3 (Web Scraping) fetchers"""
        # TODO: Implement Tier 3 execution
        logger.info("Tier 3 (Web Scraping): Not yet implemented")

    async def _execute_tier4(self, tickers: List[str]):
        """Execute Tier 4 (Browser Automation) fetchers"""
        # TODO: Implement Tier 4 execution
        logger.info("Tier 4 (Browser Automation): Not yet implemented")

    async def run_scheduled(
        self,
        interval_minutes: int = 60,
        tickers: Optional[List[str]] = None,
        run_once: bool = False
    ):
        """
        Run orchestrator on a schedule.

        Args:
            interval_minutes: Minutes between each run
            tickers: List of tickers to fetch (None = load from DB)
            run_once: If True, run only once (for testing)
        """
        logger.info(f"Starting scheduled orchestrator (interval: {interval_minutes} minutes)")

        iteration = 0
        while True:
            iteration += 1
            logger.info(f"=== Scheduled run #{iteration} starting ===")

            try:
                await self.run(tickers)
            except Exception as e:
                logger.error(f"Scheduled run #{iteration} failed: {e}", exc_info=True)

            if run_once:
                logger.info("run_once=True, stopping after first run")
                break

            # Calculate next run time
            next_run_seconds = interval_minutes * 60
            logger.info(f"=== Scheduled run #{iteration} completed. Next run in {interval_minutes} minutes ===")

            await asyncio.sleep(next_run_seconds)

    async def shutdown(self):
        """Graceful shutdown"""
        await db.disconnect()
        logger.info("Orchestrator shut down")
