"""
PROJECT AEGIS - Strategy Orchestrator
======================================
Ensemble engine that blends multiple strategy signals based on market regime
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..analysis.backtest.strategy import StrategyInterface, OrderType, Position
from .regime import MarketRegime, MarketRegimeClassifier, RegimeResult
from .registry import StrategyRegistry


@dataclass
class EnsembleSignal:
    """Ensemble Signal Result"""
    signal: OrderType
    score: float              # Weighted average score (-1 to +1)
    regime: MarketRegime
    regime_confidence: float
    strategy_votes: Dict[str, OrderType]
    strategy_scores: Dict[str, float]


class StrategyOrchestrator(StrategyInterface):
    """
    Strategy Orchestrator - Ensemble of multiple strategies

    Features:
    - Market regime detection
    - Weighted signal aggregation
    - Adaptive strategy blending

    Logic:
    1. Detect current market regime (BULL/BEAR/SIDEWAY)
    2. Get signals from all enabled strategies
    3. Apply regime-specific weights to each signal
    4. Aggregate weighted signals to final decision

    Usage:
        orchestrator = StrategyOrchestrator()
        orchestrator.add_strategy("swing", SwingStrategy(), preferred_regimes=[MarketRegime.BULL])
        orchestrator.add_strategy("mean_reversion", MeanReversionStrategy(), preferred_regimes=[MarketRegime.SIDEWAY])

        signal = orchestrator.calculate_signal(df, index)
    """

    def __init__(
        self,
        buy_threshold: float = 0.3,     # Weighted score > 0.3 = BUY
        sell_threshold: float = -0.3,   # Weighted score < -0.3 = SELL
        min_agreement: float = 0.5      # At least 50% strategies must agree
    ):
        super().__init__("AEGIS Orchestrator")
        self.registry = StrategyRegistry()
        self.regime_classifier = MarketRegimeClassifier()
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_agreement = min_agreement
        self._current_regime: Optional[RegimeResult] = None

    def add_strategy(
        self,
        name: str,
        strategy: StrategyInterface,
        weight: float = 1.0,
        preferred_regimes: Optional[List[MarketRegime]] = None
    ) -> None:
        """Add a strategy to the ensemble"""
        self.registry.register(
            name=name,
            strategy=strategy,
            default_weight=weight,
            preferred_regimes=preferred_regimes,
            enabled=True
        )

    def remove_strategy(self, name: str) -> bool:
        """Remove a strategy from the ensemble"""
        return self.registry.unregister(name)

    def set_regime_weight(self, strategy_name: str, regime: MarketRegime, weight: float) -> bool:
        """Set strategy weight for a specific regime"""
        return self.registry.set_weight(strategy_name, regime, weight)

    def get_market_regime(self, df: pd.DataFrame) -> RegimeResult:
        """Get current market regime"""
        return self.regime_classifier.classify(df)

    def _signal_to_score(self, signal: OrderType) -> float:
        """Convert OrderType to numeric score"""
        if signal == OrderType.BUY:
            return 1.0
        elif signal == OrderType.SELL:
            return -1.0
        else:
            return 0.0

    def _score_to_signal(self, score: float) -> OrderType:
        """Convert numeric score to OrderType"""
        if score >= self.buy_threshold:
            return OrderType.BUY
        elif score <= self.sell_threshold:
            return OrderType.SELL
        else:
            return OrderType.HOLD

    def aggregate_signals(
        self,
        df: pd.DataFrame,
        index: int,
        regime: MarketRegime
    ) -> EnsembleSignal:
        """
        Aggregate signals from all strategies

        Returns:
            EnsembleSignal with weighted average decision
        """
        strategies = self.registry.get_strategies_for_regime(regime, enabled_only=True)

        if not strategies:
            return EnsembleSignal(
                signal=OrderType.HOLD,
                score=0.0,
                regime=regime,
                regime_confidence=0.0,
                strategy_votes={},
                strategy_scores={}
            )

        total_weight = 0.0
        weighted_score = 0.0
        votes: Dict[str, OrderType] = {}
        scores: Dict[str, float] = {}

        for name, strategy, weight in strategies:
            # Sync position state
            strategy.position = self.position

            # Get signal from strategy
            signal = strategy.calculate_signal(df, index)
            score = self._signal_to_score(signal)

            votes[name] = signal
            scores[name] = score

            weighted_score += score * weight
            total_weight += weight

        # Calculate weighted average
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0

        # Check agreement ratio
        buy_count = sum(1 for s in votes.values() if s == OrderType.BUY)
        sell_count = sum(1 for s in votes.values() if s == OrderType.SELL)
        total_votes = len(votes)

        if total_votes > 0:
            buy_ratio = buy_count / total_votes
            sell_ratio = sell_count / total_votes
        else:
            buy_ratio = sell_ratio = 0.0

        # Determine final signal
        final_signal = self._score_to_signal(final_score)

        # Apply agreement filter
        if final_signal == OrderType.BUY and buy_ratio < self.min_agreement:
            final_signal = OrderType.HOLD
        elif final_signal == OrderType.SELL and sell_ratio < self.min_agreement:
            final_signal = OrderType.HOLD

        # If we have position, only allow SELL signals
        if self.position is not None and final_signal == OrderType.BUY:
            final_signal = OrderType.HOLD

        # If no position, only allow BUY signals
        if self.position is None and final_signal == OrderType.SELL:
            final_signal = OrderType.HOLD

        return EnsembleSignal(
            signal=final_signal,
            score=final_score,
            regime=regime,
            regime_confidence=self._current_regime.confidence if self._current_regime else 0.0,
            strategy_votes=votes,
            strategy_scores=scores
        )

    def calculate_signal(self, df: pd.DataFrame, index: int) -> OrderType:
        """
        Calculate ensemble signal (StrategyInterface implementation)

        Steps:
        1. Detect market regime
        2. Get weighted signals from all strategies
        3. Return aggregated decision
        """
        # Get market regime
        df_slice = df.iloc[:index+1]
        self._current_regime = self.get_market_regime(df_slice)

        # Aggregate signals
        ensemble = self.aggregate_signals(df, index, self._current_regime.regime)

        return ensemble.signal

    def calculate_quantity(self, capital: float, price: float, signal: OrderType) -> int:
        """Calculate position size (uses 20% of capital)"""
        if signal == OrderType.BUY:
            return int((capital * 0.2) / price)
        elif signal == OrderType.SELL and self.position:
            return self.position.quantity
        return 0

    def get_detailed_signal(self, df: pd.DataFrame, index: int) -> EnsembleSignal:
        """
        Get detailed ensemble signal with all strategy votes

        Use this for debugging or display purposes
        """
        df_slice = df.iloc[:index+1]
        self._current_regime = self.get_market_regime(df_slice)
        return self.aggregate_signals(df, index, self._current_regime.regime)

    def print_status(self):
        """Print current orchestrator status"""
        print("\n" + "=" * 50)
        print("  AEGIS Strategy Orchestrator Status")
        print("=" * 50)
        print(f"\nRegistered Strategies: {len(self.registry)}")

        for name, config in self.registry.list_strategies().items():
            status = "✅" if config['enabled'] else "❌"
            print(f"  {status} {name}")
            print(f"      Weight: {config['default_weight']}")
            print(f"      Preferred: {config['preferred_regimes']}")

        if self._current_regime:
            print(f"\nCurrent Regime: {self._current_regime.regime.value}")
            print(f"  Confidence: {self._current_regime.confidence:.0%}")

        print("=" * 50 + "\n")
