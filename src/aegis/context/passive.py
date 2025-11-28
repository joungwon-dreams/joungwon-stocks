"""
Passive Fund Tracker - Phase 5.0
지수 편입/편출 이벤트 추적

핵심 기능:
- MSCI Korea Index 리밸런싱 추적
- KOSPI200 정기변경 추적
- 지수 편입 예상 종목 매수 전략 지원
"""
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class IndexType(Enum):
    """지수 유형"""
    MSCI_KOREA = "msci_korea"
    KOSPI200 = "kospi200"
    KOSPI100 = "kospi100"
    KRX300 = "krx300"
    KOSDAQ150 = "kosdaq150"


class RebalanceAction(Enum):
    """리밸런싱 액션"""
    ADD = "add"           # 신규 편입
    DELETE = "delete"     # 편출
    WEIGHT_UP = "weight_up"    # 비중 확대
    WEIGHT_DOWN = "weight_down"  # 비중 축소


@dataclass
class RebalanceEvent:
    """리밸런싱 이벤트"""
    index_type: IndexType
    stock_code: str
    stock_name: str
    action: RebalanceAction
    announcement_date: date  # 발표일
    effective_date: date     # 시행일
    estimated_flow: Optional[float]  # 예상 자금 유입/유출 (억원)
    confidence: float  # 예측 신뢰도 (0-1)
    source: str  # 정보 출처


@dataclass
class PassiveFlowResult:
    """패시브 자금 흐름 분석 결과"""
    # 이벤트 목록
    upcoming_additions: List[RebalanceEvent]
    upcoming_deletions: List[RebalanceEvent]
    recent_changes: List[RebalanceEvent]

    # 현재 종목 분석
    stock_in_major_index: bool
    estimated_passive_weight: float  # 예상 패시브 비중

    # 다음 리밸런싱
    next_rebalance_date: Optional[date]
    days_until_rebalance: Optional[int]

    # 메타데이터
    analyzed_at: str


