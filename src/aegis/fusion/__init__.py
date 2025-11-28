"""
AEGIS Fusion Module - Phase 4.5
Multi-modal Information Fusion for Investment Decision

Components:
- DisclosureAnalyzer: DART 공시 분석
- SupplyDemandAnalyzer: 외국인/기관 수급 분석
- FundamentalIntegrator: 재무 건전성 필터
- NewsSentimentAnalyzer: 뉴스 감성 분석 (Gemini AI)
- ConsensusMomentumAnalyzer: 증권사 목표가 추세 분석
- InformationFusionEngine: 종합 점수 계산 (8요소 융합)
- Global Macro Integration: 미국-한국 커플링 분석 (Phase 4.5)
"""

from .disclosure import DisclosureAnalyzer, analyze_disclosure
from .supply import SupplyDemandAnalyzer, analyze_supply_demand
from .fundamental import FundamentalIntegrator, analyze_fundamental
from .news_sentiment import NewsSentimentAnalyzer, analyze_news_sentiment, NewsSentiment
from .consensus import ConsensusMomentumAnalyzer, analyze_consensus_momentum, ConsensusTrend
from .engine import InformationFusionEngine, AegisSignal, get_aegis_signal, get_fusion_engine, FusionResult

__all__ = [
    # Analyzers
    'DisclosureAnalyzer',
    'SupplyDemandAnalyzer',
    'FundamentalIntegrator',
    'NewsSentimentAnalyzer',
    'ConsensusMomentumAnalyzer',
    # Engine
    'InformationFusionEngine',
    'FusionResult',
    # Enums
    'AegisSignal',
    'NewsSentiment',
    'ConsensusTrend',
    # Convenience functions
    'get_aegis_signal',
    'get_fusion_engine',
    'analyze_disclosure',
    'analyze_supply_demand',
    'analyze_fundamental',
    'analyze_news_sentiment',
    'analyze_consensus_momentum',
]
