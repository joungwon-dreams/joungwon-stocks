"""
Consensus Momentum Analyzer - Phase 4
증권사 목표가 추세 분석

핵심 기능:
- 증권사 목표가 수집 및 추세 분석
- 컨센서스 상향/하향 모멘텀 감지
- 현재가 대비 괴리율 계산
- 투자의견 변화 추적
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

import aiohttp
from pykrx import stock as pykrx


class ConsensusTrend(Enum):
    """컨센서스 추세"""
    STRONG_UPGRADE = "strong_upgrade"     # 3개월 목표가 +20% 이상 상향
    UPGRADE = "upgrade"                    # 3개월 목표가 +10% 이상 상향
    STABLE = "stable"                      # 변동 ±10% 미만
    DOWNGRADE = "downgrade"               # 3개월 목표가 -10% 이상 하향
    STRONG_DOWNGRADE = "strong_downgrade" # 3개월 목표가 -20% 이상 하향


class OpinionLevel(Enum):
    """투자의견 수준"""
    STRONG_BUY = "strong_buy"      # 적극매수
    BUY = "buy"                    # 매수
    HOLD = "hold"                  # 중립
    UNDERPERFORM = "underperform" # 비중축소
    SELL = "sell"                  # 매도


@dataclass
class ConsensusData:
    """컨센서스 데이터"""
    broker: str
    target_price: int
    opinion: str
    report_date: datetime
    analyst: Optional[str] = None
    previous_target: Optional[int] = None


@dataclass
class ConsensusMomentumResult:
    """컨센서스 모멘텀 분석 결과"""
    ticker: str
    score: float  # -2.0 ~ +2.0
    trend: ConsensusTrend
    current_price: int
    average_target: int
    upside_potential: float  # %
    analyst_count: int
    buy_count: int
    hold_count: int
    sell_count: int
    target_change_3m: float  # 3개월 변화율 %
    recent_changes: List[Dict[str, Any]]
    analyzed_at: str
    details: Dict[str, Any] = field(default_factory=dict)


class ConsensusMomentumAnalyzer:
    """
    컨센서스 모멘텀 분석기

    Phase 4 Spec:
    - 증권사 목표가 추세 분석
    - 현재가 대비 괴리율 계산
    - 투자의견 변화 추적
    """

    # Naver 컨센서스 API
    NAVER_CONSENSUS_API = "https://m.stock.naver.com/api/stock/{ticker}/integration"

    # FnGuide 목표가 API (백업)
    FNGUIDE_API = "https://comp.fnguide.com/SVO2/json/chart/01_01/A{ticker}_consensusMainChart_D.json"

    # 캐시 TTL (1시간)
    CACHE_TTL = timedelta(hours=1)

    # 점수 체계
    SCORE_WEIGHTS = {
        'upside_potential': 0.4,   # 상승여력 40%
        'trend': 0.3,              # 추세 30%
        'opinion_ratio': 0.3,     # 의견 비율 30%
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, Tuple[ConsensusMomentumResult, datetime]] = {}

    async def analyze(self, ticker: str) -> ConsensusMomentumResult:
        """
        종목의 컨센서스 모멘텀 분석

        Args:
            ticker: 종목코드

        Returns:
            ConsensusMomentumResult: 분석 결과
        """
        # 캐시 확인
        if ticker in self._cache:
            cached, cached_at = self._cache[ticker]
            if datetime.now() - cached_at < self.CACHE_TTL:
                self.logger.debug(f"Cache hit for {ticker}")
                return cached

        self.logger.info(f"Analyzing consensus momentum for {ticker}")

        # 1. 현재가 조회
        current_price = await self._get_current_price(ticker)

        # 2. 컨센서스 데이터 수집
        consensus_data = await self._fetch_consensus(ticker)

        if not consensus_data:
            return self._create_empty_result(ticker, current_price)

        # 3. 통계 계산
        stats = self._calculate_stats(consensus_data, current_price)

        # 4. 추세 분석
        trend = self._analyze_trend(stats['target_change_3m'])

        # 5. 최종 점수 계산
        final_score = self._calculate_score(stats, trend)

        # 6. 최근 변화 추출
        recent_changes = self._extract_recent_changes(consensus_data)

        result = ConsensusMomentumResult(
            ticker=ticker,
            score=round(final_score, 2),
            trend=trend,
            current_price=current_price,
            average_target=stats['average_target'],
            upside_potential=stats['upside_potential'],
            analyst_count=stats['analyst_count'],
            buy_count=stats['buy_count'],
            hold_count=stats['hold_count'],
            sell_count=stats['sell_count'],
            target_change_3m=stats['target_change_3m'],
            recent_changes=recent_changes,
            analyzed_at=datetime.now().isoformat(),
            details={
                'median_target': stats['median_target'],
                'high_target': stats['high_target'],
                'low_target': stats['low_target'],
                'opinion_score': stats['opinion_score'],
            }
        )

        # 캐시 저장
        self._cache[ticker] = (result, datetime.now())

        return result

    async def _get_current_price(self, ticker: str) -> int:
        """현재가 조회"""
        try:
            # pykrx로 조회
            today = datetime.now().strftime('%Y%m%d')
            df = pykrx.get_market_ohlcv_by_date(
                fromdate=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                todate=today,
                ticker=ticker
            )

            if not df.empty:
                return int(df['종가'].iloc[-1])

        except Exception as e:
            self.logger.warning(f"Failed to get current price: {e}")

        return 0

    async def _fetch_consensus(self, ticker: str) -> List[ConsensusData]:
        """컨센서스 데이터 수집"""
        consensus_list = []

        # Naver API 시도
        naver_data = await self._fetch_naver_consensus(ticker)
        if naver_data:
            consensus_list.extend(naver_data)

        # 데이터가 부족하면 FnGuide 시도
        if len(consensus_list) < 3:
            fnguide_data = await self._fetch_fnguide_consensus(ticker)
            if fnguide_data:
                consensus_list.extend(fnguide_data)

        # 중복 제거 (브로커 + 날짜 기준)
        seen = set()
        unique_list = []
        for item in consensus_list:
            key = f"{item.broker}_{item.report_date.date()}"
            if key not in seen:
                seen.add(key)
                unique_list.append(item)

        return unique_list

    async def _fetch_naver_consensus(self, ticker: str) -> List[ConsensusData]:
        """Naver 컨센서스 API 조회"""
        try:
            url = self.NAVER_CONSENSUS_API.format(ticker=ticker)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()

                    # 투자의견 파싱
                    consensus_info = data.get('consensusInfo', {})
                    if not consensus_info:
                        return []

                    # 평균 목표가
                    target_price = self._parse_int(consensus_info.get('targetPrice'))

                    # 의견 분포
                    opinion_data = consensus_info.get('investmentOpinion', {})

                    result = []

                    # 집계 데이터로 가상 ConsensusData 생성
                    if target_price > 0:
                        result.append(ConsensusData(
                            broker='Consensus Average',
                            target_price=target_price,
                            opinion=opinion_data.get('text', 'N/A'),
                            report_date=datetime.now(),
                        ))

                    return result

        except Exception as e:
            self.logger.warning(f"Naver consensus fetch failed: {e}")
            return []

    async def _fetch_fnguide_consensus(self, ticker: str) -> List[ConsensusData]:
        """FnGuide 컨센서스 조회"""
        try:
            url = self.FNGUIDE_API.format(ticker=ticker)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()

                    result = []
                    for item in data.get('chart', []):
                        try:
                            target = self._parse_int(item.get('TARGET_PRC'))
                            if target <= 0:
                                continue

                            date_str = item.get('TRD_DT', '')
                            report_date = datetime.strptime(date_str, '%Y%m%d') if date_str else datetime.now()

                            result.append(ConsensusData(
                                broker=item.get('RATER_NM', 'Unknown'),
                                target_price=target,
                                opinion=item.get('RECOMM_NM', 'N/A'),
                                report_date=report_date,
                            ))
                        except (ValueError, TypeError):
                            continue

                    return result

        except Exception as e:
            self.logger.warning(f"FnGuide consensus fetch failed: {e}")
            return []

    def _parse_int(self, value: Any) -> int:
        """숫자 파싱"""
        if value is None:
            return 0
        try:
            return int(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0

    def _calculate_stats(
        self,
        consensus_data: List[ConsensusData],
        current_price: int
    ) -> Dict[str, Any]:
        """통계 계산"""
        if not consensus_data:
            return {
                'average_target': 0,
                'median_target': 0,
                'high_target': 0,
                'low_target': 0,
                'upside_potential': 0.0,
                'analyst_count': 0,
                'buy_count': 0,
                'hold_count': 0,
                'sell_count': 0,
                'target_change_3m': 0.0,
                'opinion_score': 0.0,
            }

        targets = [c.target_price for c in consensus_data if c.target_price > 0]

        if not targets:
            return self._calculate_stats([], current_price)

        avg_target = sum(targets) // len(targets)
        sorted_targets = sorted(targets)
        median_target = sorted_targets[len(sorted_targets) // 2]

        # 상승여력 계산
        upside = ((avg_target - current_price) / current_price * 100) if current_price > 0 else 0

        # 의견 분류
        buy_count = 0
        hold_count = 0
        sell_count = 0

        for c in consensus_data:
            opinion_lower = c.opinion.lower() if c.opinion else ''
            if any(k in opinion_lower for k in ['buy', '매수', '적극', '강력']):
                buy_count += 1
            elif any(k in opinion_lower for k in ['hold', '중립', '보유']):
                hold_count += 1
            elif any(k in opinion_lower for k in ['sell', '매도', '축소', 'under']):
                sell_count += 1
            else:
                hold_count += 1  # 기본값

        total_opinions = buy_count + hold_count + sell_count
        opinion_score = 0.0
        if total_opinions > 0:
            # 매수 비율에 따른 점수 (-1 ~ +1)
            opinion_score = (buy_count - sell_count) / total_opinions

        # 3개월 변화율 (데이터 부족 시 0)
        target_change_3m = 0.0
        three_months_ago = datetime.now() - timedelta(days=90)
        old_data = [c for c in consensus_data if c.report_date < three_months_ago]
        recent_data = [c for c in consensus_data if c.report_date >= three_months_ago]

        if old_data and recent_data:
            old_avg = sum(c.target_price for c in old_data) / len(old_data)
            recent_avg = sum(c.target_price for c in recent_data) / len(recent_data)
            if old_avg > 0:
                target_change_3m = ((recent_avg - old_avg) / old_avg) * 100

        return {
            'average_target': avg_target,
            'median_target': median_target,
            'high_target': max(targets),
            'low_target': min(targets),
            'upside_potential': round(upside, 2),
            'analyst_count': len(consensus_data),
            'buy_count': buy_count,
            'hold_count': hold_count,
            'sell_count': sell_count,
            'target_change_3m': round(target_change_3m, 2),
            'opinion_score': round(opinion_score, 2),
        }

    def _analyze_trend(self, target_change_3m: float) -> ConsensusTrend:
        """추세 분석"""
        if target_change_3m >= 20:
            return ConsensusTrend.STRONG_UPGRADE
        elif target_change_3m >= 10:
            return ConsensusTrend.UPGRADE
        elif target_change_3m <= -20:
            return ConsensusTrend.STRONG_DOWNGRADE
        elif target_change_3m <= -10:
            return ConsensusTrend.DOWNGRADE
        else:
            return ConsensusTrend.STABLE

    def _calculate_score(
        self,
        stats: Dict[str, Any],
        trend: ConsensusTrend
    ) -> float:
        """최종 점수 계산"""
        # 1. 상승여력 점수 (-2 ~ +2)
        upside = stats['upside_potential']
        if upside >= 50:
            upside_score = 2.0
        elif upside >= 30:
            upside_score = 1.5
        elif upside >= 15:
            upside_score = 1.0
        elif upside >= 5:
            upside_score = 0.5
        elif upside >= -5:
            upside_score = 0.0
        elif upside >= -15:
            upside_score = -0.5
        elif upside >= -30:
            upside_score = -1.0
        else:
            upside_score = -2.0

        # 2. 추세 점수
        trend_scores = {
            ConsensusTrend.STRONG_UPGRADE: 2.0,
            ConsensusTrend.UPGRADE: 1.0,
            ConsensusTrend.STABLE: 0.0,
            ConsensusTrend.DOWNGRADE: -1.0,
            ConsensusTrend.STRONG_DOWNGRADE: -2.0,
        }
        trend_score = trend_scores.get(trend, 0.0)

        # 3. 의견 비율 점수 (-1 ~ +1) → (-2 ~ +2)
        opinion_score = stats['opinion_score'] * 2

        # 가중 합계
        final_score = (
            upside_score * self.SCORE_WEIGHTS['upside_potential'] +
            trend_score * self.SCORE_WEIGHTS['trend'] +
            opinion_score * self.SCORE_WEIGHTS['opinion_ratio']
        )

        return max(-2.0, min(2.0, final_score))

    def _extract_recent_changes(self, consensus_data: List[ConsensusData]) -> List[Dict[str, Any]]:
        """최근 변화 추출"""
        # 최근 30일 데이터만
        cutoff = datetime.now() - timedelta(days=30)
        recent = [c for c in consensus_data if c.report_date >= cutoff]

        # 날짜순 정렬
        recent.sort(key=lambda x: x.report_date, reverse=True)

        return [
            {
                'broker': c.broker,
                'target_price': c.target_price,
                'opinion': c.opinion,
                'date': c.report_date.isoformat(),
            }
            for c in recent[:10]
        ]

    def _create_empty_result(self, ticker: str, current_price: int) -> ConsensusMomentumResult:
        """빈 결과 생성"""
        return ConsensusMomentumResult(
            ticker=ticker,
            score=0.0,
            trend=ConsensusTrend.STABLE,
            current_price=current_price,
            average_target=0,
            upside_potential=0.0,
            analyst_count=0,
            buy_count=0,
            hold_count=0,
            sell_count=0,
            target_change_3m=0.0,
            recent_changes=[],
            analyzed_at=datetime.now().isoformat(),
        )

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self.logger.info("Consensus momentum cache cleared")


# Singleton instance
_analyzer_instance: Optional[ConsensusMomentumAnalyzer] = None


def get_consensus_momentum_analyzer() -> ConsensusMomentumAnalyzer:
    """Get singleton ConsensusMomentumAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ConsensusMomentumAnalyzer()
    return _analyzer_instance


# Convenience function
async def analyze_consensus_momentum(ticker: str) -> ConsensusMomentumResult:
    """컨센서스 모멘텀 분석 편의 함수"""
    analyzer = get_consensus_momentum_analyzer()
    return await analyzer.analyze(ticker)
