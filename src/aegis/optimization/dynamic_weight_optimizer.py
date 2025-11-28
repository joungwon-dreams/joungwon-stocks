"""
Dynamic Weight Optimizer - Phase 4 Final Component
실시간 시장 상황에 따른 가중치 자동 조정

핵심 기능:
- 시장 변동성에 따른 가중치 동적 조정
- 최근 성과 기반 가중치 학습
- 시장 국면 전환 감지 및 선제 대응
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from pathlib import Path

import numpy as np
from pykrx import stock as pykrx


class MarketVolatility(Enum):
    """시장 변동성 수준"""
    LOW = "low"           # VIX < 15 or 코스피 변동성 < 1%
    NORMAL = "normal"     # VIX 15-25 or 코스피 변동성 1-2%
    HIGH = "high"         # VIX 25-35 or 코스피 변동성 2-3%
    EXTREME = "extreme"   # VIX > 35 or 코스피 변동성 > 3%


@dataclass
class WeightAdjustment:
    """가중치 조정 결과"""
    regime: str
    volatility: MarketVolatility
    original_weights: Dict[str, float]
    adjusted_weights: Dict[str, float]
    adjustment_reason: str
    confidence: float
    timestamp: str


class DynamicWeightOptimizer:
    """
    동적 가중치 최적화기

    Phase 4 Spec:
    - 시장 변동성에 따른 실시간 가중치 조정
    - 성과 기반 학습
    - 국면 전환 선제 대응
    """

    # 기본 가중치 (InformationFusionEngine과 동일)
    BASE_WEIGHTS = {
        'BULL': {
            'technical': 0.20,
            'disclosure': 0.10,
            'supply': 0.25,
            'fundamental': 0.10,
            'market_context': 0.10,
            'news_sentiment': 0.15,
            'consensus': 0.10,
        },
        'BEAR': {
            'technical': 0.15,
            'disclosure': 0.15,
            'supply': 0.15,
            'fundamental': 0.20,
            'market_context': 0.10,
            'news_sentiment': 0.15,
            'consensus': 0.10,
        },
        'SIDEWAY': {
            'technical': 0.25,
            'disclosure': 0.10,
            'supply': 0.20,
            'fundamental': 0.10,
            'market_context': 0.10,
            'news_sentiment': 0.15,
            'consensus': 0.10,
        },
    }

    # 변동성별 조정 계수
    VOLATILITY_ADJUSTMENTS = {
        MarketVolatility.LOW: {
            'technical': 1.1,      # 기술적 신호 신뢰도 증가
            'supply': 1.1,         # 수급 신호 신뢰도 증가
            'fundamental': 0.9,    # 펀더멘털 비중 감소
            'news_sentiment': 0.9,
        },
        MarketVolatility.NORMAL: {
            'technical': 1.0,
            'supply': 1.0,
            'fundamental': 1.0,
            'news_sentiment': 1.0,
        },
        MarketVolatility.HIGH: {
            'technical': 0.8,      # 기술적 신호 신뢰도 감소 (노이즈 증가)
            'supply': 0.9,
            'fundamental': 1.2,    # 펀더멘털 비중 증가 (안전자산 선호)
            'news_sentiment': 1.1,
        },
        MarketVolatility.EXTREME: {
            'technical': 0.6,      # 기술적 신호 크게 감소
            'supply': 0.7,
            'fundamental': 1.4,    # 펀더멘털 크게 증가
            'disclosure': 1.3,     # 공시 중요도 증가
            'news_sentiment': 1.2,
        },
    }

    # 저장 경로
    WEIGHTS_FILE = Path("data/optimized_weights.json")

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._current_volatility: Optional[MarketVolatility] = None
        self._cached_weights: Dict[str, Dict[str, float]] = {}
        self._performance_history: List[Dict[str, Any]] = []

        # 저장된 가중치 로드
        self._load_weights()

    async def get_optimized_weights(
        self,
        regime: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> WeightAdjustment:
        """
        최적화된 가중치 반환

        Args:
            regime: 시장 국면 (BULL/BEAR/SIDEWAY)
            market_data: 시장 데이터 (변동성 계산용)

        Returns:
            WeightAdjustment: 조정된 가중치
        """
        # 1. 기본 가중치 가져오기
        base_weights = self.BASE_WEIGHTS.get(regime, self.BASE_WEIGHTS['SIDEWAY']).copy()

        # 2. 시장 변동성 측정
        volatility = await self._measure_volatility(market_data)
        self._current_volatility = volatility

        # 3. 변동성에 따른 가중치 조정
        adjusted_weights = self._apply_volatility_adjustment(base_weights, volatility)

        # 4. 가중치 정규화 (합계 = 1.0)
        adjusted_weights = self._normalize_weights(adjusted_weights)

        # 5. 조정 이유 생성
        reason = self._generate_adjustment_reason(regime, volatility)

        return WeightAdjustment(
            regime=regime,
            volatility=volatility,
            original_weights=base_weights,
            adjusted_weights=adjusted_weights,
            adjustment_reason=reason,
            confidence=self._calculate_confidence(volatility),
            timestamp=datetime.now().isoformat()
        )

    async def _measure_volatility(
        self,
        market_data: Optional[Dict[str, Any]] = None
    ) -> MarketVolatility:
        """시장 변동성 측정"""
        try:
            # 코스피 20일 변동성 계산
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            df = pykrx.get_index_ohlcv_by_date(start_date, end_date, "1001")  # 코스피

            if df.empty or len(df) < 10:
                return MarketVolatility.NORMAL

            # 일간 수익률 계산
            returns = df['종가'].pct_change().dropna()

            # 연환산 변동성
            volatility = returns.std() * np.sqrt(252) * 100

            # 최근 5일 변동폭
            recent_range = (df['고가'].iloc[-5:].max() - df['저가'].iloc[-5:].min()) / df['종가'].iloc[-5:].mean() * 100

            self.logger.info(f"Market volatility: {volatility:.2f}%, Recent range: {recent_range:.2f}%")

            # 변동성 수준 판단
            if volatility < 12 and recent_range < 3:
                return MarketVolatility.LOW
            elif volatility < 20 and recent_range < 5:
                return MarketVolatility.NORMAL
            elif volatility < 30 and recent_range < 8:
                return MarketVolatility.HIGH
            else:
                return MarketVolatility.EXTREME

        except Exception as e:
            self.logger.warning(f"Failed to measure volatility: {e}")
            return MarketVolatility.NORMAL

    def _apply_volatility_adjustment(
        self,
        weights: Dict[str, float],
        volatility: MarketVolatility
    ) -> Dict[str, float]:
        """변동성에 따른 가중치 조정"""
        adjustments = self.VOLATILITY_ADJUSTMENTS.get(volatility, {})

        adjusted = {}
        for key, value in weights.items():
            multiplier = adjustments.get(key, 1.0)
            adjusted[key] = value * multiplier

        return adjusted

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """가중치 정규화 (합계 = 1.0)"""
        total = sum(weights.values())
        if total == 0:
            return weights

        return {k: round(v / total, 3) for k, v in weights.items()}

    def _generate_adjustment_reason(self, regime: str, volatility: MarketVolatility) -> str:
        """조정 이유 생성"""
        reasons = {
            MarketVolatility.LOW: f"낮은 변동성({regime}) - 기술적/수급 신호 강화",
            MarketVolatility.NORMAL: f"정상 변동성({regime}) - 기본 가중치 유지",
            MarketVolatility.HIGH: f"높은 변동성({regime}) - 펀더멘털/뉴스 신호 강화",
            MarketVolatility.EXTREME: f"극심한 변동성({regime}) - 방어적 가중치 적용",
        }
        return reasons.get(volatility, "Unknown")

    def _calculate_confidence(self, volatility: MarketVolatility) -> float:
        """신뢰도 계산"""
        confidence_map = {
            MarketVolatility.LOW: 0.9,
            MarketVolatility.NORMAL: 0.85,
            MarketVolatility.HIGH: 0.7,
            MarketVolatility.EXTREME: 0.5,
        }
        return confidence_map.get(volatility, 0.7)

    def record_performance(
        self,
        weights_used: Dict[str, float],
        regime: str,
        signal: str,
        actual_return: float
    ):
        """
        성과 기록 (학습용)

        Args:
            weights_used: 사용된 가중치
            regime: 시장 국면
            signal: 발생 신호 (BUY/SELL/HOLD)
            actual_return: 실제 수익률 (%)
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'regime': regime,
            'volatility': self._current_volatility.value if self._current_volatility else 'unknown',
            'weights': weights_used,
            'signal': signal,
            'actual_return': actual_return,
            'success': actual_return > 0 if signal == 'BUY' else (actual_return < 0 if signal == 'SELL' else True)
        }

        self._performance_history.append(record)

        # 최근 100건만 유지
        if len(self._performance_history) > 100:
            self._performance_history = self._performance_history[-100:]

        self.logger.info(f"Performance recorded: {signal} -> {actual_return:.2f}%")

    def get_performance_stats(self) -> Dict[str, Any]:
        """성과 통계 조회"""
        if not self._performance_history:
            return {'message': 'No performance data'}

        total = len(self._performance_history)
        successes = sum(1 for r in self._performance_history if r['success'])
        avg_return = sum(r['actual_return'] for r in self._performance_history) / total

        # 국면별 통계
        regime_stats = {}
        for regime in ['BULL', 'BEAR', 'SIDEWAY']:
            regime_records = [r for r in self._performance_history if r['regime'] == regime]
            if regime_records:
                regime_stats[regime] = {
                    'count': len(regime_records),
                    'success_rate': sum(1 for r in regime_records if r['success']) / len(regime_records),
                    'avg_return': sum(r['actual_return'] for r in regime_records) / len(regime_records),
                }

        return {
            'total_trades': total,
            'success_rate': successes / total,
            'average_return': round(avg_return, 2),
            'regime_stats': regime_stats,
        }

    def save_weights(self):
        """최적화된 가중치 저장"""
        self.WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'base_weights': self.BASE_WEIGHTS,
            'cached_weights': self._cached_weights,
            'performance_history': self._performance_history[-50:],  # 최근 50건만 저장
            'updated_at': datetime.now().isoformat(),
        }

        with open(self.WEIGHTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Weights saved to {self.WEIGHTS_FILE}")

    def _load_weights(self):
        """저장된 가중치 로드"""
        if not self.WEIGHTS_FILE.exists():
            return

        try:
            with open(self.WEIGHTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._cached_weights = data.get('cached_weights', {})
            self._performance_history = data.get('performance_history', [])

            self.logger.info(f"Weights loaded from {self.WEIGHTS_FILE}")

        except Exception as e:
            self.logger.warning(f"Failed to load weights: {e}")


# Singleton instance
_optimizer_instance: Optional[DynamicWeightOptimizer] = None


def get_dynamic_weight_optimizer() -> DynamicWeightOptimizer:
    """Get singleton DynamicWeightOptimizer instance"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = DynamicWeightOptimizer()
    return _optimizer_instance


# Convenience function
async def get_optimized_weights(
    regime: str,
    market_data: Optional[Dict[str, Any]] = None
) -> WeightAdjustment:
    """최적화된 가중치 조회 편의 함수"""
    optimizer = get_dynamic_weight_optimizer()
    return await optimizer.get_optimized_weights(regime, market_data)
