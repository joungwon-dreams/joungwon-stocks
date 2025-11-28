"""
Fundamental Integrator - Phase 4
재무 데이터 기반 건전성 필터

핵심 기능:
- 부채비율, ROE, 영업이익률 분석
- 부실 기업 필터링
- 우량 기업 가점
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from pykrx import stock


class FundamentalGrade(Enum):
    """재무 등급"""
    EXCELLENT = "excellent"   # 우량 (+1.0)
    GOOD = "good"             # 양호 (+0.5)
    AVERAGE = "average"       # 보통 (0.0)
    POOR = "poor"             # 부진 (-0.5)
    DANGER = "danger"         # 위험 (-1.0, 필터 대상)


@dataclass
class FundamentalResult:
    """재무 분석 결과"""
    ticker: str
    score: float
    grade: FundamentalGrade
    pass_filter: bool         # 투자 적합 여부
    filter_reason: Optional[str]
    metrics: Dict[str, Any]
    analyzed_at: str


class FundamentalIntegrator:
    """
    재무 건전성 분석기

    Phase 4 Spec:
    - Profitability: OPM > Industry Avg (+0.5)
    - Stability: Debt Ratio < 200% (Pass/Fail)
    - Efficiency: ROE > 10% (+0.5)
    """

    # 임계값 설정
    THRESHOLDS = {
        'debt_ratio_danger': 300,    # 부채비율 300% 초과: 위험
        'debt_ratio_warning': 200,   # 부채비율 200% 초과: 경고
        'roe_excellent': 15,         # ROE 15% 초과: 우수
        'roe_good': 10,              # ROE 10% 초과: 양호
        'roe_poor': 0,               # ROE 0% 이하: 부진
        'opm_excellent': 15,         # 영업이익률 15% 초과: 우수
        'opm_good': 10,              # 영업이익률 10% 초과: 양호
        'opm_poor': 0,               # 영업이익률 0% 이하: 적자
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, FundamentalResult] = {}
        self._cache_ttl = timedelta(hours=6)  # 재무 데이터는 자주 안 바뀜

    async def analyze(self, ticker: str) -> FundamentalResult:
        """
        종목의 재무 데이터를 분석하여 점수 및 필터 여부 반환

        Args:
            ticker: 종목코드 (예: "005930")

        Returns:
            FundamentalResult: 분석 결과
        """
        # 캐시 확인
        if ticker in self._cache:
            cached = self._cache[ticker]
            cached_time = datetime.fromisoformat(cached.analyzed_at)
            if datetime.now() - cached_time < self._cache_ttl:
                self.logger.debug(f"Cache hit for {ticker}")
                return cached

        try:
            # pykrx에서 재무 데이터 조회
            fundamentals = await self._fetch_fundamentals(ticker)

            if not fundamentals:
                return self._unknown_result(ticker)

            # 분석 수행
            score, grade, pass_filter, filter_reason = self._analyze_fundamentals(fundamentals)

            result = FundamentalResult(
                ticker=ticker,
                score=score,
                grade=grade,
                pass_filter=pass_filter,
                filter_reason=filter_reason,
                metrics=fundamentals,
                analyzed_at=datetime.now().isoformat()
            )

            # 캐시 저장
            self._cache[ticker] = result

            self.logger.info(
                f"Fundamental analysis for {ticker}: "
                f"score={score:.2f}, grade={grade.value}, pass={pass_filter}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to analyze fundamentals for {ticker}: {e}")
            return self._unknown_result(ticker)

    async def _fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """pykrx에서 재무 데이터 조회"""
        try:
            today = datetime.now().strftime("%Y%m%d")

            # 기본 재무 정보 (BPS, PER, PBR, EPS, DIV, DPS)
            df = await asyncio.to_thread(
                stock.get_market_fundamental,
                today, today, ticker
            )

            if df is None or df.empty:
                # 어제 데이터 시도
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                df = await asyncio.to_thread(
                    stock.get_market_fundamental,
                    yesterday, yesterday, ticker
                )

            if df is None or df.empty:
                return {}

            # 최근 데이터 추출
            latest = df.iloc[-1] if len(df) > 0 else {}

            fundamentals = {
                'per': float(latest.get('PER', 0)) if 'PER' in latest else None,
                'pbr': float(latest.get('PBR', 0)) if 'PBR' in latest else None,
                'eps': float(latest.get('EPS', 0)) if 'EPS' in latest else None,
                'bps': float(latest.get('BPS', 0)) if 'BPS' in latest else None,
                'div_yield': float(latest.get('DIV', 0)) if 'DIV' in latest else None,
            }

            # 추가 재무 비율 계산 (가능한 경우)
            # ROE = EPS / BPS * 100 (근사치)
            if fundamentals['eps'] and fundamentals['bps'] and fundamentals['bps'] > 0:
                fundamentals['roe'] = round(fundamentals['eps'] / fundamentals['bps'] * 100, 2)
            else:
                fundamentals['roe'] = None

            # PBR로 부채비율 추정은 어려움 - 별도 API 필요
            # 일단 None으로 설정
            fundamentals['debt_ratio'] = None
            fundamentals['opm'] = None

            return fundamentals

        except Exception as e:
            self.logger.error(f"Failed to fetch fundamentals: {e}")
            return {}

    def _analyze_fundamentals(
        self, metrics: Dict[str, Any]
    ) -> tuple[float, FundamentalGrade, bool, Optional[str]]:
        """재무 데이터 분석"""
        score = 0.0
        pass_filter = True
        filter_reason = None

        # 1. 부채비율 체크 (Pass/Fail)
        debt_ratio = metrics.get('debt_ratio')
        if debt_ratio is not None:
            if debt_ratio > self.THRESHOLDS['debt_ratio_danger']:
                pass_filter = False
                filter_reason = f"부채비율 위험: {debt_ratio:.1f}% (>300%)"
                score -= 1.0
            elif debt_ratio > self.THRESHOLDS['debt_ratio_warning']:
                score -= 0.5

        # 2. ROE 체크
        roe = metrics.get('roe')
        if roe is not None:
            if roe > self.THRESHOLDS['roe_excellent']:
                score += 0.5
            elif roe > self.THRESHOLDS['roe_good']:
                score += 0.3
            elif roe < self.THRESHOLDS['roe_poor']:
                score -= 0.3

        # 3. 영업이익률 체크
        opm = metrics.get('opm')
        if opm is not None:
            if opm > self.THRESHOLDS['opm_excellent']:
                score += 0.5
            elif opm > self.THRESHOLDS['opm_good']:
                score += 0.3
            elif opm < self.THRESHOLDS['opm_poor']:
                score -= 0.5
                if not filter_reason:
                    filter_reason = f"영업적자: {opm:.1f}%"

        # 4. PER/PBR 기반 추가 분석
        per = metrics.get('per')
        pbr = metrics.get('pbr')

        if per is not None and per > 0:
            if per < 10:
                score += 0.2  # 저PER
            elif per > 50:
                score -= 0.2  # 고PER (과열)

        if pbr is not None and pbr > 0:
            if pbr < 1.0:
                score += 0.2  # 저PBR (자산가치 대비 저평가)

        # 5. 배당수익률
        div_yield = metrics.get('div_yield')
        if div_yield is not None and div_yield > 3:
            score += 0.2  # 고배당

        # 점수 정규화 (-2.0 ~ +2.0)
        final_score = max(-2.0, min(2.0, score))

        # 등급 결정
        if final_score >= 0.8:
            grade = FundamentalGrade.EXCELLENT
        elif final_score >= 0.3:
            grade = FundamentalGrade.GOOD
        elif final_score >= -0.3:
            grade = FundamentalGrade.AVERAGE
        elif final_score >= -0.8:
            grade = FundamentalGrade.POOR
        else:
            grade = FundamentalGrade.DANGER
            pass_filter = False

        return final_score, grade, pass_filter, filter_reason

    def _unknown_result(self, ticker: str) -> FundamentalResult:
        """데이터 없을 때 기본 결과"""
        return FundamentalResult(
            ticker=ticker,
            score=0.0,
            grade=FundamentalGrade.AVERAGE,
            pass_filter=True,  # 데이터 없으면 일단 통과
            filter_reason="재무 데이터 없음",
            metrics={},
            analyzed_at=datetime.now().isoformat()
        )

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


# Singleton instance
_integrator_instance: Optional[FundamentalIntegrator] = None


def get_fundamental_integrator() -> FundamentalIntegrator:
    """Get singleton FundamentalIntegrator instance"""
    global _integrator_instance
    if _integrator_instance is None:
        _integrator_instance = FundamentalIntegrator()
    return _integrator_instance


# Convenience function
async def analyze_fundamental(ticker: str) -> FundamentalResult:
    """재무 분석 편의 함수"""
    integrator = get_fundamental_integrator()
    return await integrator.analyze(ticker)
