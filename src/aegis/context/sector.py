"""
Sector Event Monitor - Phase 5.0
섹터별 주요 이벤트 추적

핵심 기능:
- 글로벌 산업 행사 추적 (CES, ASCO, MWC 등)
- 섹터 테마 부각 시점 예측
- 관련주 매수 타이밍 지원
"""
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class SectorType(Enum):
    """섹터 유형"""
    TECH = "tech"
    SEMICONDUCTOR = "semiconductor"
    BIO_PHARMA = "bio_pharma"
    AUTO_EV = "auto_ev"
    BATTERY = "battery"
    ENERGY = "energy"
    DEFENSE = "defense"
    ENTERTAINMENT = "entertainment"
    FINANCE = "finance"
    RETAIL = "retail"


class EventType(Enum):
    """이벤트 유형"""
    CONFERENCE = "conference"      # 컨퍼런스
    EXHIBITION = "exhibition"      # 전시회
    EARNINGS = "earnings"          # 실적발표
    PRODUCT_LAUNCH = "product"     # 신제품 출시
    REGULATORY = "regulatory"      # 규제/정책
    SEASONAL = "seasonal"          # 계절성 이벤트


@dataclass
class SectorEvent:
    """섹터 이벤트"""
    name: str
    event_type: EventType
    sectors: List[SectorType]
    start_date: date
    end_date: Optional[date]
    location: str
    impact_level: str  # "low" / "medium" / "high"
    related_stocks_kr: List[str]  # 관련 한국 종목 코드
    description: str
    trading_strategy: str  # 매매 전략 힌트


@dataclass
class SectorAnalysisResult:
    """섹터 이벤트 분석 결과"""
    # 이벤트 목록
    upcoming_events: List[SectorEvent]
    active_events: List[SectorEvent]  # 현재 진행 중
    recent_events: List[SectorEvent]

    # 섹터 분석
    hot_sectors: List[SectorType]  # 주목해야 할 섹터
    sector_scores: Dict[str, float]  # 섹터별 관심도 점수

    # 관련 종목
    buy_candidates: List[str]  # 매수 검토 종목

    # 메타데이터
    analyzed_at: str


