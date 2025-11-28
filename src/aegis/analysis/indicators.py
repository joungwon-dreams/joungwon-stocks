"""
PROJECT AEGIS - Technical Indicators Module
============================================
VWAP, RSI, MA calculation functions
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    VWAP (Volume Weighted Average Price) calculation

    Note: VWAP은 당일(Intraday) 기준으로 계산됩니다.
    여러 날짜 데이터가 포함된 경우, 날짜별로 리셋됩니다.
    """
    # float64로 변환 (Decimal 등 object 타입 처리)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)

    typical_price = (high + low + close) / 3
    tp_vol = typical_price * volume

    # 날짜별 그룹화하여 VWAP 리셋 (여러 날짜 데이터 처리)
    if hasattr(df.index, 'date'):
        # DatetimeIndex인 경우 날짜별 그룹화
        dates = df.index.date
        cumsum_tp_vol = tp_vol.groupby(dates).cumsum()
        cumsum_vol = volume.groupby(dates).cumsum()
    else:
        # 단일 날짜 또는 date 컬럼이 없는 경우
        cumsum_tp_vol = tp_vol.cumsum()
        cumsum_vol = volume.cumsum()

    vwap = cumsum_tp_vol / cumsum_vol
    return vwap


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index) calculation

    Note: 초기 period만큼의 데이터 부족으로 발생하는 NaN은
    중립값(50)으로 채워집니다.
    """
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.replace([np.inf, -np.inf], 100)
    # 초기 NaN 값을 중립값(50)으로 채움
    rsi = rsi.fillna(50)
    return rsi


def calculate_ma(df: pd.DataFrame, periods: list = [5, 20, 60]) -> pd.DataFrame:
    """MA (Moving Average) calculation"""
    result = pd.DataFrame(index=df.index)
    for period in periods:
        result[f'ma_{period}'] = df['close'].rolling(window=period).mean()
    return result


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators at once"""
    result = df.copy()
    result['vwap'] = calculate_vwap(df)
    result['rsi'] = calculate_rsi(df)
    ma_df = calculate_ma(df)
    result = pd.concat([result, ma_df], axis=1)
    return result


def check_ma_alignment(df: pd.DataFrame) -> pd.Series:
    """Check MA alignment (Golden Cross / Death Cross)"""
    golden_cross = (df['ma_5'] > df['ma_20']) & (df['ma_20'] > df['ma_60'])
    death_cross = (df['ma_5'] < df['ma_20']) & (df['ma_20'] < df['ma_60'])
    alignment = pd.Series(0, index=df.index)
    alignment[golden_cross] = 1
    alignment[death_cross] = -1
    return alignment


def check_vwap_support(df: pd.DataFrame) -> pd.Series:
    """Check VWAP support/breakdown"""
    return (df['close'] > df['vwap']).astype(int) * 2 - 1


def check_rsi_signal(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> pd.Series:
    """RSI overbought/oversold signal"""
    signal = pd.Series(0, index=df.index)
    signal[df['rsi'] < oversold] = 1
    signal[df['rsi'] > overbought] = -1
    return signal
