"""
AEGIS Verification Package - Phase 7
신호 검증 및 자기 진화 시스템

Components:
- SignalTraceManager: 신호별 수익률 실시간 추적
- VerificationDashboard: 승률 히트맵 및 성과 시각화
"""

from .tracer import SignalTraceManager, get_signal_tracer
from .dashboard import VerificationDashboard, get_verification_dashboard

__all__ = [
    'SignalTraceManager',
    'get_signal_tracer',
    'VerificationDashboard',
    'get_verification_dashboard'
]
