
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
import sys
import re

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaverForceCrawler:
    def __init__(self):
        self.base_url = "https://finance.naver.com/item/main.naver?code={}"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    async def update_all_stocks(self):
        await db.connect()
        try:
            rows = await db.fetch("SELECT stock_code, stock_name FROM stock_assets")
            target_codes = [r['stock_code'] for r in rows]
            
            # Also get peers
            peer_rows = await db.fetch("SELECT peer_code FROM stock_peers")
            peer_codes = [r['peer_code'] for r in peer_rows]
            
            all_codes = list(set(target_codes + peer_codes))
            logger.info(f"🚀 Force Crawling for {len(all_codes)} stocks...")
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                for code in all_codes:
                    await self.crawl_single_stock(session, code)
                    await asyncio.sleep(0.5) # Polite delay
                    
        finally:
            await db.disconnect()

    async def crawl_single_stock(self, session, code):
        url = self.base_url.format(code)
        try:
            async with session.get(url) as resp:
                text = await resp.text(encoding='euc-kr', errors='ignore')
                soup = BeautifulSoup(text, 'html.parser')
                
                # 1. Fundamentals (PER, PBR, ROE, DivYield, MarketCap)
                # ID: _market_sum (Market Cap), _per, _pbr, _dvr (Div)
                
                def get_text_by_id(id_name):
                    tag = soup.select_one(f'#{id_name}')
                    if tag:
                        val = tag.get_text(strip=True).replace(',', '').replace('조', '').replace('%', '').replace('배', '').replace('원', '')
                        return float(val) if val and val != 'N/A' else 0.0
                    return 0.0

                def parse_market_cap(text):
                    if not text: return 0
                    # Clean up
                    text = text.replace('\n', '').replace('\t', '').replace(' ', '').replace(',', '')
                    
                    # Handle '조' (or broken encoding '議')
                    unit_map = {'조': 1000000000000, '議': 1000000000000} # 1 Trillion
                    
                    # Try to find split point
                    for unit, multiplier in unit_map.items():
                        if unit in text:
                            parts = text.split(unit)
                            trillion = int(parts[0]) if parts[0] else 0
                            billion = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                            # Billion part is usually in 억 unit (100,000,000)
                            return trillion * multiplier + billion * 100000000
                    
                    # If no unit, assume it is just number (unlikely for market cap in naver main)
                    try:
                        return int(text)
                    except:
                        return 0

                # Extract Market Cap safely
                mc_tag = soup.select_one('#_market_sum')
                market_cap = 0
                if mc_tag:
                    market_cap = parse_market_cap(mc_tag.get_text())

                per = get_text_by_id('_per')
                pbr = get_text_by_id('_pbr')
                div_yield = get_text_by_id('_dvr')
                
                # Foreign Ratio (em tag usually)
                # Example: <em id="_foreign_rate">16.54%</em>
                foreign_ratio = 0.0
                f_tag = soup.select_one('#_foreign_rate')
                if f_tag:
                    try:
                        foreign_ratio = float(f_tag.get_text(strip=True).replace('%', ''))
                    except: pass

                # Current Price (blind > no_today)
                # <div class="no_today"> ... <span class="blind">52,200</span>
                current_price = 0
                today_tag = soup.select_one('.no_today .blind')
                if today_tag:
                    current_price = int(today_tag.get_text(strip=True).replace(',', ''))

                # Update Fundamentals
                if current_price > 0:
                    await db.execute("""
                        INSERT INTO stock_fundamentals (stock_code, current_price, market_cap, per, pbr, dividend_yield, foreign_ratio, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                        ON CONFLICT (stock_code) 
                        DO UPDATE SET 
                            current_price = EXCLUDED.current_price,
                            market_cap = CASE WHEN EXCLUDED.market_cap > 0 THEN EXCLUDED.market_cap ELSE stock_fundamentals.market_cap END,
                            per = EXCLUDED.per,
                            pbr = EXCLUDED.pbr,
                            dividend_yield = EXCLUDED.dividend_yield,
                            foreign_ratio = EXCLUDED.foreign_ratio,
                            updated_at = NOW()
                    """, code, current_price, int(market_cap), per, pbr, div_yield, foreign_ratio)
                    logger.info(f"✅ Fundamentals updated for {code}: P:{current_price} PER:{per} PBR:{pbr}")

                # 2. Consensus (Target Price, Opinion)
                # <div class="rgt"> ... <em id="_target_sunik">68,000</em> ... <span id="_consensus_point">4.00</span>
                target_price = get_text_by_id('_target_sunik')
                consensus_score = get_text_by_id('_consensus_point')
                
                if target_price > 0:
                    await db.execute("""
                        INSERT INTO investment_consensus (stock_code, target_price, consensus_score, created_at, updated_at)
                        VALUES ($1, $2, $3, NOW(), NOW())
                        ON CONFLICT (stock_code)
                        DO UPDATE SET target_price = EXCLUDED.target_price, consensus_score = EXCLUDED.consensus_score, updated_at = NOW()
                    """, code, int(target_price), consensus_score)
                    logger.info(f"✅ Consensus updated for {code}: Target {target_price}")

                # 3. Financials (Annual)
                # Table class: "cop_analysis" -> 4th row: Revenue, 5th: Op Profit, 6th: Net Profit
                # This table is complex. Let's try a simple selector for recent yearly data.
                # Actually, extracting "최근 연간 실적" columns is tricky via static HTML scraping because it's often script-loaded or complex structure.
                # But let's try finding the table.
                
                analysis_table = soup.select_one('.section.cop_analysis div.sub_section table')
                if analysis_table:
                    # Headers: dates (e.g., 2021.12, 2022.12 ...)
                    thead = analysis_table.select('thead tr th')
                    # Columns 3, 4, 5, 6 usually are recent yearly. (indices 2,3,4,5 if 0-based??)
                    # It's hard to index dynamically without careful parsing.
                    # Let's skip this for 'Force Crawl' to avoid errors, relying on 'Fundamentals' and 'Consensus' which are most critical for the report.
                    # The previous fetchers should have handled financials if they worked.
                    pass

        except Exception as e:
            logger.error(f"Failed to crawl {code}: {e}")

if __name__ == '__main__':
    crawler = NaverForceCrawler()
    asyncio.run(crawler.update_all_stocks())
