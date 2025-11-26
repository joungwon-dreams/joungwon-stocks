"""
Daum Finance Fetcher - Tier 2 (Official API)
Uses Daum Finance REST API

Available data:
- Investor trading trends (외국인/기관 매매동향)
- Real-time quotes (실시간 시세)
- Financial metrics (재무 지표: EPS, ROE, 영업이익 등)
- Sector information (업종 정보)
"""
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.base_fetcher import BaseFetcher


class DaumFetcher(BaseFetcher):
    """
    Fetcher for Daum Finance API.

    Endpoints:
    - /api/investor/days: 투자자별 매매동향
    - /api/quotes/{symbol}: 시세 정보
    - /api/quote/{symbol}/sectors: 업종 정보 + 재무 지표
    - /api/charts/investors/days: 투자자 차트 데이터
    """

    BASE_URL = "https://finance.daum.net/api"

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)

        # Browser-like headers for API access
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://finance.daum.net',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    def _get_symbol_code(self, ticker: str) -> str:
        """Convert ticker to Daum symbol code (A-prefix)"""
        return f"A{ticker}"

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch comprehensive data from Daum Finance API.

        Args:
            ticker: Stock ticker code (e.g., "005930")

        Returns:
            Dictionary containing all fetched data
        """
        self.logger.info(f"Fetching Daum Finance data for {ticker}")

        symbol_code = self._get_symbol_code(ticker)

        # Update Referer header with specific symbol
        headers = self.headers.copy()
        headers['Referer'] = f'https://finance.daum.net/quotes/{symbol_code}'

        async with aiohttp.ClientSession(headers=headers) as session:
            # Fetch all API endpoints
            investor_days = await self._fetch_investor_days(session, symbol_code)
            quotes = await self._fetch_quotes(session, symbol_code)
            sectors = await self._fetch_sectors(session, symbol_code)
            charts_investors = await self._fetch_charts_investors(session, symbol_code)

            # Combine all data
            result = {
                'ticker': ticker,
                'symbol_code': symbol_code,
                'source': 'daum_finance',
                'fetched_at': datetime.now().isoformat(),
                'investor_trading': investor_days,
                'quotes': quotes,
                'sectors': sectors,
                'charts_investors': charts_investors,
                'records_count': (
                    len(investor_days.get('data', [])) +
                    (1 if quotes else 0) +
                    len(sectors.get('data', [])) +
                    len(charts_investors.get('data', []))
                )
            }

            self.logger.info(
                f"Daum Finance data fetched successfully for {ticker}: "
                f"{result['records_count']} records"
            )

            return result

    async def _fetch_investor_days(
        self,
        session: aiohttp.ClientSession,
        symbol_code: str
    ) -> Dict[str, Any]:
        """Fetch investor trading trends (최근 30일)"""
        try:
            url = f"{self.BASE_URL}/investor/days"
            params = {
                'page': 1,
                'perPage': 30,
                'symbolCode': symbol_code
            }

            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    self.logger.warning(f"investor_days API returned {resp.status}")
                    return {}
        except Exception as e:
            self.logger.error(f"Error fetching investor_days: {e}")
            return {}

    async def _fetch_quotes(
        self,
        session: aiohttp.ClientSession,
        symbol_code: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote data"""
        try:
            url = f"{self.BASE_URL}/quotes/{symbol_code}"
            params = {
                'summary': 'false',
                'changeStatistics': 'true'
            }

            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    self.logger.warning(f"quotes API returned {resp.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching quotes: {e}")
            return None

    async def _fetch_sectors(
        self,
        session: aiohttp.ClientSession,
        symbol_code: str
    ) -> Dict[str, Any]:
        """Fetch sector and financial metrics"""
        try:
            url = f"{self.BASE_URL}/quote/{symbol_code}/sectors"

            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    self.logger.warning(f"sectors API returned {resp.status}")
                    return {}
        except Exception as e:
            self.logger.error(f"Error fetching sectors: {e}")
            return {}

    async def _fetch_charts_investors(
        self,
        session: aiohttp.ClientSession,
        symbol_code: str
    ) -> Dict[str, Any]:
        """Fetch investor chart data (최근 90일)"""
        try:
            url = f"{self.BASE_URL}/charts/investors/days"
            params = {
                'symbolCode': symbol_code,
                'page': 1,
                'perPage': 90
            }

            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    self.logger.warning(f"charts_investors API returned {resp.status}")
                    return {}
        except Exception as e:
            self.logger.error(f"Error fetching charts_investors: {e}")
            return {}

    async def validate_structure(self) -> bool:
        """
        Validate Daum Finance API by testing with a known ticker.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Test with Samsung Electronics (005930)
            test_symbol = "A005930"

            headers = self.headers.copy()
            headers['Referer'] = f'https://finance.daum.net/quotes/{test_symbol}'

            async with aiohttp.ClientSession(headers=headers) as session:
                url = f"{self.BASE_URL}/quotes/{test_symbol}"

                async with session.get(url) as resp:
                    if resp.status == 200:
                        self.logger.info("Daum Finance API validation successful")
                        return True
                    else:
                        self.logger.warning(
                            f"Daum Finance API validation failed: {resp.status}"
                        )
                        return False

        except Exception as e:
            self.logger.error(f"Error validating Daum Finance API: {e}")
            return False
