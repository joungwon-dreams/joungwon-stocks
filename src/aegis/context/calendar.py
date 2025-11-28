"""
Macro Calendar Fetcher - Phase 5.0
경제 일정 및 이벤트 추적

핵심 기능:
- FOMC, CPI, 고용지표 등 미국 경제 일정 추적
- 네 마녀의 날 (Quadruple Witching) 감지
- 한국 경제 일정 (금통위, 수출입 통계)
- D-Day 기반 리스크 경고
"""
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import calendar


class EventImpact(Enum):
    """이벤트 영향도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # 시장 방향 결정적


class EventCategory(Enum):
    """이벤트 카테고리"""
    FOMC = "fomc"                    # 연준 금리결정
    INFLATION = "inflation"          # 물가지표 (CPI, PPI)
    EMPLOYMENT = "employment"        # 고용지표
    EARNINGS = "earnings"            # 실적시즌
    OPTIONS = "options"              # 옵션만기
    KOREA_MACRO = "korea_macro"      # 한국 경제지표
    OTHER = "other"


@dataclass
class EconomicEvent:
    """경제 이벤트"""
    name: str
    date: date
    category: EventCategory
    impact: EventImpact
    country: str  # "US" / "KR" / "GLOBAL"
    description: str
    d_day: int  # D-Day (0=오늘, -1=어제, 1=내일)


@dataclass
class CalendarResult:
    """캘린더 분석 결과"""
    # 이벤트 목록
    upcoming_events: List[EconomicEvent]
    today_events: List[EconomicEvent]
    past_week_events: List[EconomicEvent]

    # 리스크 평가
    risk_level: str  # "low" / "medium" / "high" / "critical"
    risk_score: float  # 0.0 ~ 1.0

    # 조정
    position_adjustment: float  # 포지션 조정 계수 (0.5 ~ 1.0)
    should_reduce_exposure: bool
    warning_message: Optional[str]

    # 메타데이터
    analyzed_at: str


class MacroCalendarFetcher:
    """
    경제 일정 추적기

    Phase 5.0 Spec:
    - 주요 경제 일정 추적 및 D-Day 계산
    - 고영향 이벤트 당일/전일 리스크 경고
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._event_cache: Optional[Tuple[List[EconomicEvent], datetime]] = None
        self._cache_ttl = timedelta(hours=6)

    async def analyze(self, days_ahead: int = 14) -> CalendarResult:
        """
        경제 일정 분석

        Args:
            days_ahead: 조회할 미래 일수

        Returns:
            CalendarResult: 캘린더 분석 결과
        """
        self.logger.info("Analyzing macro calendar...")

        # 1. 이벤트 목록 조회
        all_events = self._get_scheduled_events()

        today = date.today()

        # 2. D-Day 계산 및 분류
        upcoming_events = []
        today_events = []
        past_week_events = []

        for event in all_events:
            d_day = (event.date - today).days
            event.d_day = d_day

            if d_day == 0:
                today_events.append(event)
            elif 0 < d_day <= days_ahead:
                upcoming_events.append(event)
            elif -7 <= d_day < 0:
                past_week_events.append(event)

        # 날짜순 정렬
        upcoming_events.sort(key=lambda e: e.date)

        # 3. 리스크 평가
        risk_level, risk_score = self._evaluate_risk(today_events, upcoming_events)

        # 4. 포지션 조정 계산
        adjustment, should_reduce, warning = self._calculate_adjustments(
            risk_level, today_events, upcoming_events
        )

        return CalendarResult(
            upcoming_events=upcoming_events,
            today_events=today_events,
            past_week_events=past_week_events,
            risk_level=risk_level,
            risk_score=risk_score,
            position_adjustment=adjustment,
            should_reduce_exposure=should_reduce,
            warning_message=warning,
            analyzed_at=datetime.now().isoformat()
        )

    def _get_scheduled_events(self) -> List[EconomicEvent]:
        """
        예정된 경제 일정 반환

        Note: 실제로는 외부 API/크롤링 필요
        여기서는 2025년 주요 일정을 하드코딩
        """
        events = []
        current_year = datetime.now().year

        # ===== FOMC 일정 (2025년) =====
        fomc_dates = [
            (1, 29),   # 1월
            (3, 19),   # 3월
            (5, 7),    # 5월
            (6, 18),   # 6월
            (7, 30),   # 7월
            (9, 17),   # 9월
            (11, 5),   # 11월
            (12, 17),  # 12월
        ]
        for month, day in fomc_dates:
            events.append(EconomicEvent(
                name="FOMC 금리결정",
                date=date(current_year, month, day),
                category=EventCategory.FOMC,
                impact=EventImpact.CRITICAL,
                country="US",
                description="연준 기준금리 결정 및 경제전망 발표",
                d_day=0
            ))

        # ===== CPI 발표일 (매월 둘째 주 화/수요일) =====
        for month in range(1, 13):
            # 둘째 주 화요일/수요일 추정 (10~14일)
            cpi_day = 12 if month % 2 == 0 else 13
            try:
                events.append(EconomicEvent(
                    name=f"미국 CPI ({month}월)",
                    date=date(current_year, month, cpi_day),
                    category=EventCategory.INFLATION,
                    impact=EventImpact.HIGH,
                    country="US",
                    description="소비자물가지수 발표",
                    d_day=0
                ))
            except ValueError:
                pass

        # ===== 고용보고서 (매월 첫째 금요일) =====
        for month in range(1, 13):
            # 첫째 금요일 계산
            c = calendar.Calendar()
            fridays = [d for d in c.itermonthdays2(current_year, month)
                      if d[0] != 0 and d[1] == 4]  # 금요일
            if fridays:
                first_friday = fridays[0][0]
                events.append(EconomicEvent(
                    name=f"미국 고용보고서 ({month}월)",
                    date=date(current_year, month, first_friday),
                    category=EventCategory.EMPLOYMENT,
                    impact=EventImpact.HIGH,
                    country="US",
                    description="비농업 고용 및 실업률 발표",
                    d_day=0
                ))

        # ===== 네 마녀의 날 (분기별 셋째 금요일) =====
        witching_months = [3, 6, 9, 12]
        for month in witching_months:
            c = calendar.Calendar()
            fridays = [d for d in c.itermonthdays2(current_year, month)
                      if d[0] != 0 and d[1] == 4]
            if len(fridays) >= 3:
                third_friday = fridays[2][0]
                events.append(EconomicEvent(
                    name=f"네 마녀의 날 (Q{month//3})",
                    date=date(current_year, month, third_friday),
                    category=EventCategory.OPTIONS,
                    impact=EventImpact.HIGH,
                    country="GLOBAL",
                    description="주가지수 선물/옵션, 개별주식 선물/옵션 동시 만기",
                    d_day=0
                ))

        # ===== 한국 금통위 (매월) =====
        # 보통 둘째 주 목요일
        for month in range(1, 13):
            bok_day = 11 if month % 2 == 1 else 13
            try:
                events.append(EconomicEvent(
                    name=f"한국 금통위 ({month}월)",
                    date=date(current_year, month, bok_day),
                    category=EventCategory.KOREA_MACRO,
                    impact=EventImpact.MEDIUM,
                    country="KR",
                    description="한국은행 기준금리 결정",
                    d_day=0
                ))
            except ValueError:
                pass

        # ===== 실적시즌 =====
        earnings_periods = [
            (1, 15, 2, 15, "Q4 실적시즌"),
            (4, 15, 5, 15, "Q1 실적시즌"),
            (7, 15, 8, 15, "Q2 실적시즌"),
            (10, 15, 11, 15, "Q3 실적시즌"),
        ]
        for start_month, start_day, end_month, end_day, name in earnings_periods:
            events.append(EconomicEvent(
                name=name,
                date=date(current_year, start_month, start_day),
                category=EventCategory.EARNINGS,
                impact=EventImpact.MEDIUM,
                country="US",
                description="미국 주요 기업 실적발표 시즌",
                d_day=0
            ))

        return events

    def _evaluate_risk(
        self,
        today_events: List[EconomicEvent],
        upcoming_events: List[EconomicEvent]
    ) -> Tuple[str, float]:
        """리스크 레벨 평가"""
        risk_score = 0.0

        # 오늘 이벤트 가중치
        for event in today_events:
            if event.impact == EventImpact.CRITICAL:
                risk_score += 0.5
            elif event.impact == EventImpact.HIGH:
                risk_score += 0.3
            elif event.impact == EventImpact.MEDIUM:
                risk_score += 0.1

        # 임박한 고영향 이벤트 (1~2일 내)
        for event in upcoming_events:
            if event.d_day <= 2:
                if event.impact == EventImpact.CRITICAL:
                    risk_score += 0.3
                elif event.impact == EventImpact.HIGH:
                    risk_score += 0.15

        # 레벨 결정
        risk_score = min(1.0, risk_score)

        if risk_score >= 0.7:
            level = "critical"
        elif risk_score >= 0.4:
            level = "high"
        elif risk_score >= 0.2:
            level = "medium"
        else:
            level = "low"

        return level, round(risk_score, 2)

    def _calculate_adjustments(
        self,
        risk_level: str,
        today_events: List[EconomicEvent],
        upcoming_events: List[EconomicEvent]
    ) -> Tuple[float, bool, Optional[str]]:
        """포지션 조정 계산"""
        # 기본 조정
        adjustments = {
            "critical": (0.5, True),
            "high": (0.7, True),
            "medium": (0.9, False),
            "low": (1.0, False),
        }

        position_adj, should_reduce = adjustments.get(risk_level, (1.0, False))
        warning = None

        # 특정 이벤트 경고 메시지
        for event in today_events:
            if event.impact == EventImpact.CRITICAL:
                warning = f"⚠️ {event.name} 발표 당일 - 변동성 주의"
                break
            elif event.impact == EventImpact.HIGH:
                warning = f"📅 {event.name} 발표 당일"

        if not warning:
            # 임박한 Critical 이벤트
            for event in upcoming_events:
                if event.d_day == 1 and event.impact == EventImpact.CRITICAL:
                    warning = f"⚠️ 내일 {event.name} - 신규 매수 자제 권고"
                    should_reduce = True
                    position_adj = min(position_adj, 0.7)
                    break

        return position_adj, should_reduce, warning

    def get_next_critical_event(self) -> Optional[EconomicEvent]:
        """다음 Critical 이벤트 조회"""
        events = self._get_scheduled_events()
        today = date.today()

        critical_events = [
            e for e in events
            if e.impact == EventImpact.CRITICAL and e.date >= today
        ]

        if critical_events:
            critical_events.sort(key=lambda e: e.date)
            return critical_events[0]

        return None

    def is_earnings_season(self) -> bool:
        """현재 실적시즌 여부"""
        today = date.today()
        month, day = today.month, today.day

        # 실적시즌: 1/15~2/15, 4/15~5/15, 7/15~8/15, 10/15~11/15
        earnings_windows = [
            (1, 15, 2, 15),
            (4, 15, 5, 15),
            (7, 15, 8, 15),
            (10, 15, 11, 15),
        ]

        for sm, sd, em, ed in earnings_windows:
            start = date(today.year, sm, sd)
            end = date(today.year, em, ed)
            if start <= today <= end:
                return True

        return False

    def days_until_event(self, category: EventCategory) -> Optional[int]:
        """특정 카테고리 이벤트까지 남은 일수"""
        events = self._get_scheduled_events()
        today = date.today()

        category_events = [
            e for e in events
            if e.category == category and e.date >= today
        ]

        if category_events:
            category_events.sort(key=lambda e: e.date)
            return (category_events[0].date - today).days

        return None


# Singleton instance
_calendar_instance: Optional[MacroCalendarFetcher] = None


def get_calendar_fetcher() -> MacroCalendarFetcher:
    """Get singleton MacroCalendarFetcher instance"""
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = MacroCalendarFetcher()
    return _calendar_instance


# Convenience function
async def analyze_calendar(days_ahead: int = 14) -> CalendarResult:
    """경제 캘린더 분석 편의 함수"""
    fetcher = get_calendar_fetcher()
    return await fetcher.analyze(days_ahead)
