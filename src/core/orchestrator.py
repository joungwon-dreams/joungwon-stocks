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

# Import Tier 3 Fetchers (Web Scraping)
from src.fetchers.tier3_web_scraping.fnguide_scraper import FnGuideScraper
from src.fetchers.tier3_web_scraping.wisefn_scraper import WISEfnScraper
from src.fetchers.tier3_web_scraping.comm38_scraper import Comm38Scraper
from src.fetchers.tier3_web_scraping.mirae_asset_scraper import MiraeAssetScraper
from src.fetchers.tier3_web_scraping.samsung_securities_scraper import SamsungSecuritiesScraper
from src.fetchers.tier3_web_scraping.kiwoom_scraper import KiwoomScraper
from src.fetchers.tier3_web_scraping.kb_securities_scraper import KBSecuritiesScraper
from src.fetchers.tier3_web_scraping.shinhan_scraper import ShinhanScraper
from src.fetchers.tier3_web_scraping.meritz_scraper import MeritzScraper
from src.fetchers.tier3_web_scraping.hana_scraper import HanaScraper
from src.fetchers.tier3_web_scraping.daishin_scraper import DaishinScraper
from src.fetchers.tier3_web_scraping.korea_investment_scraper import KoreaInvestmentScraper
from src.fetchers.tier3_web_scraping.nh_investment_scraper import NHInvestmentScraper
from src.fetchers.tier3_web_scraping.quantiwise_scraper import QuantiWiseScraper
from src.fetchers.tier3_web_scraping.wise_report_scraper import WiseReportScraper
from src.fetchers.tier3_web_scraping.ebest_scraper import EBestScraper
from src.fetchers.tier3_web_scraping.eugene_scraper import EugeneScraper
from src.fetchers.tier3_web_scraping.korea_economy_scraper import KoreaEconomyScraper
from src.fetchers.tier3_web_scraping.maeil_business_scraper import MaeilBusinessScraper
from src.fetchers.tier3_web_scraping.seoul_economy_scraper import SeoulEconomyScraper
from src.fetchers.tier3_web_scraping.financial_news_scraper import FinancialNewsScraper
from src.fetchers.tier3_web_scraping.money_today_scraper import MoneyTodayScraper
from src.fetchers.tier3_web_scraping.edaily_scraper import EdailyScraper
from src.fetchers.tier3_web_scraping.yonhap_infomax_scraper import YonhapInfomaxScraper
from src.fetchers.tier3_web_scraping.newspim_scraper import NewspimScraper
from src.fetchers.tier3_web_scraping.daum_stock_news_scraper import DaumStockNewsScraper
from src.fetchers.tier3_web_scraping.naver_stock_news_scraper import NaverStockNewsScraper
from src.fetchers.tier3_web_scraping.stock_plus_scraper import StockPlusScraper

