"""
Quick Production Test: 3 stocks × 5 key scrapers
Fast validation in ~1 minute
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.core.orchestrator import Orchestrator


async def quick_test():
    """Quick test with minimal scope"""

    print("=" * 70)
    print("⚡ Quick Production Test")
    print("=" * 70)

    # Initialize
    orchestrator = Orchestrator(max_concurrent=3)
    await orchestrator.initialize()

    # 3 sample stocks
    test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER

    # 5 key scrapers to test
    key_sites = [
        'FnGuide', 'WISEfn', 'Naver Stock News',
        'Korea Economy', 'Mirae Asset'
    ]

    print(f"📊 Testing {len(test_stocks)} stocks:")
    for ticker in test_stocks:
        print(f"   {ticker}")
    print()

    # Get tier 3 fetchers
    tier3_sites = [s for s in orchestrator.sites if s.get('tier') == 3]
    tier3_fetchers = {
        sid: f for sid, f in orchestrator.fetchers.items()
        if any(s['id'] == sid and s['tier'] == 3 for s in orchestrator.sites)
    }

    # Filter to key sites
    test_fetchers = {}
    for site_id, fetcher in tier3_fetchers.items():
        site_info = next(s for s in tier3_sites if s['id'] == site_id)
        site_name = site_info['site_name_en']

        if any(key in site_name for key in key_sites):
            test_fetchers[site_id] = (fetcher, site_name)

    print(f"🎯 Testing {len(test_fetchers)} scrapers:")
    for site_id, (_, site_name) in test_fetchers.items():
        print(f"   {site_name}")
    print()

    total_ops = len(test_fetchers) * len(test_stocks)
    print(f"📈 Total operations: {total_ops}")
    print("-" * 70)

    # Execute
    results = []
    success = 0
    failed = 0

    for site_id, (fetcher, site_name) in test_fetchers.items():
        print(f"Testing {site_name:30s} ", end='')

        site_success = 0
        for ticker in test_stocks:
            try:
                result = await orchestrator._execute_with_limits(site_id, fetcher, ticker)
                if result:
                    site_success += 1
                    success += 1
            except Exception as e:
                failed += 1

        status = "✅" if site_success >= 2 else "⚠️" if site_success == 1 else "❌"
        print(f"{status} {site_success}/{len(test_stocks)}")

        results.append({
            'site': site_name,
            'success': site_success,
            'total': len(test_stocks)
        })

    # Summary
    print("-" * 70)
    print(f"✅ Success: {success}/{total_ops} ({success/total_ops*100:.1f}%)")
    print(f"❌ Failed:  {failed}/{total_ops} ({failed/total_ops*100:.1f}%)")
    print("=" * 70)

    if success / total_ops >= 0.5:
        print("✅ PASS: Scrapers are working!")
        return True
    else:
        print("⚠️  PARTIAL: Some scrapers need debugging")
        return False


if __name__ == '__main__':
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)
