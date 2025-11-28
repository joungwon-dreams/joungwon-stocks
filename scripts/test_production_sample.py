"""
Option 3: Production Sample Test (10 stocks)
Quick validation before full 101 stock deployment
"""
import asyncio
import sys
import time
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.core.orchestrator import Orchestrator


async def test_production_sample():
    """
    Production sample test with 10 stocks:
    - Validate all 28 scrapers work
    - Measure performance
    - Identify issues before full deployment
    """

    print("=" * 80)
    print("🧪 Option 3: Production Sample Test (10 Stocks)")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize orchestrator
    orchestrator = Orchestrator(max_concurrent=5)
    await orchestrator.initialize()

    # Get 10 sample stocks
    query = """
        SELECT stock_code, stock_name
        FROM stocks
        WHERE is_delisted = FALSE
        ORDER BY stock_code
        LIMIT 10
    """
    stocks = await db.fetch(query)
    stock_codes = [s['stock_code'] for s in stocks]

    print(f"📊 Sample Stocks ({len(stock_codes)}):")
    for stock in stocks[:5]:
        print(f"   {stock['stock_code']}: {stock['stock_name']}")
    print(f"   ... and {len(stocks) - 5} more")
    print()

    print(f"🔧 Initialized {len(orchestrator.fetchers)} total fetchers")

    # Filter to Tier 3 only
    tier3_sites = [s for s in orchestrator.sites if s.get('tier') == 3]
    tier3_fetchers = {
        sid: f for sid, f in orchestrator.fetchers.items()
        if any(s['id'] == sid and s['tier'] == 3 for s in orchestrator.sites)
    }

    print(f"🎯 Testing {len(tier3_fetchers)} Tier 3 scrapers")
    print(f"📈 Total operations: {len(tier3_fetchers)} × {len(stock_codes)} = {len(tier3_fetchers) * len(stock_codes)}")
    print()

    # Start execution
    start_time = time.time()

    print("🏃 Starting execution...")
    print("-" * 80)

    # Execute with rate limiting
    results_by_site = defaultdict(list)
    success_count = 0
    failure_count = 0

    for site_id, fetcher in tier3_fetchers.items():
        site_info = next(s for s in tier3_sites if s['id'] == site_id)
        site_name = site_info['site_name_en']

        print(f"Testing {site_name}...", end=' ')

        site_success = 0
        for ticker in stock_codes:
            try:
                result = await orchestrator._execute_with_limits(site_id, fetcher, ticker)

                if result is not None:
                    success_count += 1
                    site_success += 1
                    results_by_site[site_name].append({'ticker': ticker, 'status': 'success'})
                else:
                    failure_count += 1
                    results_by_site[site_name].append({'ticker': ticker, 'status': 'failed'})
            except Exception as e:
                failure_count += 1
                results_by_site[site_name].append({'ticker': ticker, 'status': 'error', 'error': str(e)})

        print(f"✅ {site_success}/{len(stock_codes)}")

    elapsed = time.time() - start_time
    total_ops = len(tier3_fetchers) * len(stock_codes)

    # Results summary
    print()
    print("=" * 80)
    print("📊 Execution Summary")
    print("=" * 80)
    print(f"⏱️  Total Time: {elapsed:.2f} seconds")
    print(f"📈 Total Operations: {total_ops}")
    print(f"✅ Successful: {success_count} ({success_count/total_ops*100:.1f}%)")
    print(f"❌ Failed: {failure_count} ({failure_count/total_ops*100:.1f}%)")
    print(f"⚡ Avg Speed: {total_ops/elapsed:.2f} ops/sec")
    print()

    # Per-site breakdown
    print("=" * 80)
    print("📋 Per-Site Success Rates")
    print("=" * 80)

    site_stats = []
    for site_name, site_results in sorted(results_by_site.items()):
        total = len(site_results)
        success = sum(1 for r in site_results if r['status'] == 'success')
        success_rate = success / total * 100 if total > 0 else 0

        site_stats.append({
            'name': site_name,
            'total': total,
            'success': success,
            'rate': success_rate
        })

    # Sort by success rate
    site_stats.sort(key=lambda x: x['rate'], reverse=True)

    high_performers = []
    medium_performers = []
    low_performers = []

    for stat in site_stats:
        if stat['rate'] >= 80:
            high_performers.append(stat)
        elif stat['rate'] >= 50:
            medium_performers.append(stat)
        else:
            low_performers.append(stat)

    if high_performers:
        print(f"\n✅ High Performers (≥80%): {len(high_performers)}")
        for stat in high_performers:
            print(f"   {stat['name']:30s} | {stat['success']}/{stat['total']} ({stat['rate']:.1f}%)")

    if medium_performers:
        print(f"\n⚠️  Medium Performers (50-79%): {len(medium_performers)}")
        for stat in medium_performers:
            print(f"   {stat['name']:30s} | {stat['success']}/{stat['total']} ({stat['rate']:.1f}%)")

    if low_performers:
        print(f"\n❌ Low Performers (<50%): {len(low_performers)}")
        for stat in low_performers:
            print(f"   {stat['name']:30s} | {stat['success']}/{stat['total']} ({stat['rate']:.1f}%)")

    print()
    print("=" * 80)
    print("🎯 Sample Test Complete")
    print("=" * 80)

    # Pass/Fail criteria
    overall_success_rate = success_count / total_ops * 100

    if overall_success_rate >= 70:
        print(f"✅ PASS: Success rate {overall_success_rate:.1f}% >= 70%")
        print("   → Ready for full 101 stock deployment")
        return True
    elif overall_success_rate >= 50:
        print(f"⚠️  PARTIAL: Success rate {overall_success_rate:.1f}% (50-70%)")
        print("   → May proceed with caution, expect similar results")
        return True
    else:
        print(f"❌ FAIL: Success rate {overall_success_rate:.1f}% < 50%")
        print("   → Requires debugging before full deployment")
        return False


if __name__ == '__main__':
    result = asyncio.run(test_production_sample())
    sys.exit(0 if result else 1)
