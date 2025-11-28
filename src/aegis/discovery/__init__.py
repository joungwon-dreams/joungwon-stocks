"""
AEGIS Discovery Module - Phase 9
AI-powered new stock discovery system (AI Sniper)

Components:
- MarketScanner: Pre-filter universe to candidate list
- OpportunityFinder: Deep analysis with InformationFusionEngine
"""

from .scanner import MarketScanner
from .finder import OpportunityFinder

__all__ = [
    'MarketScanner',
    'OpportunityFinder',
]
