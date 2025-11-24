"""
KIS Fetcher - Tier 2 (Official API)
Uses python-kis library for Korea Investment Securities API
"""
import asyncio
from typing import Dict, Any
from datetime import datetime

from src.core.base_fetcher import BaseFetcher
from src.config.settings import settings


class KISFetcher(BaseFetcher):
    """
    Fetcher for Korea Investment Securities API.

    Data provided:
    - Real-time stock prices
    - Order book (호가)
    - Trading volume
    """

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)

        # Check if API keys are configured
        if not settings.KIS_APP_KEY or not settings.KIS_APP_SECRET:
            self.logger.warning("KIS API keys not configured - fetcher will not work")
            self.enabled = False
        else:
            self.enabled = True

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch real-time data from Korea Investment Securities API.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing real-time price data
        """
        if not self.enabled:
            self.logger.warning("KIS API not configured - skipping")
            return {}

        try:
            # Import here to avoid errors if pykis not installed
            from pykis import PyKis

            self.logger.info(f"Fetching KIS data for {ticker}")

            # Initialize PyKis
            kis = await asyncio.to_thread(PyKis)

            # Get stock instance
            stock = kis.stock(ticker)

            # Get current price
            price_data = await asyncio.to_thread(stock.quote)

            # Build result
            data = {
                "ticker": ticker,
                "name": price_data.get("hts_kor_isnm"),  # 종목명
                "current_price": int(price_data.get("stck_prpr", 0)),  # 현재가
                "change": int(price_data.get("prdy_vrss", 0)),  # 전일대비
                "change_rate": float(price_data.get("prdy_ctrt", 0)),  # 등락률
                "volume": int(price_data.get("acml_vol", 0)),  # 누적거래량
                "high": int(price_data.get("stck_hgpr", 0)),  # 고가
                "low": int(price_data.get("stck_lwpr", 0)),  # 저가
                "open": int(price_data.get("stck_oprc", 0)),  # 시가
                "timestamp": datetime.now().isoformat(),
                "source": "KIS",
                "records_count": 1
            }

            return data

        except ImportError:
            self.logger.error("pykis library not installed")
            raise

        except Exception as e:
            self.logger.error(f"Failed to fetch data from KIS for {ticker}: {e}")
            raise

    async def validate_structure(self) -> bool:
        """
        Validate KIS API connectivity.

        Returns:
            True if validation succeeds
        """
        if not self.enabled:
            return False

        try:
            from pykis import PyKis

            # Test connection
            kis = await asyncio.to_thread(PyKis)
            return True

        except Exception as e:
            self.logger.error(f"KIS structure validation failed: {e}")
            return False
