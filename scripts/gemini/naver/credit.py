import aiohttp
import json
from typing import Optional, Dict, Any

class NaverCreditFetcher:
    BASE_URL = "https://m.stock.naver.com/api/stock"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.stock.naver.com/'
        }

    async def fetch_credit_rating(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch credit rating from Naver Integration API
        """
        url = f"{self.BASE_URL}/{stock_code}/integration"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Search for credit rating in totalInfos or other sections
                        # This is a heuristic search as the location varies
                        rating = self._find_credit_rating(data)
                        if rating:
                            return {
                                'agency': 'Naver', # Source
                                'rating': rating,
                                'date': None # Date often not available in summary
                            }
        except Exception as e:
            print(f"Error fetching credit rating: {e}")
            
        return None

    def _find_credit_rating(self, data: Any) -> Optional[str]:
        """Recursively search for credit rating string"""
        if isinstance(data, dict):
            for k, v in data.items():
                if 'credit' in k.lower() or 'rating' in k.lower():
                    if isinstance(v, str) and len(v) < 10: # Likely a rating like 'AA+'
                        return v
                
                res = self._find_credit_rating(v)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = self._find_credit_rating(item)
                if res:
                    return res
        return None