class PassiveFundTracker:
    """
    패시브 자금 추적기

    Phase 5.0 Spec:
    - MSCI/KOSPI200 편입/편출 이벤트 추적
    - 패시브 자금 흐름 예측
    - 편입 2주 전 매수 전략 지원
    """

    # MSCI 리밸런싱 일정 (2025년)
    # 분기: 2월, 5월, 8월, 11월 말 발표 → 다음 달 첫 영업일 시행
    MSCI_SCHEDULE = {
        2025: [
            (date(2025, 2, 28), date(2025, 3, 3)),   # Q1
            (date(2025, 5, 30), date(2025, 6, 2)),   # Q2
            (date(2025, 8, 29), date(2025, 9, 1)),   # Q3
            (date(2025, 11, 28), date(2025, 12, 1)), # Q4
        ]
    }

    # KOSPI200 정기변경 일정 (연 2회: 6월, 12월)
    KOSPI200_SCHEDULE = {
        2025: [
            (date(2025, 6, 10), date(2025, 6, 13)),   # 상반기
            (date(2025, 12, 10), date(2025, 12, 15)), # 하반기
        ]
    }

    # KOSPI200 편입 시 예상 패시브 자금 (억원, 시가총액 1조원당)
    PASSIVE_FLOW_ESTIMATE = {
        IndexType.KOSPI200: 500,   # 약 500억원
        IndexType.MSCI_KOREA: 800,  # 약 800억원
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # 예상 편입/편출 종목 (실제로는 외부 데이터 필요)
        self._predicted_changes: List[RebalanceEvent] = []

    async def analyze(self, stock_code: Optional[str] = None) -> PassiveFlowResult:
        """
        패시브 자금 흐름 분석

        Args:
            stock_code: 특정 종목 코드 (없으면 전체)

        Returns:
            PassiveFlowResult: 분석 결과
        """
        self.logger.info(f"Analyzing passive fund flow for {stock_code or 'all'}")

        today = date.today()

        # 1. 예정된 변경 이벤트 조회
        all_events = self._get_predicted_changes()

        upcoming_additions = [
            e for e in all_events
            if e.action == RebalanceAction.ADD and e.effective_date > today
        ]

        upcoming_deletions = [
            e for e in all_events
            if e.action == RebalanceAction.DELETE and e.effective_date > today
        ]

        recent_changes = [
            e for e in all_events
            if e.effective_date <= today and e.effective_date >= today - timedelta(days=30)
        ]

        # 2. 특정 종목 분석
        stock_in_index = False
        passive_weight = 0.0

        if stock_code:
            stock_in_index = self._check_stock_in_major_index(stock_code)
            passive_weight = self._estimate_passive_weight(stock_code)

        # 3. 다음 리밸런싱 일정
        next_rebalance, days_until = self._get_next_rebalance_date()

        return PassiveFlowResult(
            upcoming_additions=upcoming_additions,
            upcoming_deletions=upcoming_deletions,
            recent_changes=recent_changes,
            stock_in_major_index=stock_in_index,
            estimated_passive_weight=passive_weight,
            next_rebalance_date=next_rebalance,
            days_until_rebalance=days_until,
            analyzed_at=datetime.now().isoformat()
        )

    def _get_predicted_changes(self) -> List[RebalanceEvent]:
        """
        예상 편입/편출 종목 반환

        Note: 실제로는 증권사 리포트, KRX 데이터 등 필요
        여기서는 샘플 데이터
        """
        # 저장된 예측 데이터 반환
        if self._predicted_changes:
            return self._predicted_changes

        # 샘플 데이터 (실제 구현 시 외부 데이터 연동)
        current_year = datetime.now().year

        sample_events = [
            # KOSPI200 예상 편입 (예시)
            RebalanceEvent(
                index_type=IndexType.KOSPI200,
                stock_code="SAMPLE1",
                stock_name="예시종목1",
                action=RebalanceAction.ADD,
                announcement_date=date(current_year, 6, 10),
                effective_date=date(current_year, 6, 13),
                estimated_flow=500.0,
                confidence=0.7,
                source="시가총액/거래대금 분석"
            ),
        ]

        return sample_events

    def _check_stock_in_major_index(self, stock_code: str) -> bool:
        """주요 지수 편입 여부 확인"""
        # KOSPI200 구성종목 (주요 종목만 샘플)
        kospi200_major = {
            '005930',  # 삼성전자
            '000660',  # SK하이닉스
            '035420',  # NAVER
            '035720',  # 카카오
            '005380',  # 현대차
            '000270',  # 기아
            '068270',  # 셀트리온
            '051910',  # LG화학
            '006400',  # 삼성SDI
            '015760',  # 한국전력
            '055550',  # 신한지주
            '105560',  # KB금융
            '086790',  # 하나금융지주
            '316140',  # 우리금융지주
        }

        return stock_code in kospi200_major

    def _estimate_passive_weight(self, stock_code: str) -> float:
        """
        패시브 비중 추정

        Note: 실제로는 각 지수별 비중 데이터 필요
        """
        # 대형주일수록 패시브 비중 높음 (추정)
        major_stocks = {
            '005930': 15.0,  # 삼성전자
            '000660': 5.0,   # SK하이닉스
            '035420': 2.5,   # NAVER
            '035720': 1.5,   # 카카오
            '015760': 1.0,   # 한국전력
            '316140': 0.8,   # 우리금융지주
        }

        return major_stocks.get(stock_code, 0.0)

    def _get_next_rebalance_date(self) -> Tuple[Optional[date], Optional[int]]:
        """다음 리밸런싱 일정 조회"""
        today = date.today()
        current_year = today.year

        # KOSPI200, MSCI 일정 합치기
        all_dates = []

        if current_year in self.KOSPI200_SCHEDULE:
            for announce, effective in self.KOSPI200_SCHEDULE[current_year]:
                all_dates.append(effective)

        if current_year in self.MSCI_SCHEDULE:
            for announce, effective in self.MSCI_SCHEDULE[current_year]:
                all_dates.append(effective)

        # 미래 일정만 필터
        future_dates = [d for d in all_dates if d > today]

        if future_dates:
            next_date = min(future_dates)
            days_until = (next_date - today).days
            return next_date, days_until

        return None, None

    def add_predicted_change(self, event: RebalanceEvent):
        """예상 편입/편출 추가"""
        self._predicted_changes.append(event)
        self.logger.info(f"Added predicted change: {event.stock_name} {event.action.value}")

    def get_buy_candidates(self, days_before: int = 14) -> List[RebalanceEvent]:
        """
        편입 예정 종목 중 매수 후보 반환

        Args:
            days_before: 시행일 몇 일 전부터 매수 대상으로 볼지

        Returns:
            매수 후보 이벤트 목록
        """
        today = date.today()
        events = self._get_predicted_changes()

        candidates = []
        for event in events:
            if event.action != RebalanceAction.ADD:
                continue

            days_until = (event.effective_date - today).days

            # 시행일 2주 전부터 시행일까지 매수 대상
            if 0 < days_until <= days_before:
                candidates.append(event)

        return candidates

    def get_sell_candidates(self, days_before: int = 7) -> List[RebalanceEvent]:
        """
        편출 예정 종목 중 매도 후보 반환

        Args:
            days_before: 시행일 몇 일 전부터 매도 대상으로 볼지

        Returns:
            매도 후보 이벤트 목록
        """
        today = date.today()
        events = self._get_predicted_changes()

        candidates = []
        for event in events:
            if event.action != RebalanceAction.DELETE:
                continue

            days_until = (event.effective_date - today).days

            # 시행일 1주 전부터 시행일까지 매도 대상
            if 0 < days_until <= days_before:
                candidates.append(event)

        return candidates


# Singleton instance
_tracker_instance: Optional[PassiveFundTracker] = None


def get_passive_tracker() -> PassiveFundTracker:
    """Get singleton PassiveFundTracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = PassiveFundTracker()
    return _tracker_instance


# Convenience function
async def analyze_passive_flow(stock_code: Optional[str] = None) -> PassiveFlowResult:
    """패시브 자금 흐름 분석 편의 함수"""
    tracker = get_passive_tracker()
    return await tracker.analyze(stock_code)
