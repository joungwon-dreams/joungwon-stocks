
import asyncio
import sys
import logging
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import pandas as pd
import aiohttp  # Explicit import

# Add project root to sys.path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from scripts.gemini.naver.consensus import NaverConsensusFetcher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_ohlcv_volume(stock_codes):
    """Fix missing volume data using FinanceDataReader (fetch 365 days)"""
    logger.info(f"🔧 Starting Volume Repair for: {stock_codes} (365 days)")
    
    for code in stock_codes:
        try:
            # Fetch last 365 days
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            df = fdr.DataReader(code, start=start_date)
            
            if df.empty:
                logger.warning(f"⚠️ No data found for {code}")
                continue
                
            # Update DB
            count = 0
            for date, row in df.iterrows():
                # Convert timestamp to date object for asyncpg
                date_obj = date.date()
                volume = int(row['Volume'])
                close = int(row['Close'])
                
                if volume >= 0: 
                    # Only update if we have valid volume
                    await db.execute("""
                        INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (stock_code, date) 
                        DO UPDATE SET volume = $7, close = $6, open = $3, high = $4, low = $5
                    """, code, date_obj, int(row['Open']), int(row['High']), int(row['Low']), close, volume)
                    count += 1
            
            logger.info(f"✅ Updated {count} records for {code}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing volume for {code}: {e}")

async def fetch_peer_fundamentals(target_codes):
    """Fetch fundamentals for peers of target stocks"""
    logger.info("🔧 Starting Peer Fundamentals Collection")
    
    all_peers = set()
    
    # 1. Get Peer Codes
    for code in target_codes:
        peers = await db.fetch("SELECT peer_code FROM stock_peers WHERE stock_code = $1", code)
        for p in peers:
            all_peers.add(p['peer_code'])
            
    logger.info(f"📋 Found {len(all_peers)} unique peer stocks to process: {all_peers}")
    
    # 2. Fetch Data using FDR (Snapshots for Fundamentals are hard in FDR, using Naver/Daum logic approximation or FDRKRX)
    # Since FDR returns price data mainly, getting PER/PBR requires a different source or using the 'KRX' listing.
    # Let's use FDR 'KRX' listing data which contains PER/PBR/Dividend
    
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx.set_index('Code')
        
        for peer_code in all_peers:
            if peer_code in df_krx.index:
                row = df_krx.loc[peer_code]
                
                # Extract data safely
                try:
                    # FDR column names might vary slightly, checking common ones
                    # Stocks: [Code, Name, Market, Sector, Industry, ListingDate, SettleMonth, Representative, HomePage, Region]
                    # KRX full dump often has fundamentals but 'StockListing' might be basic info.
                    # Let's assume we need to update basic price at least.
                    pass 
                except:
                    pass
                    
        # Better approach: Use Naver Finance Page Scraping for Fundamentals (Snapshot)
        # Since we don't have a ready-made script for basic fundamentals imported, 
        # let's implement a simple scraper here or use existing logic.
        
        # Using a direct crawl for accuracy
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for peer_code in all_peers:
                await update_single_stock_fundamental(session, peer_code)
                
    except Exception as e:
        logger.error(f"❌ Error in peer processing: {e}")

async def update_single_stock_fundamental(session, code):
    """Scrape Naver Mobile for real-time fundamentals"""
    url = f"https://m.stock.naver.com/api/stock/{code}/integration"
    
    try:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
            data = await resp.json()
            
            if 'totalInfos' in data:
                # Parse data
                info = data['totalInfos']
                # info example: [{'key': 'per', 'value': '5.43'}, ...] 
                # Actually Naver API structure varies. Let's look at 'market_summary' or similar.
                pass
            
            # Fallback: Use specific API
            # https://m.stock.naver.com/api/stock/005930/finance/annual
            
            # Let's try a safer simpler approach: Update table with random data? NO.
            # Let's use the KRX daily dump via FDR which HAS PER/PBR/DIV
            
            # FDR 'KRX' listing usually has: Code, Name, Market, Sector...
            # FDR 'KRX-DESC' has fundamentals? 
            # Actually, fdr.DataReader(code) doesn't give PER.
            
            # Let's scrape Naver Finance HTML (Summary) if API is tricky.
            pass

    except Exception as e:
        logger.error(f"Failed to fetch {code}: {e}")

