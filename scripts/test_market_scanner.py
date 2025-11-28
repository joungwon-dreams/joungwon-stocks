#!/usr/bin/env python3
"""
Test script for MarketScanner (Phase 3.9)
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetchers.tier1_official_libs.market_scanner import (
    MarketScanner,
    get_market_context,
    get_leading_sectors
)


async def test_market_scanner():
    """Test MarketScanner functionality."""
    print("=" * 60)
    print("Phase 3.9 MarketScanner Test")
    print("=" * 60)

    scanner = MarketScanner()

    # 1. Test sector heatmap
    print("\n1. Testing Sector Heatmap (KOSPI)...")
    heatmap = await scanner.get_sector_heatmap("KOSPI")

    if heatmap.get("sectors"):
        print(f"   Found {len(heatmap['sectors'])} sectors")
        print("\n   Top 5 Sectors:")
        for s in heatmap["sectors"][:5]:
            print(f"   - {s['name']}: {s['change_rate']:+.2f}%")

        print("\n   Bottom 5 Sectors:")
        for s in heatmap["sectors"][-5:]:
            print(f"   - {s['name']}: {s['change_rate']:+.2f}%")
    else:
        print(f"   Error: {heatmap.get('error', 'No data')}")

    # 2. Test market breadth
    print("\n2. Testing Market Breadth (ADR)...")
    breadth = await scanner.get_market_breadth("KOSPI")

    if "adr" in breadth:
        print(f"   Advancing: {breadth['advancing']}")
        print(f"   Declining: {breadth['declining']}")
        print(f"   Unchanged: {breadth['unchanged']}")
        print(f"   ADR: {breadth['adr']:.2f}")
        print(f"   Sentiment: {breadth['adr_interpretation']}")
        print(f"   Breadth %: {breadth['breadth_pct']:.1f}%")
    else:
        print(f"   Error: {breadth.get('error', 'No data')}")

    # 3. Test full market context
    print("\n3. Testing Full Market Context...")
    context = await get_market_context("KOSPI")

    if "summary" in context:
        summary = context["summary"]
        print(f"   Leading Sectors: {', '.join(summary['leading_sectors'])}")
        print(f"   Lagging Sectors: {', '.join(summary['lagging_sectors'])}")
        print(f"   Market Sentiment: {summary['market_sentiment']}")
        print(f"   ADR: {summary['adr']:.2f}")
    else:
        print("   Error getting context")

    # 4. Test convenience function
    print("\n4. Testing Convenience Function (Top 3 Sectors)...")
    top_sectors = await get_leading_sectors(3, "KOSPI")
    for s in top_sectors:
        print(f"   - {s['name']}: {s['change_rate']:+.2f}%")

    # 5. Test KOSDAQ
    print("\n5. Testing KOSDAQ Market...")
    kosdaq_context = await scanner.get_full_market_context("KOSDAQ")
    if "summary" in kosdaq_context:
        summary = kosdaq_context["summary"]
        print(f"   Leading: {', '.join(summary['leading_sectors'][:3])}")
        print(f"   Sentiment: {summary['market_sentiment']}")

    print("\n" + "=" * 60)
    print("MarketScanner Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_market_scanner())
