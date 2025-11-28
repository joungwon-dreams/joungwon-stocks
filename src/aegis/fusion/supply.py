"""
Supply Demand Analyzer - Phase 4
외국인/기관 수급 분석을 통한 투자 신호 생성

핵심 기능:
- 외국인/기관 순매수 동향 분석
- 양매수(Dual Buy) 패턴 감지
- 연속 순매수 패턴 감지
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from pykrx import stock


class SupplyPattern(Enum):
    """수급 패턴 분류"""
    DUAL_BUY = "dual_buy"           # 외국인+기관 동시 순매수
    FOREIGN_BUY = "foreign_buy"     # 외국인 순매수
    INST_BUY = "inst_buy"           # 기관 순매수
    DUAL_SELL = "dual_sell"         # 외국인+기관 동시 순매도
    FOREIGN_SELL = "foreign_sell"   # 외국인 순매도
    INST_SELL = "inst_sell"         # 기관 순매도
    NEUTRAL = "neutral"             # 중립


@dataclass
class SupplyDemandResult:
    """수급 분석 결과"""
    ticker: str
    score: float
    pattern: SupplyPattern
    foreign_net: int           # 외국인 순매수 (주)
    inst_net: int              # 기관 순매수 (주)
    foreign_consecutive: int   # 외국인 연속 순매수 일수
    inst_consecutive: int      # 기관 연속 순매수 일수
    details: Dict[str, Any]
    analyzed_at: str


class SupplyDemandAnalyzer:
    """
    수급 분석기

    Phase 4 Spec:
    - Foreigner/Institutional Dual Buy: +1.0
    - Continuous Net Buying (3+ days): +0.5
    - Program Net Buying: +0.5
    - High Short Selling Volume: -1.0
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, SupplyDemandResult] = {}
        self._cache_ttl = timedelta(minutes=10)

    async def analyze(self, ticker: str, days: int = 10) -> SupplyDemandResult:
        """
        종목의 수급 데이터를 분석하여 점수 반환

        Args:
            ticker: 종목코드 (예: "005930")
            days: 분석할 기간 (기본 10일)

        Returns:
            SupplyDemandResult: 분석 결과
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
            # pykrx에서 투자자별 거래 데이터 조회
            investor_data = await self._fetch_investor_data(ticker, days)

            if not investor_data:
                return self._empty_result(ticker)

            # 분석 수행
            score, pattern, details = self._analyze_supply_demand(investor_data)

            # 연속 순매수 일수 계산
            foreign_consecutive = self._count_consecutive_buy(
                investor_data, 'foreign_net'
            )
            inst_consecutive = self._count_consecutive_buy(
                investor_data, 'inst_net'
            )

            # 최근 데이터 (오늘 또는 가장 최근)
            latest = investor_data[-1] if investor_data else {}

            result = SupplyDemandResult(
                ticker=ticker,
                score=score,
                pattern=pattern,
                foreign_net=latest.get('foreign_net', 0),
                inst_net=latest.get('inst_net', 0),
                foreign_consecutive=foreign_consecutive,
                inst_consecutive=inst_consecutive,
                details=details,
                analyzed_at=datetime.now().isoformat()
            )

            # 캐시 저장
            self._cache[cache_key] = result

            self.logger.info(
                f"Supply analysis for {ticker}: "
                f"score={score:.2f}, pattern={pattern.value}, "
                f"foreign_cons={foreign_consecutive}, inst_cons={inst_consecutive}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to analyze supply/demand for {ticker}: {e}")
            return self._empty_result(ticker)

    async def _fetch_investor_data(self, ticker: str, days: int) -> List[Dict[str, Any]]:
        """pykrx에서 투자자별 거래 데이터 조회"""
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days + 5)).strftime("%Y%m%d")

            # 투자자별 순매수 데이터
            df = await asyncio.to_thread(
                stock.get_market_trading_value_by_date,
                start_date, end_date, ticker
            )

            if df is None or df.empty:
                return []

            # DataFrame 처리
            data_list = []
            for date_idx, row in df.iterrows():
                try:
                    # 외국인 순매수 (매수-매도)
                    foreign_net = int(row.get('외국인합계', 0))
                    # 기관 순매수
                    inst_net = int(row.get('기관합계', 0))
                    # 개인 순매수
                    retail_net = int(row.get('개인', 0))

                    data_list.append({
                        'date': date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, 'strftime') else str(date_idx),
                        'foreign_net': foreign_net,
                        'inst_net': inst_net,
                        'retail_net': retail_net,
                    })
                except Exception as e:
                    self.logger.debug(f"Skip row: {e}")
                    continue

            return data_list[-days:]  # 최근 N일

        except Exception as e:
            self.logger.error(f"Failed to fetch investor data: {e}")
            return []

    def _analyze_supply_demand(
        self, data: List[Dict[str, Any]]
    ) -> tuple[float, SupplyPattern, Dict[str, Any]]:
        """수급 데이터 분석"""
        if not data:
            return 0.0, SupplyPattern.NEUTRAL, {}

        score = 0.0
        details = {}

        # 최근 데이터 기준
        latest = data[-1]
        foreign_net = latest.get('foreign_net', 0)
        inst_net = latest.get('inst_net', 0)

        # 기간 합계
        total_foreign = sum(d.get('foreign_net', 0) for d in data)
        total_inst = sum(d.get('inst_net', 0) for d in data)

        details['latest_foreign'] = foreign_net
        details['latest_inst'] = inst_net
        details['total_foreign'] = total_foreign
        details['total_inst'] = total_inst

        # 1. 양매수 패턴 (Dual Buy): +1.0
        if foreign_net > 0 and inst_net > 0:
            pattern = SupplyPattern.DUAL_BUY
            score += 1.0
            details['dual_buy'] = True
        elif foreign_net < 0 and inst_net < 0:
            pattern = SupplyPattern.DUAL_SELL
            score -= 1.0
            details['dual_sell'] = True
        elif foreign_net > 0:
            pattern = SupplyPattern.FOREIGN_BUY
            score += 0.3
        elif inst_net > 0:
            pattern = SupplyPattern.INST_BUY
            score += 0.3
        elif foreign_net < 0:
            pattern = SupplyPattern.FOREIGN_SELL
            score -= 0.3
        elif inst_net < 0:
            pattern = SupplyPattern.INST_SELL
            score -= 0.3
        else:
            pattern = SupplyPattern.NEUTRAL

        # 2. 연속 순매수 보너스: +0.5 (3일 이상)
        foreign_cons = self._count_consecutive_buy(data, 'foreign_net')
        inst_cons = self._count_consecutive_buy(data, 'inst_net')

        if foreign_cons >= 3:
            score += 0.5
            details['foreign_consecutive_bonus'] = True
        if inst_cons >= 3:
            score += 0.5
            details['inst_consecutive_bonus'] = True

        # 3. 기간 누적 순매수 (추세)
        if total_foreign > 0 and total_inst > 0:
            score += 0.2  # 기간 중 양매수 추세
            details['period_dual_buy_trend'] = True

        # 점수 정규화 (-2.0 ~ +2.0)
        final_score = max(-2.0, min(2.0, score))

        return final_score, pattern, details

    def _count_consecutive_buy(self, data: List[Dict[str, Any]], key: str) -> int:
        """연속 순매수 일수 계산 (최근부터)"""
        if not data:
            return 0

        count = 0
        # 최근부터 역순으로
        for d in reversed(data):
            if d.get(key, 0) > 0:
                count += 1
            else:
                break

        return count

    def _empty_result(self, ticker: str) -> SupplyDemandResult:
        """빈 결과 반환"""
        return SupplyDemandResult(
            ticker=ticker,
            score=0.0,
            pattern=SupplyPattern.NEUTRAL,
            foreign_net=0,
            inst_net=0,
            foreign_consecutive=0,
            inst_consecutive=0,
            details={},
            analyzed_at=datetime.now().isoformat()
        )

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


# Singleton instance
_analyzer_instance: Optional[SupplyDemandAnalyzer] = None


def get_supply_demand_analyzer() -> SupplyDemandAnalyzer:
    """Get singleton SupplyDemandAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SupplyDemandAnalyzer()
    return _analyzer_instance


# Convenience function
async def analyze_supply_demand(ticker: str, days: int = 10) -> SupplyDemandResult:
    """수급 분석 편의 함수"""
    analyzer = get_supply_demand_analyzer()
    return await analyzer.analyze(ticker, days)
