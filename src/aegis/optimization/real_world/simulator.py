"""
Execution Simulator - Phase 6
현실적 수익 계산 (슬리피지, 세금, 수수료)

핵심 기능:
- 매수/매도 슬리피지 적용
- 거래세 + 수수료 반영
- 시간대별 가중치 조정
"""
import asyncio
from datetime import datetime, time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class TimeSegment(Enum):
    """시간대 구분"""
    PREMARKET = "premarket"         # 08:30 ~ 09:00
    OPENING = "opening"             # 09:00 ~ 09:30 (변동성 돌파)
    MORNING = "morning"             # 09:30 ~ 11:30
    LUNCH = "lunch"                 # 11:30 ~ 13:00
    AFTERNOON = "afternoon"         # 13:00 ~ 14:30 (추세추종)
    CLOSING = "closing"             # 14:30 ~ 15:20 (종가 베팅)
    AFTER_HOURS = "after_hours"     # 15:30 ~ 18:00
    CLOSED = "closed"               # 장 마감


class OrderType(Enum):
    """주문 유형"""
    MARKET = "market"       # 시장가
    LIMIT = "limit"         # 지정가
    CONDITIONAL = "conditional"  # 조건부


@dataclass
class ExecutionResult:
    """실행 시뮬레이션 결과"""
    ticker: str
    order_type: str  # "buy" / "sell"

    # 가격 정보
    signal_price: float      # 신호 발생 시점 가격
    expected_price: float    # 예상 체결 가격 (슬리피지 적용)
    slippage: float          # 슬리피지 금액
    slippage_pct: float      # 슬리피지 비율 (%)

    # 비용
    tax_fee: float           # 세금 + 수수료
    tax_fee_pct: float       # 세금 + 수수료 비율 (%)

    # 순수익 계산
    quantity: int            # 수량
    gross_amount: float      # 총 거래금액
    net_amount: float        # 순 거래금액 (비용 차감)

    # 시간대 정보
    time_segment: TimeSegment
    weight_adjustment: float  # 시간대별 가중치 조정

    # 메타데이터
    simulated_at: str


@dataclass
class PnLSimulation:
    """손익 시뮬레이션"""
    ticker: str

    # 매수 정보
    buy_price: float
    buy_slippage: float
    buy_cost: float  # 세금+수수료

    # 매도 정보
    sell_price: float
    sell_slippage: float
    sell_cost: float  # 세금+수수료

    # 손익 계산
    gross_profit: float       # 총 수익 (슬리피지만 반영)
    total_cost: float         # 총 비용 (세금+수수료)
    net_profit: float         # 순수익
    net_profit_pct: float     # 순수익률 (%)

    # 손익분기점
    breakeven_pct: float      # 손익분기 상승률 (%)


