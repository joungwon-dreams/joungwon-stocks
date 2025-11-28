"""
AEGIS Real-World Optimization Module - Phase 6
실전 강화 및 시스템 최적화

Components:
- FinalSignalValidator: Veto System (과락/Hard Cutoff)
- DataIntegrityManager: 데이터 무결성 및 Failover
- ExecutionSimulator: 현실적 수익 계산 (슬리피지, 세금)
"""

from .validator import (
    FinalSignalValidator,
    get_signal_validator,
    ValidationResult,
    ValidationDecision,
)

from .integrity import (
    DataIntegrityManager,
    get_integrity_manager,
    DataSource,
    DataStatus,
)

from .simulator import (
    ExecutionSimulator,
    get_execution_simulator,
    ExecutionResult,
    TimeSegment,
)

__all__ = [
    # Validator
    'FinalSignalValidator',
    'get_signal_validator',
    'ValidationResult',
    'ValidationDecision',

    # Integrity
    'DataIntegrityManager',
    'get_integrity_manager',
    'DataSource',
    'DataStatus',

    # Simulator
    'ExecutionSimulator',
    'get_execution_simulator',
    'ExecutionResult',
    'TimeSegment',
]
