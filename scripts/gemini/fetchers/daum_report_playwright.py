from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import logging

logger = logging.getLogger(__name__)

class DaumReportPlaywrightFetcher:
    async def fetch_reports(self, stock_code: str):
        """
        Fetch analyst reports using Playwright to bypass API blocks.
        Target URL: https://finance.daum.net/quotes/A{code}#analysis/consensus
        """
        url = f"https://finance.daum.net/quotes/A{stock_code}#analysis/consensus"
        reports = []
        
        async with async_playwright() as p:
            # Use a realistic user agent
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # 1. Visit Main Page to get cookies/tokens
                main_url = f"https://finance.daum.net/quotes/A{stock_code}"
                logger.info(f"Navigating to {main_url} to Initialize Session...")
                await page.goto(main_url, wait_until='domcontentloaded')
                
                # 2. Call API directly using the browser's request context
                api_url = f"https://finance.daum.net/api/research/company?symbolCode=A{stock_code}&page=1&perPage=10"
                logger.info(f"Fetching API: {api_url}")
                
                # Add headers manually just in case, though browser context should handle some
                response = await page.request.get(api_url, headers={
                    'Referer': main_url,
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest'
                })
                
                if response.status == 200:
                    data = await response.json()
                    # Structure: {'data': [{'title': ..., 'cpName': ..., 'date': ...}, ...]}
                    for item in data.get('data', []):
                        reports.append({
                            'title': item.get('title', ''),
                            'firm': item.get('cpName', ''),
                            'date': item.get('date', '')[:10], # YYYY-MM-DD
                            'opinion': item.get('opinion', ''),
                            'target_price': item.get('newTargetPrice', 0),
                            'url': f"https://finance.daum.net/research/company/{item.get('id')}"
                        })
                else:
                    logger.error(f"Daum API Error via Playwright: {response.status} {response.status_text}")
                    
            except Exception as e:
                logger.error(f"Error fetching with Playwright: {e}")
            finally:
                await browser.close()
                
        return reports

if __name__ == "__main__":
    # Test run
    async def test():
        fetcher = DaumReportPlaywrightFetcher()
        data = await fetcher.fetch_reports('034230') # Paradise
        print(f"Fetched {len(data)} reports:")
        for d in data:
            print(d)
    asyncio.run(test())
