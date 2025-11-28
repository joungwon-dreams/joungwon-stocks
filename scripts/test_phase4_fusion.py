#!/usr/bin/env python3
"""
Test script for Phase 4 Fusion Module
Tests: DisclosureAnalyzer, SupplyDemandAnalyzer, FundamentalIntegrator, InformationFusionEngine
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aegis.fusion.disclosure import analyze_disclosure
from src.aegis.fusion.supply import analyze_supply_demand
from src.aegis.fusion.fundamental import analyze_fundamental
from src.aegis.fusion.engine import get_aegis_signal, AegisSignal


async def test_disclosure_analyzer():
    """Test DisclosureAnalyzer"""
    print("\n" + "=" * 60)
    print("1. DisclosureAnalyzer Test")
    print("=" * 60)

    # 테스트 종목: 삼성전자
    ticker = "005930"
    print(f"\nAnalyzing disclosures for {ticker}...")

    result = await analyze_disclosure(ticker, days=30)

    print(f"  Score: {result.score:.2f}")
    print(f"  Trading Halt: {result.trading_halt}")
    if result.halt_reason:
        print(f"  Halt Reason: {result.halt_reason}")
    print(f"  Disclosures Found: {len(result.disclosures)}")
    print(f"  Key Events: {len(result.key_events)}")

    if result.key_events:
        print("\n  Key Events:")
        for event in result.key_events[:5]:
            print(f"    - [{event['impact']}] {event['title'][:50]}...")
            print(f"      Keyword: {event['keyword']}, Score: {event['score']}")

    return result


async def test_supply_demand_analyzer():
    """Test SupplyDemandAnalyzer"""
    print("\n" + "=" * 60)
    print("2. SupplyDemandAnalyzer Test")
    print("=" * 60)

    ticker = "005930"
    print(f"\nAnalyzing supply/demand for {ticker}...")

    result = await analyze_supply_demand(ticker, days=10)

    print(f"  Score: {result.score:.2f}")
    print(f"  Pattern: {result.pattern.value}")
    print(f"  Foreign Net: {result.foreign_net:,}")
    print(f"  Inst Net: {result.inst_net:,}")
    print(f"  Foreign Consecutive Days: {result.foreign_consecutive}")
    print(f"  Inst Consecutive Days: {result.inst_consecutive}")

    if result.details:
        print("\n  Details:")
        for key, value in result.details.items():
            print(f"    - {key}: {value}")

    return result


async def test_fundamental_integrator():
    """Test FundamentalIntegrator"""
    print("\n" + "=" * 60)
    print("3. FundamentalIntegrator Test")
    print("=" * 60)

    ticker = "005930"
    print(f"\nAnalyzing fundamentals for {ticker}...")

    result = await analyze_fundamental(ticker)

    print(f"  Score: {result.score:.2f}")
    print(f"  Grade: {result.grade.value}")
    print(f"  Pass Filter: {result.pass_filter}")
    if result.filter_reason:
        print(f"  Filter Reason: {result.filter_reason}")

    if result.metrics:
        print("\n  Metrics:")
        for key, value in result.metrics.items():
            if value is not None:
                print(f"    - {key}: {value}")

    return result


async def test_combined_analysis():
    """Test combined analysis for multiple stocks"""
    print("\n" + "=" * 60)
    print("4. Combined Analysis Test (Multiple Stocks)")
    print("=" * 60)

    tickers = ["005930", "000660", "035720"]  # 삼성전자, SK하이닉스, 카카오
    ticker_names = {"005930": "삼성전자", "000660": "SK하이닉스", "035720": "카카오"}

    for ticker in tickers:
        print(f"\n--- {ticker_names.get(ticker, ticker)} ({ticker}) ---")

        # 병렬 분석
        disclosure, supply, fundamental = await asyncio.gather(
            analyze_disclosure(ticker, days=14),
            analyze_supply_demand(ticker, days=5),
            analyze_fundamental(ticker)
        )

        # 종합 점수 (간단 가중 합계)
        total_score = (
            disclosure.score * 0.3 +
            supply.score * 0.4 +
            fundamental.score * 0.3
        )

        print(f"  Disclosure Score: {disclosure.score:+.2f} (halt={disclosure.trading_halt})")
        print(f"  Supply Score: {supply.score:+.2f} ({supply.pattern.value})")
        print(f"  Fundamental Score: {fundamental.score:+.2f} ({fundamental.grade.value})")
        print(f"  >>> Combined Score: {total_score:+.2f}")

        if disclosure.trading_halt:
            print("  ⚠️ TRADING HALT RECOMMENDED!")
        elif not fundamental.pass_filter:
            print("  ⚠️ FUNDAMENTAL FILTER FAILED!")
        elif total_score >= 1.0:
            print("  ✅ STRONG BUY Signal")
        elif total_score >= 0.5:
            print("  ✅ BUY Signal")
        elif total_score <= -0.5:
            print("  ❌ SELL Signal")
        else:
            print("  ➖ HOLD")


async def test_fusion_engine():
    """Test InformationFusionEngine"""
    print("\n" + "=" * 60)
    print("5. InformationFusionEngine Test (Full AEGIS Signal)")
    print("=" * 60)

    tickers = ["005930", "000660", "035720"]
    ticker_names = {"005930": "삼성전자", "000660": "SK하이닉스", "035720": "카카오"}

    for ticker in tickers:
        print(f"\n--- {ticker_names.get(ticker, ticker)} ({ticker}) ---")

        # 기술적 분석 점수 시뮬레이션 (실제로는 외부에서 전달)
        technical_scores = {"005930": 0.5, "000660": 0.3, "035720": -0.2}
        tech_score = technical_scores.get(ticker, 0.0)

        result = await get_aegis_signal(ticker, technical_score=tech_score)

        print(f"  Final Score: {result.final_score:+.3f}")
        print(f"  Signal: {result.signal.value.upper()}")
        print(f"  Trading Halt: {result.trading_halt}")
        print(f"  Regime: {result.regime} ({result.regime_confidence:.0%})")
        print(f"  Fundamental Pass: {result.fundamental_pass}")

        print(f"\n  Component Scores:")
        print(f"    Technical: {result.technical_score:+.2f} (weight: {result.weights_used.get('technical', 0):.0%})")
        print(f"    Disclosure: {result.disclosure_score:+.2f} (weight: {result.weights_used.get('disclosure', 0):.0%})")
        print(f"    Supply: {result.supply_score:+.2f} (weight: {result.weights_used.get('supply', 0):.0%})")
        print(f"    Fundamental: {result.fundamental_score:+.2f} (weight: {result.weights_used.get('fundamental', 0):.0%})")
        print(f"    Market: {result.market_context_score:+.2f} (weight: {result.weights_used.get('market_context', 0):.0%})")

        if result.details:
            print(f"\n  Details:")
            print(f"    Supply Pattern: {result.details.get('supply_pattern', 'N/A')}")
            print(f"    Fund Grade: {result.details.get('fundamental_grade', 'N/A')}")
            print(f"    Market Sentiment: {result.details.get('market_sentiment', 'N/A')}")

        # 신호 해석
        print(f"\n  >>> AEGIS Recommendation: ", end="")
        if result.signal == AegisSignal.STRONG_BUY:
            print("✅✅ STRONG BUY")
        elif result.signal == AegisSignal.BUY:
            print("✅ BUY")
        elif result.signal == AegisSignal.HOLD:
            print("➖ HOLD")
        elif result.signal == AegisSignal.SELL:
            print("❌ SELL")
        elif result.signal == AegisSignal.STRONG_SELL:
            print("❌❌ STRONG SELL")
        elif result.signal == AegisSignal.TRADING_HALT:
            print(f"🚫 TRADING HALT: {result.halt_reason}")


async def main():
    print("=" * 60)
    print("Phase 4 Fusion Module Test")
    print("=" * 60)

    try:
        await test_disclosure_analyzer()
        await test_supply_demand_analyzer()
        await test_fundamental_integrator()
        await test_combined_analysis()
        await test_fusion_engine()

        print("\n" + "=" * 60)
        print("All Phase 4 Tests Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
