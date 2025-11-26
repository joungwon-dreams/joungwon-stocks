import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any

class DaumReportsFetcher:
    BASE_URL = "https://finance.daum.net/api/research/company"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://finance.daum.net/research/company',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }

    async def fetch_reports(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        Fetch analyst reports from Daum Finance
        """
        # Symbol code for Daum usually starts with 'A'
        symbol_code = f"A{stock_code}"
        params = {
            'symbolCode': symbol_code,
            'page': 1,
            'perPage': 10
        }
        
        reports = []
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Structure: {'data': [{'title': ..., 'cpName': ..., 'date': ...}, ...]}
                        for item in data.get('data', []):
                            reports.append({
                                'title': item.get('title', ''),
                                'firm': item.get('cpName', ''),
                                'date': item.get('date', '')[:10], # YYYY-MM-DD
                                'opinion': item.get('opinion', ''),
                                'target_price': item.get('newTargetPrice', 0),
                                'url': f"https://finance.daum.net/research/company/{item.get('id')}" # Construct URL
                            })
                    else:
                        print(f"Daum Reports API Error: {resp.status}")
        except Exception as e:
            print(f"Error fetching Daum reports: {e}")
            
        return reports
