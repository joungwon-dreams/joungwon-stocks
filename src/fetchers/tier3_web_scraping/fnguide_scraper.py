"""
FnGuide Scraper
Tier 3 - Web Scraping
Priority #1 (Quality: 0.92, Rating: 4/5)

FnGuide provides:
- Company fundamentals
- Financial statements (quarterly/annual)
- Analyst consensus & target price
- Valuation metrics (PER, PBR, EPS, BPS)
"""
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper


class FnGuideScraper(BaseScraper):
    """
    FnGuide web scraper for company fundamentals and analyst data.

    Data Types:
    - Company Fundamentals
    - Financial Statements
    - Analyst Consensus
    - Valuation Metrics
    """

    # FnGuide URL patterns
    # Note: These are template URLs - actual URLs need verification
    COMPANY_URL_TEMPLATE = "https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A{ticker}"
    FINANCE_URL_TEMPLATE = "https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A{ticker}"

    # CSS Selectors for data extraction
    # Note: These selectors are templates and need to be verified against actual FnGuide HTML
    SELECTORS = {
        'company_name': 'h1.company-name',
        'current_price': 'dd.price',
        'per': 'td.per-value',
        'pbr': 'td.pbr-value',
        'eps': 'td.eps-value',
        'bps': 'td.bps-value',
        'consensus_opinion': 'div.consensus-opinion',
        'target_price': 'dd.target-price',
        'analyst_count': 'dd.analyst-count',
        'revenue': 'td.revenue',
        'operating_profit': 'td.op-profit',
        'net_profit': 'td.net-profit',
    }

    async def build_url(self, ticker: str) -> str:
        """
        Build FnGuide URL for ticker.

        Args:
            ticker: Stock ticker code (e.g., "005930")

        Returns:
            Complete URL for the ticker
        """
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_company_info(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Parse company basic information.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary with company info
        """
        info = {
            'ticker': ticker,
            'source': 'fnguide',
            'company_name': None,
            'current_price': None,
            'crawled_at': datetime.now().isoformat(),
        }

        try:
            # Company name
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                info['company_name'] = name_elem.get_text(strip=True)

            # Current price
            price_elem = soup.select_one(self.SELECTORS['current_price'])
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace(',', '').replace('won', '')
                info['current_price'] = int(price_text) if price_text.isdigit() else None

        except Exception as e:
            self.logger.warning(f"Error parsing company info: {e}")

        return info

    async def parse_valuation_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse valuation metrics (PER, PBR, EPS, BPS).

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with valuation metrics
        """
        metrics = {
            'per': None,  # Price-to-Earnings Ratio
            'pbr': None,  # Price-to-Book Ratio
            'eps': None,  # Earnings Per Share
            'bps': None,  # Book value Per Share
        }

        try:
            # PER
            per_elem = soup.select_one(self.SELECTORS['per'])
            if per_elem:
                per_text = per_elem.get_text(strip=True)
                metrics['per'] = float(per_text) if per_text.replace('.', '').replace('-', '').isdigit() else None

            # PBR
            pbr_elem = soup.select_one(self.SELECTORS['pbr'])
            if pbr_elem:
                pbr_text = pbr_elem.get_text(strip=True)
                metrics['pbr'] = float(pbr_text) if pbr_text.replace('.', '').replace('-', '').isdigit() else None

            # EPS
            eps_elem = soup.select_one(self.SELECTORS['eps'])
            if eps_elem:
                eps_text = eps_elem.get_text(strip=True).replace(',', '')
                metrics['eps'] = int(eps_text) if eps_text.replace('-', '').isdigit() else None

            # BPS
            bps_elem = soup.select_one(self.SELECTORS['bps'])
            if bps_elem:
                bps_text = bps_elem.get_text(strip=True).replace(',', '')
                metrics['bps'] = int(bps_text) if bps_text.isdigit() else None

        except Exception as e:
            self.logger.warning(f"Error parsing valuation metrics: {e}")

        return metrics

    async def parse_analyst_consensus(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse analyst consensus data.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with analyst consensus
        """
        consensus = {
            'opinion': None,  # Buy/Hold/Sell
            'target_price': None,
            'analyst_count': None,
        }

        try:
            # Consensus opinion
            opinion_elem = soup.select_one(self.SELECTORS['consensus_opinion'])
            if opinion_elem:
                consensus['opinion'] = opinion_elem.get_text(strip=True)

            # Target price
            target_elem = soup.select_one(self.SELECTORS['target_price'])
            if target_elem:
                target_text = target_elem.get_text(strip=True).replace(',', '').replace('won', '')
                consensus['target_price'] = int(target_text) if target_text.isdigit() else None

            # Analyst count
            count_elem = soup.select_one(self.SELECTORS['analyst_count'])
            if count_elem:
                count_text = count_elem.get_text(strip=True)
                import re
                match = re.search(r'(\d+)', count_text)
                if match:
                    consensus['analyst_count'] = int(match.group(1))

        except Exception as e:
            self.logger.warning(f"Error parsing analyst consensus: {e}")

        return consensus

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Main parsing method - extracts all data from HTML.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary containing all parsed data
        """
        self.logger.info(f"Parsing FnGuide data for {ticker}")

        # Parse different sections
        company_info = await self.parse_company_info(soup, ticker)
        valuation_metrics = await self.parse_valuation_metrics(soup)
        analyst_consensus = await self.parse_analyst_consensus(soup)

        # Combine all data
        data = {
            **company_info,
            'valuation': valuation_metrics,
            'consensus': analyst_consensus,
            'data_quality': self._assess_data_quality(
                company_info,
                valuation_metrics,
                analyst_consensus
            ),
        }

        # Log what was parsed
        self.logger.info(
            f"FnGuide data parsed for {ticker}: "
            f"company={bool(company_info['company_name'])}, "
            f"valuation={bool(valuation_metrics['per'])}, "
            f"consensus={bool(analyst_consensus['opinion'])}"
        )

        return data

    def _assess_data_quality(
        self,
        company_info: Dict,
        valuation_metrics: Dict,
        analyst_consensus: Dict
    ) -> int:
        """
        Assess data quality based on completeness.

        Args:
            company_info: Company information dict
            valuation_metrics: Valuation metrics dict
            analyst_consensus: Analyst consensus dict

        Returns:
            Quality score (1-5)
        """
        # Count non-null fields
        company_fields = sum(1 for v in company_info.values() if v is not None)
        valuation_fields = sum(1 for v in valuation_metrics.values() if v is not None)
        consensus_fields = sum(1 for v in analyst_consensus.values() if v is not None)

        total_fields = company_fields + valuation_fields + consensus_fields
        max_fields = len(company_info) + len(valuation_metrics) + len(analyst_consensus)

        completeness = total_fields / max_fields if max_fields > 0 else 0

        # Convert to 1-5 scale
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

    async def validate_structure(self) -> bool:
        """
        Validate FnGuide site structure.

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Test with a well-known ticker (Samsung Electronics)
            test_ticker = "005930"
            url = await self.build_url(test_ticker)

            html = await self.fetch_html(url)
            if not html:
                return False

            soup = await self.parse_html(html)

            # Check for key elements
            required_elements = [
                self.SELECTORS['company_name'],
                self.SELECTORS['current_price'],
            ]

            for selector in required_elements:
                element = soup.select_one(selector)
                if not element:
                    self.logger.warning(f"Required element not found: {selector}")
                    return False

            self.logger.info("FnGuide structure validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Structure validation failed: {e}")
            return False


# Factory function for easy instantiation
async def create_fnguide_scraper(site_id: int, config: Dict[str, Any]) -> FnGuideScraper:
    """
    Create and initialize FnGuide scraper.

    Args:
        site_id: Reference site ID from database
        config: Site configuration

    Returns:
        Initialized FnGuideScraper instance
    """
    scraper = FnGuideScraper(site_id, config)
    return scraper
