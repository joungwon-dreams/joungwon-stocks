"""
PROJECT AEGIS - Risk Management Module
=======================================
Capital protection through position sizing and circuit breakers
"""

from .manager import RiskManager, RiskConfig
from .circuit_breaker import CircuitBreaker, TradingHaltedException

__all__ = [
    'RiskManager',
    'RiskConfig',
    'CircuitBreaker',
    'TradingHaltedException',
]
