"""
PROJECT AEGIS - Phase 3: Ensemble System Test
==============================================
Test the multi-strategy ensemble with market regime detection
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.config.database import db
from src.aegis.ensemble import (
    MarketRegime,
    MarketRegimeClassifier,
    StrategyRegistry,
    StrategyOrchestrator
)
from src.aegis.analysis.backtest.strategy import (
    AegisSwingStrategy,
    MeanReversionStrategy,
    OrderType
)
from src.aegis.analysis.backtest.engine import BacktestEngine
from src.aegis.analysis.signal import calculate_signal_score


async def load_test_data(stock_code: str = "015760", days: int = 200) -> pd.DataFrame:
    """Load OHLCV data for testing"""
    await db.connect()
    try:
        rows = await db.fetch("""
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC
            LIMIT $2
        """, stock_code, days)

        if not rows:
            raise ValueError(f"No data found for {stock_code}")

        df = pd.DataFrame([dict(r) for r in rows])
        df = df.sort_values('date').reset_index(drop=True)

        # Convert Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # Calculate signal scores (required for AegisSwingStrategy)
        df = calculate_signal_score(df)

        return df
    finally:
        await db.disconnect()


def test_regime_classifier(df: pd.DataFrame):
    """Test Market Regime Classifier"""
    print("\n" + "=" * 60)
    print("  TEST 1: Market Regime Classifier")
    print("=" * 60)

    classifier = MarketRegimeClassifier()

    # Test current regime
    result = classifier.classify(df)
    print(f"\n📊 Current Market Regime: {result.regime.value}")
    print(f"   Confidence: {result.confidence:.1%}")
    print(f"   MA(20): {result.ma_short:,.0f}")
    print(f"   MA(60): {result.ma_long:,.0f}")
    print(f"   Volatility: {result.volatility:.2%}")
    print(f"   Trend Strength: {result.trend_strength:.2f}")

    # Get regime distribution
    regimes = classifier.get_regime_series(df)
    regime_counts = regimes.value_counts()
    print(f"\n📈 Regime Distribution (last {len(df)} days):")
    for regime, count in regime_counts.items():
        pct = count / len(df) * 100
        print(f"   {regime}: {count} days ({pct:.1f}%)")

    return result


def test_strategy_registry():
    """Test Strategy Registry"""
    print("\n" + "=" * 60)
    print("  TEST 2: Strategy Registry")
    print("=" * 60)

    registry = StrategyRegistry()

    # Register strategies
    swing = AegisSwingStrategy()
    mean_rev = MeanReversionStrategy()

    registry.register(
        name="swing",
        strategy=swing,
        default_weight=1.0,
        preferred_regimes=[MarketRegime.BULL, MarketRegime.BEAR]
    )

    registry.register(
        name="mean_reversion",
        strategy=mean_rev,
        default_weight=1.0,
        preferred_regimes=[MarketRegime.SIDEWAY]
    )

    print(f"\n📋 Registered Strategies: {len(registry)}")

    strategies_info = registry.list_strategies()
    for name, info in strategies_info.items():
        print(f"\n   [{name}]")
        print(f"   - Enabled: {info['enabled']}")
        print(f"   - Default Weight: {info['default_weight']}")
        print(f"   - Preferred Regimes: {info['preferred_regimes']}")
        print(f"   - Weights by Regime:")
        for regime, weight in info['weights_by_regime'].items():
            print(f"       {regime}: {weight}")

    # Test getting strategies for different regimes
    print("\n🔍 Strategies for each regime:")
    for regime in MarketRegime:
        strategies = registry.get_strategies_for_regime(regime)
        strategy_names = [(n, w) for n, _, w in strategies]
        print(f"   {regime.value}: {strategy_names}")

    return registry


def test_orchestrator(df: pd.DataFrame):
    """Test Strategy Orchestrator"""
    print("\n" + "=" * 60)
    print("  TEST 3: Strategy Orchestrator (Ensemble)")
    print("=" * 60)

    # Create orchestrator
    orchestrator = StrategyOrchestrator(
        buy_threshold=0.3,
        sell_threshold=-0.3,
        min_agreement=0.5
    )

    # Add strategies
    orchestrator.add_strategy(
        name="swing",
        strategy=AegisSwingStrategy(buy_threshold=2, sell_threshold=-2),
        weight=1.0,
        preferred_regimes=[MarketRegime.BULL, MarketRegime.BEAR]
    )

    orchestrator.add_strategy(
        name="mean_reversion",
        strategy=MeanReversionStrategy(bb_period=20, bb_std=2.0),
        weight=1.0,
        preferred_regimes=[MarketRegime.SIDEWAY]
    )

    # Print status
    orchestrator.print_status()

    # Test signal generation at different points
    print("📊 Signal Analysis at Different Time Points:")
    test_indices = [60, 100, 150, len(df) - 1]

    for idx in test_indices:
        if idx >= len(df):
            continue

        signal = orchestrator.get_detailed_signal(df, idx)
        date = df['date'].iloc[idx] if 'date' in df.columns else f"Index {idx}"
        close = df['close'].iloc[idx]

        print(f"\n   Date: {date} | Price: {close:,.0f}")
        print(f"   Regime: {signal.regime.value} (conf: {signal.regime_confidence:.1%})")
        print(f"   Ensemble Score: {signal.score:+.2f}")
        print(f"   Final Signal: {signal.signal.value}")
        print(f"   Strategy Votes: {signal.strategy_votes}")

    return orchestrator


async def test_backtest_with_ensemble():
    """Test backtest with ensemble orchestrator"""
    print("\n" + "=" * 60)
    print("  TEST 4: Backtest with Ensemble Strategy")
    print("=" * 60)

    # Load data
    df = await load_test_data("015760", days=250)
    print(f"\n📈 Loaded {len(df)} days of data for 015760 (한국전력)")

    # Create orchestrator
    orchestrator = StrategyOrchestrator()
    orchestrator.add_strategy(
        "swing",
        AegisSwingStrategy(buy_threshold=2, sell_threshold=-2),
        preferred_regimes=[MarketRegime.BULL, MarketRegime.BEAR]
    )
    orchestrator.add_strategy(
        "mean_reversion",
        MeanReversionStrategy(),
        preferred_regimes=[MarketRegime.SIDEWAY]
    )

    # Run backtest
    engine = BacktestEngine(initial_capital=10_000_000)
    results = engine.run(df, orchestrator)

    # Extract stats from report (PerformanceReport dataclass)
    report = results.get('report')
    total_trades = report.total_trades if report else len(results.get('trades', []))
    win_rate = report.win_rate if report else 0
    max_drawdown = report.max_drawdown_pct if report else 0

    print("\n📊 Backtest Results (Ensemble Strategy):")
    print(f"   Initial Capital: {results['initial_capital']:,}원")
    print(f"   Final Capital: {results['final_capital']:,.0f}원")
    print(f"   Total Return: {results['total_return_pct']:.2f}%")
    print(f"   Total Trades: {total_trades}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")

    if 'risk_stats' in results:
        print(f"\n🛡️ Risk Stats:")
        print(f"   Stop-Loss Hits: {results['risk_stats']['stop_loss_hits']}")
        print(f"   Circuit Breaker Hits: {results['risk_stats']['circuit_breaker_hits']}")

    # Compare with single strategy
    print("\n" + "-" * 40)
    print("📊 Comparison: Single Strategy vs Ensemble")
    print("-" * 40)

    # Swing only
    swing_engine = BacktestEngine(initial_capital=10_000_000)
    swing_results = swing_engine.run(
        df,
        AegisSwingStrategy(buy_threshold=2, sell_threshold=-2)
    )

    # Mean Reversion only
    mr_engine = BacktestEngine(initial_capital=10_000_000)
    mr_results = mr_engine.run(df, MeanReversionStrategy())

    # Helper to extract stats from results
    def get_stats(r):
        rpt = r.get('report')
        return {
            'return': r['total_return_pct'],
            'trades': rpt.total_trades if rpt else len(r.get('trades', [])),
            'win_rate': rpt.win_rate if rpt else 0,
            'max_dd': rpt.max_drawdown_pct if rpt else 0
        }

    sw = get_stats(swing_results)
    mr = get_stats(mr_results)
    en = get_stats(results)

    print(f"\n   {'Strategy':<20} {'Return':>10} {'Trades':>8} {'Win Rate':>10} {'Max DD':>10}")
    print(f"   {'-'*58}")
    print(f"   {'Swing Only':<20} {sw['return']:>9.2f}% {sw['trades']:>8} {sw['win_rate']:>9.1f}% {sw['max_dd']:>9.2f}%")
    print(f"   {'Mean Reversion Only':<20} {mr['return']:>9.2f}% {mr['trades']:>8} {mr['win_rate']:>9.1f}% {mr['max_dd']:>9.2f}%")
    print(f"   {'Ensemble':<20} {en['return']:>9.2f}% {en['trades']:>8} {en['win_rate']:>9.1f}% {en['max_dd']:>9.2f}%")

    return results


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  PROJECT AEGIS - Phase 3: Ensemble System Test")
    print("=" * 60)

    # Load test data
    df = await load_test_data("015760", days=200)
    print(f"\n✅ Loaded {len(df)} days of data for testing")

    # Run tests
    test_regime_classifier(df)
    test_strategy_registry()
    test_orchestrator(df)
    await test_backtest_with_ensemble()

    print("\n" + "=" * 60)
    print("  ✅ All Phase 3 Tests Completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
