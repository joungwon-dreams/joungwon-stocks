"""
Information Fusion Engine - Phase 5.0 (Context Integration)
멀티모달 정보 융합 중앙 엔진

핵심 기능:
- 모든 분석기 결과를 종합하여 최종 AEGIS 신호 산출
- 시장 국면(Regime)별 동적 가중치 적용
- Trading Halt 및 필터 통합
- 뉴스 감성 및 컨센서스 모멘텀 통합
- 글로벌 매크로 커플링 분석 통합 (Phase 4.5)
- 시장 컨텍스트 및 캘린더 통합 (Phase 5.0)

공식 (9개 요소):
Score_final = W_tech*S_tech + W_news*S_news + W_disc*S_disc +
              W_supply*S_supply + W_fund*S_fund + W_mkt*S_mkt +
              W_consensus*S_consensus + W_global*S_global + W_context*S_context
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging

import pandas as pd

# Phase 3 imports
from src.aegis.ensemble.regime import MarketRegimeClassifier, MarketRegime, RegimeResult

# Phase 3.9 imports
from src.fetchers.tier1_official_libs.market_scanner import get_market_scanner

# Phase 4 imports
from .disclosure import DisclosureAnalyzer, DisclosureResult
from .supply import SupplyDemandAnalyzer, SupplyDemandResult
from .fundamental import FundamentalIntegrator, FundamentalResult
from .news_sentiment import NewsSentimentAnalyzer, NewsSentimentResult
from .consensus import ConsensusMomentumAnalyzer, ConsensusMomentumResult

# Phase 4.5 imports (Global Macro)
from src.aegis.global_macro import get_coupling_analyzer, CouplingResult
from src.aegis.optimization import get_dynamic_weight_optimizer

# Phase 5.0 imports (Market Context & Calendar)
from src.aegis.context import (
    get_sentiment_meter,
    get_calendar_fetcher,
    get_passive_tracker,
    get_sector_monitor,
    SentimentResult,
    CalendarResult,
)


class AegisSignal(Enum):
    """AEGIS 최종 신호"""
    STRONG_BUY = "strong_buy"       # Score >= 2.0
    BUY = "buy"                     # Score >= 1.0
    HOLD = "hold"                   # -1.0 < Score < 1.0
    SELL = "sell"                   # Score <= -1.0
    STRONG_SELL = "strong_sell"    # Score <= -2.0
    TRADING_HALT = "trading_halt"  # 매매 금지


@dataclass
class FusionResult:
    """융합 분석 결과"""
    ticker: str
    final_score: float
    signal: AegisSignal
    trading_halt: bool
    halt_reason: Optional[str]

    # 개별 점수
    disclosure_score: float
    supply_score: float
    fundamental_score: float
    market_context_score: float
    technical_score: float
    news_sentiment_score: float = 0.0
    consensus_score: float = 0.0
    global_macro_score: float = 0.0    # Phase 4.5: 글로벌 커플링
    context_score: float = 0.0         # Phase 5.0: 시장 컨텍스트 (심리/캘린더)

    # 가중치
    weights_used: Dict[str, float] = field(default_factory=dict)

    # 시장 국면
    regime: str = ""
    regime_confidence: float = 0.0

    # 필터 상태
    fundamental_pass: bool = True

    # 상세 정보
    details: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: str = ""


class InformationFusionEngine:
    """
    멀티모달 정보 융합 엔진

    Phase 4 Spec:
    - 모든 분석기 결과를 종합
    - 시장 국면별 동적 가중치 적용
    - Trading Halt 및 필터 우선 적용
    """

    # 시장 국면별 기본 가중치 (8개 요소 - Phase 4.5 Global Macro 추가)
    # Phase 5.0: 9개 요소 가중치 (총합 = 1.0)
    DEFAULT_WEIGHTS = {
        'BULL': {
            'technical': 0.16,
            'disclosure': 0.07,
            'supply': 0.20,
            'fundamental': 0.07,
            'market_context': 0.07,
            'news_sentiment': 0.12,
            'consensus': 0.07,
            'global_macro': 0.14,  # 상승장: 글로벌 커플링 중요
            'context': 0.10,       # Phase 5.0: 시장 심리/캘린더
        },
        'BEAR': {
            'technical': 0.11,
            'disclosure': 0.11,
            'supply': 0.11,
            'fundamental': 0.16,
            'market_context': 0.07,
            'news_sentiment': 0.11,
            'consensus': 0.07,
            'global_macro': 0.12,  # 하락장: 글로벌 리스크 주시
            'context': 0.14,       # Phase 5.0: 공포장에서 심리 중요
        },
        'SIDEWAY': {
            'technical': 0.20,
            'disclosure': 0.07,
            'supply': 0.16,
            'fundamental': 0.07,
            'market_context': 0.07,
            'news_sentiment': 0.12,
            'consensus': 0.07,
            'global_macro': 0.12,  # 횡보장: 글로벌 방향성 참고
            'context': 0.12,       # Phase 5.0: 캘린더 이벤트 체크
        },
    }

    # 신호 임계값
    SIGNAL_THRESHOLDS = {
        'strong_buy': 2.0,
        'buy': 1.0,
        'sell': -1.0,
        'strong_sell': -2.0,
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 분석기 인스턴스
        self.disclosure_analyzer = DisclosureAnalyzer()
        self.supply_analyzer = SupplyDemandAnalyzer()
        self.fundamental_integrator = FundamentalIntegrator()
        self.news_sentiment_analyzer = NewsSentimentAnalyzer()
        self.consensus_analyzer = ConsensusMomentumAnalyzer()
        self.regime_classifier = MarketRegimeClassifier()
        self.market_scanner = get_market_scanner()

        # Phase 4.5: 글로벌 매크로 분석기
        self.coupling_analyzer = get_coupling_analyzer()
        self.weight_optimizer = get_dynamic_weight_optimizer()

        # Phase 5.0: 시장 컨텍스트 분석기
        self.sentiment_meter = get_sentiment_meter()
        self.calendar_fetcher = get_calendar_fetcher()
        self.passive_tracker = get_passive_tracker()
        self.sector_monitor = get_sector_monitor()

        # 사용자 정의 가중치
        self._custom_weights: Optional[Dict[str, Dict[str, float]]] = None

        # Phase 4.5: 동적 가중치 사용 여부
        self._use_dynamic_weights: bool = True

    async def analyze(
        self,
        ticker: str,
        stock_name: str = "",
        price_df: Optional[pd.DataFrame] = None,
        technical_score: float = 0.0,
        sector: Optional[str] = None,
    ) -> FusionResult:
        """
        종목에 대한 종합 융합 분석 수행

        Args:
            ticker: 종목코드
            stock_name: 종목명 (커플링 분석용)
            price_df: 가격 데이터 (시장 국면 분류용)
            technical_score: 기술적 분석 점수 (외부에서 전달)
            sector: 섹터 (커플링 분석용)

        Returns:
            FusionResult: 융합 분석 결과
        """
        self.logger.info(f"Starting fusion analysis for {ticker}")

        # 1. 병렬로 모든 분석 수행 (9개 분석기 - Phase 5.0)
        disclosure_task = self.disclosure_analyzer.analyze(ticker, days=30)
        supply_task = self.supply_analyzer.analyze(ticker, days=10)
        fundamental_task = self.fundamental_integrator.analyze(ticker)
        news_task = self.news_sentiment_analyzer.analyze(ticker, days=3, use_ai=True)
        consensus_task = self.consensus_analyzer.analyze(ticker)
        market_task = self.market_scanner.get_full_market_context("KOSPI")
        coupling_task = self.coupling_analyzer.analyze(ticker, stock_name or ticker, sector)

        # Phase 5.0: 시장 컨텍스트 분석
        sentiment_task = self.sentiment_meter.analyze()
        calendar_task = self.calendar_fetcher.analyze(days_ahead=14)

        (disclosure, supply, fundamental, news, consensus, market, coupling,
         sentiment, calendar) = await asyncio.gather(
            disclosure_task, supply_task, fundamental_task,
            news_task, consensus_task, market_task, coupling_task,
            sentiment_task, calendar_task
        )

        # 2. Trading Halt 체크 (최우선)
        if disclosure.trading_halt:
            return self._create_halt_result(
                ticker, disclosure, supply, fundamental,
                disclosure.halt_reason
            )

        # 3. Fundamental 필터 체크
        if not fundamental.pass_filter:
            self.logger.warning(
                f"{ticker} failed fundamental filter: {fundamental.filter_reason}"
            )
            # 필터 실패해도 분석은 계속하되, 점수 페널티

        # 4. 시장 국면 분류
        regime = self._get_market_regime(price_df)

        # 5. 시장 컨텍스트 점수 계산
        market_score = self._calculate_market_score(market)

        # 6. 글로벌 커플링 점수 정규화 (-100~100 → -3~+3)
        global_macro_score = coupling.coupling_score / 33.33

        # 7. Phase 5.0: 시장 컨텍스트 점수 계산
        # Fear & Greed 점수 (0-100) → 정규화 (-3 ~ +3)
        # 50이 중립, 0은 극도의 공포, 100은 극도의 탐욕
        context_score = (sentiment.sentiment_score - 50) / 16.67

        # 캘린더 리스크 조정: 고위험 이벤트 시 점수 하향
        if calendar.should_reduce_exposure:
            context_score *= calendar.position_adjustment

        # 8. 가중치 조회 (동적 또는 정적)
        weights = await self._get_optimized_weights(regime.regime.value)

        # 9. 가중치 적용하여 최종 점수 계산 (9개 요소 - Phase 5.0)
        final_score = (
            weights['technical'] * technical_score +
            weights['disclosure'] * disclosure.score +
            weights['supply'] * supply.score +
            weights['fundamental'] * fundamental.score +
            weights['market_context'] * market_score +
            weights['news_sentiment'] * news.score +
            weights['consensus'] * consensus.score +
            weights['global_macro'] * global_macro_score +
            weights['context'] * context_score
        )

        # 커플링 조정 계수 적용 (강한 커플링 종목만)
        if coupling.coupling_strength.value in ['strong', 'moderate']:
            final_score *= coupling.adjustment_factor

        # Phase 5.0: 캘린더 기반 방어 모드 (Critical 이벤트 시)
        if calendar.risk_level == "critical":
            final_score *= 0.8  # 20% 페널티
            self.logger.warning(f"Critical calendar event: {calendar.warning_message}")

        # Fundamental 필터 실패 시 페널티
        if not fundamental.pass_filter:
            final_score -= 0.5

        # 9. 최종 신호 결정
        signal = self._determine_signal(final_score)

        return FusionResult(
            ticker=ticker,
            final_score=round(final_score, 3),
            signal=signal,
            trading_halt=False,
            halt_reason=None,
            disclosure_score=disclosure.score,
            supply_score=supply.score,
            fundamental_score=fundamental.score,
            market_context_score=market_score,
            technical_score=technical_score,
            news_sentiment_score=news.score,
            consensus_score=consensus.score,
            global_macro_score=round(global_macro_score, 3),
            context_score=round(context_score, 3),  # Phase 5.0
            weights_used=weights,
            regime=regime.regime.value,
            regime_confidence=regime.confidence,
            fundamental_pass=fundamental.pass_filter,
            details={
                'disclosure_events': len(disclosure.key_events),
                'supply_pattern': supply.pattern.value,
                'fundamental_grade': fundamental.grade.value,
                'market_sentiment': market.get('summary', {}).get('market_sentiment', 'unknown'),
                'leading_sectors': market.get('summary', {}).get('leading_sectors', []),
                'news_sentiment': news.sentiment.value,
                'news_count': news.news_count,
                'consensus_trend': consensus.trend.value,
                'upside_potential': consensus.upside_potential,
                'ai_summary': news.ai_summary,
                # Phase 4.5: Global Macro details
                'coupling_strength': coupling.coupling_strength.value,
                'us_sentiment': coupling.us_sentiment.value,
                'sector_sentiment': coupling.sector_sentiment.value,
                'coupling_adjustment': coupling.adjustment_factor,
                'coupling_reason': coupling.analysis_reason,
                # Phase 5.0: Market Context details
                'fear_greed_score': sentiment.sentiment_score,
                'market_condition': sentiment.condition.value,
                'position_multiplier': sentiment.position_multiplier,
                'sentiment_warning': sentiment.warning_message,
                'calendar_risk_level': calendar.risk_level,
                'calendar_risk_score': calendar.risk_score,
                'calendar_warning': calendar.warning_message,
                'today_events': [e.name for e in calendar.today_events],
                'upcoming_critical_events': [
                    e.name for e in calendar.upcoming_events
                    if e.impact.value == 'critical' and e.d_day <= 7
                ],
            },
            analyzed_at=datetime.now().isoformat()
        )

    def _get_market_regime(self, price_df: Optional[pd.DataFrame]) -> RegimeResult:
        """시장 국면 분류"""
        if price_df is not None and len(price_df) >= 60:
            return self.regime_classifier.classify(price_df)

        # 기본값: SIDEWAY
        return RegimeResult(
            regime=MarketRegime.SIDEWAY,
            confidence=0.5,
            ma_short=0,
            ma_long=0,
            volatility=0,
            trend_strength=0
        )

    def _calculate_market_score(self, market_context: Dict[str, Any]) -> float:
        """시장 컨텍스트 점수 계산"""
        summary = market_context.get('summary', {})

        sentiment = summary.get('market_sentiment', 'neutral')
        adr = summary.get('adr', 1.0)

        # ADR 기반 점수
        if adr > 1.5:
            score = 0.5
        elif adr > 1.0:
            score = 0.2
        elif adr > 0.67:
            score = 0.0
        elif adr > 0.5:
            score = -0.2
        else:
            score = -0.5

        return score

    async def _get_optimized_weights(self, regime: str) -> Dict[str, float]:
        """
        최적화된 가중치 반환 (Phase 5.0)

        동적 가중치 사용 시: DynamicWeightOptimizer에서 변동성 기반 조정
        정적 가중치 사용 시: 기본 가중치 반환
        """
        default_weights = self.DEFAULT_WEIGHTS.get(regime, self.DEFAULT_WEIGHTS['SIDEWAY'])

        # 사용자 정의 가중치 우선
        if self._custom_weights and regime in self._custom_weights:
            return self._custom_weights[regime]

        # 동적 가중치 사용
        if self._use_dynamic_weights:
            try:
                weight_adjustment = await self.weight_optimizer.get_optimized_weights(regime)
                # 기본 가중치에 누락된 키 추가 (Phase 4.5 global_macro, Phase 5.0 context)
                adjusted = weight_adjustment.adjusted_weights.copy()
                if 'global_macro' not in adjusted:
                    adjusted['global_macro'] = default_weights.get('global_macro', 0.12)
                if 'context' not in adjusted:
                    adjusted['context'] = default_weights.get('context', 0.10)
                return adjusted
            except Exception as e:
                self.logger.warning(f"Dynamic weight optimization failed: {e}")

        return default_weights

    def _get_weights(self, regime: str) -> Dict[str, float]:
        """국면별 가중치 반환 (동기 버전, 하위 호환용)"""
        if self._custom_weights and regime in self._custom_weights:
            return self._custom_weights[regime]

        return self.DEFAULT_WEIGHTS.get(regime, self.DEFAULT_WEIGHTS['SIDEWAY'])

    def set_dynamic_weights(self, enabled: bool):
        """동적 가중치 사용 여부 설정"""
        self._use_dynamic_weights = enabled
        self.logger.info(f"Dynamic weights {'enabled' if enabled else 'disabled'}")

    def _determine_signal(self, score: float) -> AegisSignal:
        """최종 신호 결정"""
        if score >= self.SIGNAL_THRESHOLDS['strong_buy']:
            return AegisSignal.STRONG_BUY
        elif score >= self.SIGNAL_THRESHOLDS['buy']:
            return AegisSignal.BUY
        elif score <= self.SIGNAL_THRESHOLDS['strong_sell']:
            return AegisSignal.STRONG_SELL
        elif score <= self.SIGNAL_THRESHOLDS['sell']:
            return AegisSignal.SELL
        else:
            return AegisSignal.HOLD

    def _create_halt_result(
        self,
        ticker: str,
        disclosure: DisclosureResult,
        supply: SupplyDemandResult,
        fundamental: FundamentalResult,
        halt_reason: str
    ) -> FusionResult:
        """Trading Halt 결과 생성"""
        return FusionResult(
            ticker=ticker,
            final_score=-999.0,
            signal=AegisSignal.TRADING_HALT,
            trading_halt=True,
            halt_reason=halt_reason,
            disclosure_score=disclosure.score,
            supply_score=supply.score,
            fundamental_score=fundamental.score,
            market_context_score=0.0,
            technical_score=0.0,
            context_score=0.0,  # Phase 5.0
            weights_used={},
            regime='N/A',
            regime_confidence=0.0,
            fundamental_pass=fundamental.pass_filter,
            details={'halt_reason': halt_reason},
            analyzed_at=datetime.now().isoformat()
        )

    def set_custom_weights(self, weights: Dict[str, Dict[str, float]]):
        """사용자 정의 가중치 설정"""
        self._custom_weights = weights
        self.logger.info(f"Custom weights set: {weights}")

    def clear_caches(self):
        """모든 분석기 캐시 초기화"""
        self.disclosure_analyzer.clear_cache()
        self.supply_analyzer.clear_cache()
        self.fundamental_integrator.clear_cache()
        self.news_sentiment_analyzer.clear_cache()
        self.consensus_analyzer.clear_cache()
        self.market_scanner.clear_cache()
        # Phase 4.5
        self.coupling_analyzer._cached_global_data = None
        self.logger.info("All analyzer caches cleared")


# Singleton instance
_engine_instance: Optional[InformationFusionEngine] = None


def get_fusion_engine() -> InformationFusionEngine:
    """Get singleton InformationFusionEngine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = InformationFusionEngine()
    return _engine_instance


# Convenience function
async def get_aegis_signal(
    ticker: str,
    price_df: Optional[pd.DataFrame] = None,
    technical_score: float = 0.0
) -> FusionResult:
    """AEGIS 신호 조회 편의 함수"""
    engine = get_fusion_engine()
    return await engine.analyze(ticker, price_df, technical_score)