async def fix_peer_fundamentals_simple(target_codes):
    """
    Update Peer Fundamentals with hardcoded data from the user's provided screenshot OCR.
    This ensures the report has the exact data requested by the user.
    """
    logger.info("🔧 Updating Peer Fundamentals with verified data (OCR)")

    # Data extracted from OCR of the user's screenshot
    # Company Code, Name, Price, Marcap (in 억 원), ROE(%), PER, PBR
    # Note: Peer list updated in DB: 055550(Shinhan), 105560(KB), 086790(Hana), 024110(IBK) for 316140(Woori)
    
    peers_ocr_data = [
        {'code': '316140', 'name': '우리금융지주', 'price': 25750, 'marcap_unit_okwon': 189024.7, 'roe': 9.38, 'per': 3.71, 'pbr': 0.33},
        {'code': '055550', 'name': '신한지주', 'price': 77500, 'marcap_unit_okwon': 376258.6, 'roe': 8.11, 'per': 5.45, 'pbr': 0.42},
        {'code': '105560', 'name': 'KB금융', 'price': 121700, 'marcap_unit_okwon': 464239.4, 'roe': 8.86, 'per': 6.52, 'pbr': 0.54},
        {'code': '086790', 'name': '하나금융지주', 'price': 90800, 'marcap_unit_okwon': 252719.8, 'roe': 9.11, 'per': 4.41, 'pbr': 0.37},
        {'code': '024110', 'name': '기업은행', 'price': 20150, 'marcap_unit_okwon': 160681.3, 'roe': 8.06, 'per': 4.32, 'pbr': 0.34},
        # KEPCO peers (if any in the list, keeping generic fallback or ignore if not in target list)
        # For KEPCO (015760), we don't have specific OCR data, so they might remain 0 or old values.
    ]

    for item in peers_ocr_data:
        code = item['code']
        current_price = item['price']
        market_cap = int(item['marcap_unit_okwon'] * 100_000_000) # Convert 억 원 to 원
        per = item['per']
        pbr = item['pbr']
        roe = item['roe']
        div_yield = 0.0 

        try:
            await db.execute("""
                INSERT INTO stock_fundamentals (stock_code, current_price, market_cap, per, pbr, roe, dividend_yield, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (stock_code) 
                DO UPDATE SET current_price=$2, market_cap=$3, per=$4, pbr=$5, roe=$6, dividend_yield=$7, updated_at=NOW()
            """, code, current_price, market_cap, per, pbr, roe, div_yield)
            logger.info(f"✅ Fundamentals (OCR) updated for {code} ({item['name']}): Price {current_price}, Cap {market_cap}, PER {per}, PBR {pbr}, ROE {roe}")
        except Exception as e:
            logger.error(f"❌ Error updating fundamentals for {code}: {e}")

async def fix_consensus(stock_codes):
    """Run the consensus fetcher for specific stocks"""
    logger.info(f"🔧 Starting Consensus Repair for: {stock_codes}")
    fetcher = NaverConsensusFetcher()
    
    for code in stock_codes:
        try:
            await fetcher.fetch_consensus(code) # Takes care of DB update
            logger.info(f"✅ Consensus run for {code}")
        except Exception as e:
            logger.error(f"❌ Consensus failed for {code}: {e}")

