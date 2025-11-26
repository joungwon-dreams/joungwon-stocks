import aiohttp
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NaverConsensusFetcher:
    BASE_URL = "https://m.stock.naver.com/api/stock"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.stock.naver.com/'
        }

    async def fetch_consensus(self, stock_code: str) -> Dict[str, Any]:
        """Fetch Target Price and Opinion using Naver Mobile API."""
        # Mobile Integration API contains consensus info
        url = f"https://m.stock.naver.com/api/stock/{stock_code}/integration"
        
        consensus = {}
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Parse 'consensusInfo'
                        # Structure: {"recommMean": "3.79", "priceTargetMean": "59,846", ...}
                        
                        consensus_info = data.get('consensusInfo', {})
                        if consensus_info:
                            consensus['target_price'] = consensus_info.get('priceTargetMean', '')
                            consensus['opinion'] = consensus_info.get('recommMean', '')
        except Exception as e:
            logger.error(f"Naver consensus API fetch error: {e}")
            
        return consensus

    async def fetch_consensus_detail(self, stock_code: str) -> Dict[str, Any]:
        """
        Fetch detailed consensus (EPS, PER) from Financials API
        Target High/Low is currently not available via simple API.
        """
        # We need to fetch annual financials to find the consensus year
        url = f"https://m.stock.naver.com/api/stock/{stock_code}/finance/annual"
        
        result = {
            'eps': 0,
            'per': 0.0,
            'target_high': 0,
            'target_low': 0
        }

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        finance_info = data.get('financeInfo', {})
                        titles = finance_info.get('trTitleList', [])
                        rows = finance_info.get('rowList', [])
                        
                        # Find the column key for consensus (isConsensus="Y")
                        consensus_key = None
                        for t in titles:
                            if t.get('isConsensus') == 'Y':
                                consensus_key = t.get('key')
                                break
                        
                        if consensus_key:
                            # Extract EPS and PER from rows
                            for row in rows:
                                title = row.get('title', '')
                                col_data = row.get('columns', {}).get(consensus_key, {})
                                value = col_data.get('value')
                                
                                if not value:
                                    continue
                                    
                                if 'EPS' in title:
                                    result['eps'] = self._parse_int(value)
                                elif 'PER' in title:
                                    result['per'] = self._parse_float(value)
                                    
        except Exception as e:
            print(f"Error fetching consensus detail: {e}")
        
        return result

    def _parse_int(self, value: Any) -> int:
        if not value:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(str(value).replace(',', ''))
        except:
            return 0

    def _parse_float(self, value: Any) -> float:
        if not value:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(',', ''))
        except:
            return 0.0
    async def fetch_analyst_reports(self, stock_code: str) -> list:
        """
        Fetch recent analyst reports.
        Since the official research API often returns outdated data,
        we search for news with keywords like '목표가', '리포트', '투자의견'.
        """
        # Use News API to find report-related news
        url = f"https://m.stock.naver.com/api/news/stock/{stock_code}"
        params = {'pageSize': 20, 'page': 1}
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.stock.naver.com/'
        }
        
        reports = []
        keywords = ['목표가', '투자의견', '리포트', '상향', '하향', '유지', '매수']
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # API returns a list of dicts, each containing 'items' list with 1 element
                        # Structure: [{'items': [...]}, {'items': [...]}, ...]
                        all_items = []
                        if isinstance(data, list):
                            for entry in data:
                                if isinstance(entry, dict):
                                    all_items.extend(entry.get('items', []))
                        elif isinstance(data, dict):
                            all_items = data.get('items', [])
                        
                        for item in all_items:
                            title = item.get('title', '')
                            # Check if title contains any keyword
                            if any(k in title for k in keywords):
                                # Extract firm name if possible (often in title like "[Kiwoom]...")
                                # For now, just use the press name as firm
                                reports.append({
                                    'title': title,
                                    'firm': item.get('officeName', ''), # Press name as proxy
                                    'date': item.get('datetime', '')[:10].replace('.', '-'),
                                    'opinion': '', # Hard to extract from title
                                    'target_price': '', # Hard to extract from title
                                    'url': f"https://m.stock.naver.com/domestic/stock/{stock_code}/news/view/{item.get('articleId')}/{item.get('officeId')}"
                                })
        except Exception as e:
            logger.error(f"Naver analyst reports (news proxy) fetch error: {e}")
            
        return reports
