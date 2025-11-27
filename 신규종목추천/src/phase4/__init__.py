"""
Phase 4: 성과 추적 및 AI 회고

이 모듈은 추천 종목의 사후 성과를 추적하고,
실패한 추천에서 AI가 스스로 학습하는 회고 기능을 제공합니다.

Components:
- ProfitTracker: 수익률 추적기 (7일, 14일, 30일 성과 측정)
- AIRetrospective: AI 회고 분석기 (실패 원인 분석 및 학습)
- IncrementalRunner: 증분 재분석 (기존 기능)
"""
from .feedback_runner import IncrementalRunner
from .profit_tracker import ProfitTracker
from .retrospective import AIRetrospective

__all__ = ['IncrementalRunner', 'ProfitTracker', 'AIRetrospective']
