"""
AEGIS Discovery Module - Phase 9 & 9.5
AI-powered new stock discovery system (AI Sniper)

Components:
- MarketScanner: Pre-filter universe to candidate list
- OpportunityFinder: Deep analysis with InformationFusionEngine
- RecommendationTracker: Track and verify recommendations (Phase 9.5)
- InvestmentReporter: AI-powered detailed investment reports (Phase 9.5)
"""

from .scanner import MarketScanner, CandidateStock
from .finder import OpportunityFinder, DiscoveryResult, get_opportunity_finder
from .tracker import RecommendationTracker, get_recommendation_tracker
from .reporter import InvestmentReporter, InvestmentReport

__all__ = [
    'MarketScanner',
    'CandidateStock',
    'OpportunityFinder',
    'DiscoveryResult',
    'get_opportunity_finder',
    'RecommendationTracker',
    'get_recommendation_tracker',
    'InvestmentReporter',
    'InvestmentReport',
]
