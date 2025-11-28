"""
AEGIS Reporting Module - Phase 10
Unified PDF report generation with WillyDreams Style branding

Components:
- ReportGenerator: Core PDF generation engine with consistent branding
- StyleConfig: Brand colors, fonts, and design tokens
"""

from .pdf_engine import ReportGenerator, StyleConfig

__all__ = [
    'ReportGenerator',
    'StyleConfig',
]
