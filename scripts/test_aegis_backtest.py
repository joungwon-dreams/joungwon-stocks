#!/usr/bin/env python
"""
PROJECT AEGIS - Backtest Test Script
=====================================
Uses daily_ohlcv data for backtesting
"""

import sys
import asyncio
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from src.aegis.analysis.signal import calculate_signal_score
from src.aegis.analysis.backtest.engine import BacktestEngine
from src.aegis.analysis.backtest.strategy import AegisSwingStrategy


async def fetch_daily_ohlcv(stock_code: str, days: int = 120) -> pd.DataFrame:
    """Fetch daily_ohlcv data from DB"""
    await db.connect()
    start_date = datetime.now() - timedelta(days=days)
    query = """
        SELECT
            date as timestamp,
            open,
            high,
            low,
            close,
            volume
        FROM daily_ohlcv
        WHERE stock_code = $1
          AND date >= $2
        ORDER BY date ASC
    """
    rows = await db.fetch(query, stock_code, start_date.date())
    await db.disconnect()

    if not rows:
        print(f"No data for {stock_code}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
    return df


async def run_backtest(stock_code: str, days: int = 120):
    """Run backtest"""
    print(f"\nPROJECT AEGIS - Backtest")
    print(f"   Stock: {stock_code}")
    print(f"   Period: Last {days} days")
    print("-" * 40)

    print("\nFetching data...")
    df = await fetch_daily_ohlcv(stock_code, days)
    if df.empty:
        return

    print(f"   Data points: {len(df)}")
    print(f"   Period: {df.index[0]} ~ {df.index[-1]}")

    print("\nCalculating indicators...")
    scored_df = calculate_signal_score(df)

    valid_data = scored_df[scored_df['ma_60'].notna()]
    print(f"   Valid data: {len(valid_data)}")

    if len(valid_data) < 10:
        print(f"Insufficient data (need 10+, got {len(valid_data)})")
        return

    print("\nRunning backtest...")
    engine = BacktestEngine(initial_capital=100_000_000)
    strategy = AegisSwingStrategy(
        buy_threshold=2,
        sell_threshold=-2,
        capital_per_trade_pct=0.2
    )

    result = engine.run(scored_df, strategy, stock_code)
    engine.print_summary(result)

    if result['signals']:
        print("\nRecent Signals:")
        for sig in result['signals'][-10:]:
            print(f"   {sig['timestamp']} | {sig['signal']:12} | {sig['price']:,.0f}")

    latest = scored_df.iloc[-1]
    print(f"\nCurrent State:")
    print(f"   Close: {latest['close']:,.0f}")
    print(f"   VWAP: {latest['vwap']:,.0f}")
    print(f"   RSI: {latest['rsi']:.1f}")
    print(f"   Total Score: {latest['total_score']:+.0f}")
    print(f"   Signal: {latest['signal']}")


async def main():
    stock_code = sys.argv[1] if len(sys.argv) >= 2 else "316140"
    days = int(sys.argv[2]) if len(sys.argv) >= 3 else 120
    await run_backtest(stock_code, days)


if __name__ == "__main__":
    asyncio.run(main())
