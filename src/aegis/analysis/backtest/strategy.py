"""
PROJECT AEGIS - Strategy Interface
===================================
Strategy interface for backtesting
"""

from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class OrderType(Enum):
    """Order Type"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Order:
    """Order Info"""
    order_type: OrderType
    price: float
    quantity: int
    timestamp: pd.Timestamp
    reason: str = ""


@dataclass
class Position:
    """Position Info"""
    stock_code: str
    quantity: int
    avg_price: float
    current_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_price == 0:
            return 0.0
        return (self.current_price - self.avg_price) / self.avg_price * 100


class StrategyInterface(ABC):
    """Strategy Abstract Base Class"""

    def __init__(self, name: str):
        self.name = name
        self.position: Optional[Position] = None
        self.orders: List[Order] = []

    @abstractmethod
    def calculate_signal(self, df: pd.DataFrame, index: int) -> OrderType:
        pass

    @abstractmethod
    def calculate_quantity(self, capital: float, price: float, signal: OrderType) -> int:
        pass

    def on_order_filled(self, order: Order) -> None:
        self.orders.append(order)

    def reset(self) -> None:
        self.position = None
        self.orders = []


class AegisSwingStrategy(StrategyInterface):
    """AEGIS Swing Trading Strategy (Trend Following)"""

    def __init__(
        self,
        buy_threshold: int = 2,
        sell_threshold: int = -2,
        capital_per_trade_pct: float = 0.2
    ):
        super().__init__("AEGIS Swing Strategy")
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.capital_per_trade_pct = capital_per_trade_pct

    def calculate_signal(self, df: pd.DataFrame, index: int) -> OrderType:
        if 'total_score' not in df.columns:
            raise ValueError("DataFrame must contain 'total_score' column")

        score = df['total_score'].iloc[index]

        if score >= self.buy_threshold and self.position is None:
            return OrderType.BUY
        if score <= self.sell_threshold and self.position is not None:
            return OrderType.SELL
        return OrderType.HOLD

    def calculate_quantity(self, capital: float, price: float, signal: OrderType) -> int:
        if signal == OrderType.BUY:
            available = capital * self.capital_per_trade_pct
            return int(available / price)
        elif signal == OrderType.SELL:
            return self.position.quantity if self.position else 0
        return 0


class MeanReversionStrategy(StrategyInterface):
    """
    Mean Reversion Strategy (Bollinger Band based)

    Logic:
    - BUY when price touches lower Bollinger Band (oversold)
    - SELL when price touches upper Bollinger Band (overbought)

    Best for SIDEWAY markets with range-bound price action
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        capital_per_trade_pct: float = 0.2
    ):
        super().__init__("Mean Reversion Strategy")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.capital_per_trade_pct = capital_per_trade_pct
        self._bb_calculated = False
        self._bb_upper = None
        self._bb_lower = None
        self._bb_middle = None

    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> None:
        """Calculate Bollinger Bands"""
        close = df['close'].astype(float)
        self._bb_middle = close.rolling(window=self.bb_period).mean()
        bb_std = close.rolling(window=self.bb_period).std()
        self._bb_upper = self._bb_middle + (bb_std * self.bb_std)
        self._bb_lower = self._bb_middle - (bb_std * self.bb_std)
        self._bb_calculated = True

    def calculate_signal(self, df: pd.DataFrame, index: int) -> OrderType:
        # Calculate Bollinger Bands if not done
        if not self._bb_calculated or len(df) != len(self._bb_middle):
            self._calculate_bollinger_bands(df)

        price = float(df['close'].iloc[index])
        upper = self._bb_upper.iloc[index]
        lower = self._bb_lower.iloc[index]

        # Handle NaN
        if pd.isna(upper) or pd.isna(lower):
            return OrderType.HOLD

        # BUY at lower band (oversold)
        if price <= lower and self.position is None:
            return OrderType.BUY

        # SELL at upper band (overbought) or if holding and price returns to middle
        if self.position is not None:
            if price >= upper:
                return OrderType.SELL
            # Also sell if price returns to middle band (take profit)
            middle = self._bb_middle.iloc[index]
            if not pd.isna(middle) and price >= middle:
                return OrderType.SELL

        return OrderType.HOLD

    def calculate_quantity(self, capital: float, price: float, signal: OrderType) -> int:
        if signal == OrderType.BUY:
            available = capital * self.capital_per_trade_pct
            return int(available / price)
        elif signal == OrderType.SELL:
            return self.position.quantity if self.position else 0
        return 0

    def reset(self) -> None:
        super().reset()
        self._bb_calculated = False
        self._bb_upper = None
        self._bb_lower = None
        self._bb_middle = None
