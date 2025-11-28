"""
PROJECT AEGIS - Strategy Registry
==================================
Repository pattern for managing multiple trading strategies
"""

from typing import Dict, List, Optional, Type
from dataclasses import dataclass

from ..analysis.backtest.strategy import StrategyInterface
from .regime import MarketRegime


@dataclass
class StrategyConfig:
    """Strategy Configuration"""
    name: str
    strategy: StrategyInterface
    default_weight: float = 1.0
    preferred_regimes: List[MarketRegime] = None  # Regimes where this strategy excels
    enabled: bool = True

    def __post_init__(self):
        if self.preferred_regimes is None:
            self.preferred_regimes = [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAY]


class StrategyRegistry:
    """
    Strategy Registry - Repository for managing trading strategies

    Features:
    - Register/unregister strategies
    - Get strategies by name or regime
    - Enable/disable strategies
    - Configure regime-specific weights

    Usage:
        registry = StrategyRegistry()
        registry.register("swing", SwingStrategy(), preferred_regimes=[MarketRegime.BULL])
        registry.register("mean_reversion", MeanReversionStrategy(), preferred_regimes=[MarketRegime.SIDEWAY])

        # Get all enabled strategies for SIDEWAY market
        strategies = registry.get_strategies_for_regime(MarketRegime.SIDEWAY)
    """

    def __init__(self):
        self._strategies: Dict[str, StrategyConfig] = {}
        self._regime_weights: Dict[MarketRegime, Dict[str, float]] = {
            MarketRegime.BULL: {},
            MarketRegime.BEAR: {},
            MarketRegime.SIDEWAY: {},
        }

    def register(
        self,
        name: str,
        strategy: StrategyInterface,
        default_weight: float = 1.0,
        preferred_regimes: Optional[List[MarketRegime]] = None,
        enabled: bool = True
    ) -> None:
        """Register a new strategy"""
        config = StrategyConfig(
            name=name,
            strategy=strategy,
            default_weight=default_weight,
            preferred_regimes=preferred_regimes,
            enabled=enabled
        )
        self._strategies[name] = config

        # Set default weights per regime
        for regime in MarketRegime:
            if regime in config.preferred_regimes:
                self._regime_weights[regime][name] = default_weight
            else:
                self._regime_weights[regime][name] = default_weight * 0.5  # Reduced weight

    def unregister(self, name: str) -> bool:
        """Unregister a strategy"""
        if name in self._strategies:
            del self._strategies[name]
            for regime in MarketRegime:
                if name in self._regime_weights[regime]:
                    del self._regime_weights[regime][name]
            return True
        return False

    def get(self, name: str) -> Optional[StrategyConfig]:
        """Get strategy by name"""
        return self._strategies.get(name)

    def get_strategy(self, name: str) -> Optional[StrategyInterface]:
        """Get strategy instance by name"""
        config = self._strategies.get(name)
        return config.strategy if config else None

    def enable(self, name: str) -> bool:
        """Enable a strategy"""
        if name in self._strategies:
            self._strategies[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a strategy"""
        if name in self._strategies:
            self._strategies[name].enabled = False
            return True
        return False

    def set_weight(self, name: str, regime: MarketRegime, weight: float) -> bool:
        """Set strategy weight for a specific regime"""
        if name not in self._strategies:
            return False
        self._regime_weights[regime][name] = max(0.0, weight)
        return True

    def get_weight(self, name: str, regime: MarketRegime) -> float:
        """Get strategy weight for a specific regime"""
        return self._regime_weights[regime].get(name, 0.0)

    def get_all_strategies(self, enabled_only: bool = True) -> List[StrategyConfig]:
        """Get all registered strategies"""
        strategies = list(self._strategies.values())
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]
        return strategies

    def get_strategies_for_regime(
        self,
        regime: MarketRegime,
        enabled_only: bool = True
    ) -> List[tuple]:
        """
        Get strategies with weights for a specific regime

        Returns:
            List of (strategy_name, strategy_instance, weight) tuples
        """
        result = []
        for name, config in self._strategies.items():
            if enabled_only and not config.enabled:
                continue
            weight = self._regime_weights[regime].get(name, config.default_weight)
            result.append((name, config.strategy, weight))
        return result

    def list_strategies(self) -> Dict[str, dict]:
        """List all strategies with their configurations"""
        result = {}
        for name, config in self._strategies.items():
            result[name] = {
                'enabled': config.enabled,
                'default_weight': config.default_weight,
                'preferred_regimes': [r.value for r in config.preferred_regimes],
                'weights_by_regime': {
                    r.value: self._regime_weights[r].get(name, 0)
                    for r in MarketRegime
                }
            }
        return result

    def __len__(self) -> int:
        return len(self._strategies)

    def __contains__(self, name: str) -> bool:
        return name in self._strategies
