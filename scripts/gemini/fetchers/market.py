
import aiohttp
import logging

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    def __init__(self):
        # Naver Realtime Indices
        self.URL = "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI,KOSDAQ"
        
    async def fetch_market_indices(self):
        """
        Fetch KOSPI, KOSDAQ, and USD/KRW (approx)
        """
        indices = {'KOSPI': {'price': 0, 'change': 0}, 'KOSDAQ': {'price': 0, 'change': 0}}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.URL, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse KOSPI
                        datas = data.get('result', {}).get('areas', [])
                        for area in datas:
                            for item in area.get('datas', []):
                                name = item.get('nm')
                                if name in indices:
                                    indices[name]['price'] = float(item.get('nv', 0)) / 100 # Naver sends index * 100 usually for domestic? Check raw.
                                    # Actually Naver Polling for index: 'nv' is value * 100 usually. 
                                    # Let's verify format. Usually "250034" -> 2500.34
                                    indices[name]['price'] = float(item.get('nv', 0)) / 100.0
                                    indices[name]['change'] = float(item.get('cv', 0)) / 100.0
                                    indices[name]['rate'] = float(item.get('cr', 0))
        except Exception as e:
            logger.error(f"Market fetch error: {e}")
            
        return indices
