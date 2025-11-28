"""
Test Batch 3: Verify all 28 Tier 3 scrapers are properly integrated
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.core.orchestrator import Orchestrator


async def test_batch3_integration():
    """Test that all 28 implemented scrapers can be instantiated"""

    # Expected scrapers by batch
    expected_scrapers = {
        'Initial (5)': [
            'FnGuide', 'WISEfn', '38', 'Mirae Asset', 'Samsung Securities'
        ],
        'Batch 1 Securities (6)': [
            'Kiwoom', 'KB', 'Shinhan', 'Meritz', 'Hana', 'Daishin'
        ],
        'Batch 2 Data/Analysis (6)': [
            'Korea Investment', 'NH Investment', 'QuantiWise',
            'Wise Report', 'eBest', 'Eugene'
        ],
        'Batch 3 News/Media (11)': [
            'Korea Economy', 'Maeil Business', 'Seoul Economy',
            'Financial News', 'Money Today', 'Edaily',
            'Yonhap Infomax', 'Newspim', 'Daum Stock News',
            'Naver Stock News', 'Stock Plus'
        ]
    }

    print("=" * 80)
    print("🧪 Batch 3 Integration Test: All 28 Tier 3 Scrapers")
    print("=" * 80)

    orchestrator = Orchestrator(max_concurrent=5)
    await orchestrator.initialize()

    print(f"\n📊 Total Sites Loaded: {len(orchestrator.sites)}")
    print(f"🔧 Total Fetchers Created: {len(orchestrator.fetchers)}")

    # Count Tier 3 fetchers
    tier3_sites = [s for s in orchestrator.sites if s.get('tier') == 3]
    tier3_fetchers = {
        sid: f for sid, f in orchestrator.fetchers.items()
        if any(s['id'] == sid and s['tier'] == 3 for s in orchestrator.sites)
    }

    print(f"\n🎯 Tier 3 Sites in DB: {len(tier3_sites)}")
    print(f"✅ Tier 3 Fetchers Implemented: {len(tier3_fetchers)}")

    # Verify each batch
    print("\n" + "=" * 80)
    print("📦 Batch-by-Batch Verification")
    print("=" * 80)

    total_found = 0
    total_expected = 0

    for batch_name, scraper_keywords in expected_scrapers.items():
        print(f"\n🔍 {batch_name}")
        batch_found = 0

        for keyword in scraper_keywords:
            # Check if any site matches this keyword
            found = False
            for site in tier3_sites:
                site_name = site.get('site_name_en', '')
                if keyword.lower() in site_name.lower():
                    # Check if fetcher exists
                    if site['id'] in tier3_fetchers:
                        fetcher = tier3_fetchers[site['id']]
                        fetcher_class = fetcher.__class__.__name__
                        print(f"  ✅ {site_name:25s} → {fetcher_class}")
                        found = True
                        batch_found += 1
                        break

            if not found:
                print(f"  ❌ {keyword:25s} → NOT FOUND")

        total_found += batch_found
        total_expected += len(scraper_keywords)
        print(f"  📊 {batch_name} Status: {batch_found}/{len(scraper_keywords)} found")

    # Final summary
    print("\n" + "=" * 80)
    print("📈 Final Summary")
    print("=" * 80)
    print(f"Total Scrapers Implemented: {total_found}/{total_expected}")
    print(f"Success Rate: {total_found/total_expected*100:.1f}%")

    if total_found == total_expected:
        print("\n🎉 SUCCESS: All 28 scrapers properly integrated!")
        return True
    else:
        print(f"\n⚠️  INCOMPLETE: {total_expected - total_found} scrapers missing")
        return False


if __name__ == '__main__':
    result = asyncio.run(test_batch3_integration())
    sys.exit(0 if result else 1)
