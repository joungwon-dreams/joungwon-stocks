"""
FinanceDataReader Fetcher - Tier 1 (Official Library)
Uses FinanceDataReader library for stock data
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import FinanceDataReader as fdr
import requests

from src.core.base_fetcher import BaseFetcher


class FDRFetcher(BaseFetcher):
    """
    Fetcher for FinanceDataReader library.

    Data provided:
    - Stock price data
    - Historical OHLCV
    - Stock listings
    """

    def _is_preferred_stock(self, ticker: str) -> bool:
        """
        Check if ticker is a preferred stock.
        Preferred stocks typically end with Y0, Z0, V0, etc.

        Args:
            ticker: Stock ticker code

        Returns:
            True if likely a preferred stock
        """
        return len(ticker) == 6 and ticker[-2] in ['Y', 'Z', 'V', 'W'] and ticker[-1] == '0'

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch stock data using FinanceDataReader.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing stock data
        """
        try:
            self.logger.info(f"Fetching FDR data for {ticker}")

            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)

            # Fetch data
            df = await asyncio.to_thread(
                fdr.DataReader,
                ticker,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if df.empty:
                self.logger.warning(f"No data found for {ticker}")
                return {}

            # Get latest data
            latest = df.iloc[-1]
            latest_date = df.index[-1]

            # Build result
            data = {
                "ticker": ticker,
                "date": latest_date.strftime("%Y-%m-%d"),
                "open": int(latest['Open']),
                "high": int(latest['High']),
                "low": int(latest['Low']),
                "close": int(latest['Close']),
                "volume": int(latest['Volume']),
                "change": int(latest['Change']) if 'Change' in latest else None,
                "source": "FinanceDataReader",
                "records_count": len(df)
            }

            # Save to collected_data table
            await self.save_collected_data(
                ticker=ticker,
                domain_id=5,  # price domain
                data_type="ohlcv",
                data_content=data,
                data_date=latest_date.strftime("%Y-%m-%d")
            )

            return data

        except requests.exceptions.HTTPError as http_err:
            # Handle HTTP errors gracefully
            if '404' in str(http_err):
                if self._is_preferred_stock(ticker):
                    # Expected: Yahoo Finance doesn't have data for Korean preferred stocks
                    self.logger.info(f"Preferred stock {ticker} not available in Yahoo Finance (expected)")
                else:
                    self.logger.warning(f"Data not found (404) for {ticker}")
                return {}  # Return empty, don't raise
            else:
                self.logger.error(f"HTTP error fetching {ticker}: {http_err}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to fetch data from FDR for {ticker}: {e}")
            raise

    async def validate_structure(self) -> bool:
        """
        Validate FinanceDataReader is working.

        Returns:
            True if validation succeeds
        """
        try:
            # Test with Samsung Electronics
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            df = await asyncio.to_thread(
                fdr.DataReader,
                "005930",
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            # Should return data or empty DataFrame without error
            return True

        except Exception as e:
            self.logger.error(f"FDR structure validation failed: {e}")
            return False
