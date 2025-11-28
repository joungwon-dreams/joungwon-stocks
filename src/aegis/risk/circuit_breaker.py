"""
PROJECT AEGIS - Circuit Breaker
================================
Trading halt mechanism for daily loss limits

Features:
- Daily loss limit enforcement
- Max trades per day limit
- Automatic trading halt
"""

from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Optional


class TradingHaltedException(Exception):
    """Exception raised when trading is halted by circuit breaker"""

    def __init__(self, reason: str, halt_until: Optional[datetime] = None):
        self.reason = reason
        self.halt_until = halt_until
        super().__init__(f"Trading Halted: {reason}")


@dataclass
class DailyStats:
    """Daily trading statistics"""
    date: date
    starting_capital: float
    current_capital: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_pct(self) -> float:
        if self.starting_capital <= 0:
            return 0.0
        return self.total_pnl / self.starting_capital * 100

    @property
    def win_rate(self) -> float:
        if self.trade_count <= 0:
            return 0.0
        return self.win_count / self.trade_count * 100


class CircuitBreaker:
    """
    Circuit Breaker for risk management

    Halts trading when:
    - Daily loss exceeds limit (-2% default)
    - Daily trade count exceeds limit (10 default)

    Usage:
        cb = CircuitBreaker(max_daily_loss_pct=0.02, max_trades=10)
        cb.start_day(capital=100_000_000)

        # Before each trade:
        cb.check_can_trade()  # Raises TradingHaltedException if not allowed

        # After each trade:
        cb.record_trade(pnl=5000, is_win=True)
    """

    def __init__(
        self,
        max_daily_loss_pct: float = 0.02,
        max_trades: int = 10
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades = max_trades
        self._is_halted: bool = False
        self._halt_reason: Optional[str] = None
        self._daily_stats: Optional[DailyStats] = None

    def start_day(self, capital: float, trading_date: Optional[date] = None):
        """Initialize daily statistics"""
        self._is_halted = False
        self._halt_reason = None
        self._daily_stats = DailyStats(
            date=trading_date or date.today(),
            starting_capital=capital,
            current_capital=capital
        )

    def reset(self):
        """Reset circuit breaker state"""
        self._is_halted = False
        self._halt_reason = None
        self._daily_stats = None

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    @property
    def halt_reason(self) -> Optional[str]:
        return self._halt_reason

    @property
    def daily_stats(self) -> Optional[DailyStats]:
        return self._daily_stats

    def _halt(self, reason: str):
        """Halt trading"""
        self._is_halted = True
        self._halt_reason = reason

    def check_can_trade(self) -> bool:
        """
        Check if trading is allowed

        Returns:
            True if trading is allowed

        Raises:
            TradingHaltedException if trading is halted
        """
        if self._is_halted:
            raise TradingHaltedException(self._halt_reason)

        if self._daily_stats is None:
            raise TradingHaltedException("Daily stats not initialized. Call start_day() first.")

        # Check daily loss limit
        loss_limit = -self.max_daily_loss_pct * 100
        if self._daily_stats.pnl_pct <= loss_limit:
            self._halt(f"Daily loss limit reached: {self._daily_stats.pnl_pct:.2f}% <= {loss_limit:.2f}%")
            raise TradingHaltedException(self._halt_reason)

        # Check trade count limit
        if self._daily_stats.trade_count >= self.max_trades:
            self._halt(f"Daily trade limit reached: {self._daily_stats.trade_count} >= {self.max_trades}")
            raise TradingHaltedException(self._halt_reason)

        return True

    def record_trade(self, pnl: float, is_win: bool):
        """Record a completed trade"""
        if self._daily_stats is None:
            return

        self._daily_stats.realized_pnl += pnl
        self._daily_stats.trade_count += 1

        if is_win:
            self._daily_stats.win_count += 1
        else:
            self._daily_stats.loss_count += 1

    def update_unrealized_pnl(self, unrealized_pnl: float):
        """Update unrealized P&L"""
        if self._daily_stats is None:
            return

        self._daily_stats.unrealized_pnl = unrealized_pnl

    def update_capital(self, current_capital: float):
        """Update current capital"""
        if self._daily_stats is None:
            return

        self._daily_stats.current_capital = current_capital

    def get_remaining_trades(self) -> int:
        """Get number of remaining allowed trades"""
        if self._daily_stats is None:
            return 0
        return max(0, self.max_trades - self._daily_stats.trade_count)

    def get_remaining_loss_budget(self) -> float:
        """Get remaining loss budget in currency"""
        if self._daily_stats is None:
            return 0.0

        max_loss = self._daily_stats.starting_capital * self.max_daily_loss_pct
        current_loss = -self._daily_stats.total_pnl if self._daily_stats.total_pnl < 0 else 0
        return max(0.0, max_loss - current_loss)

    def print_status(self):
        """Print current circuit breaker status"""
        print("\n" + "=" * 40)
        print("  AEGIS Circuit Breaker Status")
        print("=" * 40)

        if self._daily_stats:
            stats = self._daily_stats
            print(f"  Date: {stats.date}")
            print(f"  Starting Capital: {stats.starting_capital:,.0f}")
            print(f"  Current Capital: {stats.current_capital:,.0f}")
            print(f"  Realized P&L: {stats.realized_pnl:+,.0f}")
            print(f"  Unrealized P&L: {stats.unrealized_pnl:+,.0f}")
            print(f"  Total P&L: {stats.total_pnl:+,.0f} ({stats.pnl_pct:+.2f}%)")
            print(f"  Trades: {stats.trade_count}/{self.max_trades}")
            print(f"  Win Rate: {stats.win_rate:.1f}%")

        print(f"\n  Status: {'🛑 HALTED' if self._is_halted else '✅ ACTIVE'}")
        if self._halt_reason:
            print(f"  Reason: {self._halt_reason}")

        print("=" * 40 + "\n")
