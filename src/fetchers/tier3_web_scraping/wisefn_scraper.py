"""
WISEfn Scraper
Tier 3 - Web Scraping
Priority #2 (Quality: 0.91, Rating: 4/5)

WISEfn provides:
- Financial analytics
- Corporate governance data
- Investment analysis
- Quarterly/Annual financial statements
"""
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper


class WISEfnScraper(BaseScraper):
    """
    WISEfn web scraper for financial analytics.

    Data Types:
    - Corporate Governance Metrics
    - Financial Analytics
    - Investment Analysis
    - Quarterly/Annual Financials
    """

    # WISEfn URL patterns
    # Using wisefn.stockpoint.co.kr for company monitor access
    # Note: SSL verification disabled due to certificate issues
    COMPANY_URL_TEMPLATE = "http://wisefn.stockpoint.co.kr/company/c1010001.aspx?cmp_cd={ticker}"
    FINANCE_URL_TEMPLATE = "http://wisefn.stockpoint.co.kr/company/c1020001.aspx?cmp_cd={ticker}"

    # CSS Selectors for data extraction
    # Note: These selectors are templates and need to be verified against actual WISEfn HTML
    SELECTORS = {
        'company_name': 'div.company-title h1',
        'stock_price': 'span.stock-price',
        'market_cap': 'td.market-cap-value',
        'governance_score': 'div.governance-score',
        'financial_health': 'div.financial-health-score',
        'revenue': 'td.revenue-value',
        'operating_profit': 'td.op-profit-value',
        'net_profit': 'td.net-profit-value',
        'debt_ratio': 'td.debt-ratio',
        'roe': 'td.roe-value',
        'roa': 'td.roa-value',
        'analysis_summary': 'div.analysis-summary',
    }

    async def build_url(self, ticker: str) -> str:
        """
        Build WISEfn URL for ticker.

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
            'source': 'wisefn',
            'company_name': None,
            'stock_price': None,
            'market_cap': None,
            'crawled_at': datetime.now().isoformat(),
        }

        try:
            # Company name
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                info['company_name'] = name_elem.get_text(strip=True)

            # Stock price
            price_elem = soup.select_one(self.SELECTORS['stock_price'])
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace(',', '').replace('won', '')
                info['stock_price'] = int(price_text) if price_text.isdigit() else None

            # Market cap
            mcap_elem = soup.select_one(self.SELECTORS['market_cap'])
            if mcap_elem:
                mcap_text = mcap_elem.get_text(strip=True).replace(',', '').replace('won', '')
                # Convert to actual value (100 million KRW units)
                info['market_cap'] = int(float(mcap_text) * 100000000) if mcap_text.replace('.', '').isdigit() else None

        except Exception as e:
            self.logger.warning(f"Error parsing company info: {e}")

        return info

    async def parse_governance_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse corporate governance metrics.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with governance metrics
        """
        metrics = {
            'governance_score': None,  # ESG governance score
            'board_independence': None,
            'transparency_score': None,
        }

        try:
            # Governance score
            score_elem = soup.select_one(self.SELECTORS['governance_score'])
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                # Extract numeric score
                import re
                match = re.search(r'(\d+\.?\d*)', score_text)
                if match:
                    metrics['governance_score'] = float(match.group(1))

        except Exception as e:
            self.logger.warning(f"Error parsing governance metrics: {e}")

        return metrics

    async def parse_financial_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse financial performance metrics.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with financial metrics
        """
        metrics = {
            'revenue': None,  # Sales
            'operating_profit': None,  # Operating Profit
            'net_profit': None,  # Net Profit
            'debt_ratio': None,  # Debt Ratio
            'roe': None,  # Return on Equity
            'roa': None,  # Return on Assets
            'financial_health_score': None,
        }

        try:
            # Revenue
            revenue_elem = soup.select_one(self.SELECTORS['revenue'])
            if revenue_elem:
                revenue_text = revenue_elem.get_text(strip=True).replace(',', '')
                metrics['revenue'] = int(revenue_text) if revenue_text.isdigit() else None

            # Operating profit
            op_elem = soup.select_one(self.SELECTORS['operating_profit'])
            if op_elem:
                op_text = op_elem.get_text(strip=True).replace(',', '')
                metrics['operating_profit'] = int(op_text) if op_text.isdigit() else None

            # Net profit
            net_elem = soup.select_one(self.SELECTORS['net_profit'])
            if net_elem:
                net_text = net_elem.get_text(strip=True).replace(',', '')
                metrics['net_profit'] = int(net_text) if net_text.isdigit() else None

            # Debt ratio
            debt_elem = soup.select_one(self.SELECTORS['debt_ratio'])
            if debt_elem:
                debt_text = debt_elem.get_text(strip=True).replace('%', '')
                metrics['debt_ratio'] = float(debt_text) if debt_text.replace('.', '').isdigit() else None

            # ROE
            roe_elem = soup.select_one(self.SELECTORS['roe'])
            if roe_elem:
                roe_text = roe_elem.get_text(strip=True).replace('%', '')
                metrics['roe'] = float(roe_text) if roe_text.replace('.', '').replace('-', '').isdigit() else None

            # ROA
            roa_elem = soup.select_one(self.SELECTORS['roa'])
            if roa_elem:
                roa_text = roa_elem.get_text(strip=True).replace('%', '')
                metrics['roa'] = float(roa_text) if roa_text.replace('.', '').replace('-', '').isdigit() else None

            # Financial health score
            health_elem = soup.select_one(self.SELECTORS['financial_health'])
            if health_elem:
                health_text = health_elem.get_text(strip=True)
                import re
                match = re.search(r'(\d+\.?\d*)', health_text)
                if match:
                    metrics['financial_health_score'] = float(match.group(1))

        except Exception as e:
            self.logger.warning(f"Error parsing financial metrics: {e}")

        return metrics

    async def parse_investment_analysis(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse investment analysis summary.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with investment analysis
        """
        analysis = {
            'summary': None,
            'strengths': [],
            'weaknesses': [],
            'recommendation': None,
        }

        try:
            # Analysis summary
            summary_elem = soup.select_one(self.SELECTORS['analysis_summary'])
            if summary_elem:
                analysis['summary'] = summary_elem.get_text(strip=True)

            # Note: Strengths and weaknesses extraction would need more specific selectors
            # based on actual WISEfn HTML structure

        except Exception as e:
            self.logger.warning(f"Error parsing investment analysis: {e}")

        return analysis

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Main parsing method - extracts all data from HTML.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary containing all parsed data
        """
        self.logger.info(f"Parsing WISEfn data for {ticker}")

        # Parse different sections
        company_info = await self.parse_company_info(soup, ticker)
        governance_metrics = await self.parse_governance_metrics(soup)
        financial_metrics = await self.parse_financial_metrics(soup)
        investment_analysis = await self.parse_investment_analysis(soup)

        # Combine all data
        data = {
            **company_info,
            'governance': governance_metrics,
            'financials': financial_metrics,
            'analysis': investment_analysis,
            'data_quality': self._assess_data_quality(
                company_info,
                governance_metrics,
                financial_metrics,
                investment_analysis
            ),
        }

        # Log what was parsed
        self.logger.info(
            f"WISEfn data parsed for {ticker}: "
            f"company={bool(company_info['company_name'])}, "
            f"governance={bool(governance_metrics['governance_score'])}, "
            f"financials={bool(financial_metrics['revenue'])}, "
            f"analysis={bool(investment_analysis['summary'])}"
        )

        return data

    def _assess_data_quality(
        self,
        company_info: Dict,
        governance_metrics: Dict,
        financial_metrics: Dict,
        investment_analysis: Dict
    ) -> int:
        """
        Assess data quality based on completeness.

        Args:
            company_info: Company information dict
            governance_metrics: Governance metrics dict
            financial_metrics: Financial metrics dict
            investment_analysis: Investment analysis dict

        Returns:
            Quality score (1-5)
        """
        # Count non-null fields
        company_fields = sum(1 for v in company_info.values() if v is not None)
        governance_fields = sum(1 for v in governance_metrics.values() if v is not None)
        financial_fields = sum(1 for v in financial_metrics.values() if v is not None)
        analysis_fields = sum(1 for v in investment_analysis.values() if v is not None and (not isinstance(v, list) or len(v) > 0))

        total_fields = company_fields + governance_fields + financial_fields + analysis_fields
        max_fields = len(company_info) + len(governance_metrics) + len(financial_metrics) + len(investment_analysis)

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
        Validate WISEfn site structure.

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
                self.SELECTORS['stock_price'],
            ]

            for selector in required_elements:
                element = soup.select_one(selector)
                if not element:
                    self.logger.warning(f"Required element not found: {selector}")
                    return False

            self.logger.info("WISEfn structure validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Structure validation failed: {e}")
            return False


# Factory function for easy instantiation
async def create_wisefn_scraper(site_id: int, config: Dict[str, Any]) -> WISEfnScraper:
    """
    Create and initialize WISEfn scraper.

    Args:
        site_id: Reference site ID from database
        config: Site configuration

    Returns:
        Initialized WISEfnScraper instance
    """
    scraper = WISEfnScraper(site_id, config)
    return scraper
