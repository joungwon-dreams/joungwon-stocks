"""
PROJECT AEGIS - Risk Manager
=============================
Position sizing and dynamic stop-loss calculation

Features:
- Kelly Criterion for optimal position sizing
- Fixed Fractional Risk (1-2% per trade)
- ATR-based dynamic stop-loss
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RiskConfig:
    """Risk Management Configuration"""
    # Position Sizing
    max_capital_per_trade_pct: float = 0.20    # 20% max per single trade
    risk_per_trade_pct: float = 0.02           # 2% risk per trade

    # Stop Loss
    atr_multiplier: float = 2.0               # ATR * 2 for stop-loss
    fixed_stop_loss_pct: float = 0.03         # 3% fixed stop-loss fallback

    # Kelly Criterion
    use_kelly: bool = False                   # Use Kelly for sizing
    kelly_fraction: float = 0.5               # Half-Kelly (conservative)

    # Circuit Breaker (daily limits)
    max_daily_loss_pct: float = 0.02          # -2% daily loss limit
    max_daily_trades: int = 10                # Max trades per day


class RiskManager:
    """
    Risk Manager for position sizing and stop-loss calculation

    Methods:
    - calculate_position_size: Determine how many shares to buy
    - calculate_dynamic_stop_loss: ATR-based stop-loss price
    - calculate_kelly_fraction: Kelly Criterion position sizing
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self._win_rate: float = 0.5
        self._avg_win: float = 1.0
        self._avg_loss: float = 1.0

    def update_statistics(self, win_rate: float, avg_win: float, avg_loss: float):
        """Update trading statistics for Kelly calculation"""
        self._win_rate = max(0.01, min(0.99, win_rate))
        self._avg_win = max(0.001, avg_win)
        self._avg_loss = max(0.001, avg_loss)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        ATR = Moving Average of True Range
        True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
        """
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)

        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def calculate_dynamic_stop_loss(
        self,
        df: pd.DataFrame,
        entry_price: Optional[float] = None
    ) -> float:
        """
        Calculate dynamic stop-loss based on ATR

        Stop Loss = Current Price - (ATR * multiplier)

        Returns:
            Stop-loss price level
        """
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]

        if pd.isna(current_atr) or current_atr <= 0:
            # Fallback to fixed stop-loss
            price = entry_price or float(df['close'].iloc[-1])
            return price * (1 - self.config.fixed_stop_loss_pct)

        price = entry_price or float(df['close'].iloc[-1])
        stop_loss = price - (current_atr * self.config.atr_multiplier)

        # Ensure stop-loss is not too tight (min 1%)
        min_stop = price * 0.99
        return min(stop_loss, min_stop)

    def calculate_kelly_fraction(self) -> float:
        """
        Calculate Kelly Criterion fraction

        Kelly % = W - [(1-W) / R]
        Where:
            W = Win rate
            R = Win/Loss ratio (avg_win / avg_loss)

        Returns:
            Optimal fraction of capital to risk (0.0 ~ 1.0)
        """
        w = self._win_rate
        r = self._avg_win / self._avg_loss if self._avg_loss > 0 else 1.0

        kelly = w - ((1 - w) / r)

        # Apply half-Kelly for safety
        kelly = kelly * self.config.kelly_fraction

        # Clamp to reasonable bounds
        return max(0.0, min(kelly, self.config.max_capital_per_trade_pct))

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: Optional[float] = None,
        df: Optional[pd.DataFrame] = None
    ) -> Tuple[int, float]:
        """
        Calculate optimal position size

        Two methods:
        1. Fixed Fractional: Risk X% of capital per trade
        2. Kelly Criterion: Optimal sizing based on win rate

        Args:
            capital: Available capital
            entry_price: Expected entry price
            stop_loss_price: Stop-loss price (optional)
            df: Price data for ATR calculation (optional)

        Returns:
            (quantity, stop_loss_price)
        """
        # Calculate stop-loss if not provided
        if stop_loss_price is None:
            if df is not None:
                stop_loss_price = self.calculate_dynamic_stop_loss(df, entry_price)
            else:
                stop_loss_price = entry_price * (1 - self.config.fixed_stop_loss_pct)

        # Calculate risk per share
        risk_per_share = entry_price - stop_loss_price

        if risk_per_share <= 0:
            risk_per_share = entry_price * self.config.fixed_stop_loss_pct

        # Determine capital allocation
        if self.config.use_kelly:
            allocation_pct = self.calculate_kelly_fraction()
        else:
            allocation_pct = self.config.risk_per_trade_pct

        # Calculate risk amount
        risk_amount = capital * allocation_pct

        # Calculate position size
        quantity = int(risk_amount / risk_per_share)

        # Apply max capital constraint
        max_quantity = int((capital * self.config.max_capital_per_trade_pct) / entry_price)
        quantity = min(quantity, max_quantity)

        # Ensure at least 1 share if capital allows
        if quantity <= 0 and capital >= entry_price:
            quantity = 1

        return quantity, stop_loss_price

    def should_trade(
        self,
        current_position_value: float,
        total_portfolio_value: float
    ) -> bool:
        """
        Check if trading is allowed based on position limits

        Returns:
            True if trade is allowed
        """
        if total_portfolio_value <= 0:
            return False

        position_pct = current_position_value / total_portfolio_value
        return position_pct < self.config.max_capital_per_trade_pct

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,
        atr: Optional[float] = None
    ) -> float:
        """
        Calculate trailing stop-loss

        Trailing stop follows price up but never down

        Returns:
            Trailing stop-loss price
        """
        if atr and atr > 0:
            trail_distance = atr * self.config.atr_multiplier
        else:
            trail_distance = highest_price * self.config.fixed_stop_loss_pct

        trailing_stop = highest_price - trail_distance

        # Never lower than initial stop
        initial_stop = entry_price * (1 - self.config.fixed_stop_loss_pct)

        return max(trailing_stop, initial_stop)
