"""
Collect and Cache Stock Data
Integrates existing Daum/Naver fetchers with database cache tables.
Designed for daily scheduled runs to keep data fresh.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from scripts.gemini.daum.price import DaumPriceFetcher
from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.daum.financials import DaumFinancialsFetcher
from scripts.gemini.daum.reports import DaumReportsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.naver.news import NaverNewsFetcher
from scripts.gemini.naver.financials import NaverFinancialsFetcher
from scripts.gemini.naver.credit import NaverCreditFetcher
async def cache_fundamentals(stock_code: str, daum_price: DaumPriceFetcher, daum_fin: DaumFinancialsFetcher):
    """Cache fundamental data (stock_fundamentals table)"""
    print(f"   📊 Caching fundamentals for {stock_code}...")

    # Fetch quote and financial ratios
    quote = await daum_price.fetch_quote(stock_code)
    fin_data = await daum_fin.fetch_ratios(stock_code)
    ratios = fin_data.get('ratios', {})

    # Upsert to stock_fundamentals
    # Calculate Dividend Yield
    dps = quote.get('dps')
    price = quote.get('tradePrice')
    dividend_yield = 0.0
    if dps and price:
        dividend_yield = (float(dps) / float(price)) * 100

    query = '''
        INSERT INTO stock_fundamentals (
            stock_code, current_price, change_rate, change_price,
            open_price, high_price, low_price, acc_trade_volume, acc_trade_price,
            week52_high, week52_low, market_cap, foreign_ratio,
            per, pbr, eps, roe, bps,
            sector, dividend_yield, company_summary,
            updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, 
            $19, $20, $21,
            NOW()
        )
        ON CONFLICT (stock_code) DO UPDATE SET
            current_price = EXCLUDED.current_price,
            change_rate = EXCLUDED.change_rate,
            change_price = EXCLUDED.change_price,
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            acc_trade_volume = EXCLUDED.acc_trade_volume,
            acc_trade_price = EXCLUDED.acc_trade_price,
            week52_high = EXCLUDED.week52_high,
            week52_low = EXCLUDED.week52_low,
            market_cap = EXCLUDED.market_cap,
            foreign_ratio = EXCLUDED.foreign_ratio,
            per = EXCLUDED.per,
            pbr = EXCLUDED.pbr,
            eps = EXCLUDED.eps,
            roe = EXCLUDED.roe,
            bps = EXCLUDED.bps,
            sector = EXCLUDED.sector,
            dividend_yield = EXCLUDED.dividend_yield,
            company_summary = EXCLUDED.company_summary,
            updated_at = NOW()
    '''

    await db.execute(query,
        stock_code,
        quote.get('tradePrice', 0),
        quote.get('changeRate', 0.0),
        quote.get('changePrice', 0),
        quote.get('openingPrice', 0),
        quote.get('highPrice', 0),
        quote.get('lowPrice', 0),
        quote.get('accTradeVolume', 0),
        quote.get('accTradePrice', 0),
        quote.get('high52wPrice', 0),
        quote.get('low52wPrice', 0),
        quote.get('marketCap', 0),
        quote.get('foreignRatio', 0.0),
        ratios.get('per', 0.0),
        ratios.get('pbr', 0.0),
        ratios.get('eps', 0),
        ratios.get('roe', 0.0),
        ratios.get('bps', 0),
        quote.get('wicsSectorName', ''),
        dividend_yield,
        quote.get('companySummary', '')
    )

    print(f"   ✅ Fundamentals cached (Price: {quote.get('tradePrice'):,}원)")





async def cache_peers(stock_code: str, daum_fin: DaumFinancialsFetcher):
    """Cache peer companies (stock_peers table)"""
    print(f"   🏢 Caching peers for {stock_code}...")

    fin_data = await daum_fin.fetch_ratios(stock_code)
    peers = fin_data.get('peers', [])

    if not peers:
        print(f"   ⚠️ No peer data available")
        return

    # Delete old peers first
    await db.execute('DELETE FROM stock_peers WHERE stock_code = $1', stock_code)

    # Insert new peers
    for peer in peers:
        query = '''
            INSERT INTO stock_peers (stock_code, peer_code, peer_name, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (stock_code, peer_code) DO UPDATE SET
                peer_name = EXCLUDED.peer_name,
                updated_at = NOW()
        '''
        await db.execute(query, stock_code, peer.get('code'), peer.get('name'))

    print(f"   ✅ {len(peers)} peers cached")


async def cache_investor_trends(stock_code: str, daum_supply: DaumSupplyFetcher, days: int = 10):
    """Cache investor trends (investor_trends table)"""
    print(f"   📈 Caching investor trends for {stock_code} (last {days} days)...")

    trends = await daum_supply.fetch_history(stock_code, days)

    if not trends:
        print(f"   ⚠️ No investor trends data available")
        return

    # Insert/update each day's data
    inserted = 0
    for trend in trends:
        query = '''
            INSERT INTO investor_trends (
                stock_code, trade_date, individual, "foreign", institutional, collected_at
            ) VALUES (
                $1, $2, $3, $4, $5, NOW()
            )
            ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                individual = EXCLUDED.individual,
                "foreign" = EXCLUDED."foreign",
                institutional = EXCLUDED.institutional,
                collected_at = NOW()
        '''
        # Parse date (handle string or date object)
        trade_date = trend['date']
        if isinstance(trade_date, str):
            trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()

        await db.execute(query,
            stock_code,
            trade_date,
            trend.get('individual', 0),
            trend.get('foreign', 0),
            trend.get('institutional', 0)
        )
        inserted += 1

    print(f"   ✅ {inserted} days of investor trends cached")


async def cache_ohlcv_to_db(stock_code: str, daum_price: DaumPriceFetcher, days: int = 365):
    """Cache OHLCV history to daily_ohlcv table (if not already exists)"""
    print(f"   📉 Checking OHLCV history for {stock_code}...")

    # Check existing data count
    count_query = 'SELECT COUNT(*) FROM daily_ohlcv WHERE stock_code = $1'
    existing_count = await db.fetchval(count_query, stock_code)

    if existing_count >= 200:
        print(f"   ✅ OHLCV already cached ({existing_count} days)")
        return

    print(f"   📥 Fetching {days} days OHLCV from Daum...")
    history = await daum_price.fetch_history(stock_code, days)

    if not history:
        print(f"   ⚠️ No OHLCV data available")
        return

    # Insert/update OHLCV data
    inserted = 0
    for item in history:
        query = '''
            INSERT INTO daily_ohlcv (
                stock_code, date, open, high, low, close, volume, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, NOW()
            )
            ON CONFLICT (stock_code, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                created_at = NOW()
        '''
        # Parse date (handle string or date object)
        ohlcv_date = item['date']
        if isinstance(ohlcv_date, str):
            ohlcv_date = datetime.strptime(ohlcv_date, '%Y-%m-%d').date()

        await db.execute(query,
            stock_code,
            ohlcv_date,
            item['open'],
            item['high'],
            item['low'],
            item['close'],
            item['volume']
        )
        inserted += 1

    print(f"   ✅ {inserted} days OHLCV cached")


async def cache_financial_statements(stock_code: str, daum_fin: DaumFinancialsFetcher, naver_fin: NaverFinancialsFetcher):
    """Cache financial statements (stock_financials table)"""
    print(f"   📊 Caching financial statements for {stock_code}...")

    # 1. Try Daum first
    statements = await daum_fin.fetch_statements(stock_code)
    source = "Daum"
    
    # 2. Fallback to Naver if Daum is empty
    if not statements['yearly'] and not statements['quarterly']:
        print(f"   ⚠️ Daum financials empty, trying Naver...")
        statements = await naver_fin.fetch_statements(stock_code)
        source = "Naver"

    if not statements['yearly'] and not statements['quarterly']:
        print(f"   ⚠️ No financial statements available (Daum & Naver)")
        return

    print(f"   ✅ Fetched financials from {source}")

    inserted = 0
    # Process both yearly and quarterly
    for period_type in ['yearly', 'quarterly']:
        for item in statements[period_type]:
            # Parse date to get year and quarter
            period_date_str = item['date']
            fiscal_year = 0
            fiscal_quarter = 4 # Default for yearly
            
            try:
                if isinstance(period_date_str, str):
                    p_date = datetime.strptime(period_date_str, '%Y-%m-%d').date()
                    fiscal_year = p_date.year
                    month = p_date.month
                    fiscal_quarter = (month - 1) // 3 + 1
                else:
                    continue
            except ValueError:
                continue

            query = '''
                INSERT INTO stock_financials (
                    stock_code, period_type, fiscal_year, fiscal_quarter, 
                    revenue, operating_profit, net_profit, collected_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, NOW()
                )
                ON CONFLICT (stock_code, period_type, fiscal_year, fiscal_quarter) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    operating_profit = EXCLUDED.operating_profit,
                    net_profit = EXCLUDED.net_profit,
                    collected_at = NOW()
            '''
            
            await db.execute(query,
                stock_code,
                period_type,
                fiscal_year,
                fiscal_quarter,
                int(item.get('revenue', 0)),
                int(item.get('operating_profit', 0)),
                int(item.get('net_income', 0))
            )
            inserted += 1

    print(f"   ✅ {inserted} financial statements cached")


async def cache_analyst_reports_legacy(stock_code: str, naver_cons: NaverConsensusFetcher):
    """Cache analyst reports (analyst_reports table)"""
    print(f"   📑 Caching analyst reports for {stock_code}...")

    reports = await naver_cons.fetch_analyst_reports(stock_code)
    
    if not reports:
        print(f"   ⚠️ No analyst reports available")
        return

    inserted = 0
    for report in reports:
        query = '''
            INSERT INTO analyst_reports (
                stock_code, report_title, securities_firm, report_date, opinion, target_price, report_url, collected_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, NOW()
            )
            ON CONFLICT (stock_code, securities_firm, report_date) DO UPDATE SET
                report_title = EXCLUDED.report_title,
                opinion = EXCLUDED.opinion,
                target_price = EXCLUDED.target_price,
                report_url = EXCLUDED.report_url,
                collected_at = NOW()
        '''
        
        # Parse date
        report_date = report['date']
        if isinstance(report_date, str):
            try:
                # Naver usually returns 'YYYY.MM.DD' or 'YY.MM.DD'
                # Check format from debug output or assume standard
                if '.' in report_date:
                    if len(report_date.split('.')[0]) == 4:
                        report_date = datetime.strptime(report_date, '%Y.%m.%d').date()
                    else:
                         report_date = datetime.strptime(report_date, '%y.%m.%d').date()
                elif '-' in report_date:
                    report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
            except ValueError:
                continue
                
        # Parse target price (remove commas)
        target_price = report.get('target_price')
        if target_price and isinstance(target_price, str):
            try:
                target_price = int(target_price.replace(',', ''))
            except ValueError:
                target_price = None
        elif not target_price:
            target_price = None
        else:
            target_price = int(target_price)

        await db.execute(query,
            stock_code,
            report.get('title', ''),
            report.get('firm', ''),
            report_date,
            report.get('opinion', ''),
            target_price,
            report.get('url', '')
        )
        inserted += 1

    print(f"   ✅ {inserted} analyst reports cached")


async def cache_credit_rating(stock_code: str, naver_credit: NaverCreditFetcher):
    """Fetch and cache credit rating"""
    print(f"   💳 Caching credit rating for {stock_code}...")
    rating_info = await naver_credit.fetch_credit_rating(stock_code)
    
    if rating_info:
        query = '''
            INSERT INTO stock_credit_rating (
                stock_code, agency, rating, date, collected_at
            ) VALUES (
                $1, $2, $3, $4, NOW()
            )
            ON CONFLICT (stock_code, agency, date) DO UPDATE SET
                rating = EXCLUDED.rating,
                collected_at = NOW()
        '''
        await db.execute(query,
            stock_code,
            rating_info.get('agency', 'Unknown'),
            rating_info.get('rating'),
            rating_info.get('date') or datetime.now().date()
        )
        print(f"   ✅ Credit rating cached: {rating_info.get('rating')}")
    else:
        print(f"   ⚠️ No credit rating found")

async def cache_daum_reports(stock_code: str, daum_reports: DaumReportsFetcher):
    """Fetch and cache analyst reports from Daum"""
    print(f"   📑 Caching Daum analyst reports for {stock_code}...")
    reports = await daum_reports.fetch_reports(stock_code)
    
    if not reports:
        print(f"   ⚠️ No Daum reports available")
        return

    query = '''
        INSERT INTO analyst_reports (
            stock_code, report_title, securities_firm, report_date, opinion, target_price, report_url, collected_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, NOW()
        )
        ON CONFLICT (stock_code, securities_firm, report_date) DO UPDATE SET
            report_title = EXCLUDED.report_title,
            opinion = EXCLUDED.opinion,
            target_price = EXCLUDED.target_price,
            report_url = EXCLUDED.report_url,
            collected_at = NOW()
    '''

    for r in reports:
        # Parse target price
        tp = r['target_price']
        if isinstance(tp, str):
            tp = int(tp.replace(',', '')) if tp.replace(',', '').isdigit() else 0
            
        await db.execute(query,
            stock_code,
            r['title'],
            r['firm'],
            datetime.strptime(r['date'], '%Y-%m-%d').date(),
            r['opinion'],
            tp,
            r['url']
        )
    
    print(f"   ✅ {len(reports)} Daum reports cached")

async def cache_analyst_target_prices(stock_code: str, naver_news: NaverNewsFetcher):
    """
    Fetch and cache analyst reports/target prices.
    Fallback: Use Naver News to find target price updates.
    """
    print(f"   📑 Caching analyst reports (via News) for {stock_code}...")
    
    # We need stock name for the query
    # Fetch name using DaumPriceFetcher
    daum_price = DaumPriceFetcher()
    quote = await daum_price.fetch_quote(stock_code)
    stock_name = quote.get('name', '')
    
    if not stock_name:
        print("   ⚠️ Could not determine stock name for news search")
        return

    reports = await naver_news.fetch_target_price_news(stock_code, stock_name)
    
    if not reports:
        print(f"   ⚠️ No target price news found for {stock_name}")
        return

    query = '''
        INSERT INTO analyst_target_prices (
            stock_code, title, brokerage, report_date, opinion, target_price, url, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, NOW()
        )
        ON CONFLICT (stock_code, brokerage, report_date) DO UPDATE SET
            title = EXCLUDED.title,
            target_price = EXCLUDED.target_price,
            url = EXCLUDED.url,
            updated_at = NOW()
    '''

    for r in reports:
        # Date format from Naver News is usually YYYYMMDD or datetime
        # We need YYYY-MM-DD (or YYYYMMDD as per user request? User schema says VARCHAR(8))
        # User requested: '20251119' (YYYYMMDD)
        # NaverNewsFetcher returns YYYYMMDD in 'date' field (from Step 1076: parsed['date'] = item.get('datetime', '')[:8])
        # So we can use it directly.
        
        await db.execute(query,
            stock_code,
            r['title'],
            r['firm'],
            r['date'], # YYYYMMDD
            'Buy', # Default opinion
            r['target_price'],
            r['url']
        )
    
    print(f"   ✅ {len(reports)} analyst target prices (from news) cached")

async def cache_consensus(stock_code: str, naver_cons: NaverConsensusFetcher):
    """Fetch and cache consensus (Basic + Detail)"""
    print(f"   🎯 Caching consensus for {stock_code}...")
    
    # 1. Basic Consensus
    cons = await naver_cons.fetch_consensus(stock_code)
    
    # 2. Detailed Consensus
    detail = await naver_cons.fetch_consensus_detail(stock_code)
    
    # Merge detail into cons
    cons.update(detail)

    query = '''
        INSERT INTO stock_consensus (
            stock_code, target_price, opinion, 
            eps_consensus, per_consensus, target_high, target_low,
            updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, NOW()
        )
        ON CONFLICT (stock_code) DO UPDATE SET
            target_price = EXCLUDED.target_price,
            opinion = EXCLUDED.opinion,
            eps_consensus = EXCLUDED.eps_consensus,
            per_consensus = EXCLUDED.per_consensus,
            target_high = EXCLUDED.target_high,
            target_low = EXCLUDED.target_low,
            updated_at = NOW()
    '''

    # Parse numeric fields
    def parse_int(val):
        if isinstance(val, str):
            val = val.replace(',', '')
            if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                return int(val)
        if isinstance(val, (int, float)):
            return int(val)
        return 0

    target_price = parse_int(cons.get('target_price'))
    eps_consensus = parse_int(cons.get('eps'))
    target_high = parse_int(cons.get('target_high'))
    target_low = parse_int(cons.get('target_low'))
    
    await db.execute(query,
        stock_code,
        target_price,
        cons.get('opinion', 0.0),
        eps_consensus,
        cons.get('per', 0.0),
        target_high,
        target_low
    )

    print(f"   ✅ Consensus cached (Target: {target_price}, EPS: {eps_consensus})")

async def collect_peer_data(daum_price: DaumPriceFetcher, daum_fin: DaumFinancialsFetcher, naver_fin: NaverFinancialsFetcher):
    """Collect fundamentals and financials for specific peer companies"""
    peers = [
        {'code': '036460', 'name': '한국가스공사'},
        {'code': '071320', 'name': '지역난방공사'},
        {'code': '004690', 'name': '삼천리'},
        {'code': '005090', 'name': 'SGC에너지'}
    ]
    
    print(f"\n{'='*60}")
    print(f"🔄 Collecting data for {len(peers)} Peer Companies")
    print(f"{'='*60}")
    
    for peer in peers:
        code = peer['code']
        name = peer['name']
        print(f"\n👉 Processing Peer: {name} ({code})")
        
        try:
            # 1. Fundamentals (Price, PER, PBR, Market Cap, etc.)
            await cache_fundamentals(code, daum_price, daum_fin)
            
            # 2. Financial Statements (Revenue, Operating Profit, etc.)
            await cache_financial_statements(code, daum_fin, naver_fin)
            
        except Exception as e:
            print(f"❌ Error collecting peer data for {name} ({code}): {e}")

async def collect_and_cache_stock(stock_code: str):
    """Main orchestration function for a single stock"""
    print(f"\n{'='*60}")
    print(f"🔄 Collecting and caching data for {stock_code}")
    print(f"{'='*60}")

    # Initialize Fetchers
    daum_price = DaumPriceFetcher()
    daum_supply = DaumSupplyFetcher()
    daum_fin = DaumFinancialsFetcher()
    daum_reports = DaumReportsFetcher() # New
    naver_cons = NaverConsensusFetcher()
    naver_news = NaverNewsFetcher()
    naver_fin = NaverFinancialsFetcher()
    naver_credit = NaverCreditFetcher() # New

    try:
        # 1. Cache Fundamentals (Price, Market Cap, PER/PBR, Sector, Dividend)
        await cache_fundamentals(stock_code, daum_price, daum_fin)

        # 2. Cache Consensus (Target Price, Opinion, EPS, PER) - Updated
        await cache_consensus(stock_code, naver_cons)
        
        # 3. Cache Credit Rating - New
        await cache_credit_rating(stock_code, naver_credit)

        # 4. Cache peers (weekly, but safe to run daily)
        await cache_peers(stock_code, daum_fin)

        # 5. Cache investor trends (daily, last 10 days)
        await cache_investor_trends(stock_code, daum_supply, days=10)

        # 6. Cache OHLCV history (only if missing)
        await cache_ohlcv_to_db(stock_code, daum_price, days=365)
        
        # 7. Cache Financial Statements (Quarterly/Yearly)
        await cache_financial_statements(stock_code, daum_fin, naver_fin)
        
        # 8. Cache Analyst Reports (Daum + Naver Fallback)
        await cache_daum_reports(stock_code, daum_reports)
        await cache_analyst_target_prices(stock_code, naver_news) # Keep Naver as secondary fallback

        print(f"\n✅ All data cached successfully for {stock_code}")
        
        # 9. Collect Peer Data (Specific Peers)
        await collect_peer_data(daum_price, daum_fin, naver_fin)

    except Exception as e:
        print(f"\n❌ Error caching data for {stock_code}: {e}")
        import traceback
        traceback.print_exc()


import argparse

async def main():
    """Entry point - collect and cache data for a specific stock"""
    parser = argparse.ArgumentParser(description='Collect and cache stock data.')
    parser.add_argument('--code', type=str, default='015760', help='Target stock code (default: 015760 KEPCO)')
    args = parser.parse_args()
    
    target_stock_code = args.code

    print(f"🚀 Starting data collection and caching for {target_stock_code}...")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    await db.connect()

    try:
        await collect_and_cache_stock(target_stock_code)

        print(f"\n{'='*60}")
        print(f"✨ All done!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
