"""
Test Tier 3 Scrapers Integration with Orchestrator
Verifies that all 5 scrapers are properly registered and can be created
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import Orchestrator


async def test_tier3_integration():
    """Test Tier 3 scrapers integration with Orchestrator"""

    print("\n" + "="*60)
    print("Tier 3 Integration Test")
    print("="*60 + "\n")

    # Initialize orchestrator
    print("Step 1: Initializing Orchestrator...")
    orchestrator = Orchestrator(max_concurrent=3)
    await orchestrator.initialize()

    # Check loaded sites
    tier3_sites = [s for s in orchestrator.sites if s['tier'] == 3]
    print(f"✅ Loaded {len(tier3_sites)} Tier 3 sites from database\n")

    # Check created fetchers
    tier3_fetchers = {}
    for site in tier3_sites:
        site_id = site['id']
        if site_id in orchestrator.fetchers:
            tier3_fetchers[site_id] = orchestrator.fetchers[site_id]

    print(f"Step 2: Checking Tier 3 Fetchers...")
    print(f"✅ Created {len(tier3_fetchers)} Tier 3 fetchers\n")

    # Display fetcher details
    print("Tier 3 Fetchers:")
    print("-" * 60)

    priority_scrapers = {
        'FnGuide': False,
        'WISEfn': False,
        '38 Communication': False,
        'Mirae Asset': False,
        'Samsung Securities': False,
    }

    for site_id, fetcher in tier3_fetchers.items():
        site = next(s for s in tier3_sites if s['id'] == site_id)
        site_name_ko = site['site_name_ko']
        site_name_en = site['site_name_en']
        fetcher_type = type(fetcher).__name__

        print(f"  {site_name_ko} ({site_name_en})")
        print(f"    - Site ID: {site_id}")
        print(f"    - Fetcher: {fetcher_type}")
        print(f"    - Quality: {site.get('data_quality_score', 0)}")
        print()

        # Check if it's one of our priority scrapers
        for scraper_key in priority_scrapers.keys():
            if scraper_key in site_name_en or scraper_key in site_name_ko:
                priority_scrapers[scraper_key] = True

    # Verify priority scrapers
    print("-" * 60)
    print("\nStep 3: Verifying Priority Scrapers:")
    print("-" * 60)

    all_found = True
    for scraper_name, found in priority_scrapers.items():
        status = "✅ Found" if found else "❌ Missing"
        print(f"  {status}: {scraper_name}")
        if not found:
            all_found = False

    print("\n" + "="*60)
    if all_found:
        print("✅ SUCCESS: All 5 priority scrapers are registered!")
    else:
        print("⚠️  WARNING: Some priority scrapers are missing")
    print("="*60 + "\n")

    return all_found


async def main():
    """Main test function"""
    try:
        success = await test_tier3_integration()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
