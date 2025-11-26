"""
Naver Main Page Comprehensive Fetcher
Tier 4 - Browser Automation

Fetches from https://finance.naver.com/item/main.naver?code={ticker}:
- 투자자별 매매동향 (Investor Trading Trends)
- 기업실적분석 (Company Performance Analysis)
- 주요재무정보 (Key Financial Metrics)
- 동종업종비교 (Peer Comparison)
"""
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_playwright_fetcher import BasePlaywrightFetcher


class NaverMainComprehensiveFetcher(BasePlaywrightFetcher):
    """
    Comprehensive fetcher for Naver Finance main page.

    Target URL: https://finance.naver.com/item/main.naver?code={ticker}
    """

    BASE_URL = "https://finance.naver.com/item/main.naver"

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)
        self.config['data_type'] = 'naver_main_comprehensive'

    def build_url(self, ticker: str) -> str:
        """Build Naver main page URL for ticker"""
        return f"{self.BASE_URL}?code={ticker}"

    async def fetch_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive data from Naver main page.

        Args:
            ticker: Stock ticker code

        Returns:
            Comprehensive data dictionary or None
        """
        url = self.build_url(ticker)

        # Navigate to page
        success = await self.navigate_to(url, wait_until='networkidle')
        if not success:
            return None

        # Wait for page to fully load
        await self.page.wait_for_timeout(3000)

        # Parse all data
        data = await self.parse_data(ticker)

        return data

    async def parse_data(self, ticker: str) -> Dict[str, Any]:
        """
        Parse all comprehensive data from current page.

        Args:
            ticker: Stock ticker code

        Returns:
            Comprehensive data dictionary
        """
        data = {
            'ticker': ticker,
            'source': 'naver_main',
            'crawled_at': datetime.now().isoformat(),
            'investor_trading': await self.parse_investor_trading(),
            'annual_performance': await self.parse_annual_performance(),
            'quarterly_performance': await self.parse_quarterly_performance(),
            'financial_ratios': await self.parse_financial_ratios(),
            'peer_comparison': await self.parse_peer_comparison()
        }

        self.logger.info(
            f"Naver main comprehensive data parsed for {ticker}"
        )

        return data

    async def parse_investor_trading(self) -> Dict[str, Any]:
        """
        Parse investor trading trends (투자자별 매매동향).

        Returns:
            Investor trading data with daily foreign/institutional net purchases
        """
        result = {}

        try:
            # Find the section with investor trading data
            section = await self.page.query_selector('.sub_section.right')

            if section:
                # Get table with daily data (tb_type1)
                table = await section.query_selector('table.tb_type1')

                if table:
                    rows = await table.query_selector_all('tr')

                    trading_data = []
                    for row in rows[1:]:  # Skip header row
                        cols = await row.query_selector_all('th, td')
                        if len(cols) >= 5:
                            texts = []
                            for col in cols:
                                text = await col.text_content()
                                texts.append(text.strip() if text else '')

                            # Parse trading data
                            # Format: 날짜, 종가, 전일비, 외국인, 기관
                            if texts[0] and texts[0] != '':
                                trading = {
                                    'date': texts[0],  # 11/24
                                    'close_price': self._parse_number(texts[1]) if len(texts) > 1 else None,
                                    'change': self._parse_number(texts[2]) if len(texts) > 2 else None,
                                    'foreign_net': self._parse_number(texts[3]) if len(texts) > 3 else None,
                                    'institution_net': self._parse_number(texts[4]) if len(texts) > 4 else None
                                }
                                trading_data.append(trading)

                    result['daily_trading'] = trading_data

        except Exception as e:
            self.logger.warning(f"Error parsing investor trading: {e}")

        return result

    async def parse_annual_performance(self) -> List[Dict[str, Any]]:
        """
        Parse annual performance data (최근 연간 실적).

        Returns:
            List of annual performance dictionaries
        """
        performances = []

        try:
            # Find tables with "최근 연간 실적"
            tables = await self.page.query_selector_all('table')

            for table in tables:
                # Check table title
                prev_elem = await table.evaluate(
                    'el => el.previousElementSibling?.innerText || ""'
                )

                if '연간 실적' in prev_elem or '연간실적' in prev_elem:
                    # Parse annual data
                    rows = await table.query_selector_all('tr')

                    # Get years from header
                    header_row = rows[0] if rows else None
                    years = []
                    if header_row:
                        headers = await header_row.query_selector_all('th')
                        for header in headers[1:]:  # Skip first column (metric name)
                            text = await header.text_content()
                            if text:
                                years.append(text.strip())

                    # Parse data rows
                    for row in rows[1:]:
                        cols = await row.query_selector_all('th, td')
                        if cols:
                            texts = []
                            for col in cols:
                                text = await col.text_content()
                                texts.append(text.strip() if text else '')

                            if texts and texts[0]:
                                metric_name = texts[0]
                                values = [self._parse_number(t) for t in texts[1:]]

                                # Create performance entry
                                for i, year in enumerate(years):
                                    if i < len(values):
                                        perf = {
                                            'year': year,
                                            'metric': metric_name,
                                            'value': values[i]
                                        }
                                        performances.append(perf)
                    break

        except Exception as e:
            self.logger.warning(f"Error parsing annual performance: {e}")

        return performances

    async def parse_quarterly_performance(self) -> List[Dict[str, Any]]:
        """
        Parse quarterly performance data (최근 분기 실적).

        Returns:
            List of quarterly performance dictionaries
        """
        performances = []

        try:
            tables = await self.page.query_selector_all('table')

            for table in tables:
                prev_elem = await table.evaluate(
                    'el => el.previousElementSibling?.innerText || ""'
                )

                if '분기 실적' in prev_elem or '분기실적' in prev_elem:
                    rows = await table.query_selector_all('tr')

                    # Get quarters from header
                    header_row = rows[0] if rows else None
                    quarters = []
                    if header_row:
                        headers = await header_row.query_selector_all('th')
                        for header in headers[1:]:
                            text = await header.text_content()
                            if text:
                                quarters.append(text.strip())

                    # Parse data rows
                    for row in rows[1:]:
                        cols = await row.query_selector_all('th, td')
                        if cols:
                            texts = []
                            for col in cols:
                                text = await col.text_content()
                                texts.append(text.strip() if text else '')

                            if texts and texts[0]:
                                metric_name = texts[0]
                                values = [self._parse_number(t) for t in texts[1:]]

                                for i, quarter in enumerate(quarters):
                                    if i < len(values):
                                        perf = {
                                            'quarter': quarter,
                                            'metric': metric_name,
                                            'value': values[i]
                                        }
                                        performances.append(perf)
                    break

        except Exception as e:
            self.logger.warning(f"Error parsing quarterly performance: {e}")

        return performances

    async def parse_financial_ratios(self) -> Dict[str, Any]:
        """
        Parse key financial ratios (주요재무정보).

        Returns:
            Financial ratios dictionary
        """
        ratios = {}

        try:
            # Find all strong tags (metric names) and their associated values
            strongs = await self.page.query_selector_all('strong')

            for strong in strongs:
                metric_name = await strong.text_content()
                metric_name = metric_name.strip() if metric_name else ''

                # Get value from nearby element
                parent = await strong.evaluate('el => el.parentElement')
                if parent:
                    parent_text = await strong.evaluate(
                        'el => el.parentElement.innerText'
                    )

                    # Extract number from text
                    if metric_name and parent_text:
                        # Remove metric name from text
                        value_text = parent_text.replace(metric_name, '').strip()
                        value = self._parse_number(value_text)

                        if value is not None:
                            ratios[metric_name] = value

        except Exception as e:
            self.logger.warning(f"Error parsing financial ratios: {e}")

        return ratios

    async def parse_peer_comparison(self) -> List[Dict[str, Any]]:
        """
        Parse peer comparison data (동종업종비교).

        Returns:
            List of peer company data
        """
        peers = []

        try:
            # Find peer comparison table
            # Usually has title "동종업종비교"
            tables = await self.page.query_selector_all('table')

            for table in tables:
                # Check if this is peer comparison table
                prev_text = await table.evaluate(
                    'el => el.previousElementSibling?.innerText || ""'
                )

                if '동종업종' in prev_text or '업종비교' in prev_text:
                    rows = await table.query_selector_all('tbody tr')

                    for row in rows:
                        cols = await row.query_selector_all('th, td')
                        if len(cols) >= 2:
                            texts = []
                            for col in cols:
                                text = await col.text_content()
                                texts.append(text.strip() if text else '')

                            if texts[0] and texts[0] != '종목명':
                                peer = {
                                    'company': texts[0],
                                    'data': texts[1:] if len(texts) > 1 else []
                                }
                                peers.append(peer)
                    break

        except Exception as e:
            self.logger.warning(f"Error parsing peer comparison: {e}")

        return peers

    async def validate_structure(self) -> bool:
        """
        Validate that the Naver main page structure is as expected.

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Check for key page elements
            # 1. Check for investor trading table
            investor_table = await self.page.query_selector('table.type2')

            # 2. Check for performance/financial tables
            tables = await self.page.query_selector_all('table')

            # 3. Check for strong tags (financial metrics)
            strongs = await self.page.query_selector_all('strong')

            # Structure is valid if we have at least basic tables
            is_valid = (
                investor_table is not None and
                len(tables) > 0 and
                len(strongs) > 0
            )

            if not is_valid:
                self.logger.warning("Naver main page structure validation failed")

            return is_valid

        except Exception as e:
            self.logger.error(f"Error validating structure: {e}")
            return False

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """
        Parse number from text, handling Korean number formats.

        Args:
            text: Text containing number

        Returns:
            Parsed number or None
        """
        if not text:
            return None

        try:
            # Remove common formatting
            text = text.replace(',', '').replace(' ', '').replace('%', '')
            text = text.replace('+', '').replace('억', '').replace('조', '')
            text = text.replace('원', '').replace('배', '')

            # Try to parse
            return float(text)
        except (ValueError, AttributeError):
            return None
