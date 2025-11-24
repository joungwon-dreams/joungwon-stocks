"""
Naver Finance Fetcher - Tier 2 (Official API)
Uses Naver Finance mobile API
"""
import aiohttp
from typing import Dict, Any

from src.core.base_fetcher import BaseFetcher


class NaverFetcher(BaseFetcher):
    """
    Fetcher for Naver Finance API.

    Data provided:
    - Stock basic info
    - Current price
    - Market cap
    """

    BASE_URL = "https://m.stock.naver.com/api/stock/{ticker}/basic"

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch stock data from Naver Finance API.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing stock data
        """
        url = self.BASE_URL.format(ticker=ticker)

        try:
            self.logger.info(f"Fetching Naver data for {ticker}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        self.logger.error(f"Naver API returned status {response.status}")
                        return {}

                    data_raw = await response.json()

                    if not data_raw:
                        return {}

                    # Parse response
                    data = {
                        "ticker": ticker,
                        "name": data_raw.get("stockName"),
                        "current_price": self._parse_price(data_raw.get("closePrice")),
                        "change": self._parse_price(data_raw.get("compareToPreviousClosePrice")),
                        "change_rate": self._parse_price(data_raw.get("fluctuationsRatio")),
                        "volume": self._parse_price(data_raw.get("accumulatedTradingVolume")),
                        "market_cap": data_raw.get("marketValue"),
                        "source": "Naver Finance",
                        "records_count": 1
                    }

                    # Save to collected_data table
                    await self.save_collected_data(
                        ticker=ticker,
                        domain_id=5,  # price domain
                        data_type="price",
                        data_content=data
                    )

                    return data

        except aiohttp.ClientError as e:
            self.logger.error(f"Naver API connection error for {ticker}: {e}")
            raise

        except Exception as e:
            self.logger.error(f"Failed to fetch data from Naver for {ticker}: {e}")
            raise

    def _parse_price(self, price_str: str) -> int:
        """Parse price string with commas"""
        if not price_str:
            return 0
        try:
            return int(str(price_str).replace(",", ""))
        except (ValueError, AttributeError):
            return 0

    async def validate_structure(self) -> bool:
        """
        Validate Naver Finance API.

        Returns:
            True if validation succeeds
        """
        try:
            url = self.BASE_URL.format(ticker="005930")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Naver structure validation failed: {e}")
            return False
