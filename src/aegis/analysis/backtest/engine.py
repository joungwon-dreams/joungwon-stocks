"""
PROJECT AEGIS - Backtest Engine
================================
Pandas-based lightweight backtesting engine with risk management
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

from .strategy import StrategyInterface, OrderType, Order, Position
from .performance import PerformanceMonitor, TradeRecord
from ...risk import RiskManager, RiskConfig, CircuitBreaker, TradingHaltedException


class BacktestEngine:
    """Backtesting Engine with Risk Management"""

    SLIPPAGE_PCT = 0.0005      # 0.05%
    COMMISSION_PCT = 0.00015   # 0.015%

    def __init__(
        self,
        initial_capital: float = 100_000_000,
        risk_config: Optional[RiskConfig] = None,
        use_risk_management: bool = True
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position: Optional[Position] = None
        self.monitor = PerformanceMonitor()
        self._entry_time: Optional[datetime] = None
        self._entry_price: Optional[float] = None
        self._entry_quantity: Optional[int] = None
        self._stop_loss_price: Optional[float] = None
        self._highest_price: Optional[float] = None

        # Risk Management (Phase 2)
        self.use_risk_management = use_risk_management
        self.risk_manager = RiskManager(risk_config) if use_risk_management else None
        self.circuit_breaker = CircuitBreaker(
            max_daily_loss_pct=risk_config.max_daily_loss_pct if risk_config else 0.02,
            max_trades=risk_config.max_daily_trades if risk_config else 10
        ) if use_risk_management else None

    def reset(self):
        self.capital = self.initial_capital
        self.position = None
        self.monitor.reset(self.initial_capital)
        self._entry_time = None
        self._entry_price = None
        self._entry_quantity = None
        self._stop_loss_price = None
        self._highest_price = None
        if self.circuit_breaker:
            self.circuit_breaker.reset()

    def _apply_slippage(self, price: float, order_type: OrderType) -> float:
        if order_type == OrderType.BUY:
            return price * (1 + self.SLIPPAGE_PCT)
        elif order_type == OrderType.SELL:
            return price * (1 - self.SLIPPAGE_PCT)
        return price

    def _calculate_commission(self, price: float, quantity: int) -> float:
        return price * quantity * self.COMMISSION_PCT

    def _execute_buy(self, price: float, quantity: int, timestamp: datetime, stock_code: str = "TEST") -> bool:
        if quantity <= 0:
            return False
        exec_price = self._apply_slippage(price, OrderType.BUY)
        cost = exec_price * quantity
        commission = self._calculate_commission(exec_price, quantity)
        total_cost = cost + commission
        if total_cost > self.capital:
            quantity = int((self.capital - commission) / exec_price)
            if quantity <= 0:
                return False
            cost = exec_price * quantity
            commission = self._calculate_commission(exec_price, quantity)
            total_cost = cost + commission
        self.capital -= total_cost
        self.position = Position(stock_code=stock_code, quantity=quantity, avg_price=exec_price, current_price=exec_price)
        self._entry_time = timestamp
        self._entry_price = exec_price
        self._entry_quantity = quantity
        return True

    def _execute_sell(self, price: float, timestamp: datetime) -> Optional[TradeRecord]:
        if self.position is None or self.position.quantity <= 0:
            return None
        exec_price = self._apply_slippage(price, OrderType.SELL)
        quantity = self.position.quantity
        proceeds = exec_price * quantity
        commission = self._calculate_commission(exec_price, quantity)
        net_proceeds = proceeds - commission
        entry_cost = self._entry_price * quantity
        pnl = net_proceeds - entry_cost
        pnl_pct = pnl / entry_cost * 100
        self.capital += net_proceeds
        holding_period = int((timestamp - self._entry_time).total_seconds() / 60)
        trade = TradeRecord(
            entry_time=self._entry_time,
            exit_time=timestamp,
            entry_price=self._entry_price,
            exit_price=exec_price,
            quantity=quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_period=holding_period
        )
        self.position = None
        self._entry_time = None
        self._entry_price = None
        self._entry_quantity = None
        return trade

    def run(self, df: pd.DataFrame, strategy: StrategyInterface, stock_code: str = "TEST") -> Dict[str, Any]:
        self.reset()
        strategy.reset()
        signals = []
        equity_history = []
        stop_loss_hits = 0
        circuit_breaker_hits = 0
        current_date = None

        if 'total_score' not in df.columns:
            raise ValueError("DataFrame must contain 'total_score' column. Run calculate_signal_score() first.")

        start_idx = 60
        if 'ma_60' in df.columns:
            valid_idx = df['ma_60'].first_valid_index()
            if valid_idx is not None:
                if isinstance(valid_idx, pd.Timestamp):
                    start_idx = df.index.get_loc(valid_idx)
                else:
                    start_idx = max(60, valid_idx)

        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            timestamp = df.index[i] if isinstance(df.index[i], datetime) else datetime.now()
            price = float(row['close'])

            # Daily reset for circuit breaker
            if self.circuit_breaker:
                trade_date = timestamp.date() if hasattr(timestamp, 'date') else None
                if trade_date and trade_date != current_date:
                    current_date = trade_date
                    self.circuit_breaker.start_day(self.capital, trade_date)

            if self.position:
                self.position.current_price = price
                # Track highest price for trailing stop
                if self._highest_price is None or price > self._highest_price:
                    self._highest_price = price

            # Check stop-loss (Risk Management)
            if self.position and self._stop_loss_price and price <= self._stop_loss_price:
                trade = self._execute_sell(price, timestamp)
                if trade:
                    self.monitor.record_trade(trade)
                    signals.append({'timestamp': timestamp, 'signal': 'STOP_LOSS', 'price': price})
                    strategy.position = None
                    stop_loss_hits += 1
                    if self.circuit_breaker:
                        self.circuit_breaker.record_trade(trade.pnl, trade.pnl > 0)
                continue

            signal = strategy.calculate_signal(df, i)
            strategy.position = self.position

            # Circuit breaker check before trading
            can_trade = True
            if self.circuit_breaker and signal == OrderType.BUY:
                try:
                    self.circuit_breaker.check_can_trade()
                except TradingHaltedException:
                    can_trade = False
                    circuit_breaker_hits += 1

            if signal == OrderType.BUY and can_trade:
                # Use RiskManager for position sizing
                if self.risk_manager:
                    quantity, stop_loss = self.risk_manager.calculate_position_size(
                        capital=self.capital,
                        entry_price=price,
                        df=df.iloc[:i+1]
                    )
                    self._stop_loss_price = stop_loss
                else:
                    quantity = strategy.calculate_quantity(self.capital, price, signal)
                    self._stop_loss_price = price * 0.97  # Default 3% stop

                if quantity > 0:
                    success = self._execute_buy(price, quantity, timestamp, stock_code)
                    if success:
                        self._highest_price = price
                        signals.append({
                            'timestamp': timestamp,
                            'signal': 'BUY',
                            'price': price,
                            'stop_loss': self._stop_loss_price
                        })
                        strategy.position = self.position

            elif signal == OrderType.SELL:
                trade = self._execute_sell(price, timestamp)
                if trade:
                    self.monitor.record_trade(trade)
                    signals.append({'timestamp': timestamp, 'signal': 'SELL', 'price': price})
                    strategy.position = None
                    if self.circuit_breaker:
                        self.circuit_breaker.record_trade(trade.pnl, trade.pnl > 0)

            equity = self.capital
            if self.position:
                equity += self.position.market_value
            equity_history.append(equity)
            self.monitor.update_equity(equity)

            # Update circuit breaker with unrealized P&L
            if self.circuit_breaker and self.position:
                self.circuit_breaker.update_unrealized_pnl(self.position.unrealized_pnl)

        if self.position:
            final_price = float(df['close'].iloc[-1])
            final_timestamp = df.index[-1] if isinstance(df.index[-1], datetime) else datetime.now()
            trade = self._execute_sell(final_price, final_timestamp)
            if trade:
                self.monitor.record_trade(trade)
                signals.append({'timestamp': final_timestamp, 'signal': 'FORCE_SELL', 'price': final_price})

        report = self.monitor.generate_report()
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return_pct': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'signals': signals,
            'equity_curve': self.monitor.equity_curve,
            'report': report,
            'trades': self.monitor.trades,
            'risk_stats': {
                'stop_loss_hits': stop_loss_hits,
                'circuit_breaker_hits': circuit_breaker_hits,
            }
        }

    def print_summary(self, result: Dict[str, Any]):
        print("\n" + "=" * 50)
        print("       PROJECT AEGIS - Backtest Summary")
        print("=" * 50)
        print(f"\nCapital:")
        print(f"   Initial: {result['initial_capital']:,.0f}")
        print(f"   Final: {result['final_capital']:,.0f}")
        print(f"   Return: {result['total_return_pct']:+.2f}%")
        if result['report']:
            self.monitor.print_report(result['report'])
        else:
            print("\nNo trades")
        print(f"\nSignals Generated: {len(result['signals'])}")

        # Risk Management Stats (Phase 2)
        if 'risk_stats' in result:
            risk = result['risk_stats']
            print("\nRisk Management:")
            print(f"   Stop-Loss Hits: {risk.get('stop_loss_hits', 0)}")
            print(f"   Circuit Breaker Blocks: {risk.get('circuit_breaker_hits', 0)}")

        print("=" * 50 + "\n")
