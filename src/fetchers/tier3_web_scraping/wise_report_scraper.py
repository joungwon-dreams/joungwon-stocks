"""
Wise Report Scraper
와이즈리포트 웹 스크래퍼
"""
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WiseReportScraper(BaseScraper):
    """Wise Report data scraper."""

    # Using wisereport.co.kr based on earlier research
    COMPANY_URL_TEMPLATE = "https://www.wisereport.co.kr/stock/comp_anal.aspx?cmp_cd={ticker}"

    SELECTORS = {
        'company_name': 'span.comp_name',
        'current_price': 'span.price',
        'consensus': 'td.consensus',
        'target_price': 'td.target_price',
    }

    async def build_url(self, ticker: str) -> str:
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        data = {
            'ticker': ticker,
            'source': 'wise_report',
            'company_name': None,
            'current_price': None,
            'consensus': None,
            'target_price': None,
        }

        try:
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            price_elem = soup.select_one(self.SELECTORS['current_price'])
            if price_elem:
                price_text = price_elem.text.strip().replace(',', '')
                data['current_price'] = int(price_text) if price_text.isdigit() else None

            consensus_elem = soup.select_one(self.SELECTORS['consensus'])
            if consensus_elem:
                data['consensus'] = consensus_elem.text.strip()

            target_elem = soup.select_one(self.SELECTORS['target_price'])
            if target_elem:
                data['target_price'] = target_elem.text.strip()
        except Exception as e:
            logger.error(f"Error parsing Wise Report data: {e}")

        data['data_quality'] = self._assess_data_quality(data)

        return data

    async def validate_structure(self) -> bool:
        return True

    def _assess_data_quality(self, data: Dict[str, Any]) -> int:
        score = sum([
            1 if data.get('company_name') else 0,
            1 if data.get('current_price') else 0,
            1 if data.get('consensus') else 0,
            1 if data.get('target_price') else 0,
        ])

        completeness = score / 4
        if completeness >= 0.9: return 5
        elif completeness >= 0.7: return 4
        elif completeness >= 0.5: return 3
        elif completeness >= 0.3: return 2
        else: return 1
