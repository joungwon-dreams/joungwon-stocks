"""
PROJECT AEGIS - Performance Monitor
====================================
Backtesting performance analysis
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class TradeRecord:
    """Individual trade record"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    holding_period: int


@dataclass
class PerformanceReport:
    """Performance report"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_pnl_per_trade: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    start_date: datetime
    end_date: datetime
    avg_holding_period: float


class PerformanceMonitor:
    """Backtesting performance monitor"""

    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[float] = []
        self.initial_capital: float = 0

    def reset(self, initial_capital: float):
        self.trades = []
        self.equity_curve = [initial_capital]
        self.initial_capital = initial_capital

    def record_trade(self, trade: TradeRecord):
        self.trades.append(trade)

    def update_equity(self, equity: float):
        self.equity_curve.append(equity)

    def calculate_mdd(self) -> tuple:
        if len(self.equity_curve) < 2:
            return 0.0, 0.0
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity
        drawdown_pct = drawdown / peak * 100
        max_dd = np.max(drawdown)
        max_dd_pct = np.max(drawdown_pct)
        return float(max_dd), float(max_dd_pct)

    def calculate_win_rate(self) -> float:
        if not self.trades:
            return 0.0
        winning = sum(1 for t in self.trades if t.pnl > 0)
        return winning / len(self.trades) * 100

    def calculate_profit_factor(self) -> float:
        if not self.trades:
            return 0.0
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.035) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        equity = np.array(self.equity_curve)
        returns = np.diff(equity) / equity[:-1]
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        annualization_factor = np.sqrt(252 * 390)
        excess_return = avg_return * annualization_factor - risk_free_rate
        sharpe = excess_return / (std_return * annualization_factor)
        return float(sharpe)

    def generate_report(self) -> Optional[PerformanceReport]:
        if not self.trades:
            return None
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_pct = (self.equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0
        max_dd, max_dd_pct = self.calculate_mdd()
        return PerformanceReport(
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=self.calculate_win_rate(),
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_pnl_per_trade=total_pnl / len(self.trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=self.calculate_profit_factor(),
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=self.calculate_sharpe_ratio(),
            start_date=self.trades[0].entry_time,
            end_date=self.trades[-1].exit_time,
            avg_holding_period=np.mean([t.holding_period for t in self.trades]),
        )

    def print_report(self, report: Optional[PerformanceReport] = None):
        if report is None:
            report = self.generate_report()
        if report is None:
            print("No trades to report")
            return

        print("\n" + "=" * 50)
        print("       PROJECT AEGIS - Performance Report")
        print("=" * 50)
        print(f"\nPeriod: {report.start_date.strftime('%Y-%m-%d')} ~ {report.end_date.strftime('%Y-%m-%d')}")
        print(f"\nTrade Statistics:")
        print(f"   Total Trades: {report.total_trades}")
        print(f"   Win: {report.winning_trades} | Loss: {report.losing_trades}")
        print(f"   Win Rate: {report.win_rate:.1f}%")
        print(f"\nProfit Analysis:")
        print(f"   Total PnL: {report.total_pnl:+,.0f} ({report.total_pnl_pct:+.2f}%)")
        print(f"   Avg PnL/Trade: {report.avg_pnl_per_trade:+,.0f}")
        print(f"   Avg Win: {report.avg_win:+,.0f}")
        print(f"   Avg Loss: {report.avg_loss:+,.0f}")
        print(f"   Profit Factor: {report.profit_factor:.2f}")
        print(f"\nRisk Metrics:")
        print(f"   MDD: {report.max_drawdown:,.0f} ({report.max_drawdown_pct:.2f}%)")
        print(f"   Sharpe Ratio: {report.sharpe_ratio:.2f}")
        print(f"\nAvg Holding Period: {report.avg_holding_period:.0f} mins")
        print("=" * 50 + "\n")
