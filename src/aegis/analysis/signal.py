"""
PROJECT AEGIS - Trading Signal Module
======================================
Score-based trading signal generation

Score System (-3 ~ +3):
| Indicator | Condition | Score |
|-----------|-----------|-------|
| MA        | Golden    | +1    |
| MA        | Death     | -1    |
| VWAP      | Support   | +1    |
| VWAP      | Breakdown | -1    |
| RSI       | < 30      | +1    |
| RSI       | > 70      | -1    |

Signal:
- >= +2: STRONG BUY
- +1: BUY
- 0: HOLD
- -1: SELL
- <= -2: STRONG SELL
"""

import pandas as pd
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from .indicators import (
    calculate_all_indicators,
    check_ma_alignment,
    check_vwap_support,
    check_rsi_signal
)


class Signal(Enum):
    """Trading Signal Enum"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class SignalResult:
    """Signal Result Data Class"""
    signal: Signal
    score: int
    ma_score: int
    vwap_score: int
    rsi_score: int
    details: dict


def score_to_signal(score: int) -> Signal:
    """Convert score to signal"""
    if score >= 2:
        return Signal.STRONG_BUY
    elif score == 1:
        return Signal.BUY
    elif score == 0:
        return Signal.HOLD
    elif score == -1:
        return Signal.SELL
    else:
        return Signal.STRONG_SELL


def calculate_signal_score(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate signal score for each timestamp"""
    result = calculate_all_indicators(df)
    result['ma_score'] = check_ma_alignment(result)
    result['vwap_score'] = check_vwap_support(result)
    result['rsi_score'] = check_rsi_signal(result)
    result['total_score'] = result['ma_score'] + result['vwap_score'] + result['rsi_score']
    result['signal'] = result['total_score'].apply(lambda x: score_to_signal(x).value)
    return result


def get_current_signal(df: pd.DataFrame) -> SignalResult:
    """Get current trading signal"""
    scored_df = calculate_signal_score(df)
    latest = scored_df.iloc[-1]
    return SignalResult(
        signal=score_to_signal(int(latest['total_score'])),
        score=int(latest['total_score']),
        ma_score=int(latest['ma_score']),
        vwap_score=int(latest['vwap_score']),
        rsi_score=int(latest['rsi_score']),
        details={
            'close': latest['close'],
            'vwap': latest['vwap'],
            'rsi': latest['rsi'],
            'ma_5': latest['ma_5'],
            'ma_20': latest['ma_20'],
            'ma_60': latest['ma_60'],
        }
    )


def generate_signal_summary(result: SignalResult) -> str:
    """Generate human-readable signal summary"""
    emoji_map = {
        Signal.STRONG_BUY: "++",
        Signal.BUY: "+",
        Signal.HOLD: "=",
        Signal.SELL: "-",
        Signal.STRONG_SELL: "--",
    }
    lines = [
        "==== AEGIS Signal ====",
        f"{emoji_map[result.signal]} {result.signal.value} (Score: {result.score:+d})",
        "",
        "Indicator Scores:",
        f"  MA: {result.ma_score:+d}",
        f"  VWAP: {result.vwap_score:+d}",
        f"  RSI: {result.rsi_score:+d}",
        "",
        "Current Values:",
        f"  Close: {result.details['close']:,.0f}",
        f"  VWAP: {result.details['vwap']:,.0f}",
        f"  RSI: {result.details['rsi']:.1f}",
        f"  MA5/20/60: {result.details['ma_5']:,.0f}/{result.details['ma_20']:,.0f}/{result.details['ma_60']:,.0f}",
        "=====================",
    ]
    return "\n".join(lines)
