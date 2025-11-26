
import asyncio
import sys
import logging
import FinanceDataReader as fdr
import pandas as pd

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def repair_fundamentals():
    await db.connect()
    try:
        logger.info("🚀 Fetching KRX Listing data via FinanceDataReader...")
        df_krx = fdr.StockListing('KRX')
        
        # Prepare DataFrame
        # Columns might include: Code, Name, Close, PER, PBR, DividendYield (sometimes MarketCap)
        # FDR columns change often. Let's inspect keys if possible, but assume standard names.
        # Usually: 'Code', 'Name', 'Close', 'Marcap', 'Stocks', 'Market'
        # 'PER', 'PBR' might be in 'KRX-DESC' or different call? 
        # Actually 'KRX' listing usually has basic price. 
        # 'KRX-DESC' is deprecated or merged.
        
        # Let's try 'KRX' first. If PER is missing, we might need another source.
        # But Price and Marcap are definitely there.
        
        df_krx['Code'] = df_krx['Code'].astype(str).str.zfill(6)
        df_krx = df_krx.set_index('Code')
        
        # Get all stocks from DB (Target + Peers)
        targets = await db.fetch("SELECT stock_code FROM stocks")
        target_codes = [r['stock_code'] for r in targets]
        
        # Also fetch peers just in case
        peers = await db.fetch("SELECT peer_code FROM stock_peers")
        peer_codes = [r['peer_code'] for r in peers]
        
        all_codes = set(target_codes + peer_codes)
        
        logger.info(f"Updating fundamentals for {len(all_codes)} stocks...")
        
        count = 0
        for code in all_codes:
            if code in df_krx.index:
                row = df_krx.loc[code]
                
                def safe_get_int(val):
                    try:
                        return int(str(val).replace(',', ''))
                    except:
                        return 0
                        
                def safe_get_float(val):
                    try:
                        return float(str(val).replace(',', ''))
                    except:
                        return 0.0
                
                # Extract (Safe get)
                current_price = safe_get_int(row.get('Close'))
                market_cap = safe_get_int(row.get('Marcap'))
                
                per = safe_get_float(row.get('PER'))
                pbr = safe_get_float(row.get('PBR'))
                div_yield = safe_get_float(row.get('DividendYield'))
                
                # ROE is not in FDR usually. Keep existing or 0.
                
                await db.execute("""
                    INSERT INTO stock_fundamentals (stock_code, current_price, market_cap, per, pbr, dividend_yield, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (stock_code) 
                    DO UPDATE SET 
                        current_price = EXCLUDED.current_price,
                        market_cap = EXCLUDED.market_cap,
                        per = CASE WHEN EXCLUDED.per > 0 THEN EXCLUDED.per ELSE stock_fundamentals.per END,
                        pbr = CASE WHEN EXCLUDED.pbr > 0 THEN EXCLUDED.pbr ELSE stock_fundamentals.pbr END,
                        dividend_yield = CASE WHEN EXCLUDED.dividend_yield > 0 THEN EXCLUDED.dividend_yield ELSE stock_fundamentals.dividend_yield END,
                        updated_at = NOW()
                """, code, current_price, market_cap, per, pbr, div_yield)
                count += 1
                
        logger.info(f"✅ Successfully updated {count} stocks from FDR KRX listing.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(repair_fundamentals())
