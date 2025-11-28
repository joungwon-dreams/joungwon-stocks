"""
Weight Optimizer - Phase 3.5
Grid Search를 통한 최적 전략 가중치 탐색

핵심 기능:
- 시장 국면(Regime)별 최적 가중치 탐색
- Sharpe Ratio / Profit Factor 기반 최적화
- 백테스트 연동
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import itertools

import pandas as pd
import numpy as np


class MarketRegime(Enum):
    """시장 국면"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


@dataclass
class OptimizationResult:
    """최적화 결과"""
    regime: MarketRegime
    best_weights: Dict[str, float]
    sharpe_ratio: float
    profit_factor: float
    win_rate: float
    total_return: float
    iterations: int
    optimized_at: str


class WeightOptimizer:
    """
    전략 가중치 최적화기

    Phase 3.5 Spec:
    - Grid Search로 가중치 조합 탐색
    - 각 Regime별 최적 가중치 산출
    - Sharpe Ratio 또는 Profit Factor 최대화
    """

    # 기본 전략 목록
    DEFAULT_STRATEGIES = ['swing', 'mean_reversion', 'trend_following']

    # 가중치 탐색 범위 (10% 단위)
    WEIGHT_STEPS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    def __init__(self, strategies: Optional[List[str]] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strategies = strategies or self.DEFAULT_STRATEGIES
        self._optimal_weights: Dict[MarketRegime, Dict[str, float]] = {}

    def optimize_for_regime(
        self,
        regime: MarketRegime,
        backtest_results: List[Dict[str, Any]],
        metric: str = "sharpe_ratio"
    ) -> OptimizationResult:
        """
        특정 시장 국면에 대한 최적 가중치 탐색

        Args:
            regime: 시장 국면 (BULL, BEAR, SIDEWAYS)
            backtest_results: 백테스트 결과 목록 (각 가중치 조합별)
            metric: 최적화 지표 ("sharpe_ratio" or "profit_factor")

        Returns:
            OptimizationResult: 최적화 결과
        """
        if not backtest_results:
            self.logger.warning(f"No backtest results for {regime.value}")
            return self._empty_result(regime)

        # 최적 결과 찾기
        best_result = None
        best_metric_value = float('-inf')

        for result in backtest_results:
            metric_value = result.get(metric, 0)
            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_result = result

        if not best_result:
            return self._empty_result(regime)

        # 결과 저장
        optimal_weights = best_result.get('weights', {})
        self._optimal_weights[regime] = optimal_weights

        return OptimizationResult(
            regime=regime,
            best_weights=optimal_weights,
            sharpe_ratio=best_result.get('sharpe_ratio', 0),
            profit_factor=best_result.get('profit_factor', 0),
            win_rate=best_result.get('win_rate', 0),
            total_return=best_result.get('total_return', 0),
            iterations=len(backtest_results),
            optimized_at=datetime.now().isoformat()
        )

    def generate_weight_combinations(
        self,
        strategies: Optional[List[str]] = None,
        step: float = 0.1
    ) -> List[Dict[str, float]]:
        """
        가중치 조합 생성 (합계 = 1.0)

        Args:
            strategies: 전략 목록
            step: 가중치 증가 단위

        Returns:
            가중치 조합 목록
        """
        strategies = strategies or self.strategies
        n_strategies = len(strategies)

        if n_strategies == 0:
            return []

        # 가능한 가중치 값
        weights = np.arange(0, 1 + step, step)
        weights = [round(w, 2) for w in weights]

        combinations = []

        # 모든 조합 생성 (합계 = 1.0)
        for combo in itertools.product(weights, repeat=n_strategies):
            if abs(sum(combo) - 1.0) < 0.01:  # 합이 1.0인 경우만
                weight_dict = {
                    strategies[i]: combo[i]
                    for i in range(n_strategies)
                }
                combinations.append(weight_dict)

        self.logger.info(
            f"Generated {len(combinations)} weight combinations "
            f"for {n_strategies} strategies"
        )

        return combinations

    def get_optimal_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """
        특정 국면의 최적 가중치 반환

        Args:
            regime: 시장 국면

        Returns:
            최적 가중치 딕셔너리
        """
        if regime in self._optimal_weights:
            return self._optimal_weights[regime]

        # 기본 가중치 반환
        return self._get_default_weights(regime)

    def get_all_optimal_weights(self) -> Dict[str, Dict[str, float]]:
        """
        모든 국면의 최적 가중치 반환

        Returns:
            {regime_name: {strategy: weight, ...}, ...}
        """
        result = {}
        for regime in MarketRegime:
            weights = self.get_optimal_weights(regime)
            result[regime.value] = weights
        return result

    def set_optimal_weights(
        self,
        regime: MarketRegime,
        weights: Dict[str, float]
    ):
        """
        최적 가중치 수동 설정

        Args:
            regime: 시장 국면
            weights: 가중치 딕셔너리
        """
        # 가중치 합계 검증
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            self.logger.warning(
                f"Weights sum to {total}, normalizing to 1.0"
            )
            weights = {k: v / total for k, v in weights.items()}

        self._optimal_weights[regime] = weights
        self.logger.info(f"Set optimal weights for {regime.value}: {weights}")

    def _get_default_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """
        국면별 기본 가중치

        설계 문서 기준:
        - BULL: TrendFollowing(50%) + Swing(30%) + MeanReversion(20%)
        - SIDEWAYS: MeanReversion(60%) + Swing(30%) + TrendFollowing(10%)
        - BEAR: Defensive weights
        """
        defaults = {
            MarketRegime.BULL: {
                'swing': 0.3,
                'mean_reversion': 0.2,
                'trend_following': 0.5,
            },
            MarketRegime.SIDEWAYS: {
                'swing': 0.3,
                'mean_reversion': 0.6,
                'trend_following': 0.1,
            },
            MarketRegime.BEAR: {
                'swing': 0.2,
                'mean_reversion': 0.5,
                'trend_following': 0.3,
            },
        }
        return defaults.get(regime, {'swing': 0.5, 'mean_reversion': 0.3, 'trend_following': 0.2})

    def _empty_result(self, regime: MarketRegime) -> OptimizationResult:
        """빈 결과 반환"""
        return OptimizationResult(
            regime=regime,
            best_weights=self._get_default_weights(regime),
            sharpe_ratio=0.0,
            profit_factor=0.0,
            win_rate=0.0,
            total_return=0.0,
            iterations=0,
            optimized_at=datetime.now().isoformat()
        )

    def save_weights(self, filepath: str):
        """가중치를 JSON 파일로 저장"""
        import json
        data = {
            regime.value: weights
            for regime, weights in self._optimal_weights.items()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Weights saved to {filepath}")

    def load_weights(self, filepath: str):
        """JSON 파일에서 가중치 로드"""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)

        for regime_name, weights in data.items():
            regime = MarketRegime(regime_name)
            self._optimal_weights[regime] = weights

        self.logger.info(f"Weights loaded from {filepath}")


# Singleton instance
_optimizer_instance: Optional[WeightOptimizer] = None


def get_weight_optimizer() -> WeightOptimizer:
    """Get singleton WeightOptimizer instance"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = WeightOptimizer()
    return _optimizer_instance
