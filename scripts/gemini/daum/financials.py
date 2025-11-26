import aiohttp
import logging
from typing import Dict, Any
from .base import DaumBaseFetcher

logger = logging.getLogger(__name__)

class DaumFinancialsFetcher(DaumBaseFetcher):
    async def fetch_ratios(self, stock_code: str) -> dict:
        """
        Fetch key financial ratios and peer data from sector info.
        Returns: {'ratios': dict, 'peers': list}
        """
        symbol_code = f"A{stock_code}"
        url = f"{self.BASE_URL}/quote/{symbol_code}/sectors"
        
        result = {'ratios': {}, 'peers': []}
        try:
            async with aiohttp.ClientSession(headers=self._get_headers(symbol_code)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get('data', [])
                        
                        # Find target stock
                        target = next((item for item in items if item['symbolCode'] == symbol_code), None)
                        if target:
                            result['ratios'] = {
                                'per': target.get('per'),
                                'pbr': target.get('pbr'),
                                'roe': target.get('roe'),
                                'market_cap': target.get('marketCap'),
                                'revenue': target.get('netSales'),
                                'operating_profit': target.get('operatingProfit'),
                                'net_income': target.get('netIncome')
                            }
                            
                        # Peers (All items in sector response)
                        for item in items:
                            if item['symbolCode'] != symbol_code:
                                result['peers'].append({
                                    'name': item['name'],
                                    'code': item['symbolCode'][1:], # Remove 'A'
                                    'per': item.get('per'),
                                    'pbr': item.get('pbr')
                                })
        except Exception as e:
            logger.error(f"Daum ratios fetch error: {e}")
        return result

    async def fetch_statements(self, stock_code: str) -> Dict[str, Any]:
        """Fetch yearly and quarterly financial statements."""
        # Use singular 'quote' endpoint
        symbol_code = f"A{stock_code}"
        url = f"{self.BASE_URL}/quote/{symbol_code}/financials"
        
        financials = {'yearly': [], 'quarterly': []}
        try:
            # Referer header is critical for this endpoint
            headers = self._get_headers(symbol_code)
            headers['Referer'] = f"https://finance.daum.net/quotes/{symbol_code}"
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Structure: {'data': {'YEAR': [...], 'QUARTER': [...]}}
                        fin_data = data.get('data', {})
                        
                        # Parse Yearly
                        for item in fin_data.get('YEAR', []):
                            financials['yearly'].append({
                                'date': item.get('date', ''), # e.g., '2023-12-01'
                                'revenue': float(item.get('sales', 0) or 0),
                                'operating_profit': float(item.get('operatingProfit', 0) or 0),
                                'net_income': float(item.get('netIncome', 0) or 0)
                            })
                            
                        # Parse Quarterly
                        for item in fin_data.get('QUARTER', []):
                            financials['quarterly'].append({
                                'date': item.get('date', ''),
                                'revenue': float(item.get('sales', 0) or 0),
                                'operating_profit': float(item.get('operatingProfit', 0) or 0),
                                'net_income': float(item.get('netIncome', 0) or 0)
                            })
                            
        except Exception as e:
            logger.error(f"Daum financials fetch error: {e}")
            
        return financials
