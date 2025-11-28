#!/usr/bin/env python3
"""
PROJECT AEGIS - Backtest Test Script
=====================================
한국전력(015760) 1분봉 데이터로 백테스팅 실행
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import asyncpg
from datetime import datetime, timedelta

from src.aegis.analysis.signal import calculate_signal_score, get_current_signal, generate_signal_summary
from src.aegis.analysis.backtest.engine import BacktestEngine
from src.aegis.analysis.backtest.strategy import AegisSwingStrategy
from src.aegis.risk import RiskConfig


DB_URL = "postgresql://wonny@localhost/stock_investment_db"
STOCK_CODE = "015760"  # 한국전력
STOCK_NAME = "한국전력"


async def fetch_min_ticks_data(days: int = 7) -> pd.DataFrame:
    """min_ticks 테이블에서 데이터 조회"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 최근 N일 데이터 조회
        start_date = datetime.now() - timedelta(days=days)

        rows = await conn.fetch('''
            SELECT timestamp, price, volume
            FROM min_ticks
            WHERE stock_code = $1
              AND timestamp >= $2
            ORDER BY timestamp ASC
        ''', STOCK_CODE, start_date)

        if not rows:
            print(f"⚠️ min_ticks에 {STOCK_NAME} 데이터가 없습니다.")
            return None

        print(f"✅ {len(rows):,}개 1분봉 데이터 로드 ({days}일)")

        # DataFrame 변환
        df = pd.DataFrame([dict(r) for r in rows])
        df.set_index('timestamp', inplace=True)
        df.index = pd.to_datetime(df.index)

        # OHLCV 형식으로 변환 (1분봉이므로 open=high=low=close)
        # Decimal → float 변환 (PostgreSQL numeric 타입 처리)
        df['price'] = df['price'].astype(float)
        df['volume'] = df['volume'].fillna(0).astype(float)

        df['open'] = df['price']
        df['high'] = df['price']
        df['low'] = df['price']
        df['close'] = df['price']

        return df[['open', 'high', 'low', 'close', 'volume']]

    finally:
        await conn.close()


def generate_mock_data(days: int = 7) -> pd.DataFrame:
    """Mock 데이터 생성 (DB 연결 불가 시 사용)"""
    print("📊 Mock 데이터 생성 중...")

    periods = days * 390  # 하루 6.5시간 * 60분
    base_price = 52000

    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=periods,
        freq='1min'
    )

    # 랜덤 가격 변동 생성
    import numpy as np
    np.random.seed(42)

    returns = np.random.normal(0, 0.001, periods)
    prices = base_price * np.cumprod(1 + returns)
    volumes = np.random.randint(1000, 50000, periods)

    df = pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': volumes
    }, index=timestamps)

    print(f"✅ {len(df):,}개 Mock 데이터 생성")
    return df


async def main():
    print("\n" + "=" * 60)
    print("       PROJECT AEGIS - Backtesting Test")
    print("=" * 60)
    print(f"\n종목: {STOCK_NAME} ({STOCK_CODE})")
    print(f"실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 데이터 로드
    print("[1/4] 데이터 로드...")
    try:
        df = await fetch_min_ticks_data(days=7)
        if df is None or len(df) < 100:
            print("   → DB 데이터 부족, Mock 데이터 사용")
            df = generate_mock_data(days=7)
    except Exception as e:
        print(f"   → DB 연결 실패: {e}")
        print("   → Mock 데이터 사용")
        df = generate_mock_data(days=7)

    print(f"   데이터 기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"   총 데이터: {len(df):,}개\n")

    # 2. 신호 계산
    print("[2/4] 기술 지표 및 신호 계산...")
    df_scored = calculate_signal_score(df)

    # 신호 분포
    signal_counts = df_scored['signal'].value_counts()
    print(f"   신호 분포:")
    for signal, count in signal_counts.items():
        print(f"      {signal}: {count:,}개 ({count/len(df_scored)*100:.1f}%)")
    print()

    # 3. 현재 신호 확인
    print("[3/4] 현재 신호...")
    current_signal = get_current_signal(df)
    print(generate_signal_summary(current_signal))
    print()

    # 4. 백테스트 실행 (with Risk Management - Phase 2)
    print("[4/4] 백테스트 실행 (Risk Management 적용)...")

    # Risk Configuration
    risk_config = RiskConfig(
        max_capital_per_trade_pct=0.20,    # 20% max per trade
        risk_per_trade_pct=0.02,           # 2% risk per trade
        atr_multiplier=2.0,                # ATR * 2 for stop-loss
        fixed_stop_loss_pct=0.03,          # 3% fallback stop-loss
        max_daily_loss_pct=0.02,           # -2% daily loss limit
        max_daily_trades=10,               # Max 10 trades per day
        use_kelly=False,                   # Use fixed fractional (not Kelly)
    )

    engine = BacktestEngine(
        initial_capital=100_000_000,
        risk_config=risk_config,
        use_risk_management=True
    )

    strategy = AegisSwingStrategy(
        buy_threshold=2,      # STRONG_BUY에서만 매수
        sell_threshold=-2,    # STRONG_SELL에서만 매도
        capital_per_trade_pct=0.2
    )

    result = engine.run(df_scored, strategy, stock_code=STOCK_CODE)

    # 5. 결과 출력
    engine.print_summary(result)

    # 6. 신호 상세
    if result['signals']:
        print("\n📈 거래 신호 내역:")
        print("-" * 50)
        for i, sig in enumerate(result['signals'][:10], 1):
            print(f"  {i}. {sig['timestamp']} | {sig['signal']:10s} | {sig['price']:,.0f}원")
        if len(result['signals']) > 10:
            print(f"  ... 외 {len(result['signals']) - 10}개")

    print("\n✅ AEGIS 백테스트 완료!")
    print("=" * 60 + "\n")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
