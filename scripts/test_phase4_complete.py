#!/usr/bin/env python3
"""
Test script for Phase 4 Complete Fusion Module
Tests ALL analyzers: Disclosure, Supply, Fundamental, News, Consensus + FusionEngine
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aegis.fusion.disclosure import analyze_disclosure
from src.aegis.fusion.supply import analyze_supply_demand
from src.aegis.fusion.fundamental import analyze_fundamental
from src.aegis.fusion.news_sentiment import analyze_news_sentiment, NewsSentiment
from src.aegis.fusion.consensus import analyze_consensus_momentum, ConsensusTrend
from src.aegis.fusion.engine import get_aegis_signal, AegisSignal


async def test_news_sentiment():
    """Test NewsSentimentAnalyzer"""
    print("\n" + "=" * 60)
    print("1. NewsSentimentAnalyzer Test (Gemini AI)")
    print("=" * 60)

    ticker = "005930"  # 삼성전자
    print(f"\nAnalyzing news sentiment for {ticker}...")

    result = await analyze_news_sentiment(ticker, days=3, use_ai=False)  # AI 비활성화 (빠른 테스트)

    print(f"  Score: {result.score:+.2f}")
    print(f"  Sentiment: {result.sentiment.value}")
    print(f"  News Count: {result.news_count}")
    print(f"  Positive: {result.positive_count}, Negative: {result.negative_count}")

    if result.key_headlines:
        print("\n  Key Headlines:")
        for h in result.key_headlines[:3]:
            print(f"    - [{h['source']}] {h['title'][:40]}...")
            print(f"      Keywords: {h['keywords']}, Score: {h['score']}")

    if result.ai_summary:
        print(f"\n  AI Summary: {result.ai_summary}")

    return result


async def test_consensus_momentum():
    """Test ConsensusMomentumAnalyzer"""
    print("\n" + "=" * 60)
    print("2. ConsensusMomentumAnalyzer Test")
    print("=" * 60)

    ticker = "005930"
    print(f"\nAnalyzing consensus momentum for {ticker}...")

    result = await analyze_consensus_momentum(ticker)

    print(f"  Score: {result.score:+.2f}")
    print(f"  Trend: {result.trend.value}")
    print(f"  Current Price: {result.current_price:,}원")
    print(f"  Average Target: {result.average_target:,}원")
    print(f"  Upside Potential: {result.upside_potential:+.1f}%")
    print(f"  Analyst Count: {result.analyst_count}")
    print(f"  Buy/Hold/Sell: {result.buy_count}/{result.hold_count}/{result.sell_count}")
    print(f"  3M Target Change: {result.target_change_3m:+.1f}%")

    if result.recent_changes:
        print("\n  Recent Changes:")
        for c in result.recent_changes[:3]:
            print(f"    - [{c['broker']}] Target: {c['target_price']:,}원 ({c['opinion']})")

    return result


async def test_full_fusion_engine():
    """Test Complete InformationFusionEngine with all 7 analyzers"""
    print("\n" + "=" * 60)
    print("3. Complete FusionEngine Test (7 Analyzers)")
    print("=" * 60)

    tickers = ["005930", "000660", "035720"]
    ticker_names = {"005930": "삼성전자", "000660": "SK하이닉스", "035720": "카카오"}

    for ticker in tickers:
        print(f"\n--- {ticker_names.get(ticker, ticker)} ({ticker}) ---")

        # 기술적 분석 점수 시뮬레이션
        technical_scores = {"005930": 0.5, "000660": 0.3, "035720": -0.2}
        tech_score = technical_scores.get(ticker, 0.0)

        result = await get_aegis_signal(ticker, technical_score=tech_score)

        print(f"\n  🎯 Final Score: {result.final_score:+.3f}")
        print(f"  📊 Signal: {result.signal.value.upper()}")
        print(f"  🚫 Trading Halt: {result.trading_halt}")
        print(f"  📈 Regime: {result.regime} ({result.regime_confidence:.0%})")
        print(f"  ✅ Fundamental Pass: {result.fundamental_pass}")

        print(f"\n  Component Scores (7 factors):")
        print(f"    Technical:      {result.technical_score:+.2f} (w={result.weights_used.get('technical', 0):.0%})")
        print(f"    Disclosure:     {result.disclosure_score:+.2f} (w={result.weights_used.get('disclosure', 0):.0%})")
        print(f"    Supply:         {result.supply_score:+.2f} (w={result.weights_used.get('supply', 0):.0%})")
        print(f"    Fundamental:    {result.fundamental_score:+.2f} (w={result.weights_used.get('fundamental', 0):.0%})")
        print(f"    Market:         {result.market_context_score:+.2f} (w={result.weights_used.get('market_context', 0):.0%})")
        print(f"    News Sentiment: {result.news_sentiment_score:+.2f} (w={result.weights_used.get('news_sentiment', 0):.0%})")
        print(f"    Consensus:      {result.consensus_score:+.2f} (w={result.weights_used.get('consensus', 0):.0%})")

        print(f"\n  Details:")
        print(f"    Supply Pattern: {result.details.get('supply_pattern', 'N/A')}")
        print(f"    Fund Grade: {result.details.get('fundamental_grade', 'N/A')}")
        print(f"    News Sentiment: {result.details.get('news_sentiment', 'N/A')}")
        print(f"    Consensus Trend: {result.details.get('consensus_trend', 'N/A')}")
        print(f"    Upside Potential: {result.details.get('upside_potential', 0):+.1f}%")

        if result.details.get('ai_summary'):
            print(f"    AI Summary: {result.details['ai_summary'][:80]}...")

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


async def test_individual_analyzers():
    """Test individual analyzers (quick check)"""
    print("\n" + "=" * 60)
    print("4. Quick Individual Analyzer Check")
    print("=" * 60)

    ticker = "005930"

    # 병렬 실행
    disclosure, supply, fundamental = await asyncio.gather(
        analyze_disclosure(ticker, days=14),
        analyze_supply_demand(ticker, days=5),
        analyze_fundamental(ticker)
    )

    print(f"\n  Disclosure: {disclosure.score:+.2f} (halt={disclosure.trading_halt})")
    print(f"  Supply: {supply.score:+.2f} ({supply.pattern.value})")
    print(f"  Fundamental: {fundamental.score:+.2f} ({fundamental.grade.value})")


async def main():
    print("=" * 60)
    print("Phase 4 Complete Fusion Module Test")
    print("=" * 60)
    print("\nThis test includes ALL 7 analyzers:")
    print("  1. DisclosureAnalyzer (DART)")
    print("  2. SupplyDemandAnalyzer (투자자 수급)")
    print("  3. FundamentalIntegrator (재무)")
    print("  4. NewsSentimentAnalyzer (뉴스 + Gemini AI)")
    print("  5. ConsensusMomentumAnalyzer (목표가 추세)")
    print("  6. MarketScanner (시장 컨텍스트)")
    print("  7. Technical (외부 입력)")

    try:
        await test_news_sentiment()
        await test_consensus_momentum()
        await test_individual_analyzers()
        await test_full_fusion_engine()

        print("\n" + "=" * 60)
        print("✅ All Phase 4 Complete Tests Passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
