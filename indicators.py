"""Calculation of technical indicators.

Pure functions without any I/O: every function receives a price series and
returns a :class:`pandas.DataFrame` with the indicator values plus a signal
column (``buy`` / ``sell`` / ``-``).
"""

from __future__ import annotations

import math
import numbers
from typing import Final, Mapping, Sequence

import numpy as np
import pandas as pd

BUY: Final[str] = "buy"
SELL: Final[str] = "sell"
NO_SIGNAL: Final[str] = "-"
MAX_PERIOD: Final[int] = 1_000_000  # ~2700 years of daily data, far beyond any real use


def rsi(
    close: pd.Series,
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> pd.DataFrame:
    """Relative Strength Index using Wilder's smoothing.

    Average gains/losses are exponentially smoothed with ``alpha = 1 / period``,
    which is Wilder's original definition (as used by TA-Lib and most charting
    tools). Prices below ``oversold`` are marked ``buy``, prices above
    ``overbought`` are marked ``sell``.
    """
    _require_price_series(close)
    _require_positive_int("period", period, minimum=2)
    oversold, overbought = _validate_thresholds(oversold, overbought)

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    with np.errstate(divide="ignore", invalid="ignore"):
        relative_strength = avg_gain / avg_loss
        values = 100.0 - (100.0 / (1.0 + relative_strength))
    # No losses at all: relative_strength is inf, the result is already 100.
    # Neither gains nor losses: 0/0 -> NaN, treat a flat market as neutral.
    values[(avg_gain == 0) & (avg_loss == 0)] = 50.0

    signal = pd.Series(NO_SIGNAL, index=close.index, dtype="object")
    signal[values < oversold] = BUY
    signal[values > overbought] = SELL

    return pd.DataFrame(
        {
            "Price": close,
            f"RSI ({period}d)": values,
            "Signal": signal,
        }
    )


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    ``MACD = EMA(fast) - EMA(slow)``; the signal line is an EMA of the MACD
    line. A crossover of the MACD line above its signal line is marked ``buy``,
    a crossunder ``sell``.
    """
    _require_price_series(close)
    _require_positive_int("fast", fast)
    _require_positive_int("slow", slow)
    _require_positive_int("signal_period", signal_period)
    if fast >= slow:
        raise ValueError(f"fast period ({fast}) must be smaller than slow period ({slow})")

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    # The EMAs are defined from the first row on but only meaningful after a
    # warm-up phase; suppress every signal that would be based on fewer values
    # than the slow EMA and the signal line need.
    warmup = slow + signal_period - 1
    valid = pd.Series(np.arange(len(close)) >= warmup, index=close.index)
    above = macd_line > signal_line
    crossover = valid & above & ~above.shift(1, fill_value=False)
    crossunder = valid & ~above & above.shift(1, fill_value=False)

    signal = pd.Series(
        np.select([crossover, crossunder], [BUY, SELL], default=NO_SIGNAL),
        index=close.index,
        dtype="object",
    )

    return pd.DataFrame(
        {
            "Price": close,
            "MACD": macd_line,
            "Signal line": signal_line,
            "Signal": signal,
        }
    )


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands around a simple moving average.

    A price at or below the lower band is marked ``buy``, a price at or above
    the upper band ``sell``.
    """
    _require_price_series(close)
    _require_positive_int("period", period, minimum=2)
    _require_positive_float("num_std", num_std)

    middle = close.rolling(window=period).mean()
    deviation = close.rolling(window=period).std()
    upper = middle + num_std * deviation
    lower = middle - num_std * deviation

    signal = pd.Series(NO_SIGNAL, index=close.index, dtype="object")
    signal[close <= lower] = BUY
    signal[close >= upper] = SELL

    return pd.DataFrame(
        {
            "Price": close,
            "Lower band": lower,
            "Middle band": middle,
            "Upper band": upper,
            "Signal": signal,
        }
    )


def combine_signals(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine several indicator frames (same index) into one signal table."""
    if not frames:
        raise ValueError("at least one indicator frame is required")
    first = next(iter(frames.values()))
    combined = pd.DataFrame({"Price": first["Price"]})
    for name, frame in frames.items():
        combined[f"{name} signals"] = frame["Signal"]
    return combined


def only_signals(frame: pd.DataFrame, signal_columns: Sequence[str] = ("Signal",)) -> pd.DataFrame:
    """Return only the rows where one of ``signal_columns`` says buy or sell."""
    if not signal_columns:
        raise ValueError("at least one signal column is required")
    mask = pd.Series(False, index=frame.index)
    for column in signal_columns:
        mask |= frame[column].isin((BUY, SELL))
    return frame[mask]


def _require_price_series(close: pd.Series) -> None:
    if not isinstance(close, pd.Series):
        raise ValueError("a pandas Series of prices is required")
    if close.empty:
        raise ValueError("the price series is empty")
    if not pd.api.types.is_numeric_dtype(close):
        raise ValueError(f"the price series must be numeric, got dtype {close.dtype}")


def _require_positive_int(name: str, value: int, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    if value > MAX_PERIOD:
        raise ValueError(f"{name} must be <= {MAX_PERIOD}, got {value}")
    return int(value)


def _require_positive_float(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value}")
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return float(value)


def _validate_thresholds(oversold: float, overbought: float) -> tuple[float, float]:
    oversold = _require_positive_float("oversold", oversold)
    overbought = _require_positive_float("overbought", overbought)
    if oversold >= overbought:
        raise ValueError(f"oversold ({oversold}) must be smaller than overbought ({overbought})")
    if overbought > 100:
        raise ValueError(f"overbought must be <= 100, got {overbought}")
    return oversold, overbought