class SectorEventMonitor:
    """
    섹터 이벤트 모니터

    Phase 5.0 Spec:
    - 글로벌 산업 행사 추적
    - 섹터 테마 부각 타이밍 예측
    - 관련주 매수 전략 지원
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze(self, target_sector: Optional[SectorType] = None) -> SectorAnalysisResult:
        """
        섹터 이벤트 분석

        Args:
            target_sector: 특정 섹터만 분석 (없으면 전체)

        Returns:
            SectorAnalysisResult: 분석 결과
        """
        self.logger.info(f"Analyzing sector events for {target_sector or 'all sectors'}")

        today = date.today()

        # 1. 이벤트 목록 조회
        all_events = self._get_sector_events()

        # 섹터 필터
        if target_sector:
            all_events = [e for e in all_events if target_sector in e.sectors]

        # 2. 이벤트 분류
        upcoming_events = []
        active_events = []
        recent_events = []

        for event in all_events:
            end_date = event.end_date or event.start_date

            if event.start_date > today:
                # 미래 이벤트
                days_until = (event.start_date - today).days
                if days_until <= 60:  # 2개월 내
                    upcoming_events.append(event)
            elif event.start_date <= today <= end_date:
                # 진행 중
                active_events.append(event)
            elif (today - end_date).days <= 14:
                # 최근 종료 (2주 내)
                recent_events.append(event)

        # 날짜순 정렬
        upcoming_events.sort(key=lambda e: e.start_date)

        # 3. Hot 섹터 분석
        hot_sectors, sector_scores = self._analyze_hot_sectors(
            upcoming_events, active_events
        )

        # 4. 매수 후보 종목
        buy_candidates = self._get_buy_candidates(upcoming_events, active_events)

        return SectorAnalysisResult(
            upcoming_events=upcoming_events,
            active_events=active_events,
            recent_events=recent_events,
            hot_sectors=hot_sectors,
            sector_scores=sector_scores,
            buy_candidates=buy_candidates,
            analyzed_at=datetime.now().isoformat()
        )

    def _get_sector_events(self) -> List[SectorEvent]:
        """
        섹터 이벤트 목록 반환

        Note: 실제로는 외부 캘린더 API 연동 필요
        여기서는 2025년 주요 행사 하드코딩
        """
        current_year = datetime.now().year

        events = [
            # ===== 테크/반도체 =====
            SectorEvent(
                name="CES 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.TECH, SectorType.SEMICONDUCTOR, SectorType.AUTO_EV],
                start_date=date(current_year, 1, 7),
                end_date=date(current_year, 1, 10),
                location="Las Vegas, USA",
                impact_level="high",
                related_stocks_kr=['005930', '000660', '035420', '035720'],
                description="세계 최대 가전/IT 전시회",
                trading_strategy="행사 1개월 전부터 관련주 매수 검토, 행사 후 차익실현"
            ),
            SectorEvent(
                name="MWC 2025 (Mobile World Congress)",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.TECH, SectorType.SEMICONDUCTOR],
                start_date=date(current_year, 2, 24),
                end_date=date(current_year, 2, 27),
                location="Barcelona, Spain",
                impact_level="high",
                related_stocks_kr=['005930', '017670', '066570'],
                description="세계 최대 모바일 전시회",
                trading_strategy="5G, 스마트폰 관련주 주목"
            ),
            SectorEvent(
                name="NVIDIA GTC 2025",
                event_type=EventType.CONFERENCE,
                sectors=[SectorType.SEMICONDUCTOR, SectorType.TECH],
                start_date=date(current_year, 3, 17),
                end_date=date(current_year, 3, 21),
                location="San Jose, USA",
                impact_level="high",
                related_stocks_kr=['000660', '005930'],
                description="NVIDIA GPU/AI 기술 컨퍼런스",
                trading_strategy="AI/HBM 관련주 주목, 행사 전후 변동성 주의"
            ),
            SectorEvent(
                name="Computex 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.SEMICONDUCTOR, SectorType.TECH],
                start_date=date(current_year, 6, 3),
                end_date=date(current_year, 6, 6),
                location="Taipei, Taiwan",
                impact_level="medium",
                related_stocks_kr=['000660', '005930'],
                description="아시아 최대 컴퓨터 전시회",
                trading_strategy="PC/서버 관련 반도체주 주목"
            ),

            # ===== 바이오/제약 =====
            SectorEvent(
                name="JP Morgan Healthcare Conference",
                event_type=EventType.CONFERENCE,
                sectors=[SectorType.BIO_PHARMA],
                start_date=date(current_year, 1, 13),
                end_date=date(current_year, 1, 16),
                location="San Francisco, USA",
                impact_level="high",
                related_stocks_kr=['068270', '207940', '326030'],
                description="세계 최대 헬스케어 투자 컨퍼런스",
                trading_strategy="바이오 빅딜 기대, 행사 전 매수 검토"
            ),
            SectorEvent(
                name="ASCO 2025 (미국임상종양학회)",
                event_type=EventType.CONFERENCE,
                sectors=[SectorType.BIO_PHARMA],
                start_date=date(current_year, 5, 30),
                end_date=date(current_year, 6, 3),
                location="Chicago, USA",
                impact_level="high",
                related_stocks_kr=['068270', '207940', '145020'],
                description="세계 최대 항암제 학회",
                trading_strategy="임상 결과 발표 종목 주목"
            ),

            # ===== 자동차/EV/배터리 =====
            SectorEvent(
                name="디트로이트 오토쇼 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.AUTO_EV, SectorType.BATTERY],
                start_date=date(current_year, 1, 11),
                end_date=date(current_year, 1, 20),
                location="Detroit, USA",
                impact_level="medium",
                related_stocks_kr=['005380', '000270', '006400', '373220'],
                description="북미 최대 자동차 전시회",
                trading_strategy="EV 신차 발표 기대"
            ),
            SectorEvent(
                name="IAA Mobility 2025 (뮌헨 모터쇼)",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.AUTO_EV, SectorType.BATTERY],
                start_date=date(current_year, 9, 9),
                end_date=date(current_year, 9, 14),
                location="Munich, Germany",
                impact_level="high",
                related_stocks_kr=['005380', '000270', '006400'],
                description="유럽 최대 자동차 전시회",
                trading_strategy="유럽향 EV 수출 기대 반영"
            ),
            SectorEvent(
                name="InterBattery 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.BATTERY],
                start_date=date(current_year, 3, 5),
                end_date=date(current_year, 3, 7),
                location="Seoul, Korea",
                impact_level="medium",
                related_stocks_kr=['006400', '373220', '247540', '086520'],
                description="한국 배터리 산업 전시회",
                trading_strategy="2차전지 관련주 전반 주목"
            ),

            # ===== 에너지 =====
            SectorEvent(
                name="Solar Power International 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.ENERGY],
                start_date=date(current_year, 9, 15),
                end_date=date(current_year, 9, 18),
                location="Anaheim, USA",
                impact_level="medium",
                related_stocks_kr=['322000', '336260'],
                description="미국 최대 태양광 전시회",
                trading_strategy="태양광/신재생에너지 관련주"
            ),

            # ===== 엔터테인먼트 =====
            SectorEvent(
                name="E3 2025",
                event_type=EventType.EXHIBITION,
                sectors=[SectorType.ENTERTAINMENT, SectorType.TECH],
                start_date=date(current_year, 6, 10),
                end_date=date(current_year, 6, 13),
                location="Los Angeles, USA",
                impact_level="medium",
                related_stocks_kr=['263750', '112040'],
                description="세계 최대 게임 전시회",
                trading_strategy="게임주 신작 기대감"
            ),

            # ===== 계절성 이벤트 =====
            SectorEvent(
                name="블랙프라이데이/사이버먼데이",
                event_type=EventType.SEASONAL,
                sectors=[SectorType.RETAIL, SectorType.TECH],
                start_date=date(current_year, 11, 28),
                end_date=date(current_year, 12, 2),
                location="Global",
                impact_level="high",
                related_stocks_kr=['005930', '035720'],
                description="미국 연말 쇼핑 시즌",
                trading_strategy="소비 관련주, 반도체(수요 증가)"
            ),
            SectorEvent(
                name="중국 광군절 (Singles' Day)",
                event_type=EventType.SEASONAL,
                sectors=[SectorType.RETAIL, SectorType.TECH],
                start_date=date(current_year, 11, 11),
                end_date=date(current_year, 11, 11),
                location="China",
                impact_level="medium",
                related_stocks_kr=['035720', '035420'],
                description="중국 최대 쇼핑 행사",
                trading_strategy="중국향 수출 관련주"
            ),
        ]

        return events

    def _analyze_hot_sectors(
        self,
        upcoming: List[SectorEvent],
        active: List[SectorEvent]
    ) -> Tuple[List[SectorType], Dict[str, float]]:
        """Hot 섹터 분석"""
        sector_scores: Dict[str, float] = {}

        # 진행 중 이벤트 가중치 높음
        for event in active:
            for sector in event.sectors:
                current = sector_scores.get(sector.value, 0)
                impact_weight = {'high': 3, 'medium': 2, 'low': 1}.get(event.impact_level, 1)
                sector_scores[sector.value] = current + impact_weight * 2

        # 임박한 이벤트 (30일 내)
        today = date.today()
        for event in upcoming:
            days_until = (event.start_date - today).days
            if days_until <= 30:
                for sector in event.sectors:
                    current = sector_scores.get(sector.value, 0)
                    impact_weight = {'high': 3, 'medium': 2, 'low': 1}.get(event.impact_level, 1)
                    # 가까울수록 점수 높음
                    time_weight = 1 + (30 - days_until) / 30
                    sector_scores[sector.value] = current + impact_weight * time_weight

        # 정규화 (0-100)
        if sector_scores:
            max_score = max(sector_scores.values())
            if max_score > 0:
                sector_scores = {k: round(v / max_score * 100, 1) for k, v in sector_scores.items()}

        # Hot 섹터 (점수 50 이상)
        hot_sectors = [
            SectorType(k) for k, v in sector_scores.items()
            if v >= 50
        ]

        return hot_sectors, sector_scores

    def _get_buy_candidates(
        self,
        upcoming: List[SectorEvent],
        active: List[SectorEvent]
    ) -> List[str]:
        """매수 후보 종목 추출"""
        candidates = set()
        today = date.today()

        # 진행 중 이벤트 관련주
        for event in active:
            if event.impact_level in ['high', 'medium']:
                candidates.update(event.related_stocks_kr)

        # 임박한 이벤트 (2주 내) 관련주
        for event in upcoming:
            days_until = (event.start_date - today).days
            if days_until <= 14 and event.impact_level == 'high':
                candidates.update(event.related_stocks_kr)

        return list(candidates)

    def get_events_for_stock(self, stock_code: str) -> List[SectorEvent]:
        """특정 종목 관련 이벤트 조회"""
        all_events = self._get_sector_events()

        return [
            e for e in all_events
            if stock_code in e.related_stocks_kr
        ]


# Singleton instance
_monitor_instance: Optional[SectorEventMonitor] = None


def get_sector_monitor() -> SectorEventMonitor:
    """Get singleton SectorEventMonitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = SectorEventMonitor()
    return _monitor_instance


# Convenience function
async def analyze_sector_events(
    target_sector: Optional[SectorType] = None
) -> SectorAnalysisResult:
    """섹터 이벤트 분석 편의 함수"""
    monitor = get_sector_monitor()
    return await monitor.analyze(target_sector)
