"""
Base Playwright Fetcher for Tier 4 (Browser Automation)

Provides common functionality for browser-based data fetching:
- Browser lifecycle management
- Page navigation and waiting
- Element interaction
- Screenshot capture
- Error handling
"""
from typing import Dict, Any, Optional, List
from abc import abstractmethod
import asyncio
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError

from src.core.base_fetcher import BaseFetcher
from src.config.database import db


class BasePlaywrightFetcher(BaseFetcher):
    """
    Base class for Playwright-based fetchers (Tier 4).

    Handles:
    - Browser initialization (headless/headful)
    - Page management
    - Common navigation patterns
    - Error handling for browser operations
    """

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)

        # Browser configuration
        self.headless = config.get('headless', True)
        self.viewport = config.get('viewport', {'width': 1920, 'height': 1080})
        self.user_agent = config.get('user_agent', None)
        self.timeout = config.get('timeout', 30000)  # 30 seconds

        # Browser instances (initialized on first use)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self):
        """Initialize Playwright and browser"""
        if self.browser is None:
            self.logger.info("Initializing Playwright browser...")

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']  # Anti-detection
            )

            self.context = await self.browser.new_context(
                viewport=self.viewport,
                user_agent=self.user_agent
            )

            # Anti-detection: remove webdriver flag
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.timeout)

            self.logger.info("Browser initialized successfully")

    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
            self.page = None

        if self.context:
            await self.context.close()
            self.context = None

        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self.logger.info("Browser cleaned up")

    async def navigate_to(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        """
        Navigate to URL and wait for page load.

        Args:
            url: Target URL
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            await self.page.goto(url, wait_until=wait_until)
            self.logger.info(f"Navigated to {url}")
            return True

        except PlaywrightTimeoutError:
            self.logger.error(f"Timeout navigating to {url}")
            return False

        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            return False

    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds (None = use default)

        Returns:
            True if element found, False otherwise
        """
        try:
            await self.page.wait_for_selector(
                selector,
                timeout=timeout or self.timeout
            )
            return True

        except PlaywrightTimeoutError:
            self.logger.warning(f"Timeout waiting for selector: {selector}")
            return False

        except Exception as e:
            self.logger.error(f"Error waiting for selector {selector}: {e}")
            return False

    async def click_element(self, selector: str, wait_after: int = 1000) -> bool:
        """
        Click element and wait.

        Args:
            selector: CSS selector
            wait_after: Wait time after click (ms)

        Returns:
            True if click successful, False otherwise
        """
        try:
            await self.page.click(selector)
            await asyncio.sleep(wait_after / 1000)
            self.logger.debug(f"Clicked element: {selector}")
            return True

        except Exception as e:
            self.logger.error(f"Error clicking {selector}: {e}")
            return False

    async def fill_input(self, selector: str, value: str) -> bool:
        """
        Fill input field.

        Args:
            selector: CSS selector
            value: Value to fill

        Returns:
            True if fill successful, False otherwise
        """
        try:
            await self.page.fill(selector, value)
            self.logger.debug(f"Filled input {selector} with: {value}")
            return True

        except Exception as e:
            self.logger.error(f"Error filling input {selector}: {e}")
            return False

    async def get_text_content(self, selector: str) -> Optional[str]:
        """
        Get text content of element.

        Args:
            selector: CSS selector

        Returns:
            Text content or None if not found
        """
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content()
            return None

        except Exception as e:
            self.logger.error(f"Error getting text from {selector}: {e}")
            return None

    async def get_all_text_contents(self, selector: str) -> List[str]:
        """
        Get text content of all matching elements.

        Args:
            selector: CSS selector

        Returns:
            List of text contents
        """
        try:
            elements = await self.page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.text_content()
                if text:
                    texts.append(text.strip())
            return texts

        except Exception as e:
            self.logger.error(f"Error getting texts from {selector}: {e}")
            return []

    async def take_screenshot(self, path: str, full_page: bool = False) -> bool:
        """
        Take screenshot of page.

        Args:
            path: Output file path
            full_page: Capture full page or viewport only

        Returns:
            True if screenshot successful, False otherwise
        """
        try:
            await self.page.screenshot(path=path, full_page=full_page)
            self.logger.info(f"Screenshot saved to {path}")
            return True

        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return False

    async def evaluate_script(self, script: str) -> Any:
        """
        Execute JavaScript in page context.

        Args:
            script: JavaScript code to execute

        Returns:
            Script result
        """
        try:
            return await self.page.evaluate(script)

        except Exception as e:
            self.logger.error(f"Error evaluating script: {e}")
            return None

    async def wait_for_network_idle(self, timeout: int = 5000):
        """
        Wait for network to be idle.

        Args:
            timeout: Timeout in milliseconds
        """
        try:
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
            self.logger.debug("Network idle")

        except PlaywrightTimeoutError:
            self.logger.warning("Network idle timeout")

    @abstractmethod
    async def fetch_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data for ticker (must be implemented by subclass).

        Args:
            ticker: Stock ticker code

        Returns:
            Fetched data dictionary or None
        """
        pass

    @abstractmethod
    async def parse_data(self, ticker: str) -> Dict[str, Any]:
        """
        Parse data from current page (must be implemented by subclass).

        Args:
            ticker: Stock ticker code

        Returns:
            Parsed data dictionary
        """
        pass

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Main fetch method (implements BaseFetcher interface).

        Args:
            ticker: Stock ticker code

        Returns:
            Fetched data with metadata
        """
        try:
            await self.initialize()

            data = await self.fetch_data(ticker)

            if data is None:
                self.logger.warning(f"No data fetched for {ticker}")
                return {}

            # Add metadata
            result = {
                'ticker': ticker,
                'site_id': self.site_id,
                'fetched_at': datetime.now().isoformat(),
                'data': data
            }

            # Save to database
            await self.save_to_db(result, ticker)

            return result

        except Exception as e:
            self.logger.error(f"Error in fetch for {ticker}: {e}", exc_info=True)
            return {}

        finally:
            await self.cleanup()

    async def save_to_db(self, data: Dict[str, Any], ticker: str):
        """
        Save fetched data to database.

        Args:
            data: Data to save
            ticker: Stock ticker code
        """
        try:
            # Determine data type from subclass
            data_type = self.config.get('data_type', 'browser_data')

            query = '''
                INSERT INTO collected_data (
                    ticker, site_id, domain_id, data_type, data_content, collected_at
                )
                VALUES ($1, $2, $3, $4, $5, NOW())
            '''

            await db.execute(
                query,
                ticker,
                self.site_id,
                self.config.get('domain_id'),
                data_type,
                json.dumps(data, ensure_ascii=False)
            )

            self.logger.info(f"Data saved to database for {ticker}")

        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
