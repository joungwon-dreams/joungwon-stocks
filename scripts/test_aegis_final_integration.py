#!/usr/bin/env python3
"""
AEGIS Final Integration Test - Phase 0 ~ 6
모든 컴포넌트가 유기적으로 작동하는지 종합 검증

테스트 항목:
1. FinalSignalValidator 과락 로직
2. ExecutionSimulator 비용 모델
3. DynamicWeightOptimizer + CouplingAnalyzer 영향
4. GlobalMarketFetcher + DataIntegrityManager 연동
5. 전체 파이프라인 통합 테스트
"""
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

# AEGIS Core
from src.aegis.fusion.engine import (
    InformationFusionEngine,
    get_fusion_engine,
    FusionResult,
    AegisSignal
)

# Phase 5.0: Context
from src.aegis.context import (
    get_sentiment_meter,
    get_calendar_fetcher,
    get_passive_tracker,
    get_sector_monitor,
)

# Phase 4.5: Global Macro
from src.aegis.global_macro import get_coupling_analyzer

# Phase 6: Real-World Optimization
from src.aegis.optimization import (
    get_signal_validator,
    get_execution_simulator,
    get_integrity_manager,
    ValidationDecision,
    TimeSegment,
)


@dataclass
class IntegrationTestResult:
    """통합 테스트 결과"""
    test_name: str
    passed: bool
    details: Dict[str, Any]
    error: str = ""


