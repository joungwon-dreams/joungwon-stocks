"""서울경제 Scraper"""
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SeoulEconomyScraper(BaseScraper):
    """서울경제 news scraper."""

    COMPANY_URL_TEMPLATE = "https://www.sedaily.com/Stock/Quote/{ticker}"
    SELECTORS = {
        'company_name': 'h1.stock-name',
        'news_title': 'div.article-list h3.title',
        'news_date': 'span.date',
    }

    async def build_url(self, ticker: str) -> str:
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        data = {
            'ticker': ticker,
            'source': 'seoul_economy',
            'company_name': None,
            'news_articles': [],
        }

        try:
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            titles = soup.select(self.SELECTORS['news_title'])
            for title in titles[:5]:
                data['news_articles'].append({'title': title.text.strip()})
        except Exception as e:
            logger.error(f"Error: {e}")

        data['data_quality'] = self._assess_data_quality(data)
        return data

    async def validate_structure(self) -> bool:
        return True

    def _assess_data_quality(self, data: Dict[str, Any]) -> int:
        score = sum([
            1 if data.get('company_name') else 0,
            3 if data.get('news_articles') and len(data['news_articles']) > 0 else 0,
        ])
        completeness = score / 4
        if completeness >= 0.9: return 5
        elif completeness >= 0.7: return 4
        elif completeness >= 0.5: return 3
        elif completeness >= 0.3: return 2
        else: return 1
