"""
Test script for all Tier 3 web scrapers.

Tests:
1. Structure validation
2. Data fetch with Samsung (005930)
3. Error handling

Usage:
    python scripts/test_tier3_scrapers.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetchers.tier3_web_scraping import (
    FnGuideScraper,
    WISEfnScraper,
    Comm38Scraper,
    MiraeAssetScraper,
    SamsungSecuritiesScraper
)


async def test_scraper(scraper_class, scraper_name: str) -> dict:
    """
    Test a single scraper.

    Args:
        scraper_class: Scraper class to test
        scraper_name: Human-readable scraper name

    Returns:
        Test results dict
    """
    print(f"\n{'='*60}")
    print(f"Testing {scraper_name}")
    print(f"{'='*60}\n")

    results = {
        'name': scraper_name,
        'structure_validation': False,
        'data_fetch': False,
        'error_handling': False,
    }

    # Initialize scraper
    config = {
        'url': 'https://example.com',
        'site_name_ko': scraper_name,
        'site_name_en': scraper_class.__name__,
    }

    scraper = scraper_class(site_id=999, config=config)

    try:
        # Test 1: Structure Validation
        print(f"Test 1: Structure Validation")
        print(f"Testing if {scraper_name} site structure is valid...")

        try:
            is_valid = await scraper.validate_structure()
            if is_valid:
                print(f"✅ Structure validation: PASS")
                results['structure_validation'] = True
            else:
                print(f"⚠️  Structure validation: FAIL (selectors may need update)")
        except Exception as e:
            print(f"❌ Structure validation: ERROR - {e}")

        # Test 2: Data Fetch
        print(f"\nTest 2: Data Fetch (Samsung Electronics: 005930)")

        try:
            data = await scraper.execute("005930")

            if data and 'ticker' in data:
                print(f"✅ Data fetch: PASS")
                print(f"   - Ticker: {data.get('ticker')}")
                print(f"   - Source: {data.get('source')}")
                print(f"   - Company: {data.get('company_name', 'N/A')}")
                print(f"   - Data Quality: {data.get('data_quality', 'N/A')}/5")

                # Show some key fields based on scraper type
                if 'valuation' in data:
                    print(f"   - Valuation: {list(data['valuation'].keys())}")
                if 'governance' in data:
                    print(f"   - Governance: {list(data['governance'].keys())}")
                if 'signals' in data:
                    print(f"   - Signals: {list(data['signals'].keys())}")

                results['data_fetch'] = True
            else:
                print(f"⚠️  Data fetch: FAIL (empty data returned)")
                print(f"   Data: {data}")

        except Exception as e:
            print(f"❌ Data fetch: ERROR - {e}")

        # Test 3: Error Handling
        print(f"\nTest 3: Error Handling (invalid ticker)")

        try:
            data = await scraper.execute("INVALID_TICKER_999")

            # Should return empty dict or handle gracefully
            if isinstance(data, dict):
                print(f"✅ Error handling: PASS (graceful degradation)")
                results['error_handling'] = True
            else:
                print(f"⚠️  Error handling: UNEXPECTED - {type(data)}")

        except Exception as e:
            print(f"⚠️  Error handling: EXCEPTION - {e}")
            print(f"   (Should handle errors gracefully without raising)")

    finally:
        # Cleanup
        await scraper.cleanup()

    return results


async def main():
    """
    Run all scraper tests.
    """
    print("\n" + "="*60)
    print("Tier 3 Web Scraper Test Suite")
    print("="*60)
    print("Testing 5 scrapers: Top 5 Priority Sites")
    print("="*60)

    scrapers = [
        (FnGuideScraper, "FnGuide (에프앤가이드)"),
        (WISEfnScraper, "WISEfn"),
        (Comm38Scraper, "38커뮤니케이션 (38 Communication)"),
        (MiraeAssetScraper, "미래에셋증권 (Mirae Asset)"),
        (SamsungSecuritiesScraper, "삼성증권 (Samsung Securities)"),
    ]

    all_results = []

    for scraper_class, scraper_name in scrapers:
        results = await test_scraper(scraper_class, scraper_name)
        all_results.append(results)

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}\n")

    for result in all_results:
        name = result['name']
        total_tests = 3
        passed_tests = sum([
            result['structure_validation'],
            result['data_fetch'],
            result['error_handling'],
        ])

        status = "✅ PASS" if passed_tests == total_tests else "⚠️  PARTIAL"
        if passed_tests == 0:
            status = "❌ FAIL"

        print(f"{name}:")
        print(f"  Status: {status}")
        print(f"  Tests passed: {passed_tests}/{total_tests}")
        print(f"  - Structure validation: {'✅' if result['structure_validation'] else '❌'}")
        print(f"  - Data fetch: {'✅' if result['data_fetch'] else '❌'}")
        print(f"  - Error handling: {'✅' if result['error_handling'] else '❌'}")
        print()

    # Overall summary
    total_scrapers = len(all_results)
    total_tests_run = total_scrapers * 3
    total_tests_passed = sum([
        sum([
            r['structure_validation'],
            r['data_fetch'],
            r['error_handling'],
        ])
        for r in all_results
    ])

    print(f"{'='*60}")
    print(f"Overall: {total_tests_passed}/{total_tests_run} tests passed")
    print(f"Success rate: {total_tests_passed/total_tests_run*100:.1f}%")
    print(f"{'='*60}\n")

    # Exit code
    if total_tests_passed == total_tests_run:
        print("✅ All tests passed!")
        return 0
    elif total_tests_passed > 0:
        print("⚠️  Some tests failed. Review output above.")
        return 1
    else:
        print("❌ All tests failed. Check scraper implementations.")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
