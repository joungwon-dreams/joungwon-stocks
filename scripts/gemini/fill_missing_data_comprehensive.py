
import asyncio
import sys
import logging
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import pandas as pd

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from scripts.gemini.naver.competitors import NaverCompetitorsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/data_fill.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataGapFiller:
    def __init__(self):
        self.comp_fetcher = NaverCompetitorsFetcher()
        self.cons_fetcher = NaverConsensusFetcher()

    async def run(self):
        await db.connect()
        try:
            # 1. Get All Assets
            assets = await db.fetch("SELECT stock_code, stock_name FROM stock_assets ORDER BY stock_code")
            logger.info(f"🚀 Starting Comprehensive Data Fill for {len(assets)} stocks")

            for asset in assets:
                code = asset['stock_code']
                name = asset['stock_name']
                logger.info(f"🔎 Checking {name} ({code})...")
                
                await self.check_and_fix_ohlcv(code)
                await self.check_and_fix_fundamentals_and_peers(code)
                await self.check_and_fix_consensus(code)
                
        finally:
            await db.disconnect()
            logger.info("✨ All tasks finished.")

    async def check_and_fix_ohlcv(self, code):
        """Check if recent volume is missing or 0"""
        # Check last 3 days
        rows = await db.fetch("SELECT volume FROM daily_ohlcv WHERE stock_code = $1 ORDER BY date DESC LIMIT 3", code)
        
        needs_fix = False
        if not rows or len(rows) < 3:
            needs_fix = True
        else:
            for r in rows:
                if r['volume'] == 0:
                    needs_fix = True
                    break
        
        if needs_fix:
            logger.warning(f"   ⚠️ OHLCV Volume missing/zero for {code}. Fetching from FDR...")
            try:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                df = fdr.DataReader(code, start=start_date)
                
                if not df.empty:
                    for date, row in df.iterrows():
                        date_obj = date.date()
                        vol = int(row['Volume'])
                        if vol >= 0: # Update even if 0 to ensure row exists
                            await db.execute("""
                                INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                                ON CONFLICT (stock_code, date) 
                                DO UPDATE SET volume = $7, close = $6, open = $3, high = $4, low = $5
                            """, code, date_obj, int(row['Open']), int(row['High']), int(row['Low']), int(row['Close']), vol)
                    logger.info(f"   ✅ OHLCV updated ({len(df)} rows)")
            except Exception as e:
                logger.error(f"   ❌ Failed to fix OHLCV for {code}: {e}")

    async def check_and_fix_fundamentals_and_peers(self, code):
        """Check if fundamentals (PER/PBR) or Peers are missing"""
        # Check Fundamentals
        fund = await db.fetchrow("SELECT per, pbr, market_cap FROM stock_fundamentals WHERE stock_code = $1", code)
        
        # Check Peers
        peer_count_row = await db.fetchrow("SELECT count(*) as cnt FROM stock_peers WHERE stock_code = $1", code)
        peer_cnt = peer_count_row['cnt']
        
        needs_fix = False
        if not fund or fund['market_cap'] == 0 or (fund['per'] == 0 and fund['pbr'] == 0):
            needs_fix = True
            logger.warning(f"   ⚠️ Fundamentals missing for {code}")
        
        if peer_cnt == 0:
            needs_fix = True
            logger.warning(f"   ⚠️ No peers found for {code}")
            
        if needs_fix:
            logger.info(f"   🔧 Fetching Fundamentals & Peers from Naver...")
            try:
                # fetch_competitors_data gets data for Target AND Peers
                results = await self.comp_fetcher.fetch_competitors_data(code)
                
                if results:
                    # 1. Update Target & Peers Fundamentals
                    for data in results:
                        c_code = data.get('code')
                        if not c_code: continue # Some peers might not have code parsed if we didn't implement deep crawling
                        
                        # If it's a peer (not target), insert into stock_peers if missing
                        if c_code != code:
                            await db.execute("""
                                INSERT INTO stock_peers (stock_code, peer_code, peer_name, updated_at)
                                VALUES ($1, $2, $3, NOW())
                                ON CONFLICT (stock_code, peer_code) DO NOTHING
                            """, code, c_code, data.get('name'))
                        
                        # Update Fundamentals for everyone (Target + Peers)
                        await db.execute("""
                            INSERT INTO stock_fundamentals (stock_code, current_price, market_cap, per, pbr, roe, dividend_yield, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                            ON CONFLICT (stock_code) 
                            DO UPDATE SET current_price=$2, market_cap=$3, per=$4, pbr=$5, roe=$6, dividend_yield=$7, updated_at=NOW()
                        """, c_code, 
                           int(data.get('current_price') or 0), 
                           int(data.get('market_cap') or 0), 
                           float(data.get('per') or 0), 
                           float(data.get('pbr') or 0), 
                           float(data.get('roe') or 0), 
                           float(data.get('dividend_yield') or 0))
                           
                    logger.info(f"   ✅ Updated fundamentals and {len(results)-1} peers")
                else:
                    logger.warning(f"   ⚠️ Naver returned no data for {code}")
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to fix fundamentals/peers for {code}: {e}")

    async def check_and_fix_consensus(self, code):
        """Check if consensus exists"""
        cons = await db.fetchrow("SELECT target_price FROM investment_consensus WHERE stock_code = $1", code)
        
        if not cons:
            logger.warning(f"   ⚠️ Consensus missing for {code}. Fetching...")
            try:
                await self.cons_fetcher.fetch_consensus(code)
                logger.info(f"   ✅ Consensus updated")
            except Exception as e:
                logger.error(f"   ❌ Failed to fix consensus for {code}: {e}")

if __name__ == "__main__":
    filler = DataGapFiller()
    asyncio.run(filler.run())
