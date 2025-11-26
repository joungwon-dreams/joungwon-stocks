"""
QuantiWise Scraper
QuantiWise 데이터 스크래퍼
"""
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class QuantiWiseScraper(BaseScraper):
    """QuantiWise quantitative analysis platform scraper."""

    # Using placeholder URL - needs verification
    COMPANY_URL_TEMPLATE = "https://www.quantiwise.com/stock/{ticker}"

    SELECTORS = {
        'company_name': 'h1.company-name',
        'current_price': 'span.current-price',
        'quant_score': 'div.quant-score',
        'analysis_date': 'span.date',
    }

    async def build_url(self, ticker: str) -> str:
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        data = {
            'ticker': ticker,
            'source': 'quantiwise',
            'company_name': None,
            'current_price': None,
            'quant_score': None,
        }

        try:
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            price_elem = soup.select_one(self.SELECTORS['current_price'])
            if price_elem:
                price_text = price_elem.text.strip().replace(',', '')
                data['current_price'] = int(price_text) if price_text.isdigit() else None

            score_elem = soup.select_one(self.SELECTORS['quant_score'])
            if score_elem:
                data['quant_score'] = score_elem.text.strip()
        except Exception as e:
            logger.error(f"Error parsing QuantiWise data: {e}")

        data['data_quality'] = self._assess_data_quality(data)

        return data

    async def validate_structure(self) -> bool:
        return True

    def _assess_data_quality(self, data: Dict[str, Any]) -> int:
        score = sum([
            1 if data.get('company_name') else 0,
            1 if data.get('current_price') else 0,
            2 if data.get('quant_score') else 0,
        ])

        completeness = score / 4
        if completeness >= 0.9: return 5
        elif completeness >= 0.7: return 4
        elif completeness >= 0.5: return 3
        elif completeness >= 0.3: return 2
        else: return 1
