
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any
import sys

# Add project root to sys.path to import db
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

logger = logging.getLogger(__name__)

class NaverCompetitorsFetcher:
    """
    Fetches competitor comparison data using Naver Mobile API.
    It first retrieves the peer list from the DB, then fetches data for each.
    """
    
    def __init__(self):
        self.API_URL = "https://m.stock.naver.com/api/stock/{code}/integration"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        }

    async def fetch_competitors_data(self, target_code: str) -> List[Dict[str, Any]]:
        """
        Fetches data for target stock AND its peers.
        """
        # 1. Get Peer List from DB
        peers = []
        try:
            # Ensure DB connection if not connected? 
            # Usually caller manages connection, but let's assume pool exists or create simple one for test
            # In production flow, db is connected.
            
            # Get target first
            target_name_row = await db.fetchrow("SELECT stock_name FROM stocks WHERE stock_code = $1", target_code)
            target_name = target_name_row['stock_name'] if target_name_row else target_code
            
            peers.append({'code': target_code, 'name': target_name})
            
            # Get peers
            rows = await db.fetch("SELECT peer_code, peer_name FROM stock_peers WHERE stock_code = $1", target_code)
            for r in rows:
                peers.append({'code': r['peer_code'], 'name': r['peer_name']})
                
        except Exception as e:
            logger.error(f"DB Error fetching peers: {e}")
            # Fallback if DB fails or empty? Return just target
            if not peers:
                peers.append({'code': target_code, 'name': 'Target'})

        # 2. Fetch Data for all
        results = []
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self._fetch_single_stock(session, p['code'], p['name']) for p in peers]
            results = await asyncio.gather(*tasks)
            
        # Filter out None results
        return [r for r in results if r]

    async def _fetch_single_stock(self, session, code, name) -> Dict[str, Any]:
        url = self.API_URL.format(code=code)
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    
                    # Parse 'totalInfos' for PER/PBR/ROE/Price/Cap
                    infos = {item['key']: item['value'] for item in data.get('totalInfos', [])}
                    
                    # Deal Trend for Price (Realtime)
                    # data['dealTrend']['nv'] is current price usually
                    price = 0
                    if 'dealTrend' in data and 'nv' in data['dealTrend']:
                        price = int(str(data['dealTrend']['nv']).replace(',', ''))
                    
                    # Helper for safe float conversion
                    def parse_float(val):
                        try:
                            return float(str(val).replace(',', '').replace('배', '').replace('%', ''))
                        except:
                            return 0.0
                            
                    def parse_cap(val):
                        # "21조 3,456" -> number
                        if not val: return 0
                        try:
                            val = str(val).replace(',', '')
                            if '조' in val:
                                parts = val.split('조')
                                t = int(parts[0]) * 1000000000000
                                b = int(parts[1]) * 100000000 if len(parts) > 1 and parts[1].strip() else 0
                                return t + b
                            return int(val) * 100000000 # Default 억 unit if just number
                        except:
                            return 0

                    # Financials (Sales, Op Profit) - Usually in 'finance' section but abbreviated
                    # The integration API might not have full financials table.
                    # We might need to fetch 'finance/annual' separately if we really want Sales/OpProfit for all peers.
                    # For the report's "Peer Comparison" table (Price, Cap, PER, PBR, ROE), totalInfos is enough.
                    
                    return {
                        'code': code,
                        'name': name,
                        'current_price': price,
                        'market_cap': parse_cap(infos.get('marketVal')),
                        'per': parse_float(infos.get('per')),
                        'pbr': parse_float(infos.get('pbr')),
                        'roe': parse_float(infos.get('roe')), # Sometimes missing in totalInfos
                        'dividend_yield': parse_float(infos.get('yield'))
                    }
        except Exception as e:
            logger.error(f"Error fetching {code}: {e}")
        return None

if __name__ == "__main__":
    # Test needs DB connection
    async def test():
        await db.connect()
        fetcher = NaverCompetitorsFetcher()
        data = await fetcher.fetch_competitors_data("316140")
        print(data)
        await db.disconnect()
    
    asyncio.run(test())
