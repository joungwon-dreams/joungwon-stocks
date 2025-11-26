"""
Base Scraper for Tier 3 Web Scraping
Extends BaseFetcher with web scraping capabilities
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import hashlib
import random

from src.core.base_fetcher import BaseFetcher


class BaseScraper(BaseFetcher, ABC):
    """
    Base class for all web scrapers (Tier 3).
    Provides common HTTP request, HTML parsing, and structure validation.
    """

    # Default headers to mimic browser requests
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Common User-Agent rotation pool
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    ]

    def __init__(self, site_id: int, config: Dict[str, Any]):
        """
        Initialize web scraper.

        Args:
            site_id: Reference site ID from database
            config: Site configuration including URL, selectors, etc.
        """
        super().__init__(site_id, config)

        self.base_url = config.get('url', '')
        self.timeout = config.get('timeout_seconds', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay_seconds', 5)
        self.use_random_ua = config.get('use_random_user_agent', True)

        # HTML selectors for parsing (subclasses should override)
        self.selectors = config.get('html_selectors', {})

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for request.
        Rotates User-Agent if configured.

        Returns:
            Dictionary of HTTP headers
        """
        headers = self.DEFAULT_HEADERS.copy()

        if self.use_random_ua:
            headers['User-Agent'] = random.choice(self.USER_AGENTS)

        # Allow config to override specific headers
        custom_ua = self.config.get('custom_user_agent')
        if custom_ua:
            headers['User-Agent'] = custom_ua

        return headers

    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session.
        Reuses session for connection pooling.

        Returns:
            Active aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close_session(self):
        """Close the aiohttp session if open."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def fetch_html(self, url: str, retries: int = 0) -> Optional[str]:
        """
        Fetch HTML content from URL with retry logic.

        Args:
            url: URL to fetch
            retries: Current retry count

        Returns:
            HTML content as string, or None if failed
        """
        try:
            session = await self.get_session()
            headers = await self.get_headers()

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return html
                elif response.status == 429:  # Rate limit
                    if retries < self.max_retries:
                        wait_time = self.retry_delay * (2 ** retries)  # Exponential backoff
                        self.logger.warning(f"Rate limited (429), waiting {wait_time}s before retry {retries + 1}/{self.max_retries}")
                        await asyncio.sleep(wait_time)
                        return await self.fetch_html(url, retries + 1)
                    else:
                        self.logger.error(f"Max retries reached for {url} (429 rate limit)")
                        return None
                else:
                    self.logger.error(f"HTTP {response.status} for {url}")
                    return None

        except asyncio.TimeoutError:
            if retries < self.max_retries:
                self.logger.warning(f"Timeout, retrying {retries + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
                return await self.fetch_html(url, retries + 1)
            else:
                self.logger.error(f"Timeout after {retries} retries for {url}")
                raise

        except aiohttp.ClientError as e:
            self.logger.error(f"Client error fetching {url}: {e}")
            if retries < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                return await self.fetch_html(url, retries + 1)
            return None

        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    async def parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup.

        Args:
            html: Raw HTML string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'lxml')

    async def compute_structure_hash(self, html: str) -> str:
        """
        Compute SHA-256 hash of HTML structure.
        Used for detecting site structure changes.

        Args:
            html: Raw HTML string

        Returns:
            SHA-256 hash (hex string)
        """
        # Parse and get structure (tags only, no content)
        soup = await self.parse_html(html)

        # Extract tag structure
        tag_structure = ''.join([tag.name for tag in soup.find_all()])

        # Compute hash
        hash_obj = hashlib.sha256(tag_structure.encode('utf-8'))
        return hash_obj.hexdigest()

    async def save_structure_snapshot(
        self,
        html: str,
        snapshot_type: str = 'change_detection'
    ):
        """
        Save HTML structure snapshot to database.

        Args:
            html: Raw HTML content
            snapshot_type: Type of snapshot (baseline/change_detection)
        """
        from src.config.database import db

        structure_hash = await self.compute_structure_hash(html)
        soup = await self.parse_html(html)

        # Get sample (first 1000 chars)
        structure_sample = html[:1000]

        # Extract elements
        elements_found = {
            'title': soup.title.string if soup.title else None,
            'meta_tags': len(soup.find_all('meta')),
            'scripts': len(soup.find_all('script')),
            'links': len(soup.find_all('link')),
            'forms': len(soup.find_all('form')),
            'tables': len(soup.find_all('table')),
        }

        import json

        query = """
            INSERT INTO site_structure_snapshots (
                site_id, snapshot_type, structure_hash, structure_sample, elements_found
            ) VALUES (
                $1, $2, $3, $4, $5
            )
        """

        try:
            await db.execute(
                query,
                self.site_id,
                snapshot_type,
                structure_hash,
                structure_sample,
                json.dumps(elements_found)
            )
            self.logger.info(f"Saved structure snapshot (hash={structure_hash[:8]}...)")
        except Exception as e:
            self.logger.error(f"Failed to save structure snapshot: {e}")

    @abstractmethod
    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Parse data from BeautifulSoup object.
        Must be implemented by subclasses.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary containing parsed data
        """
        pass

    @abstractmethod
    async def build_url(self, ticker: str) -> str:
        """
        Build URL for fetching ticker data.
        Must be implemented by subclasses.

        Args:
            ticker: Stock ticker code

        Returns:
            Complete URL for the ticker
        """
        pass

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Main fetch method - orchestrates the scraping process.
        Implements abstract method from BaseFetcher.

        Args:
            ticker: Stock ticker code

        Returns:
            Dictionary containing fetched data
        """
        try:
            # Build URL
            url = await self.build_url(ticker)
            self.logger.debug(f"Fetching URL: {url}")

            # Fetch HTML
            html = await self.fetch_html(url)
            if not html:
                return {}

            # Parse HTML
            soup = await self.parse_html(html)

            # Extract data
            data = await self.parse_data(soup, ticker)

            # Save structure snapshot (periodically, not every fetch)
            # Subclasses can override this behavior
            if random.random() < 0.05:  # 5% chance to save snapshot
                await self.save_structure_snapshot(html)

            return data

        except Exception as e:
            self.logger.error(f"Error in fetch for {ticker}: {e}", exc_info=True)
            return {}

    async def validate_structure(self) -> bool:
        """
        Validate site structure matches expectations.
        Checks for key HTML elements defined in selectors.

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Fetch homepage or a test URL
            test_url = self.base_url
            html = await self.fetch_html(test_url)

            if not html:
                return False

            soup = await self.parse_html(html)

            # Check for expected elements (subclasses can override)
            expected_elements = self.config.get('expected_elements', {})

            for element_type, selector in expected_elements.items():
                element = soup.select_one(selector)
                if not element:
                    self.logger.warning(f"Expected element '{element_type}' not found (selector: {selector})")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Structure validation failed: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources (close session, etc.)"""
        await self.close_session()