class ExecutionSimulator:
    """
    실행 시뮬레이터

    Phase 6 Spec:
    - 현실적인 체결가 시뮬레이션
    - 거래세 + 수수료 반영
    - 시간대별 전략 가중치 조정
    """

    # 비용 상수 (2024년 기준)
    COSTS = {
        'trading_tax': 0.0018,      # 거래세 0.18% (코스피)
        'trading_tax_kosdaq': 0.0018,  # 거래세 0.18% (코스닥)
        'brokerage_fee': 0.00015,   # 증권사 수수료 0.015% (온라인)
        'total_sell_cost': 0.0023,  # 매도 시 총 비용 0.23%
        'total_buy_cost': 0.00015,  # 매수 시 총 비용 (수수료만)
    }

    # 호가 단위 (가격대별)
    TICK_SIZES = [
        (2000, 1),
        (5000, 5),
        (20000, 10),
        (50000, 50),
        (200000, 100),
        (500000, 500),
        (float('inf'), 1000),
    ]

    # 시간대별 가중치 조정
    TIME_WEIGHTS = {
        TimeSegment.PREMARKET: {
            'volatility_breakout': 0.8,
            'trend_following': 0.5,
            'supply_demand': 0.6,
        },
        TimeSegment.OPENING: {
            'volatility_breakout': 1.5,  # 변동성 돌파 강화
            'trend_following': 0.7,
            'supply_demand': 0.8,
        },
        TimeSegment.MORNING: {
            'volatility_breakout': 1.0,
            'trend_following': 1.2,
            'supply_demand': 1.1,
        },
        TimeSegment.LUNCH: {
            'volatility_breakout': 0.6,
            'trend_following': 0.8,
            'supply_demand': 0.7,
        },
        TimeSegment.AFTERNOON: {
            'volatility_breakout': 0.8,
            'trend_following': 1.3,  # 추세추종 강화
            'supply_demand': 1.4,    # 수급 분석 강화
        },
        TimeSegment.CLOSING: {
            'volatility_breakout': 0.5,
            'trend_following': 1.0,
            'supply_demand': 1.5,    # 종가 베팅
        },
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_current_time_segment(self) -> TimeSegment:
        """현재 시간대 반환"""
        now = datetime.now().time()

        if time(8, 30) <= now < time(9, 0):
            return TimeSegment.PREMARKET
        elif time(9, 0) <= now < time(9, 30):
            return TimeSegment.OPENING
        elif time(9, 30) <= now < time(11, 30):
            return TimeSegment.MORNING
        elif time(11, 30) <= now < time(13, 0):
            return TimeSegment.LUNCH
        elif time(13, 0) <= now < time(14, 30):
            return TimeSegment.AFTERNOON
        elif time(14, 30) <= now < time(15, 20):
            return TimeSegment.CLOSING
        elif time(15, 30) <= now < time(18, 0):
            return TimeSegment.AFTER_HOURS
        else:
            return TimeSegment.CLOSED

    def get_tick_size(self, price: float) -> int:
        """가격대별 호가 단위 반환"""
        for threshold, tick in self.TICK_SIZES:
            if price < threshold:
                return tick
        return 1000

    def calculate_slippage(
        self,
        price: float,
        order_type: str,
        ticks: int = 1
    ) -> Tuple[float, float]:
        """
        슬리피지 계산

        Args:
            price: 현재가
            order_type: "buy" / "sell"
            ticks: 슬리피지 호가 수

        Returns:
            (슬리피지 적용 가격, 슬리피지 금액)
        """
        tick_size = self.get_tick_size(price)
        slippage_amount = tick_size * ticks

        if order_type == "buy":
            # 매수: 현재가 + 1호가
            expected_price = price + slippage_amount
        else:
            # 매도: 현재가 - 1호가
            expected_price = price - slippage_amount

        return expected_price, slippage_amount

    def simulate_buy(
        self,
        ticker: str,
        price: float,
        quantity: int,
        slippage_ticks: int = 1
    ) -> ExecutionResult:
        """
        매수 시뮬레이션

        Args:
            ticker: 종목코드
            price: 현재가
            quantity: 수량
            slippage_ticks: 슬리피지 호가 수

        Returns:
            ExecutionResult: 시뮬레이션 결과
        """
        time_segment = self.get_current_time_segment()

        # 슬리피지 계산
        expected_price, slippage = self.calculate_slippage(
            price, "buy", slippage_ticks
        )
        slippage_pct = (slippage / price) * 100

        # 비용 계산 (매수: 수수료만)
        gross_amount = expected_price * quantity
        tax_fee = gross_amount * self.COSTS['total_buy_cost']
        tax_fee_pct = self.COSTS['total_buy_cost'] * 100
        net_amount = gross_amount + tax_fee

        # 시간대별 가중치
        weight_adj = self.TIME_WEIGHTS.get(
            time_segment, {}
        ).get('trend_following', 1.0)

        return ExecutionResult(
            ticker=ticker,
            order_type="buy",
            signal_price=price,
            expected_price=expected_price,
            slippage=slippage,
            slippage_pct=slippage_pct,
            tax_fee=tax_fee,
            tax_fee_pct=tax_fee_pct,
            quantity=quantity,
            gross_amount=gross_amount,
            net_amount=net_amount,
            time_segment=time_segment,
            weight_adjustment=weight_adj,
            simulated_at=datetime.now().isoformat()
        )

    def simulate_sell(
        self,
        ticker: str,
        price: float,
        quantity: int,
        slippage_ticks: int = 1
    ) -> ExecutionResult:
        """
        매도 시뮬레이션

        Args:
            ticker: 종목코드
            price: 현재가
            quantity: 수량
            slippage_ticks: 슬리피지 호가 수

        Returns:
            ExecutionResult: 시뮬레이션 결과
        """
        time_segment = self.get_current_time_segment()

        # 슬리피지 계산
        expected_price, slippage = self.calculate_slippage(
            price, "sell", slippage_ticks
        )
        slippage_pct = (slippage / price) * 100

        # 비용 계산 (매도: 세금 + 수수료)
        gross_amount = expected_price * quantity
        tax_fee = gross_amount * self.COSTS['total_sell_cost']
        tax_fee_pct = self.COSTS['total_sell_cost'] * 100
        net_amount = gross_amount - tax_fee

        # 시간대별 가중치
        weight_adj = self.TIME_WEIGHTS.get(
            time_segment, {}
        ).get('trend_following', 1.0)

        return ExecutionResult(
            ticker=ticker,
            order_type="sell",
            signal_price=price,
            expected_price=expected_price,
            slippage=slippage,
            slippage_pct=slippage_pct,
            tax_fee=tax_fee,
            tax_fee_pct=tax_fee_pct,
            quantity=quantity,
            gross_amount=gross_amount,
            net_amount=net_amount,
            time_segment=time_segment,
            weight_adjustment=weight_adj,
            simulated_at=datetime.now().isoformat()
        )

    def simulate_round_trip(
        self,
        ticker: str,
        buy_price: float,
        sell_price: float,
        quantity: int,
        slippage_ticks: int = 1
    ) -> PnLSimulation:
        """
        왕복 거래 손익 시뮬레이션

        Args:
            ticker: 종목코드
            buy_price: 매수가
            sell_price: 매도가
            quantity: 수량
            slippage_ticks: 슬리피지 호가 수

        Returns:
            PnLSimulation: 손익 시뮬레이션 결과
        """
        # 매수 슬리피지
        buy_expected, buy_slippage = self.calculate_slippage(
            buy_price, "buy", slippage_ticks
        )
        buy_amount = buy_expected * quantity
        buy_cost = buy_amount * self.COSTS['total_buy_cost']

        # 매도 슬리피지
        sell_expected, sell_slippage = self.calculate_slippage(
            sell_price, "sell", slippage_ticks
        )
        sell_amount = sell_expected * quantity
        sell_cost = sell_amount * self.COSTS['total_sell_cost']

        # 손익 계산
        gross_profit = sell_amount - buy_amount  # 슬리피지만 반영
        total_cost = buy_cost + sell_cost
        net_profit = gross_profit - total_cost
        net_profit_pct = (net_profit / buy_amount) * 100

        # 손익분기점 계산
        # 매수비용 + 매도비용 + 슬리피지를 커버하려면 얼마나 올라야 하는가?
        total_cost_pct = (
            self.COSTS['total_buy_cost'] +
            self.COSTS['total_sell_cost'] +
            (buy_slippage / buy_price) +
            (sell_slippage / sell_price)
        )
        breakeven_pct = total_cost_pct * 100

        return PnLSimulation(
            ticker=ticker,
            buy_price=buy_expected,
            buy_slippage=buy_slippage,
            buy_cost=buy_cost,
            sell_price=sell_expected,
            sell_slippage=sell_slippage,
            sell_cost=sell_cost,
            gross_profit=round(gross_profit, 0),
            total_cost=round(total_cost, 0),
            net_profit=round(net_profit, 0),
            net_profit_pct=round(net_profit_pct, 2),
            breakeven_pct=round(breakeven_pct, 2)
        )

    def get_time_based_weight_adjustment(
        self,
        strategy: str = 'trend_following'
    ) -> float:
        """
        현재 시간대에 따른 가중치 조정값 반환

        Args:
            strategy: 전략 유형 ('volatility_breakout', 'trend_following', 'supply_demand')

        Returns:
            가중치 조정 계수 (0.5 ~ 1.5)
        """
        segment = self.get_current_time_segment()
        return self.TIME_WEIGHTS.get(segment, {}).get(strategy, 1.0)

    def estimate_breakeven(self, price: float) -> Dict[str, float]:
        """
        손익분기점 상승률 추정

        Args:
            price: 현재가

        Returns:
            손익분기 정보
        """
        tick_size = self.get_tick_size(price)

        # 슬리피지 비율
        buy_slippage_pct = (tick_size / price) * 100
        sell_slippage_pct = (tick_size / price) * 100

        # 비용 비율
        buy_cost_pct = self.COSTS['total_buy_cost'] * 100
        sell_cost_pct = self.COSTS['total_sell_cost'] * 100

        # 총 손익분기점
        total_breakeven = (
            buy_slippage_pct +
            sell_slippage_pct +
            buy_cost_pct +
            sell_cost_pct
        )

        return {
            'price': price,
            'tick_size': tick_size,
            'buy_slippage_pct': round(buy_slippage_pct, 3),
            'sell_slippage_pct': round(sell_slippage_pct, 3),
            'buy_cost_pct': round(buy_cost_pct, 3),
            'sell_cost_pct': round(sell_cost_pct, 3),
            'total_breakeven_pct': round(total_breakeven, 3),
            'note': f"최소 {total_breakeven:.2f}% 상승해야 본전"
        }


# Singleton instance
_simulator_instance: Optional[ExecutionSimulator] = None


def get_execution_simulator() -> ExecutionSimulator:
    """Get singleton ExecutionSimulator instance"""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = ExecutionSimulator()
    return _simulator_instance
