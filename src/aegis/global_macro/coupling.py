"""
Coupling Analyzer - Phase 4.5
미국-한국 종목 커플링 분석

핵심 기능:
- 미국 종목과 한국 종목 간 연관성 매핑
- 미국 시장 변화가 한국 종목에 미치는 영향 분석
- 커플링 조정 점수 산출
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from .fetcher import (
    GlobalMarketFetcher,
    get_global_market_fetcher,
    GlobalMarketData,
    MarketSentiment,
    IndexData
)


class CouplingStrength(Enum):
    """커플링 강도"""
    STRONG = "strong"       # 직접 연관 (삼성전자-NVDA)
    MODERATE = "moderate"   # 간접 연관 (섹터 레벨)
    WEAK = "weak"          # 약한 연관 (시장 전체)
    NONE = "none"          # 연관 없음


@dataclass
class CouplingMapping:
    """커플링 매핑 정보"""
    kr_stock_code: str
    kr_stock_name: str
    us_symbols: List[str]          # 연관 미국 종목
    us_indices: List[str]          # 연관 미국 지수
    sector: str                    # 섹터
    coupling_strength: CouplingStrength
    description: str               # 설명


@dataclass
class CouplingResult:
    """커플링 분석 결과"""
    stock_code: str
    stock_name: str

    # 커플링 정보
    coupling_strength: CouplingStrength
    related_us_stocks: Dict[str, IndexData]  # 연관 미국 종목 데이터
    related_us_indices: Dict[str, IndexData]  # 연관 미국 지수 데이터

    # 분석 결과
    us_sentiment: MarketSentiment    # 미국 시장 심리
    sector_sentiment: MarketSentiment  # 섹터 심리
    coupling_score: float            # 커플링 점수 (-100 ~ +100)
    adjustment_factor: float         # 가중치 조정 계수 (0.8 ~ 1.2)

    # 메타데이터
    analysis_reason: str
    analyzed_at: str


class CouplingAnalyzer:
    """
    미국-한국 종목 커플링 분석기

    Phase 4.5 Spec:
    - 미국 종목/지수와 한국 종목 간 연관성 분석
    - 미국 시장 변화에 따른 한국 종목 영향도 계산
    - FusionEngine 가중치 조정용 점수 산출
    """

    # 커플링 매핑 정의
    COUPLING_MAP: Dict[str, CouplingMapping] = {
        # 반도체
        '005930': CouplingMapping(
            kr_stock_code='005930',
            kr_stock_name='삼성전자',
            us_symbols=['NVDA', 'MU', 'AMD', 'INTC', 'ASML'],
            us_indices=['^SOX', '^NDX'],
            sector='semiconductor',
            coupling_strength=CouplingStrength.STRONG,
            description='글로벌 반도체 사이클 직접 연동'
        ),
        '000660': CouplingMapping(
            kr_stock_code='000660',
            kr_stock_name='SK하이닉스',
            us_symbols=['NVDA', 'MU', 'AMD'],
            us_indices=['^SOX', '^NDX'],
            sector='semiconductor',
            coupling_strength=CouplingStrength.STRONG,
            description='HBM 수혜주, NVIDIA 직접 연관'
        ),

        # 2차전지/EV
        '243840': CouplingMapping(
            kr_stock_code='243840',
            kr_stock_name='금양그린파워',
            us_symbols=['TSLA', 'RIVN', 'ALB'],
            us_indices=['^NDX'],
            sector='ev_battery',
            coupling_strength=CouplingStrength.MODERATE,
            description='2차전지 소재주, Tesla 간접 연관'
        ),
        '247540': CouplingMapping(
            kr_stock_code='247540',
            kr_stock_name='에코프로비엠',
            us_symbols=['TSLA', 'ALB'],
            us_indices=['^NDX'],
            sector='ev_battery',
            coupling_strength=CouplingStrength.MODERATE,
            description='양극재 공급, Tesla 간접 연관'
        ),
        '086520': CouplingMapping(
            kr_stock_code='086520',
            kr_stock_name='에코프로',
            us_symbols=['TSLA', 'ALB'],
            us_indices=['^NDX'],
            sector='ev_battery',
            coupling_strength=CouplingStrength.MODERATE,
            description='2차전지 소재, EV 시장 연관'
        ),

        # 테크/플랫폼
        '035720': CouplingMapping(
            kr_stock_code='035720',
            kr_stock_name='카카오',
            us_symbols=['META', 'GOOGL'],
            us_indices=['^NDX', '^IXIC'],
            sector='tech',
            coupling_strength=CouplingStrength.MODERATE,
            description='플랫폼/광고 사업, 빅테크 심리 연동'
        ),
        '035420': CouplingMapping(
            kr_stock_code='035420',
            kr_stock_name='NAVER',
            us_symbols=['META', 'GOOGL', 'AAPL'],
            us_indices=['^NDX', '^IXIC'],
            sector='tech',
            coupling_strength=CouplingStrength.MODERATE,
            description='검색/광고/AI, 빅테크 심리 연동'
        ),

        # 에너지/태양광
        '322000': CouplingMapping(
            kr_stock_code='322000',
            kr_stock_name='HD현대에너지솔루션',
            us_symbols=['FSLR', 'ENPH'],
            us_indices=['^GSPC'],
            sector='energy',
            coupling_strength=CouplingStrength.MODERATE,
            description='태양광 모듈, 미국 태양광주 연관'
        ),
        '015760': CouplingMapping(
            kr_stock_code='015760',
            kr_stock_name='한국전력',
            us_symbols=['NEE'],
            us_indices=['^GSPC'],
            sector='energy',
            coupling_strength=CouplingStrength.WEAK,
            description='전력/유틸리티, 간접 연관'
        ),

        # 금융 (약한 커플링)
        '316140': CouplingMapping(
            kr_stock_code='316140',
            kr_stock_name='우리금융지주',
            us_symbols=[],
            us_indices=['^GSPC', '^DJI'],
            sector='financial',
            coupling_strength=CouplingStrength.WEAK,
            description='국내 금융, 글로벌 금융 심리만 연관'
        ),
    }

    # 섹터별 기본 매핑 (개별 종목 매핑 없을 경우)
    SECTOR_DEFAULT_MAP = {
        'semiconductor': {
            'us_symbols': ['NVDA', 'AMD'],
            'us_indices': ['^SOX', '^NDX'],
            'strength': CouplingStrength.MODERATE,
        },
        'ev_battery': {
            'us_symbols': ['TSLA'],
            'us_indices': ['^NDX'],
            'strength': CouplingStrength.WEAK,
        },
        'tech': {
            'us_symbols': ['META', 'GOOGL'],
            'us_indices': ['^NDX', '^IXIC'],
            'strength': CouplingStrength.WEAK,
        },
        'energy': {
            'us_symbols': ['FSLR'],
            'us_indices': ['^GSPC'],
            'strength': CouplingStrength.WEAK,
        },
        'financial': {
            'us_symbols': [],
            'us_indices': ['^GSPC'],
            'strength': CouplingStrength.WEAK,
        },
        'default': {
            'us_symbols': [],
            'us_indices': ['^GSPC', '^IXIC'],
            'strength': CouplingStrength.WEAK,
        },
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._global_fetcher = get_global_market_fetcher()
        self._cached_global_data: Optional[GlobalMarketData] = None

    async def analyze(
        self,
        stock_code: str,
        stock_name: str,
        sector: Optional[str] = None
    ) -> CouplingResult:
        """
        종목별 커플링 분석

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            sector: 섹터 (없으면 자동 판단)

        Returns:
            CouplingResult: 커플링 분석 결과
        """
        self.logger.info(f"Analyzing coupling for {stock_name}({stock_code})")

        # 1. 글로벌 시장 데이터 조회
        global_data = await self._get_global_data()

        # 2. 커플링 매핑 조회
        mapping = self._get_coupling_mapping(stock_code, stock_name, sector)

        # 3. 연관 미국 종목/지수 데이터 추출
        related_stocks = self._extract_related_stocks(global_data, mapping)
        related_indices = self._extract_related_indices(global_data, mapping)

        # 4. 심리 분석
        us_sentiment = global_data.overall_sentiment
        sector_sentiment = self._get_sector_sentiment(global_data, mapping.sector)

        # 5. 커플링 점수 계산
        coupling_score = self._calculate_coupling_score(
            related_stocks, related_indices, mapping.coupling_strength
        )

        # 6. 조정 계수 계산
        adjustment_factor = self._calculate_adjustment_factor(
            coupling_score, mapping.coupling_strength
        )

        # 7. 분석 이유 생성
        analysis_reason = self._generate_analysis_reason(
            mapping, us_sentiment, sector_sentiment, coupling_score
        )

        return CouplingResult(
            stock_code=stock_code,
            stock_name=stock_name,
            coupling_strength=mapping.coupling_strength,
            related_us_stocks=related_stocks,
            related_us_indices=related_indices,
            us_sentiment=us_sentiment,
            sector_sentiment=sector_sentiment,
            coupling_score=coupling_score,
            adjustment_factor=adjustment_factor,
            analysis_reason=analysis_reason,
            analyzed_at=datetime.now().isoformat()
        )

    async def analyze_batch(
        self,
        stocks: List[Tuple[str, str, Optional[str]]]
    ) -> Dict[str, CouplingResult]:
        """
        다수 종목 일괄 분석

        Args:
            stocks: [(stock_code, stock_name, sector), ...] 리스트

        Returns:
            Dict[stock_code, CouplingResult]
        """
        # 글로벌 데이터 한 번만 조회
        self._cached_global_data = await self._global_fetcher.fetch()

        results = {}
        for stock_code, stock_name, sector in stocks:
            try:
                result = await self.analyze(stock_code, stock_name, sector)
                results[stock_code] = result
            except Exception as e:
                self.logger.warning(f"Failed to analyze {stock_code}: {e}")

        return results

    async def _get_global_data(self) -> GlobalMarketData:
        """글로벌 시장 데이터 조회 (캐시 활용)"""
        if self._cached_global_data:
            return self._cached_global_data
        return await self._global_fetcher.fetch()

    def _get_coupling_mapping(
        self,
        stock_code: str,
        stock_name: str,
        sector: Optional[str]
    ) -> CouplingMapping:
        """커플링 매핑 조회"""
        # 1. 직접 매핑 확인
        if stock_code in self.COUPLING_MAP:
            return self.COUPLING_MAP[stock_code]

        # 2. 섹터 기반 기본 매핑
        sector_key = sector if sector in self.SECTOR_DEFAULT_MAP else 'default'
        sector_config = self.SECTOR_DEFAULT_MAP[sector_key]

        return CouplingMapping(
            kr_stock_code=stock_code,
            kr_stock_name=stock_name,
            us_symbols=sector_config['us_symbols'],
            us_indices=sector_config['us_indices'],
            sector=sector_key,
            coupling_strength=sector_config['strength'],
            description=f'{sector_key} 섹터 기본 커플링'
        )

    def _extract_related_stocks(
        self,
        global_data: GlobalMarketData,
        mapping: CouplingMapping
    ) -> Dict[str, IndexData]:
        """연관 미국 종목 데이터 추출"""
        result = {}
        for symbol in mapping.us_symbols:
            if symbol in global_data.stocks:
                result[symbol] = global_data.stocks[symbol]
        return result

    def _extract_related_indices(
        self,
        global_data: GlobalMarketData,
        mapping: CouplingMapping
    ) -> Dict[str, IndexData]:
        """연관 미국 지수 데이터 추출"""
        result = {}
        for symbol in mapping.us_indices:
            if symbol in global_data.indices:
                result[symbol] = global_data.indices[symbol]
        return result

    def _get_sector_sentiment(
        self,
        global_data: GlobalMarketData,
        sector: str
    ) -> MarketSentiment:
        """섹터 심리 조회"""
        return global_data.sector_sentiments.get(sector, MarketSentiment.NEUTRAL)

    def _calculate_coupling_score(
        self,
        related_stocks: Dict[str, IndexData],
        related_indices: Dict[str, IndexData],
        strength: CouplingStrength
    ) -> float:
        """
        커플링 점수 계산 (-100 ~ +100)

        미국 연관 종목/지수의 변화율을 가중 평균하여 점수화
        """
        if strength == CouplingStrength.NONE:
            return 0.0

        # 강도별 가중치
        strength_weights = {
            CouplingStrength.STRONG: {'stock': 0.7, 'index': 0.3},
            CouplingStrength.MODERATE: {'stock': 0.5, 'index': 0.5},
            CouplingStrength.WEAK: {'stock': 0.3, 'index': 0.7},
        }

        weights = strength_weights.get(strength, {'stock': 0.3, 'index': 0.7})

        # 종목 평균 변화율
        stock_changes = [s.change_pct for s in related_stocks.values()]
        avg_stock_change = sum(stock_changes) / len(stock_changes) if stock_changes else 0

        # 지수 평균 변화율
        index_changes = [i.change_pct for i in related_indices.values()]
        avg_index_change = sum(index_changes) / len(index_changes) if index_changes else 0

        # 가중 평균
        weighted_change = (
            avg_stock_change * weights['stock'] +
            avg_index_change * weights['index']
        )

        # 점수화 (변화율 * 10, -100~+100 범위로 클램핑)
        score = max(-100, min(100, weighted_change * 10))

        return round(score, 2)

    def _calculate_adjustment_factor(
        self,
        coupling_score: float,
        strength: CouplingStrength
    ) -> float:
        """
        가중치 조정 계수 계산 (0.8 ~ 1.2)

        커플링 점수에 따라 FusionEngine 가중치 조정용 계수 산출
        """
        if strength == CouplingStrength.NONE:
            return 1.0

        # 강도별 조정 범위
        adjustment_ranges = {
            CouplingStrength.STRONG: 0.2,    # 0.8 ~ 1.2
            CouplingStrength.MODERATE: 0.15,  # 0.85 ~ 1.15
            CouplingStrength.WEAK: 0.1,       # 0.9 ~ 1.1
        }

        max_adjustment = adjustment_ranges.get(strength, 0.1)

        # 점수를 -1 ~ +1 범위로 정규화
        normalized = coupling_score / 100

        # 조정 계수 계산
        factor = 1.0 + (normalized * max_adjustment)

        return round(factor, 3)

    def _generate_analysis_reason(
        self,
        mapping: CouplingMapping,
        us_sentiment: MarketSentiment,
        sector_sentiment: MarketSentiment,
        coupling_score: float
    ) -> str:
        """분석 이유 생성"""
        sentiment_kr = {
            MarketSentiment.STRONG_BULLISH: "강한 상승",
            MarketSentiment.BULLISH: "상승",
            MarketSentiment.NEUTRAL: "중립",
            MarketSentiment.BEARISH: "하락",
            MarketSentiment.STRONG_BEARISH: "강한 하락",
        }

        us_str = sentiment_kr.get(us_sentiment, "중립")
        sector_str = sentiment_kr.get(sector_sentiment, "중립")

        score_direction = "긍정적" if coupling_score > 0 else "부정적" if coupling_score < 0 else "중립"

        return (
            f"[{mapping.coupling_strength.value}] {mapping.description} | "
            f"미국시장 {us_str}, 섹터({mapping.sector}) {sector_str} | "
            f"커플링 점수 {coupling_score:+.1f} ({score_direction})"
        )

    def get_supported_mappings(self) -> List[str]:
        """지원하는 종목 코드 목록 반환"""
        return list(self.COUPLING_MAP.keys())

    def add_custom_mapping(self, mapping: CouplingMapping):
        """커스텀 매핑 추가"""
        self.COUPLING_MAP[mapping.kr_stock_code] = mapping
        self.logger.info(f"Added custom mapping: {mapping.kr_stock_name}")


# Singleton instance
_analyzer_instance: Optional[CouplingAnalyzer] = None


def get_coupling_analyzer() -> CouplingAnalyzer:
    """Get singleton CouplingAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CouplingAnalyzer()
    return _analyzer_instance


# Convenience function
async def analyze_coupling(
    stock_code: str,
    stock_name: str,
    sector: Optional[str] = None
) -> CouplingResult:
    """커플링 분석 편의 함수"""
    analyzer = get_coupling_analyzer()
    return await analyzer.analyze(stock_code, stock_name, sector)
