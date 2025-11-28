"""
PROJECT AEGIS - Multi-Strategy Ensemble Module
===============================================
Adaptive trading through market regime detection and strategy blending
"""

from .regime import MarketRegime, MarketRegimeClassifier
from .registry import StrategyRegistry
from .orchestrator import StrategyOrchestrator

__all__ = [
    'MarketRegime',
    'MarketRegimeClassifier',
    'StrategyRegistry',
    'StrategyOrchestrator',
]
