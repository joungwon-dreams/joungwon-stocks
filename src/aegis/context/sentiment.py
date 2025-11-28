"""
Market Sentiment Meter - Phase 5.0
시장 공포/탐욕 지표 분석

핵심 기능:
- VIX (공포지수) 기반 시장 심리 측정
- 시장 RSI (KOSPI 과열/과매도)
- 신용잔고율 모니터링
- 종합 시장 상태 진단 (Overheated/Neutral/Fear/Panic)
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

import pandas as pd
from pykrx import stock as pykrx

# Phase 4.5 global macro fetcher (VIX 데이터)
from src.aegis.global_macro import get_global_market_fetcher


class MarketCondition(Enum):
    """시장 상태"""
    EUPHORIA = "euphoria"        # 극도의 탐욕 (버블 경고)
    OVERHEATED = "overheated"    # 과열 (조정 예상)
    BULLISH = "bullish"          # 낙관
    NEUTRAL = "neutral"          # 중립
    CAUTIOUS = "cautious"        # 주의
    FEAR = "fear"                # 공포
    PANIC = "panic"              # 패닉 (바닥 신호 가능)


class SentimentLevel(Enum):
    """심리 레벨 (0-100)"""
    EXTREME_FEAR = "extreme_fear"      # 0-20
    FEAR = "fear"                       # 21-40
    NEUTRAL = "neutral"                 # 41-60
    GREED = "greed"                     # 61-80
    EXTREME_GREED = "extreme_greed"    # 81-100


@dataclass
class SentimentResult:
    """시장 심리 분석 결과"""
    # 종합 결과
    condition: MarketCondition
    sentiment_level: SentimentLevel
    sentiment_score: int  # 0-100 (Fear & Greed Index)

    # 개별 지표
    vix_value: float
    vix_level: str  # "low" / "normal" / "elevated" / "high" / "extreme"

    market_rsi: float
    market_rsi_signal: str  # "oversold" / "neutral" / "overbought"

    credit_balance_ratio: float  # 신용잔고율 (%)
    credit_signal: str  # "low" / "normal" / "high" / "warning"

    # 추가 지표
    advance_decline_ratio: float  # 상승/하락 비율
    put_call_ratio: Optional[float]  # 풋콜비율

    # 조정 계수
    position_multiplier: float  # 포지션 사이즈 조정 (0.5 ~ 1.5)
    risk_warning: bool
    warning_message: Optional[str]

    # 메타데이터
    analyzed_at: str


class MarketSentimentMeter:
    """
    시장 심리 측정기

    Phase 5.0 Spec:
    - VIX, 시장 RSI, 신용잔고율 기반 공포/탐욕 진단
    - 극단적 상황에서 매매 신호 조정
    """

    # VIX 레벨 기준
    VIX_LEVELS = {
        'low': (0, 12),          # 안일함 (과열 경고)
        'normal': (12, 20),      # 정상
        'elevated': (20, 25),    # 주의
        'high': (25, 35),        # 높음
        'extreme': (35, 100),    # 극단적 공포
    }

    # 시장 RSI 기준
    RSI_LEVELS = {
        'oversold': (0, 30),     # 과매도
        'neutral': (30, 70),     # 중립
        'overbought': (70, 100), # 과열
    }

    # 신용잔고율 기준 (%)
    CREDIT_LEVELS = {
        'low': (0, 2),           # 낮음
        'normal': (2, 4),        # 정상
        'high': (4, 6),          # 높음
        'warning': (6, 100),     # 경고 (반대매매 리스크)
    }

    # 캐시 TTL
    CACHE_TTL = timedelta(minutes=10)

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._global_fetcher = get_global_market_fetcher()
        self._cache: Optional[Tuple[SentimentResult, datetime]] = None

    async def analyze(self, force_refresh: bool = False) -> SentimentResult:
        """
        시장 심리 분석

        Args:
            force_refresh: 캐시 무시

        Returns:
            SentimentResult: 심리 분석 결과
        """
        # 캐시 확인
        if not force_refresh and self._cache:
            cached_data, cached_at = self._cache
            if datetime.now() - cached_at < self.CACHE_TTL:
                return cached_data

        self.logger.info("Analyzing market sentiment...")

        # 1. VIX 데이터 (Phase 4.5 GlobalMarketFetcher에서)
        vix_value, vix_level = await self._get_vix_data()

        # 2. 시장 RSI (KOSPI)
        market_rsi, rsi_signal = await self._calculate_market_rsi()

        # 3. 신용잔고율
        credit_ratio, credit_signal = await self._get_credit_balance()

        # 4. 상승/하락 비율
        adr = await self._get_advance_decline_ratio()

        # 5. 종합 심리 점수 계산 (0-100)
        sentiment_score = self._calculate_sentiment_score(
            vix_value, market_rsi, credit_ratio, adr
        )

        # 6. 심리 레벨 결정
        sentiment_level = self._get_sentiment_level(sentiment_score)

        # 7. 시장 상태 결정
        condition = self._determine_market_condition(
            vix_level, rsi_signal, credit_signal, sentiment_score
        )

        # 8. 포지션 조정 계수 및 경고
        position_multiplier, risk_warning, warning_msg = self._calculate_adjustments(
            condition, vix_level, rsi_signal, credit_signal
        )

        result = SentimentResult(
            condition=condition,
            sentiment_level=sentiment_level,
            sentiment_score=sentiment_score,
            vix_value=vix_value,
            vix_level=vix_level,
            market_rsi=market_rsi,
            market_rsi_signal=rsi_signal,
            credit_balance_ratio=credit_ratio,
            credit_signal=credit_signal,
            advance_decline_ratio=adr,
            put_call_ratio=None,  # 추후 구현
            position_multiplier=position_multiplier,
            risk_warning=risk_warning,
            warning_message=warning_msg,
            analyzed_at=datetime.now().isoformat()
        )

        # 캐시 저장
        self._cache = (result, datetime.now())

        return result

    async def _get_vix_data(self) -> Tuple[float, str]:
        """VIX 데이터 조회"""
        try:
            global_data = await self._global_fetcher.fetch()

            if '^VIX' in global_data.indices:
                vix_value = global_data.indices['^VIX'].price
            else:
                vix_value = 20.0  # 기본값

            # 레벨 판단
            vix_level = 'normal'
            for level, (low, high) in self.VIX_LEVELS.items():
                if low <= vix_value < high:
                    vix_level = level
                    break

            return vix_value, vix_level

        except Exception as e:
            self.logger.warning(f"Failed to get VIX data: {e}")
            return 20.0, 'normal'

    async def _calculate_market_rsi(self, period: int = 14) -> Tuple[float, str]:
        """KOSPI RSI 계산"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

            df = pykrx.get_index_ohlcv_by_date(start_date, end_date, "1001")  # KOSPI

            if df.empty or len(df) < period + 1:
                return 50.0, 'neutral'

            # RSI 계산
            delta = df['종가'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            market_rsi = round(rsi.iloc[-1], 2)

            # 신호 판단
            if market_rsi < 30:
                signal = 'oversold'
            elif market_rsi > 70:
                signal = 'overbought'
            else:
                signal = 'neutral'

            return market_rsi, signal

        except Exception as e:
            self.logger.warning(f"Failed to calculate market RSI: {e}")
            return 50.0, 'neutral'

    async def _get_credit_balance(self) -> Tuple[float, str]:
        """
        신용잔고율 조회

        Note: 실제 데이터는 금융투자협회 등에서 제공
        여기서는 추정값 사용
        """
        try:
            # TODO: 실제 신용잔고 데이터 소스 연결
            # 현재는 시장 상황 기반 추정
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            df = pykrx.get_index_ohlcv_by_date(start_date, end_date, "1001")

            if df.empty:
                return 3.0, 'normal'

            # 최근 30일 상승률로 신용잔고 추정
            # (실제로는 금융투자협회 데이터 사용해야 함)
            recent_return = (df['종가'].iloc[-1] / df['종가'].iloc[0] - 1) * 100

            # 상승장일수록 신용잔고 높음 (추정)
            if recent_return > 10:
                credit_ratio = 5.5
            elif recent_return > 5:
                credit_ratio = 4.5
            elif recent_return > 0:
                credit_ratio = 3.5
            elif recent_return > -5:
                credit_ratio = 3.0
            else:
                credit_ratio = 2.5

            # 레벨 판단
            credit_signal = 'normal'
            for level, (low, high) in self.CREDIT_LEVELS.items():
                if low <= credit_ratio < high:
                    credit_signal = level
                    break

            return round(credit_ratio, 2), credit_signal

        except Exception as e:
            self.logger.warning(f"Failed to get credit balance: {e}")
            return 3.0, 'normal'

    async def _get_advance_decline_ratio(self) -> float:
        """상승/하락 종목 비율 (ADR)"""
        try:
            today = datetime.now().strftime('%Y%m%d')

            # KOSPI 전 종목 등락
            df = pykrx.get_market_ohlcv_by_date(today, today, market="KOSPI")

            if df.empty:
                # 전일 데이터 시도
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df = pykrx.get_market_ohlcv_by_date(yesterday, yesterday, market="KOSPI")

            if df.empty:
                return 1.0

            # 등락 계산
            advances = len(df[df['등락률'] > 0])
            declines = len(df[df['등락률'] < 0])
            unchanged = len(df[df['등락률'] == 0])

            if declines == 0:
                return 2.0 if advances > 0 else 1.0

            adr = advances / declines

            return round(adr, 2)

        except Exception as e:
            self.logger.warning(f"Failed to get ADR: {e}")
            return 1.0

    def _calculate_sentiment_score(
        self,
        vix: float,
        rsi: float,
        credit_ratio: float,
        adr: float
    ) -> int:
        """
        종합 심리 점수 계산 (0-100)

        0 = Extreme Fear, 100 = Extreme Greed
        """
        scores = []

        # VIX 점수 (역방향: VIX 높으면 Fear)
        if vix < 12:
            vix_score = 90
        elif vix < 20:
            vix_score = 70
        elif vix < 25:
            vix_score = 50
        elif vix < 35:
            vix_score = 30
        else:
            vix_score = 10
        scores.append(('vix', vix_score, 0.35))  # 가중치 35%

        # RSI 점수
        rsi_score = rsi  # RSI 그대로 사용
        scores.append(('rsi', rsi_score, 0.25))  # 가중치 25%

        # 신용잔고 점수 (높으면 Greed)
        if credit_ratio < 2:
            credit_score = 30
        elif credit_ratio < 4:
            credit_score = 50
        elif credit_ratio < 6:
            credit_score = 70
        else:
            credit_score = 85
        scores.append(('credit', credit_score, 0.20))  # 가중치 20%

        # ADR 점수
        if adr < 0.5:
            adr_score = 15
        elif adr < 0.8:
            adr_score = 35
        elif adr < 1.2:
            adr_score = 50
        elif adr < 1.5:
            adr_score = 65
        else:
            adr_score = 80
        scores.append(('adr', adr_score, 0.20))  # 가중치 20%

        # 가중 평균
        total_score = sum(score * weight for _, score, weight in scores)

        return max(0, min(100, int(total_score)))

    def _get_sentiment_level(self, score: int) -> SentimentLevel:
        """심리 레벨 결정"""
        if score <= 20:
            return SentimentLevel.EXTREME_FEAR
        elif score <= 40:
            return SentimentLevel.FEAR
        elif score <= 60:
            return SentimentLevel.NEUTRAL
        elif score <= 80:
            return SentimentLevel.GREED
        else:
            return SentimentLevel.EXTREME_GREED

    def _determine_market_condition(
        self,
        vix_level: str,
        rsi_signal: str,
        credit_signal: str,
        sentiment_score: int
    ) -> MarketCondition:
        """시장 상태 결정"""
        # 극단적 상황 우선
        if vix_level == 'extreme':
            return MarketCondition.PANIC

        if vix_level == 'high' and sentiment_score < 30:
            return MarketCondition.FEAR

        if vix_level == 'low' and rsi_signal == 'overbought' and credit_signal in ['high', 'warning']:
            return MarketCondition.EUPHORIA

        if rsi_signal == 'overbought' and credit_signal in ['high', 'warning']:
            return MarketCondition.OVERHEATED

        if rsi_signal == 'oversold' and vix_level in ['elevated', 'high']:
            return MarketCondition.FEAR

        # 일반 상황
        if sentiment_score >= 70:
            return MarketCondition.BULLISH
        elif sentiment_score >= 45:
            return MarketCondition.NEUTRAL
        elif sentiment_score >= 30:
            return MarketCondition.CAUTIOUS
        else:
            return MarketCondition.FEAR

    def _calculate_adjustments(
        self,
        condition: MarketCondition,
        vix_level: str,
        rsi_signal: str,
        credit_signal: str
    ) -> Tuple[float, bool, Optional[str]]:
        """포지션 조정 계수 및 경고 계산"""
        # 기본값
        multiplier = 1.0
        risk_warning = False
        warning_msg = None

        # 상태별 조정
        adjustments = {
            MarketCondition.PANIC: (0.3, True, "패닉 상태 - 현금 비중 확대 권고"),
            MarketCondition.FEAR: (0.6, True, "공포 심리 확산 - 신규 매수 자제"),
            MarketCondition.CAUTIOUS: (0.8, False, None),
            MarketCondition.NEUTRAL: (1.0, False, None),
            MarketCondition.BULLISH: (1.1, False, None),
            MarketCondition.OVERHEATED: (0.7, True, "시장 과열 - 차익실현 고려"),
            MarketCondition.EUPHORIA: (0.5, True, "버블 경고 - 신규 매수 금지"),
        }

        if condition in adjustments:
            multiplier, risk_warning, warning_msg = adjustments[condition]

        # 추가 경고
        if credit_signal == 'warning' and not warning_msg:
            risk_warning = True
            warning_msg = "신용잔고 과다 - 반대매매 리스크"

        return multiplier, risk_warning, warning_msg

    def clear_cache(self):
        """캐시 초기화"""
        self._cache = None
        self.logger.info("Sentiment cache cleared")


# Singleton instance
_meter_instance: Optional[MarketSentimentMeter] = None


def get_sentiment_meter() -> MarketSentimentMeter:
    """Get singleton MarketSentimentMeter instance"""
    global _meter_instance
    if _meter_instance is None:
        _meter_instance = MarketSentimentMeter()
    return _meter_instance


# Convenience function
async def analyze_market_sentiment(force_refresh: bool = False) -> SentimentResult:
    """시장 심리 분석 편의 함수"""
    meter = get_sentiment_meter()
    return await meter.analyze(force_refresh)
