"""
Disclosure Analyzer - Phase 4
DART 공시 분석을 통한 투자 신호 생성

핵심 기능:
- 공시 제목에서 중요 키워드 감지
- 점수화 (+2.0 ~ -2.0)
- Trading Halt 신호 (횡령, 배임 등)
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

import OpenDartReader
from src.config.settings import settings


class DisclosureImpact(Enum):
    """공시 영향도 분류"""
    VERY_POSITIVE = "very_positive"   # +2.0
    POSITIVE = "positive"             # +1.0
    NEUTRAL = "neutral"               # 0.0
    NEGATIVE = "negative"             # -1.0
    VERY_NEGATIVE = "very_negative"   # -2.0
    TRADING_HALT = "trading_halt"     # 거래 정지 권고


@dataclass
class DisclosureResult:
    """공시 분석 결과"""
    ticker: str
    score: float
    trading_halt: bool
    halt_reason: Optional[str]
    disclosures: List[Dict[str, Any]]
    key_events: List[Dict[str, Any]]
    analyzed_at: str


class DisclosureAnalyzer:
    """
    DART 공시 분석기

    Phase 4 Spec:
    - Supply Contract (>10% rev): +2.0
    - Stock Buyback / Insider Buy: +1.0
    - Capital Increase (General Public): -2.0
    - Embezzlement / Breach of Trust: TRADING HALT
    """

    # 호재 키워드 (점수, 키워드 리스트)
    POSITIVE_KEYWORDS: Dict[float, List[str]] = {
        2.0: [
            '단일판매', '단일공급', '공급계약', '판매계약',
            '대규모수주', '수주공시', '납품계약',
        ],
        1.5: [
            '자기주식취득', '자사주매입', '자기주식소각',
            '최대주주변경', '경영권양수',  # 프리미엄 기대
        ],
        1.0: [
            '주요주주매수', '임원매수', '특수관계인매수',
            '배당결정', '중간배당', '특별배당',
            '흑자전환', '영업이익증가',
        ],
        0.5: [
            '신규시설투자', '타법인주식취득', '합병',
            '자회사설립', '사업확장',
        ],
    }

    # 악재 키워드 (점수, 키워드 리스트)
    NEGATIVE_KEYWORDS: Dict[float, List[str]] = {
        -0.5: [
            '유상증자결정', '전환사채발행', '신주인수권부사채',
            '주식관련사채', 'CB발행', 'BW발행',
        ],
        -1.0: [
            '감자결정', '자본감소', '주식병합',
            '영업손실', '당기순손실', '적자전환',
            '관리종목지정', '투자주의환기',
        ],
        -1.5: [
            '상장폐지', '거래정지', '불성실공시',
            '감사의견거절', '감사의견한정', '계속기업불확실',
        ],
    }

    # Trading Halt 키워드 (즉시 매매 정지 권고)
    HALT_KEYWORDS: List[str] = [
        '횡령', '배임', '부정행위', '분식회계',
        '허위공시', '시세조종', '내부자거래',
        '검찰조사', '금감원조사', '압수수색',
        '대표이사구속', '상장폐지결정',
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.dart = OpenDartReader(settings.DART_API_KEY)
        self._cache: Dict[str, DisclosureResult] = {}
        self._cache_ttl = timedelta(minutes=30)

    async def analyze(self, ticker: str, days: int = 30) -> DisclosureResult:
        """
        종목의 최근 공시를 분석하여 점수와 Trading Halt 여부 반환

        Args:
            ticker: 종목코드 (예: "005930")
            days: 분석할 기간 (기본 30일)

        Returns:
            DisclosureResult: 분석 결과
        """
        # 캐시 확인
        cache_key = f"{ticker}_{days}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached_time = datetime.fromisoformat(cached.analyzed_at)
            if datetime.now() - cached_time < self._cache_ttl:
                self.logger.debug(f"Cache hit for {ticker}")
                return cached

        try:
            # DART에서 공시 조회
            disclosures = await self._fetch_disclosures(ticker, days)

            if not disclosures:
                return DisclosureResult(
                    ticker=ticker,
                    score=0.0,
                    trading_halt=False,
                    halt_reason=None,
                    disclosures=[],
                    key_events=[],
                    analyzed_at=datetime.now().isoformat()
                )

            # 공시 분석
            total_score = 0.0
            trading_halt = False
            halt_reason = None
            key_events = []

            for disc in disclosures:
                title = disc.get('report_nm', '')
                score, impact, matched_keyword = self._analyze_title(title)

                if impact == DisclosureImpact.TRADING_HALT:
                    trading_halt = True
                    halt_reason = f"위험 공시 감지: {matched_keyword}"
                    key_events.append({
                        'title': title,
                        'date': disc.get('rcept_dt', ''),
                        'impact': 'TRADING_HALT',
                        'keyword': matched_keyword,
                        'score': -999  # 매매 정지
                    })
                elif score != 0:
                    total_score += score
                    key_events.append({
                        'title': title,
                        'date': disc.get('rcept_dt', ''),
                        'impact': impact.value,
                        'keyword': matched_keyword,
                        'score': score
                    })

            # 점수 정규화 (-2.0 ~ +2.0 범위로 클램핑)
            final_score = max(-2.0, min(2.0, total_score))

            result = DisclosureResult(
                ticker=ticker,
                score=final_score,
                trading_halt=trading_halt,
                halt_reason=halt_reason,
                disclosures=disclosures[:10],  # 최근 10개만
                key_events=key_events,
                analyzed_at=datetime.now().isoformat()
            )

            # 캐시 저장
            self._cache[cache_key] = result

            self.logger.info(
                f"Disclosure analysis for {ticker}: "
                f"score={final_score:.2f}, halt={trading_halt}, "
                f"events={len(key_events)}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to analyze disclosures for {ticker}: {e}")
            return DisclosureResult(
                ticker=ticker,
                score=0.0,
                trading_halt=False,
                halt_reason=None,
                disclosures=[],
                key_events=[],
                analyzed_at=datetime.now().isoformat()
            )

    async def _fetch_disclosures(self, ticker: str, days: int) -> List[Dict[str, Any]]:
        """DART에서 공시 목록 조회"""
        try:
            # 종목코드로 회사코드 조회
            corp_code = await asyncio.to_thread(
                self.dart.find_corp_code,
                ticker
            )

            if not corp_code:
                self.logger.warning(f"No corp_code found for {ticker}")
                return []

            # 공시 목록 조회
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            df = await asyncio.to_thread(
                self.dart.list,
                corp=corp_code,
                start=start_date,
                end=end_date
            )

            if df is None or df.empty:
                return []

            # DataFrame to list of dicts
            return df.to_dict('records')

        except Exception as e:
            self.logger.error(f"Failed to fetch disclosures: {e}")
            return []

    def _analyze_title(self, title: str) -> Tuple[float, DisclosureImpact, Optional[str]]:
        """
        공시 제목 분석

        Returns:
            (점수, 영향도, 매칭된 키워드)
        """
        title_normalized = title.replace(' ', '').lower()

        # 1. Trading Halt 체크 (최우선)
        for keyword in self.HALT_KEYWORDS:
            if keyword in title_normalized:
                return -999, DisclosureImpact.TRADING_HALT, keyword

        # 2. 호재 체크
        for score, keywords in self.POSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.replace(' ', '').lower() in title_normalized:
                    impact = (DisclosureImpact.VERY_POSITIVE if score >= 2.0
                              else DisclosureImpact.POSITIVE)
                    return score, impact, keyword

        # 3. 악재 체크
        for score, keywords in self.NEGATIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.replace(' ', '').lower() in title_normalized:
                    impact = (DisclosureImpact.VERY_NEGATIVE if score <= -1.5
                              else DisclosureImpact.NEGATIVE)
                    return score, impact, keyword

        # 4. 중립
        return 0.0, DisclosureImpact.NEUTRAL, None

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


# Singleton instance
_analyzer_instance: Optional[DisclosureAnalyzer] = None


def get_disclosure_analyzer() -> DisclosureAnalyzer:
    """Get singleton DisclosureAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = DisclosureAnalyzer()
    return _analyzer_instance


# Convenience function
async def analyze_disclosure(ticker: str, days: int = 30) -> DisclosureResult:
    """공시 분석 편의 함수"""
    analyzer = get_disclosure_analyzer()
    return await analyzer.analyze(ticker, days)
