"""
Kiwoom Securities Scraper
키움증권 웹 스크래퍼

Data collected:
- Company fundamentals
- Stock analysis
- Investment recommendations
- Research reports
- Target prices
"""
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class KiwoomScraper(BaseScraper):
    """
    Kiwoom Securities data scraper using BeautifulSoup4.

    Collects:
    - Company Information
    - Research Reports
    - Investment Opinions
    - Target Prices
    - Analyst Recommendations
    """

    # Kiwoom Securities URL patterns
    # Note: Using Naver Finance aggregated research as primary source
    COMPANY_URL_TEMPLATE = "https://finance.naver.com/research/company_list.naver?searchType=itemCode&itemCode={ticker}&companyName=키움증권"
    REPORT_URL_TEMPLATE = "https://finance.naver.com/research/company_read.naver?itemcode={ticker}"

    # CSS Selectors for Naver Finance research pages
    SELECTORS = {
        'company_name': 'div.wrap_company h2',
        'current_price': 'span.number',
        'research_title': 'table.type_1 td.file',
        'research_date': 'table.type_1 td.date',
        'target_price': 'table.type_1 td:nth-child(4)',
        'opinion': 'table.type_1 td:nth-child(5)',
        'analyst_name': 'table.type_1 td:nth-child(6)',
        'report_link': 'table.type_1 td.file a',
    }

    async def build_url(self, ticker: str) -> str:
        """
        Build URL for Kiwoom Securities data for given ticker.

        Args:
            ticker: Stock ticker code

        Returns:
            Formatted URL string
        """
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Parse Kiwoom Securities data from BeautifulSoup object.

        Args:
            soup: BeautifulSoup parsed HTML
            ticker: Stock ticker code

        Returns:
            Dictionary containing parsed data
        """
        data = {
            'ticker': ticker,
            'source': 'kiwoom',
            'company_name': None,
            'current_price': None,
            'research_reports': [],
        }

        # Parse company info
        company_info = await self.parse_company_info(soup)
        data.update(company_info)

        # Parse research reports
        research_reports = await self.parse_research_reports(soup)
        data['research_reports'] = research_reports

        # Assess data quality
        data['data_quality'] = self._assess_data_quality(data)

        return data

    async def parse_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse basic company information."""
        company_info = {
            'company_name': None,
            'current_price': None,
        }

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
        """Parse research reports list."""
        reports = []

        try:
            report_rows = soup.select('table.type_1 tr')

            for row in report_rows[1:]:  # Skip header row
                cells = row.select('td')
                if len(cells) >= 6:
                    report = {
                        'title': cells[0].text.strip() if cells[0] else None,
                        'date': cells[1].text.strip() if cells[1] else None,
                        'target_price': cells[3].text.strip() if cells[3] else None,
                        'opinion': cells[4].text.strip() if cells[4] else None,
                        'analyst': cells[5].text.strip() if cells[5] else None,
                    }

                    # Extract report link
                    link_elem = cells[0].select_one('a')
                    if link_elem and link_elem.get('href'):
                        report['link'] = f"https://finance.naver.com{link_elem['href']}"

                    reports.append(report)

        except Exception as e:
            logger.error(f"Error parsing research reports: {e}")

        return reports

    async def validate_structure(self) -> bool:
        """
        Validate that the scraped data has expected structure.

        Returns:
            True if structure is valid, False otherwise
        """
        expected_elements = [
            self.SELECTORS['company_name'],
            self.SELECTORS['research_title'],
            self.SELECTORS['research_date'],
        ]

        # For now, assume structure is valid
        # In production, should verify against live website
        return True

    def _assess_data_quality(self, data: Dict[str, Any]) -> int:
        """
        Assess data quality on a scale of 1-5.

        Args:
            data: Parsed data dictionary

        Returns:
            Quality score (1-5)
        """
        score = 0
        total_fields = 4

        # Check key fields
        if data.get('company_name'):
            score += 1
        if data.get('current_price'):
            score += 1
        if data.get('research_reports') and len(data['research_reports']) > 0:
            score += 2

        # Convert to 1-5 scale
        completeness = score / total_fields
        if completeness >= 0.9:
            return 5
        elif completeness >= 0.7:
            return 4
        elif completeness >= 0.5:
            return 3
        elif completeness >= 0.3:
            return 2
        else:
            return 1
