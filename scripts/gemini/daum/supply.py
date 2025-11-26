import aiohttp
import logging
from .base import DaumBaseFetcher

logger = logging.getLogger(__name__)

class DaumSupplyFetcher(DaumBaseFetcher):
    async def fetch_history(self, stock_code: str, days: int = 30) -> list:
        """Fetch historical investor trading trends (Foreign/Institutional)."""
        symbol_code = f"A{stock_code}"
        url = f"{self.BASE_URL}/investor/days"
        params = {
            'symbolCode': symbol_code,
            'page': 1,
            'perPage': days,
            'pagination': 'true'
        }
        
        trends = []
        try:
            async with aiohttp.ClientSession(headers=self._get_headers(symbol_code)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('data', []):
                            trends.append({
                                'date': item['date'].split(' ')[0],
                                'foreign': float(item.get('foreignStraightPurchaseVolume', 0) or 0),
                                'institutional': float(item.get('institutionStraightPurchaseVolume', 0) or 0),
                                'individual': float(item.get('individualStraightPurchaseVolume', 0) or 0) # Note: API might not have individual volume directly, need to check
                            })
        except Exception as e:
            logger.error(f"Daum investor history fetch error: {e}")
            
        return sorted(trends, key=lambda x: x['date'])
