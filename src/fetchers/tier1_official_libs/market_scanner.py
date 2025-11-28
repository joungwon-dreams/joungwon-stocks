"""
Market Scanner - Tier 1 (Official Library)
Phase 3.9: Advanced Data Pipeline

Uses pykrx library to scan market-wide data including:
- Sector/Industry performance heatmap
- Market breadth (ADR: Advance-Decline Ratio)
- Top leading/lagging sectors

Provides market context for AEGIS trading decisions.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pykrx import stock
import logging


class MarketScanner:
    """
    Market-wide scanner providing context to AEGIS.

    Phase 3.9 Features:
    - Sector heatmap: Which sectors are leading today
    - Market breadth: ADR (Advance-Decline Ratio)
    - Top movers: Best/worst performing sectors

    Note: This is a standalone scanner, not a BaseFetcher subclass,
    because it doesn't operate on individual tickers.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # 5분 캐시

    # Industry sectors to filter (skip broad market indices)
    INDUSTRY_SECTORS = [
        '음식료·담배', '섬유·의류', '종이·목재', '화학', '제약', '비금속',
        '철강금속', '기계', '전기전자', '의료·정밀기기', '운송장비·부품',
        '유통', '전기가스', '건설', '운송', '통신', '금융', '은행',
        '증권', '보험', '서비스', '제조'
    ]

    async def get_sector_heatmap(self, market: str = "KOSPI") -> Dict[str, Any]:
        """
        Get sector performance heatmap.

        Args:
            market: "KOSPI" or "KOSDAQ"

        Returns:
            Dictionary containing sector performance data
        """
        try:
            today = datetime.now().strftime("%Y%m%d")

            # Use get_index_price_change for sector data
            df = await asyncio.to_thread(
                stock.get_index_price_change,
                today, today, market
            )

            if df.empty:
                # Try yesterday if today's data not available
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                df = await asyncio.to_thread(
                    stock.get_index_price_change,
                    yesterday, yesterday, market
                )
                today = yesterday

            if df.empty:
                self.logger.warning(f"No sector data available for {market}")
                return {"sectors": [], "date": today, "market": market}

            # Extract sector data (filter out broad indices)
            sectors = []
            for sector_name in df.index:
                # Skip broad market indices (코스피, 코스피 200, etc.)
                if any(skip in sector_name for skip in ['코스피', '코스닥', 'KRX', 'KTOP']):
                    continue

                try:
                    row = df.loc[sector_name]
                    change_rate = float(row['등락률']) if '등락률' in row.index else 0.0

                    sectors.append({
                        "name": sector_name,
                        "change_rate": round(change_rate, 2),
                        "close": float(row['종가']) if '종가' in row.index else 0,
                        "volume": int(row['거래량']) if '거래량' in row.index else 0
                    })
                except Exception as e:
                    self.logger.debug(f"Skip sector {sector_name}: {e}")
                    continue

            # Sort by change rate
            sectors.sort(key=lambda x: x['change_rate'], reverse=True)

            return {
                "market": market,
                "date": today,
                "sectors": sectors,
                "top_3": sectors[:3] if len(sectors) >= 3 else sectors,
                "bottom_3": sectors[-3:] if len(sectors) >= 3 else sectors,
                "scan_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get sector heatmap: {e}")
            return {"sectors": [], "error": str(e)}

    async def get_market_breadth(self, market: str = "KOSPI") -> Dict[str, Any]:
        """
        Calculate market breadth indicators.

        ADR (Advance-Decline Ratio) = Advancing stocks / Declining stocks
        - ADR > 1: Bullish market breadth
        - ADR < 1: Bearish market breadth
        - ADR ~= 1: Neutral

        Args:
            market: "KOSPI" or "KOSDAQ"

        Returns:
            Dictionary containing breadth indicators
        """
        try:
            today = datetime.now().strftime("%Y%m%d")

            # Get all tickers for the market
            tickers = await asyncio.to_thread(
                stock.get_market_ticker_list, today, market
            )

            if not tickers:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                tickers = await asyncio.to_thread(
                    stock.get_market_ticker_list, yesterday, market
                )
                today = yesterday

            if not tickers:
                return {"error": "No tickers found", "market": market}

            # Get price changes for all stocks
            df = await asyncio.to_thread(
                stock.get_market_price_change,
                today, today, market
            )

            if df.empty:
                return {"error": "No price data", "market": market}

            # Count advancing and declining stocks
            advancing = 0
            declining = 0
            unchanged = 0

            if '등락률' in df.columns:
                for change in df['등락률']:
                    if change > 0:
                        advancing += 1
                    elif change < 0:
                        declining += 1
                    else:
                        unchanged += 1

            # Calculate ADR
            adr = round(advancing / declining, 2) if declining > 0 else float('inf')

            # Market sentiment based on ADR
            if adr > 1.5:
                sentiment = "strong_bullish"
            elif adr > 1.0:
                sentiment = "bullish"
            elif adr > 0.67:
                sentiment = "neutral"
            elif adr > 0.5:
                sentiment = "bearish"
            else:
                sentiment = "strong_bearish"

            return {
                "market": market,
                "date": today,
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "total_stocks": advancing + declining + unchanged,
                "adr": adr,
                "adr_interpretation": sentiment,
                "breadth_pct": round(advancing / (advancing + declining) * 100, 1) if (advancing + declining) > 0 else 50.0,
                "scan_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get market breadth: {e}")
            return {"error": str(e), "market": market}

    async def get_top_sectors(self, n: int = 3, market: str = "KOSPI") -> List[Dict[str, Any]]:
        """
        Get top N performing sectors.

        Args:
            n: Number of top sectors to return
            market: "KOSPI" or "KOSDAQ"

        Returns:
            List of top performing sectors
        """
        heatmap = await self.get_sector_heatmap(market)
        return heatmap.get("top_3", [])[:n]

    async def get_bottom_sectors(self, n: int = 3, market: str = "KOSPI") -> List[Dict[str, Any]]:
        """
        Get bottom N performing sectors.

        Args:
            n: Number of bottom sectors to return
            market: "KOSPI" or "KOSDAQ"

        Returns:
            List of worst performing sectors
        """
        heatmap = await self.get_sector_heatmap(market)
        return heatmap.get("bottom_3", [])[:n]

    async def get_full_market_context(self, market: str = "KOSPI") -> Dict[str, Any]:
        """
        Get comprehensive market context for AEGIS.

        Combines sector heatmap and market breadth into
        a single context object for decision making.

        Args:
            market: "KOSPI" or "KOSDAQ"

        Returns:
            Complete market context dictionary
        """
        # Check cache
        cache_key = f"market_context_{market}"
        if self._cache_time and datetime.now() - self._cache_time < self._cache_ttl:
            if cache_key in self._cache:
                self.logger.debug(f"Returning cached market context for {market}")
                return self._cache[cache_key]

        # Fetch fresh data
        heatmap, breadth = await asyncio.gather(
            self.get_sector_heatmap(market),
            self.get_market_breadth(market)
        )

        context = {
            "market": market,
            "scan_time": datetime.now().isoformat(),
            "sector_heatmap": heatmap,
            "market_breadth": breadth,
            "summary": {
                "leading_sectors": [s["name"] for s in heatmap.get("top_3", [])],
                "lagging_sectors": [s["name"] for s in heatmap.get("bottom_3", [])],
                "market_sentiment": breadth.get("adr_interpretation", "unknown"),
                "adr": breadth.get("adr", 0),
                "breadth_pct": breadth.get("breadth_pct", 50.0)
            }
        }

        # Update cache
        self._cache[cache_key] = context
        self._cache_time = datetime.now()

        return context

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        self._cache_time = None


# Singleton instance for easy access
_scanner_instance: Optional[MarketScanner] = None


def get_market_scanner() -> MarketScanner:
    """Get the singleton MarketScanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = MarketScanner()
    return _scanner_instance


# Convenience functions
async def get_market_context(market: str = "KOSPI") -> Dict[str, Any]:
    """Convenience function to get full market context."""
    scanner = get_market_scanner()
    return await scanner.get_full_market_context(market)


async def get_leading_sectors(n: int = 3, market: str = "KOSPI") -> List[Dict[str, Any]]:
    """Convenience function to get leading sectors."""
    scanner = get_market_scanner()
    return await scanner.get_top_sectors(n, market)
