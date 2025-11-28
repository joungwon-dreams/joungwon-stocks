"""
AEGIS Context Module - Phase 5.0
시장 컨텍스트 및 캘린더 분석

Components:
- MarketSentimentMeter: VIX, RSI, 신용잔고 기반 시장 심리 측정
- MacroCalendarFetcher: FOMC, CPI, 네 마녀의 날 등 경제 일정 추적
- PassiveFundTracker: MSCI, KOSPI200 지수 편입/편출 추적
- SectorEventMonitor: CES, ASCO 등 섹터별 주요 행사 추적
"""

from .sentiment import (
    MarketSentimentMeter,
    get_sentiment_meter,
    analyze_market_sentiment,
    MarketCondition,
    SentimentLevel,
    SentimentResult,
)

from .calendar import (
    MacroCalendarFetcher,
    get_calendar_fetcher,
    analyze_calendar,
    EventImpact,
    EventCategory,
    EconomicEvent,
    CalendarResult,
)

from .passive import (
    PassiveFundTracker,
    get_passive_tracker,
    analyze_passive_flow,
    IndexType,
    RebalanceAction,
    RebalanceEvent,
    PassiveFlowResult,
)

from .sector import (
    SectorEventMonitor,
    get_sector_monitor,
    analyze_sector_events,
    SectorType,
    EventType,
    SectorEvent,
    SectorAnalysisResult,
)

__all__ = [
    # Sentiment
    'MarketSentimentMeter',
    'get_sentiment_meter',
    'analyze_market_sentiment',
    'MarketCondition',
    'SentimentLevel',
    'SentimentResult',

    # Calendar
    'MacroCalendarFetcher',
    'get_calendar_fetcher',
    'analyze_calendar',
    'EventImpact',
    'EventCategory',
    'EconomicEvent',
    'CalendarResult',

    # Passive Fund
    'PassiveFundTracker',
    'get_passive_tracker',
    'analyze_passive_flow',
    'IndexType',
    'RebalanceAction',
    'RebalanceEvent',
    'PassiveFlowResult',

    # Sector
    'SectorEventMonitor',
    'get_sector_monitor',
    'analyze_sector_events',
    'SectorType',
    'EventType',
    'SectorEvent',
    'SectorAnalysisResult',
]
