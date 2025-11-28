"""
Test Tier 3 Data Collection
Runs a simple data collection test with 1 ticker (Samsung 005930)
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import Orchestrator


async def test_tier3_collection():
    """Test Tier 3 data collection with Samsung Electronics"""

    print("\n" + "="*60)
    print("Tier 3 Data Collection Test")
    print("="*60 + "\n")

    # Test ticker (Samsung Electronics)
    test_ticker = "005930"

    # Initialize orchestrator
    print("Step 1: Initializing Orchestrator...")
    orchestrator = Orchestrator(max_concurrent=2)
    await orchestrator.initialize()

    # Get Tier 3 fetchers
    tier3_sites = [s for s in orchestrator.sites if s['tier'] == 3]
    tier3_fetchers = {
        site_id: fetcher
        for site_id, fetcher in orchestrator.fetchers.items()
        if any(s['id'] == site_id and s['tier'] == 3 for s in orchestrator.sites)
    }

    print(f"✅ Loaded {len(tier3_fetchers)} Tier 3 fetchers\n")

    # Test each fetcher with Samsung Electronics
    print(f"Step 2: Testing data collection for {test_ticker} (Samsung)")
    print("-" * 60)

    results = {}
    for site_id, fetcher in tier3_fetchers.items():
        site = next(s for s in tier3_sites if s['id'] == site_id)
        site_name = site['site_name_ko']
        fetcher_type = type(fetcher).__name__

        print(f"\n  Testing {site_name} ({fetcher_type})...")

        try:
            # Execute fetcher
            data = await fetcher.execute(test_ticker)

            if data and isinstance(data, dict) and 'ticker' in data:
                print(f"    ✅ SUCCESS - Data fetched")
                print(f"       - Ticker: {data.get('ticker')}")
                print(f"       - Source: {data.get('source')}")
                print(f"       - Data keys: {list(data.keys())[:5]}...")  # First 5 keys
                results[site_name] = 'success'
            else:
                print(f"    ⚠️  NO DATA - Empty response")
                results[site_name] = 'no_data'

        except Exception as e:
            print(f"    ❌ ERROR - {str(e)[:50]}...")
            results[site_name] = 'error'

    # Summary
    print("\n" + "-" * 60)
    print("\nStep 3: Summary")
    print("-" * 60)

    success_count = sum(1 for r in results.values() if r == 'success')
    no_data_count = sum(1 for r in results.values() if r == 'no_data')
    error_count = sum(1 for r in results.values() if r == 'error')
    total_count = len(results)

    print(f"\nTotal Tier 3 Fetchers Tested: {total_count}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⚠️  No Data: {no_data_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"\nSuccess Rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

    print("\n" + "="*60)
    if success_count > 0:
        print(f"✅ Test completed - {success_count} fetchers working!")
    else:
        print("⚠️  No successful fetches - check scraper implementations")
    print("="*60 + "\n")

    return success_count > 0


async def main():
    """Main test function"""
    try:
        success = await test_tier3_collection()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
