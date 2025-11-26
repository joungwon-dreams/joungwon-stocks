import aiohttp
import logging
from .base import DaumBaseFetcher

logger = logging.getLogger(__name__)

class DaumPriceFetcher(DaumBaseFetcher):
    async def fetch_quote(self, stock_code: str) -> dict:
        """Fetch real-time quote snapshot."""
        symbol_code = f"A{stock_code}"
        url = f"{self.BASE_URL}/quotes/{symbol_code}"
        params = {'summary': 'false', 'changeStatistics': 'true'}
        
        try:
            async with aiohttp.ClientSession(headers=self._get_headers(symbol_code)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Daum quote fetch error: {e}")
        return {}

    async def fetch_history(self, stock_code: str, days: int = 365) -> list:
        """Fetch historical OHLCV data."""
        symbol_code = f"A{stock_code}"
        url = f"{self.BASE_URL}/quote/{symbol_code}/days"
        params = {
            'symbolCode': symbol_code,
            'page': 1,
            'perPage': days,
            'pagination': 'true'
        }
        
        history = []
        try:
            async with aiohttp.ClientSession(headers=self._get_headers(symbol_code)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('data', []):
                            history.append({
                                'date': item['date'].split(' ')[0],
                                'open': float(item['openingPrice']),
                                'high': float(item['highPrice']),
                                'low': float(item['lowPrice']),
                                'close': float(item['tradePrice']),
                                'volume': float(item.get('candleAccTradeVolume', 0))
                            })
        except Exception as e:
            logger.error(f"Daum history fetch error: {e}")
            
        return sorted(history, key=lambda x: x['date'])
