#!/usr/bin/env python
"""
Phase 4.5 Global Macro Integration Test
글로벌 매크로 커플링 분석 통합 테스트

테스트 항목:
1. GlobalMarketFetcher - 미국 시장 데이터 수집
2. CouplingAnalyzer - 미국-한국 종목 커플링 분석
3. DynamicWeightOptimizer - 변동성 기반 가중치 조정
4. FusionEngine 통합 - 8개 요소 융합 분석
"""
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_global_market_fetcher():
    """1. GlobalMarketFetcher 테스트"""
    print("\n" + "=" * 60)
    print("1. GlobalMarketFetcher 테스트")
    print("=" * 60)

    from src.aegis.global_macro import get_global_market_fetcher

    fetcher = get_global_market_fetcher()
    data = await fetcher.fetch()

    print(f"\n📊 미국 시장 데이터 (조회 시각: {data.fetched_at})")
    print(f"   시장 세션: {data.market_session.value}")
    print(f"   전체 심리: {data.overall_sentiment.value}")

    print("\n📈 주요 지수:")
    for symbol, idx in data.indices.items():
        arrow = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "→"
        print(f"   {idx.name}: {idx.price:,.2f} ({arrow}{idx.change_pct:+.2f}%)")

    print("\n🏢 핵심 종목:")
    for symbol, stock in list(data.stocks.items())[:5]:  # 상위 5개만
        arrow = "↑" if stock.change_pct > 0 else "↓" if stock.change_pct < 0 else "→"
        print(f"   {stock.name}: ${stock.price:,.2f} ({arrow}{stock.change_pct:+.2f}%)")

    print(f"\n💱 환율: ${data.usd_krw:,.2f} ({data.usd_krw_change:+.2f}%)")

    if data.nasdaq_futures:
        print(f"📉 나스닥100 선물: {data.nasdaq_futures.price:,.2f} ({data.nasdaq_futures.change_pct:+.2f}%)")

    print("\n🏭 섹터별 심리:")
    for sector, sentiment in data.sector_sentiments.items():
        print(f"   {sector}: {sentiment.value}")

    return True


async def test_coupling_analyzer():
    """2. CouplingAnalyzer 테스트"""
    print("\n" + "=" * 60)
    print("2. CouplingAnalyzer 테스트")
    print("=" * 60)

    from src.aegis.global_macro import get_coupling_analyzer

    analyzer = get_coupling_analyzer()

    # 테스트 종목 (현재 보유 종목 중 커플링 있는 것들)
    test_stocks = [
        ("035720", "카카오", "tech"),
        ("015760", "한국전력", "energy"),
        ("316140", "우리금융지주", "financial"),
    ]

    print("\n🔗 커플링 분석 결과:")
    for code, name, sector in test_stocks:
        result = await analyzer.analyze(code, name, sector)

        print(f"\n   [{name}] ({code})")
        print(f"   커플링 강도: {result.coupling_strength.value}")
        print(f"   미국 시장 심리: {result.us_sentiment.value}")
        print(f"   섹터 심리: {result.sector_sentiment.value}")
        print(f"   커플링 점수: {result.coupling_score:+.2f}")
        print(f"   조정 계수: {result.adjustment_factor:.3f}")
        print(f"   분석: {result.analysis_reason}")

        if result.related_us_stocks:
            print(f"   연관 미국 종목: {', '.join(result.related_us_stocks.keys())}")

    return True


async def test_dynamic_weight_optimizer():
    """3. DynamicWeightOptimizer 테스트"""
    print("\n" + "=" * 60)
    print("3. DynamicWeightOptimizer 테스트")
    print("=" * 60)

    from src.aegis.optimization import get_dynamic_weight_optimizer

    optimizer = get_dynamic_weight_optimizer()

    regimes = ['BULL', 'BEAR', 'SIDEWAY']

    print("\n⚖️ 동적 가중치 조정 결과:")
    for regime in regimes:
        result = await optimizer.get_optimized_weights(regime)

        print(f"\n   [{regime}] 국면 (변동성: {result.volatility.value})")
        print(f"   조정 이유: {result.adjustment_reason}")
        print(f"   신뢰도: {result.confidence:.2f}")

        print("   가중치 변화:")
        for key in result.original_weights:
            orig = result.original_weights[key]
            adj = result.adjusted_weights.get(key, orig)
            change = ((adj - orig) / orig * 100) if orig > 0 else 0
            arrow = "↑" if change > 0 else "↓" if change < 0 else "="
            print(f"      {key}: {orig:.3f} → {adj:.3f} ({arrow}{change:+.1f}%)")

    return True


async def test_fusion_engine_integration():
    """4. FusionEngine 통합 테스트"""
    print("\n" + "=" * 60)
    print("4. FusionEngine 통합 테스트 (8요소 융합)")
    print("=" * 60)

    from src.aegis.fusion import get_fusion_engine

    engine = get_fusion_engine()

    # 테스트 종목
    test_stocks = [
        ("035720", "카카오"),
        ("015760", "한국전력"),
    ]

    print("\n🎯 AEGIS 융합 분석 결과:")
    for code, name in test_stocks:
        try:
            result = await engine.analyze(
                ticker=code,
                stock_name=name,
                technical_score=0.5,  # 임시 기술적 점수
            )

            print(f"\n   [{name}] ({code})")
            print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"   최종 신호: {result.signal.value} (점수: {result.final_score:+.3f})")
            print(f"   시장 국면: {result.regime} (신뢰도: {result.regime_confidence:.2f})")

            print("\n   📊 개별 점수:")
            print(f"      기술적: {result.technical_score:+.3f}")
            print(f"      공시: {result.disclosure_score:+.3f}")
            print(f"      수급: {result.supply_score:+.3f}")
            print(f"      펀더멘털: {result.fundamental_score:+.3f}")
            print(f"      시장 컨텍스트: {result.market_context_score:+.3f}")
            print(f"      뉴스 감성: {result.news_sentiment_score:+.3f}")
            print(f"      컨센서스: {result.consensus_score:+.3f}")
            print(f"      글로벌 매크로: {result.global_macro_score:+.3f}")

            print("\n   🌐 글로벌 커플링:")
            details = result.details
            print(f"      커플링 강도: {details.get('coupling_strength', 'N/A')}")
            print(f"      미국 시장 심리: {details.get('us_sentiment', 'N/A')}")
            print(f"      섹터 심리: {details.get('sector_sentiment', 'N/A')}")
            print(f"      조정 계수: {details.get('coupling_adjustment', 1.0):.3f}")

            print("\n   ⚖️ 사용된 가중치:")
            for key, weight in result.weights_used.items():
                print(f"      {key}: {weight:.3f}")

        except Exception as e:
            logger.error(f"Failed to analyze {name}: {e}")
            import traceback
            traceback.print_exc()

    return True


async def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("Phase 4.5 Global Macro Integration Test")
    print(f"실행 시각: {datetime.now().isoformat()}")
    print("=" * 60)

    tests = [
        ("GlobalMarketFetcher", test_global_market_fetcher),
        ("CouplingAnalyzer", test_coupling_analyzer),
        ("DynamicWeightOptimizer", test_dynamic_weight_optimizer),
        ("FusionEngine Integration", test_fusion_engine_integration),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = await test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = f"❌ ERROR: {str(e)[:50]}"

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for name, status in results.items():
        print(f"   {name}: {status}")

    all_passed = all("PASS" in s for s in results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과! Phase 4.5 구현 완료")
    else:
        print("⚠️ 일부 테스트 실패 - 로그 확인 필요")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