# Import Tier 4 Fetchers (Browser Automation)
from src.fetchers.tier4_browser_automation.fnguide_playwright_fetcher import FnGuidePlaywrightFetcher
from src.fetchers.tier4_browser_automation.naver_stock_news_fetcher import NaverStockNewsFetcher as NaverStockNewsPlaywrightFetcher

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
        elif tier == 3:
            if 'FnGuide' in site_name or 'fnguide' in site_name.lower():
                return FnGuideScraper(site_id, site)
            elif 'WISEfn' in site_name or 'wisefn' in site_name.lower():
                return WISEfnScraper(site_id, site)
            elif '38' in site_name or '38comm' in site_name.lower():
                return Comm38Scraper(site_id, site)
            elif 'Mirae Asset' in site_name or '미래에셋' in site_name:
                return MiraeAssetScraper(site_id, site)
            elif 'Samsung Securities' in site_name or '삼성증권' in site_name:
                return SamsungSecuritiesScraper(site_id, site)
            elif 'Kiwoom' in site_name or '키움' in site_name:
                return KiwoomScraper(site_id, site)
            elif 'KB' in site_name or 'kb' in site_name.lower():
                return KBSecuritiesScraper(site_id, site)
            elif 'Shinhan' in site_name or '신한' in site_name:
                return ShinhanScraper(site_id, site)
            elif 'Meritz' in site_name or '메리츠' in site_name:
                return MeritzScraper(site_id, site)
            elif 'Hana' in site_name or '하나' in site_name:
                return HanaScraper(site_id, site)
            elif 'Daishin' in site_name or '대신' in site_name:
                return DaishinScraper(site_id, site)
            elif 'Korea Investment' in site_name or '한국투자' in site_name:
                return KoreaInvestmentScraper(site_id, site)
            elif 'NH Investment' in site_name or 'NH투자' in site_name:
                return NHInvestmentScraper(site_id, site)
            elif 'QuantiWise' in site_name or 'quantiwise' in site_name.lower():
                return QuantiWiseScraper(site_id, site)
            elif 'Wise Report' in site_name or '와이즈리포트' in site_name:
                return WiseReportScraper(site_id, site)
            elif 'eBest' in site_name or '이베스트' in site_name:
                return EBestScraper(site_id, site)
            elif 'Eugene' in site_name or '유진' in site_name:
                return EugeneScraper(site_id, site)
            elif 'Korea Economy' in site_name or '한국경제' in site_name:
                return KoreaEconomyScraper(site_id, site)
            elif 'Maeil Business' in site_name or '매일경제' in site_name:
                return MaeilBusinessScraper(site_id, site)
            elif 'Seoul Economy' in site_name or '서울경제' in site_name:
                return SeoulEconomyScraper(site_id, site)
            elif 'Financial News' in site_name or '파이낸셜뉴스' in site_name:
                return FinancialNewsScraper(site_id, site)
            elif 'Money Today' in site_name or '머니투데이' in site_name:
                return MoneyTodayScraper(site_id, site)
            elif 'Edaily' in site_name or '이데일리' in site_name:
                return EdailyScraper(site_id, site)
            elif 'Yonhap Infomax' in site_name or '연합인포맥스' in site_name:
                return YonhapInfomaxScraper(site_id, site)
            elif 'Newspim' in site_name or '뉴스핌' in site_name:
                return NewspimScraper(site_id, site)
            elif 'Daum Stock News' in site_name or '다음 증권뉴스' in site_name:
                return DaumStockNewsScraper(site_id, site)
            elif 'Naver Stock News' in site_name or '네이버 증권뉴스' in site_name:
                return NaverStockNewsScraper(site_id, site)
            elif 'Stock Plus' in site_name or '스톡플러스' in site_name:
                return StockPlusScraper(site_id, site)

        # Tier 4: Browser Automation
        elif tier == 4:
            if 'FnGuide' in site_name or 'fnguide' in site_name.lower():
                return FnGuidePlaywrightFetcher(site_id, site)
            elif 'Naver Stock News' in site_name or '네이버 증권뉴스' in site_name:
                return NaverStockNewsPlaywrightFetcher(site_id, site)

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
        """Execute Tier 3 (Web Scraping) fetchers with rate limiting and concurrency control"""
        tier3_fetchers = {
            sid: f for sid, f in self.fetchers.items()
            if self.sites[next(i for i, s in enumerate(self.sites) if s['id'] == sid)]['tier'] == 3
        }

        if not tier3_fetchers:
            logger.info("No Tier 3 fetchers available")
            return

        logger.info(f"Executing Tier 3: {len(tier3_fetchers)} web scraping fetchers")

        tasks = []
        for site_id, fetcher in tier3_fetchers.items():
            for ticker in tickers:
                tasks.append(self._execute_with_limits(site_id, fetcher, ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if isinstance(r, dict) and r)
        logger.info(f"Tier 3 completed: {success_count}/{len(results)} successful")

    async def _execute_tier4(self, tickers: List[str]):
        """Execute Tier 4 (Browser Automation) fetchers with rate limiting and concurrency control"""
        tier4_fetchers = {
            sid: f for sid, f in self.fetchers.items()
            if self.sites[next(i for i, s in enumerate(self.sites) if s['id'] == sid)]['tier'] == 4
        }

        if not tier4_fetchers:
            logger.info("No Tier 4 fetchers available")
            return

        logger.info(f"Executing Tier 4: {len(tier4_fetchers)} browser automation fetchers")

        tasks = []
        for site_id, fetcher in tier4_fetchers.items():
            for ticker in tickers:
                tasks.append(self._execute_with_limits(site_id, fetcher, ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if isinstance(r, dict) and r)
        logger.info(f"Tier 4 completed: {success_count}/{len(results)} successful")

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
