"""
Tier 4 - Browser Automation Fetchers

Playwright-based fetchers for JavaScript-heavy sites and dynamic content.
"""

from .base_playwright_fetcher import BasePlaywrightFetcher
from .fnguide_playwright_fetcher import FnGuidePlaywrightFetcher, create_fnguide_playwright_fetcher
from .naver_stock_news_fetcher import NaverStockNewsFetcher, create_naver_stock_news_fetcher

__all__ = [
    'BasePlaywrightFetcher',
    'FnGuidePlaywrightFetcher',
    'create_fnguide_playwright_fetcher',
    'NaverStockNewsFetcher',
    'create_naver_stock_news_fetcher',
]
