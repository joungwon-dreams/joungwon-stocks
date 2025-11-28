"""
Option 3: Production Deployment Test
Test all 28 Tier 3 scrapers with 101 stocks
"""
import asyncio
import sys
import time
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.core.orchestrator import Orchestrator


async def test_production_deployment():
    """
    Production deployment test:
    1. Load all 101 active stocks
    2. Execute all 28 Tier 3 scrapers
    3. Measure performance
    4. Report results
    """

    print("=" * 80)
    print("🚀 Option 3: Production Deployment Test")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize orchestrator
    orchestrator = Orchestrator(max_concurrent=10)
    await orchestrator.initialize()

    # Get stocks from database
    query = """
        SELECT stock_code, stock_name
        FROM stocks
        WHERE is_delisted = FALSE
        ORDER BY stock_code
        LIMIT 101
    """
    stocks = await db.fetch(query)
    stock_codes = [s['stock_code'] for s in stocks]

    print(f"📊 Loaded {len(stock_codes)} stocks from database")
    print(f"🔧 Initialized {len(orchestrator.fetchers)} fetchers")

    # Filter to Tier 3 only
    tier3_sites = [s for s in orchestrator.sites if s.get('tier') == 3]
    tier3_fetchers = {
        sid: f for sid, f in orchestrator.fetchers.items()
        if any(s['id'] == sid and s['tier'] == 3 for s in orchestrator.sites)
    }

    print(f"🎯 Testing {len(tier3_fetchers)} Tier 3 scrapers")
    print(f"📈 Total operations: {len(tier3_fetchers)} × {len(stock_codes)} = {len(tier3_fetchers) * len(stock_codes)}")
    print()

    # Confirm before starting
    print("⚠️  This will execute ~3,000 scraping operations!")
    print("⏱️  Estimated time: 5-10 minutes (with rate limiting)")
    print()

    # Start execution
    start_time = time.time()

    print("🏃 Starting Tier 3 execution...")
    print("-" * 80)

    # Execute with rate limiting
    tasks = []
    results_by_site = defaultdict(list)

    for site_id, fetcher in tier3_fetchers.items():
        site_info = next(s for s in tier3_sites if s['id'] == site_id)

        for ticker in stock_codes:
            task = orchestrator._execute_with_limits(site_id, fetcher, ticker)
            tasks.append((site_id, site_info['site_name_en'], ticker, task))

    # Execute in batches to avoid overwhelming
    batch_size = 100
    total_tasks = len(tasks)
    completed = 0
    success_count = 0
    failure_count = 0

    for i in range(0, total_tasks, batch_size):
        batch = tasks[i:i+batch_size]
        batch_tasks = [t[3] for t in batch]

        results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        for (site_id, site_name, ticker, _), result in zip(batch, results):
            completed += 1

            if isinstance(result, Exception):
                failure_count += 1
                results_by_site[site_name].append({'ticker': ticker, 'status': 'error'})
            elif result is None:
                failure_count += 1
                results_by_site[site_name].append({'ticker': ticker, 'status': 'failed'})
            else:
                success_count += 1
                results_by_site[site_name].append({'ticker': ticker, 'status': 'success', 'data': result})

        # Progress update
        progress = completed / total_tasks * 100
        print(f"Progress: {completed}/{total_tasks} ({progress:.1f}%) | ✅ {success_count} | ❌ {failure_count}", end='\r')

    print()  # New line after progress

    elapsed = time.time() - start_time

    # Results summary
    print("-" * 80)
    print("📊 Execution Summary")
    print("=" * 80)
    print(f"⏱️  Total Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"📈 Total Operations: {total_tasks}")
    print(f"✅ Successful: {success_count} ({success_count/total_tasks*100:.1f}%)")
    print(f"❌ Failed: {failure_count} ({failure_count/total_tasks*100:.1f}%)")
    print(f"⚡ Avg Speed: {total_tasks/elapsed:.2f} ops/sec")
    print()

    # Per-site breakdown
    print("=" * 80)
    print("📋 Per-Site Results")
    print("=" * 80)

    site_stats = []
    for site_name, site_results in sorted(results_by_site.items()):
        total = len(site_results)
        success = sum(1 for r in site_results if r['status'] == 'success')
        failed = total - success
        success_rate = success / total * 100 if total > 0 else 0

        site_stats.append({
            'name': site_name,
            'total': total,
            'success': success,
            'failed': failed,
            'rate': success_rate
        })

    # Sort by success rate
    site_stats.sort(key=lambda x: x['rate'], reverse=True)

    for stat in site_stats:
        status_icon = "✅" if stat['rate'] >= 80 else "⚠️" if stat['rate'] >= 50 else "❌"
        print(f"{status_icon} {stat['name']:30s} | {stat['success']:3d}/{stat['total']:3d} ({stat['rate']:5.1f}%)")

    print()
    print("=" * 80)
    print("🎯 Production Deployment Test Complete")
    print("=" * 80)

    # Pass/Fail criteria
    overall_success_rate = success_count / total_tasks * 100

    if overall_success_rate >= 80:
        print("✅ PASS: Overall success rate >= 80%")
        return True
    elif overall_success_rate >= 60:
        print("⚠️  PARTIAL: Success rate between 60-80%, needs optimization")
        return True
    else:
        print("❌ FAIL: Success rate < 60%, requires debugging")
        return False


if __name__ == '__main__':
    result = asyncio.run(test_production_deployment())
    sys.exit(0 if result else 1)