class AegisIntegrationTester:
    """AEGIS 통합 테스트 클래스"""

    def __init__(self):
        self.engine = get_fusion_engine()
        self.validator = get_signal_validator()
        self.simulator = get_execution_simulator()
        self.integrity_mgr = get_integrity_manager()
        self.results: List[IntegrationTestResult] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        print("=" * 60)
        print("AEGIS FINAL INTEGRATION TEST")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        print()

        # 1. Phase 5.0 Context 모듈 테스트
        await self._test_context_modules()

        # 2. Phase 4.5 Global Macro 테스트
        await self._test_global_macro()

        # 3. Phase 6 Real-World 테스트
        await self._test_real_world_components()

        # 4. FinalSignalValidator 과락 로직 테스트
        await self._test_validator_veto_logic()

        # 5. ExecutionSimulator 비용 모델 테스트
        self._test_execution_simulator()

        # 6. 전체 파이프라인 통합 테스트
        await self._test_full_pipeline()

        # 결과 요약
        return self._generate_summary()

    async def _test_context_modules(self):
        """Phase 5.0 Context 모듈 테스트"""
        print("\n[TEST 1] Phase 5.0 Context Modules")
        print("-" * 40)

        try:
            # Sentiment Meter
            sentiment = await get_sentiment_meter().analyze()
            print(f"  Sentiment Score: {sentiment.sentiment_score}/100")
            print(f"  Market Condition: {sentiment.condition.value}")

            # Calendar Fetcher
            calendar = await get_calendar_fetcher().analyze(days_ahead=14)
            print(f"  Calendar Risk: {calendar.risk_level}")
            print(f"  Today Events: {len(calendar.today_events)}")
            print(f"  Upcoming Events: {len(calendar.upcoming_events)}")

            # Passive Tracker
            passive = await get_passive_tracker().analyze()
            print(f"  Next Rebalance: {passive.next_rebalance_date}")

            # Sector Monitor
            sector = await get_sector_monitor().analyze()
            print(f"  Hot Sectors: {[s.value for s in sector.hot_sectors]}")
            print(f"  Active Events: {[e.name for e in sector.active_events]}")

            self.results.append(IntegrationTestResult(
                test_name="Phase 5.0 Context Modules",
                passed=True,
                details={
                    'sentiment_score': sentiment.sentiment_score,
                    'calendar_risk': calendar.risk_level,
                    'hot_sectors': [s.value for s in sector.hot_sectors],
                }
            ))
            print("  ✅ PASSED")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="Phase 5.0 Context Modules",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    async def _test_global_macro(self):
        """Phase 4.5 Global Macro 테스트"""
        print("\n[TEST 2] Phase 4.5 Global Macro (CouplingAnalyzer)")
        print("-" * 40)

        try:
            analyzer = get_coupling_analyzer()
            result = await analyzer.analyze(
                stock_code='005930',
                stock_name='삼성전자',
                sector='반도체'
            )

            print(f"  Coupling Score: {result.coupling_score}")
            print(f"  Coupling Strength: {result.coupling_strength.value}")
            print(f"  US Sentiment: {result.us_sentiment.value}")
            print(f"  Adjustment Factor: {result.adjustment_factor}")

            self.results.append(IntegrationTestResult(
                test_name="Phase 4.5 Global Macro",
                passed=True,
                details={
                    'coupling_score': result.coupling_score,
                    'coupling_strength': result.coupling_strength.value,
                    'adjustment_factor': result.adjustment_factor,
                }
            ))
            print("  ✅ PASSED")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="Phase 4.5 Global Macro",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    async def _test_real_world_components(self):
        """Phase 6 Real-World 컴포넌트 테스트"""
        print("\n[TEST 3] Phase 6 Real-World Components")
        print("-" * 40)

        try:
            # DataIntegrityManager - NQ Futures
            nq = await self.integrity_mgr.get_nq_futures()
            if nq:
                print(f"  NQ Futures: {nq.price:,.2f} ({nq.change_pct:+.2f}%)")
                premarket = self.integrity_mgr.get_premarket_signal(nq)
                print(f"  Premarket Signal: {premarket['signal']} ({premarket['bias']})")
            else:
                print("  NQ Futures: Not available")

            # Time Segment
            segment = self.simulator.get_current_time_segment()
            print(f"  Current Time Segment: {segment.value}")

            # Market Status
            print(f"  Is Market Open: {self.integrity_mgr.is_market_open()}")

            self.results.append(IntegrationTestResult(
                test_name="Phase 6 Real-World Components",
                passed=True,
                details={
                    'nq_available': nq is not None,
                    'nq_price': nq.price if nq else None,
                    'time_segment': segment.value,
                }
            ))
            print("  ✅ PASSED")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="Phase 6 Real-World Components",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    async def _test_validator_veto_logic(self):
        """FinalSignalValidator 과락 로직 테스트"""
        print("\n[TEST 4] FinalSignalValidator Veto Logic")
        print("-" * 40)

        try:
            # Mock FusionResult for testing
            class MockFusionResult:
                def __init__(self, fundamental=-2.5, market_ctx=-1.0, trading_halt=False):
                    self.signal = AegisSignal.BUY
                    self.final_score = 1.5
                    self.trading_halt = trading_halt
                    self.halt_reason = "Test halt" if trading_halt else None
                    self.fundamental_score = fundamental
                    self.market_context_score = market_ctx
                    self.details = {
                        'calendar_risk_level': 'low',
                        'fear_greed_score': 50,
                        'market_condition': 'neutral',
                    }

            # Test 1: Fundamental Risk (과락)
            mock_result = MockFusionResult(fundamental=-2.5)
            validation = await self.validator.validate(
                ticker='TEST001',
                fusion_result=mock_result,
                avg_traded_value_5d=50_000_000_000  # 500억
            )
            fundamental_blocked = validation.decision == ValidationDecision.BLOCK_BUY
            print(f"  Fundamental Risk Test: {'BLOCKED' if fundamental_blocked else 'PASSED'}")

            # Test 2: Liquidity Trap (유동성 부족)
            mock_result2 = MockFusionResult(fundamental=1.0)
            validation2 = await self.validator.validate(
                ticker='TEST002',
                fusion_result=mock_result2,
                avg_traded_value_5d=5_000_000_000  # 50억 (100억 미만)
            )
            liquidity_blocked = validation2.decision == ValidationDecision.BLOCK_BUY
            print(f"  Liquidity Trap Test: {'BLOCKED' if liquidity_blocked else 'PASSED'}")

            # Test 3: Normal Case (통과)
            mock_result3 = MockFusionResult(fundamental=1.0)
            validation3 = await self.validator.validate(
                ticker='TEST003',
                fusion_result=mock_result3,
                avg_traded_value_5d=50_000_000_000  # 500억
            )
            normal_passed = validation3.decision == ValidationDecision.PASS
            print(f"  Normal Case Test: {'PASSED' if normal_passed else 'BLOCKED'}")

            # Test 4: Trading Halt (강제 매도)
            mock_result4 = MockFusionResult(trading_halt=True)
            validation4 = await self.validator.validate(
                ticker='TEST004',
                fusion_result=mock_result4,
                avg_traded_value_5d=50_000_000_000
            )
            halt_force_sell = validation4.decision == ValidationDecision.FORCE_SELL
            print(f"  Trading Halt Test: {'FORCE_SELL' if halt_force_sell else 'OTHER'}")

            all_passed = fundamental_blocked and liquidity_blocked and normal_passed and halt_force_sell

            self.results.append(IntegrationTestResult(
                test_name="FinalSignalValidator Veto Logic",
                passed=all_passed,
                details={
                    'fundamental_blocked': fundamental_blocked,
                    'liquidity_blocked': liquidity_blocked,
                    'normal_passed': normal_passed,
                    'halt_force_sell': halt_force_sell,
                }
            ))
            print(f"  {'✅ ALL VETO TESTS PASSED' if all_passed else '❌ SOME VETO TESTS FAILED'}")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="FinalSignalValidator Veto Logic",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    def _test_execution_simulator(self):
        """ExecutionSimulator 비용 모델 테스트"""
        print("\n[TEST 5] ExecutionSimulator Cost Model")
        print("-" * 40)

        try:
            # 삼성전자 55,000원 기준 테스트
            price = 55000
            quantity = 100

            # 손익분기점 계산
            breakeven = self.simulator.estimate_breakeven(price)
            print(f"  Price: {price:,}원")
            print(f"  Tick Size: {breakeven['tick_size']}원")
            print(f"  Buy Slippage: {breakeven['buy_slippage_pct']:.3f}%")
            print(f"  Sell Slippage: {breakeven['sell_slippage_pct']:.3f}%")
            print(f"  Buy Cost: {breakeven['buy_cost_pct']:.3f}%")
            print(f"  Sell Cost: {breakeven['sell_cost_pct']:.3f}%")
            print(f"  Total Breakeven: {breakeven['total_breakeven_pct']:.3f}%")

            # 왕복 거래 시뮬레이션
            pnl = self.simulator.simulate_round_trip(
                ticker='005930',
                buy_price=55000,
                sell_price=56000,
                quantity=100
            )
            print(f"\n  Round-trip Simulation (55,000 → 56,000):")
            print(f"    Buy Price (w/ slippage): {pnl.buy_price:,.0f}원")
            print(f"    Sell Price (w/ slippage): {pnl.sell_price:,.0f}원")
            print(f"    Total Cost: {pnl.total_cost:,.0f}원")
            print(f"    Net Profit: {pnl.net_profit:,.0f}원 ({pnl.net_profit_pct}%)")
            print(f"    Breakeven Required: {pnl.breakeven_pct:.2f}%")

            # 검증: 비용이 0보다 커야 함
            cost_valid = pnl.total_cost > 0
            # 검증: 순수익 < 총수익 (비용 차감)
            profit_valid = pnl.net_profit < pnl.gross_profit

            self.results.append(IntegrationTestResult(
                test_name="ExecutionSimulator Cost Model",
                passed=cost_valid and profit_valid,
                details={
                    'breakeven_pct': breakeven['total_breakeven_pct'],
                    'net_profit': pnl.net_profit,
                    'total_cost': pnl.total_cost,
                }
            ))
            print(f"  {'✅ PASSED' if cost_valid and profit_valid else '❌ FAILED'}")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="ExecutionSimulator Cost Model",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    async def _test_full_pipeline(self):
        """전체 파이프라인 통합 테스트"""
        print("\n[TEST 6] Full Pipeline Integration (FusionEngine)")
        print("-" * 40)

        try:
            # 삼성전자 분석
            print("  Analyzing 005930 (삼성전자)...")
            result = await self.engine.analyze(
                ticker='005930',
                stock_name='삼성전자',
                technical_score=1.5,
                sector='반도체'
            )

            print(f"\n  === FusionEngine Result ===")
            print(f"  Final Score: {result.final_score}")
            print(f"  Signal: {result.signal.value}")
            print(f"  Regime: {result.regime}")
            print(f"\n  --- Individual Scores (9 Elements) ---")
            print(f"    Technical: {result.technical_score}")
            print(f"    Disclosure: {result.disclosure_score}")
            print(f"    Supply: {result.supply_score}")
            print(f"    Fundamental: {result.fundamental_score}")
            print(f"    Market Context: {result.market_context_score}")
            print(f"    News Sentiment: {result.news_sentiment_score}")
            print(f"    Consensus: {result.consensus_score}")
            print(f"    Global Macro: {result.global_macro_score}")
            print(f"    Context (Phase 5.0): {result.context_score}")

            # Phase 5.0 Context Details
            print(f"\n  --- Phase 5.0 Context Details ---")
            print(f"    Fear & Greed: {result.details.get('fear_greed_score')}")
            print(f"    Market Condition: {result.details.get('market_condition')}")
            print(f"    Calendar Risk: {result.details.get('calendar_risk_level')}")

            # Phase 4.5 Global Macro Details
            print(f"\n  --- Phase 4.5 Global Macro Details ---")
            print(f"    Coupling Strength: {result.details.get('coupling_strength')}")
            print(f"    US Sentiment: {result.details.get('us_sentiment')}")
            print(f"    Coupling Adjustment: {result.details.get('coupling_adjustment')}")

            # Phase 6: Validator 적용
            print(f"\n  --- Phase 6 Validation ---")
            validation = await self.validator.validate(
                ticker='005930',
                fusion_result=result,
                avg_traded_value_5d=500_000_000_000  # 5000억 (삼성전자급)
            )
            print(f"    Decision: {validation.decision.value}")
            print(f"    Warnings: {validation.warnings}")
            print(f"    Adjusted Signal: {validation.adjusted_signal}")

            # 검증
            has_scores = all([
                result.final_score is not None,
                result.context_score is not None,
                result.global_macro_score is not None,
            ])

            self.results.append(IntegrationTestResult(
                test_name="Full Pipeline Integration",
                passed=has_scores,
                details={
                    'final_score': result.final_score,
                    'signal': result.signal.value,
                    'context_score': result.context_score,
                    'global_macro_score': result.global_macro_score,
                    'validation_decision': validation.decision.value,
                }
            ))
            print(f"\n  {'✅ PASSED' if has_scores else '❌ FAILED'}")

        except Exception as e:
            self.results.append(IntegrationTestResult(
                test_name="Full Pipeline Integration",
                passed=False,
                details={},
                error=str(e)
            ))
            print(f"  ❌ FAILED: {e}")

    def _generate_summary(self) -> Dict[str, Any]:
        """결과 요약 생성"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"\nTotal: {passed}/{total} tests passed")
        print()

        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"  {status} - {r.test_name}")
            if r.error:
                print(f"         Error: {r.error}")

        print()
        print("=" * 60)

        if passed == total:
            print("🎉 ALL TESTS PASSED - AEGIS Phase 0~6 Integration Complete!")
        else:
            print(f"⚠️ {total - passed} test(s) failed - Review required")

        print("=" * 60)

        return {
            'passed': passed,
            'total': total,
            'all_passed': passed == total,
            'results': [
                {
                    'name': r.test_name,
                    'passed': r.passed,
                    'details': r.details,
                    'error': r.error,
                }
                for r in self.results
            ],
            'timestamp': datetime.now().isoformat(),
        }


async def main():
    """메인 함수"""
    tester = AegisIntegrationTester()
    summary = await tester.run_all_tests()
    return summary


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result['all_passed'] else 1)
