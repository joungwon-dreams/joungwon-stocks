import aiohttp
import logging
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)

class NaverFinancialsFetcher:
    def __init__(self):
        self.BASE_URL = "https://m.stock.naver.com/api/stock"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.stock.naver.com/'
        }

    async def fetch_statements(self, stock_code: str) -> Dict[str, Any]:
        """
        Fetch yearly and quarterly financial statements from Naver.
        Returns structure compatible with DaumFinancialsFetcher:
        {'yearly': [{'date': '...', 'revenue': ...}, ...], 'quarterly': [...]}
        """
        financials = {'yearly': [], 'quarterly': []}
        
        # Fetch Annual
        annual_data = await self._fetch_period(stock_code, 'annual')
        if annual_data:
            financials['yearly'] = annual_data

        # Fetch Quarterly
        quarterly_data = await self._fetch_period(stock_code, 'quarter')
        if quarterly_data:
            financials['quarterly'] = quarterly_data
            
        return financials

    async def _fetch_period(self, stock_code: str, period: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{stock_code}/finance/{period}"
        results = []
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'financeInfo' in data:
                            results = self._parse_finance_info(data['financeInfo'])
        except Exception as e:
            logger.error(f"Naver financials ({period}) fetch error: {e}")
            
        return results

    def _parse_finance_info(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        parsed_data = []
        
        if not isinstance(info, dict):
            return parsed_data
            
        titles = info.get('trTitleList', [])
        rows = info.get('rowList', [])
        
        # Map keys to dates
        # titles example: [{"title": "2022.12.", "key": "202212"}, ...]
        date_map = {} # key -> date_str
        for t in titles:
            key = t.get('key')
            title = t.get('title')
            if key and title:
                # Convert "2022.12." to "2022-12-01" (approximate for sorting/storage)
                # Or keep as is and let the caching script handle parsing
                # Daum returns "2022-12-01", let's try to match that format
                clean_date = title.rstrip('.')
                parts = clean_date.split('.')
                if len(parts) == 2:
                    date_str = f"{parts[0]}-{parts[1]}-01"
                elif len(parts) == 3:
                    date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
                else:
                    date_str = clean_date
                date_map[key] = date_str

        # Find relevant rows
        # Row titles: "매출액", "영업이익", "당기순이익"
        revenue_row = next((r for r in rows if r.get('title') == '매출액'), None)
        op_profit_row = next((r for r in rows if r.get('title') == '영업이익'), None)
        net_income_row = next((r for r in rows if r.get('title') == '당기순이익'), None)
        
        if not revenue_row:
            return parsed_data

        # Iterate over columns (dates)
        for key, date_str in date_map.items():
            try:
                # Helper to extract value
                def get_val(row, k):
                    if not row or 'columns' not in row or k not in row['columns']:
                        return 0.0
                    val_str = row['columns'][k].get('value', '0')
                    if val_str == '-' or not val_str:
                        return 0.0
                    return float(val_str.replace(',', ''))

                revenue = get_val(revenue_row, key)
                op_profit = get_val(op_profit_row, key)
                net_income = get_val(net_income_row, key)
                
                # Naver unit is 100 Million KRW (억 원). Convert to Won.
                # 1 억 = 100,000,000
                unit_multiplier = 100_000_000
                
                parsed_data.append({
                    'date': date_str,
                    'revenue': revenue * unit_multiplier,
                    'operating_profit': op_profit * unit_multiplier,
                    'net_income': net_income * unit_multiplier
                })
            except Exception as e:
                logger.warning(f"Error parsing Naver financial row for key {key}: {e}")
                continue
                
        # Sort by date
        parsed_data.sort(key=lambda x: x['date'])
        return parsed_data