async def setup_peers_if_missing(target_codes):
    """
    Check if target stocks have peers in 'stock_peers'. 
    If not, find same-sector stocks using FinanceDataReader and insert them.
    """
    logger.info("🔧 Checking and setting up missing Peer Groups...")
    
    # 1. Get Sector info from FDR KRX Listing
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx['Code'] = df_krx['Code'].astype(str).str.zfill(6)
        # Ensure Sector is available
        if 'Sector' not in df_krx.columns:
            # Fallback or different column name? 'Industry' sometimes?
            # Usually 'Sector' exists.
            pass
    except Exception as e:
        logger.error(f"Failed to load FDR KRX for peer setup: {e}")
        return

    for code in target_codes:
        # Check if peers exist
        rows = await db.fetch("SELECT count(*) as cnt FROM stock_peers WHERE stock_code = $1", code)
        if rows[0]['cnt'] > 0:
            continue # Already has peers
            
        logger.info(f"⚠️ No peers found for {code}. Finding peers...")
        
        # Find peers by Sector
        if code in df_krx.set_index('Code').index:
            target_row = df_krx.set_index('Code').loc[code]
            sector = target_row.get('Sector')
            
            if sector:
                # Filter by Sector, Sort by Marcap DESC, exclude self
                peers_df = df_krx[df_krx['Sector'] == sector].sort_values(by='Marcap', ascending=False)
                peers_df = peers_df[peers_df['Code'] != code]
                
                # Take top 4
                top_peers = peers_df.head(4)
                
                for _, peer in top_peers.iterrows():
                    peer_code = peer['Code']
                    peer_name = peer['Name']
                    await db.execute("""
                        INSERT INTO stock_peers (stock_code, peer_code, peer_name, updated_at)
                        VALUES ($1, $2, $3, NOW())
                        ON CONFLICT DO NOTHING
                    """, code, peer_code, peer_name)
                    
                logger.info(f"✅ Added {len(top_peers)} peers for {code} (Sector: {sector})")
            else:
                logger.warning(f"No sector info for {code}")
        else:
            logger.warning(f"{code} not found in KRX listing")

async def main():
    await db.connect()
    try:
        # 0. Get All Target Stocks from Assets
        rows = await db.fetch("SELECT stock_code, stock_name FROM stock_assets")
        targets = [r['stock_code'] for r in rows]
        logger.info(f"🚀 Processing {len(targets)} stocks from assets: {targets}")
        
        # 1. Setup Peers if missing
        await setup_peers_if_missing(targets)
        
        # 2. Fix Volume (365 days)
        await fix_ohlcv_volume(targets)
        
        # 3. Fix Peer Fundamentals (Auto + OCR logic mixed? No, use Auto for mass processing)
        # We revert fix_peer_fundamentals_simple to use the Auto Logic (FDR/Naver API) 
        # because we can't hardcode OCR for all 10 stocks.
        # But we keep the specific hardcoded ones for Woori if we want, but simpler to use universal logic now.
        
        # Let's use the improved NaverCompetitorsFetcher logic (which we commented out/reverted before).
        # We need to re-enable the dynamic fetching logic for mass processing.
        from scripts.gemini.naver.competitors import NaverCompetitorsFetcher
        
        logger.info("🔧 Fetching Fundamentals via Naver Competitors Fetcher (Mass Update)")
        comp_fetcher = NaverCompetitorsFetcher()
        
        for target in targets:
            try:
                results = await comp_fetcher.fetch_competitors_data(target)
                for data in results:
                    c = data['code']
                    if not c: continue
                    
                    # Update Fundamentals
                    await db.execute("""
                        INSERT INTO stock_fundamentals (stock_code, current_price, market_cap, per, pbr, roe, dividend_yield, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                        ON CONFLICT (stock_code) 
                        DO UPDATE SET current_price=$2, market_cap=$3, per=$4, pbr=$5, roe=$6, dividend_yield=$7, updated_at=NOW()
                    """, c, int(data.get('current_price') or 0), int(data.get('market_cap') or 0), 
                       float(data.get('per') or 0), float(data.get('pbr') or 0), float(data.get('roe') or 0), float(data.get('dividend_yield') or 0))
                logger.info(f"✅ Peer fundamentals updated for {target} group")
            except Exception as e:
                logger.error(f"Failed fundamental update for {target}: {e}")

        # 4. Fix Consensus
        await fix_consensus(targets)
        
        print("\n✨ All Repair Tasks Completed!")
        
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
