"""
AEGIS Optimization Module - Phase 6
Ensemble Optimization & Real-World Reinforcement

Components:
- WeightOptimizer: Grid search로 최적 가중치 탐색
- RobustnessTester: 다양한 종목/기간에 대한 강건성 검증
- DynamicWeightOptimizer: 실시간 시장 변동성 기반 가중치 조정 (Phase 4)
- real_world: 실전 강화 모듈 (Phase 6)
  - FinalSignalValidator: Veto System
  - DataIntegrityManager: NQ 선물 연동
  - ExecutionSimulator: 슬리피지/세금 반영
"""

from .weight_optimizer import WeightOptimizer
from .robustness_tester import RobustnessTester
from .dynamic_weight_optimizer import (
    DynamicWeightOptimizer,
    get_dynamic_weight_optimizer,
    get_optimized_weights,
    WeightAdjustment,
    MarketVolatility,
)

# Phase 6: Real-World Optimization
from .real_world import (
    FinalSignalValidator,
    get_signal_validator,
    ValidationResult,
    ValidationDecision,
    DataIntegrityManager,
    get_integrity_manager,
    ExecutionSimulator,
    get_execution_simulator,
    TimeSegment,
)

__all__ = [
    # Phase 4
    'WeightOptimizer',
    'RobustnessTester',
    'DynamicWeightOptimizer',
    'get_dynamic_weight_optimizer',
    'get_optimized_weights',
    'WeightAdjustment',
    'MarketVolatility',

    # Phase 6: Real-World
    'FinalSignalValidator',
    'get_signal_validator',
    'ValidationResult',
    'ValidationDecision',
    'DataIntegrityManager',
    'get_integrity_manager',
    'ExecutionSimulator',
    'get_execution_simulator',
    'TimeSegment',
]
