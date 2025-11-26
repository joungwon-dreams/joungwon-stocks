"""
Shinhan Securities Scraper
신한투자증권 웹 스크래퍼

Data collected:
- Company analysis
- Investment recommendations
- Target prices
- Research reports
"""
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ShinhanScraper(BaseScraper):
    """Shinhan Securities data scraper."""

    COMPANY_URL_TEMPLATE = "https://finance.naver.com/research/company_list.naver?searchType=itemCode&itemCode={ticker}&companyName=신한투자증권"

    SELECTORS = {
        'company_name': 'div.wrap_company h2',
        'current_price': 'span.number',
        'research_title': 'table.type_1 td.file',
        'research_date': 'table.type_1 td.date',
        'target_price': 'table.type_1 td:nth-child(4)',
        'opinion': 'table.type_1 td:nth-child(5)',
    }

    async def build_url(self, ticker: str) -> str:
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        data = {
            'ticker': ticker,
            'source': 'shinhan',
            'company_name': None,
            'current_price': None,
            'research_reports': [],
        }

        company_info = await self.parse_company_info(soup)
        data.update(company_info)

        reports = await self.parse_research_reports(soup)
        data['research_reports'] = reports
        data['data_quality'] = self._assess_data_quality(data)

        return data

    async def parse_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        company_info = {'company_name': None, 'current_price': None}

        try:
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                company_info['company_name'] = name_elem.text.strip()

            price_elem = soup.select_one(self.SELECTORS['current_price'])
            if price_elem:
                price_text = price_elem.text.strip().replace(',', '')
                company_info['current_price'] = int(price_text) if price_text.isdigit() else None
        except Exception as e:
            logger.error(f"Error parsing company info: {e}")

        return company_info

    async def parse_research_reports(self, soup: BeautifulSoup) -> list:
        reports = []

        try:
            report_rows = soup.select('table.type_1 tr')

            for row in report_rows[1:]:
                cells = row.select('td')
                if len(cells) >= 6:
                    reports.append({
                        'title': cells[0].text.strip() if cells[0] else None,
                        'date': cells[1].text.strip() if cells[1] else None,
                        'target_price': cells[3].text.strip() if cells[3] else None,
                        'opinion': cells[4].text.strip() if cells[4] else None,
                    })
        except Exception as e:
            logger.error(f"Error parsing reports: {e}")

        return reports

    async def validate_structure(self) -> bool:
        return True

    def _assess_data_quality(self, data: Dict[str, Any]) -> int:
        score = sum([
            1 if data.get('company_name') else 0,
            1 if data.get('current_price') else 0,
            2 if data.get('research_reports') and len(data['research_reports']) > 0 else 0,
        ])

        completeness = score / 4
        if completeness >= 0.9: return 5
        elif completeness >= 0.7: return 4
        elif completeness >= 0.5: return 3
        elif completeness >= 0.3: return 2
        else: return 1
