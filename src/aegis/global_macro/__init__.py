"""
AEGIS Global Macro Module - Phase 4.5
글로벌 시장 분석 및 커플링 전략

Components:
- GlobalMarketFetcher: 미국 시장 데이터 수집 (yfinance)
- CouplingAnalyzer: 미국-한국 종목 커플링 분석
"""

from .fetcher import GlobalMarketFetcher, get_global_market_fetcher
from .coupling import CouplingAnalyzer, get_coupling_analyzer, CouplingResult

__all__ = [
    'GlobalMarketFetcher',
    'get_global_market_fetcher',
    'CouplingAnalyzer',
    'get_coupling_analyzer',
    'CouplingResult',
]
