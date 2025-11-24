"""
KRX Fetcher - Tier 1 (Official Library)
Uses pykrx library to fetch data from Korea Exchange
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from pykrx import stock

from src.core.base_fetcher import BaseFetcher


class KRXFetcher(BaseFetcher):
    """
    Fetcher for KRX (Korea Exchange) using pykrx library.

    Data provided:
    - OHLCV (Open, High, Low, Close, Volume)
    - Market capitalization
    - Trading value
    - Change rate
    """

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch OHLCV data from KRX via pykrx.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing OHLCV data
        """
        try:
            # Get date range (last 5 trading days to ensure we get latest)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

            self.logger.info(f"Fetching KRX data for {ticker} ({start_date} ~ {end_date})")

            # pykrx is synchronous, so run in thread pool
            df = await asyncio.to_thread(
                stock.get_market_ohlcv_by_date,
                start_date,
                end_date,
                ticker
            )

            if df.empty:
                self.logger.warning(f"No data found for {ticker}")
                return {}

            # Get the latest trading day data
            latest_data = df.iloc[-1]
            latest_date = df.index[-1]

            # Also get market cap if available
            try:
                cap_df = await asyncio.to_thread(
                    stock.get_market_cap_by_date,
                    latest_date.strftime("%Y%m%d"),
                    latest_date.strftime("%Y%m%d"),
                    ticker
                )
                market_cap = int(cap_df.iloc[-1]['시가총액']) if not cap_df.empty else None
                shares = int(cap_df.iloc[-1]['상장주식수']) if not cap_df.empty else None
            except Exception:
                market_cap = None
                shares = None

            # Build result
            data = {
                "ticker": ticker,
                "date": latest_date.strftime("%Y-%m-%d"),
                "open": int(latest_data['시가']),
                "high": int(latest_data['고가']),
                "low": int(latest_data['저가']),
                "close": int(latest_data['종가']),
                "volume": int(latest_data['거래량']),
                "change_rate": round(float(latest_data['등락률']), 2),
                "market_cap": market_cap,
                "shares_outstanding": shares,
                "source": "KRX",
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

        except Exception as e:
            self.logger.error(f"Failed to fetch data from KRX for {ticker}: {e}")
            raise

    async def validate_structure(self) -> bool:
        """
        Validate that pykrx is working properly.
        Test with Samsung Electronics (005930).

        Returns:
            True if validation succeeds
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = end_date

            # Test fetch - should not crash even if market is closed
            df = await asyncio.to_thread(
                stock.get_market_ohlcv_by_date,
                start_date,
                end_date,
                "005930"
            )

            # If we get here without exception, structure is valid
            return True

        except Exception as e:
            self.logger.error(f"KRX structure validation failed: {e}")
            return False
