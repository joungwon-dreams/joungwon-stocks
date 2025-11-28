"""
PROJECT AEGIS - Market Regime Classifier
=========================================
Detect market conditions: BULL, BEAR, SIDEWAY

Logic:
- BULL: MA(20) > MA(60) and upward momentum
- BEAR: MA(20) < MA(60) and downward momentum
- SIDEWAY: Neither, low volatility or mixed signals
"""

import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class MarketRegime(Enum):
    """Market Regime Types"""
    BULL = "BULL"       # Uptrend
    BEAR = "BEAR"       # Downtrend
    SIDEWAY = "SIDEWAY" # Range-bound


@dataclass
class RegimeResult:
    """Market Regime Detection Result"""
    regime: MarketRegime
    confidence: float       # 0.0 ~ 1.0
    ma_short: float
    ma_long: float
    volatility: float
    trend_strength: float


class MarketRegimeClassifier:
    """
    Market Regime Classifier

    Determines market condition based on:
    1. MA Crossover (MA20 vs MA60)
    2. Trend Strength (ADX or slope)
    3. Volatility (ATR ratio)

    Usage:
        classifier = MarketRegimeClassifier()
        result = classifier.classify(df)
        print(f"Market is {result.regime.value} with {result.confidence:.0%} confidence")
    """

    def __init__(
        self,
        ma_short_period: int = 20,
        ma_long_period: int = 60,
        atr_period: int = 14,
        trend_threshold: float = 0.02,  # 2% MA gap for trend
        sideway_threshold: float = 0.01 # 1% MA gap for sideway
    ):
        self.ma_short_period = ma_short_period
        self.ma_long_period = ma_long_period
        self.atr_period = atr_period
        self.trend_threshold = trend_threshold
        self.sideway_threshold = sideway_threshold

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate required indicators for regime detection"""
        result = df.copy()

        # Moving Averages
        close = df['close'].astype(float)
        result['ma_short'] = close.rolling(window=self.ma_short_period).mean()
        result['ma_long'] = close.rolling(window=self.ma_long_period).mean()

        # MA Gap (percentage)
        result['ma_gap'] = (result['ma_short'] - result['ma_long']) / result['ma_long']

        # Volatility (ATR / Close)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_period).mean()
        result['volatility'] = atr / close

        # Trend Strength (MA slope over 5 periods)
        result['ma_slope'] = result['ma_short'].diff(5) / result['ma_short'].shift(5)

        return result

    def classify(self, df: pd.DataFrame) -> RegimeResult:
        """
        Classify current market regime

        Returns:
            RegimeResult with regime type and confidence
        """
        indicators = self.calculate_indicators(df)
        latest = indicators.iloc[-1]

        ma_short = latest['ma_short']
        ma_long = latest['ma_long']
        ma_gap = latest['ma_gap']
        volatility = latest['volatility']
        ma_slope = latest['ma_slope']

        # Handle NaN values
        if pd.isna(ma_short) or pd.isna(ma_long):
            return RegimeResult(
                regime=MarketRegime.SIDEWAY,
                confidence=0.5,
                ma_short=ma_short if not pd.isna(ma_short) else 0,
                ma_long=ma_long if not pd.isna(ma_long) else 0,
                volatility=volatility if not pd.isna(volatility) else 0,
                trend_strength=0
            )

        # Determine regime
        regime = MarketRegime.SIDEWAY
        confidence = 0.5
        trend_strength = abs(ma_gap) / self.trend_threshold if self.trend_threshold > 0 else 0

        if ma_gap > self.trend_threshold:
            # BULL: MA short above MA long with significant gap
            regime = MarketRegime.BULL
            confidence = min(1.0, 0.5 + trend_strength * 0.5)

            # Boost confidence if slope is positive
            if not pd.isna(ma_slope) and ma_slope > 0:
                confidence = min(1.0, confidence + 0.1)

        elif ma_gap < -self.trend_threshold:
            # BEAR: MA short below MA long with significant gap
            regime = MarketRegime.BEAR
            confidence = min(1.0, 0.5 + trend_strength * 0.5)

            # Boost confidence if slope is negative
            if not pd.isna(ma_slope) and ma_slope < 0:
                confidence = min(1.0, confidence + 0.1)

        else:
            # SIDEWAY: No clear trend
            regime = MarketRegime.SIDEWAY
            # Higher confidence in sideway when volatility is low
            if not pd.isna(volatility) and volatility < 0.02:
                confidence = 0.7
            else:
                confidence = 0.6

        return RegimeResult(
            regime=regime,
            confidence=confidence,
            ma_short=float(ma_short),
            ma_long=float(ma_long),
            volatility=float(volatility) if not pd.isna(volatility) else 0,
            trend_strength=float(trend_strength)
        )

    def get_regime_series(self, df: pd.DataFrame) -> pd.Series:
        """
        Get regime for each row in DataFrame

        Returns:
            Series with MarketRegime values
        """
        indicators = self.calculate_indicators(df)

        def row_to_regime(row):
            ma_gap = row['ma_gap']
            if pd.isna(ma_gap):
                return MarketRegime.SIDEWAY.value
            if ma_gap > self.trend_threshold:
                return MarketRegime.BULL.value
            elif ma_gap < -self.trend_threshold:
                return MarketRegime.BEAR.value
            else:
                return MarketRegime.SIDEWAY.value

        return indicators.apply(row_to_regime, axis=1)
