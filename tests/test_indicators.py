"""Tests for the pure indicator calculations (no network access)."""

import pandas as pd
import pytest

from indicators import (
    BUY,
    NO_SIGNAL,
    SELL,
    bollinger_bands,
    combine_signals,
    macd,
    only_signals,
    rsi,
)


def prices(values) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=index, dtype="float64")


# --- RSI -------------------------------------------------------------------


def test_rsi_of_strongly_rising_market_is_overbought():
    result = rsi(prices([100.0 + i for i in range(40)]), period=14)
    column = result["RSI (14d)"]
    assert column.iloc[-1] == pytest.approx(100.0)
    assert result["Signal"].iloc[-1] == SELL


def test_rsi_of_strongly_falling_market_is_oversold():
    result = rsi(prices([200.0 - i for i in range(40)]), period=14)
    column = result["RSI (14d)"]
    assert column.iloc[-1] == pytest.approx(0.0)
    assert result["Signal"].iloc[-1] == BUY


def test_rsi_of_flat_market_is_neutral():
    result = rsi(prices([50.0] * 30), period=14)
    assert result["RSI (14d)"].iloc[-1] == pytest.approx(50.0)
    assert result["Signal"].iloc[-1] == NO_SIGNAL


def test_rsi_is_bounded_and_padded_with_nan():
    values = [100.0, 103.0, 99.0, 101.0, 97.0, 104.0, 102.0, 98.0, 105.0, 101.0, 99.0, 103.0, 100.0, 102.0, 101.0]
    result = rsi(prices(values * 3), period=14)
    column = result["RSI (14d)"]
    assert column.iloc[:13].isna().all()
    valid = column.dropna()
    assert ((valid >= 0) & (valid <= 100)).all()


def test_rsi_marks_prices_below_oversold_as_buy():
    # long rise, then a crash in the last three days
    values = [100.0 + i for i in range(30)] + [110.0, 95.0, 80.0]
    result = rsi(prices(values), period=14)
    assert result["Signal"].iloc[-1] == BUY


@pytest.mark.parametrize("period", [0, -1, 1])
def test_rsi_rejects_invalid_period(period):
    with pytest.raises(ValueError):
        rsi(prices([1.0, 2.0, 3.0]), period=period)


def test_rsi_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        rsi(prices([1.0, 2.0, 3.0]), oversold=70, overbought=30)
    with pytest.raises(ValueError):
        rsi(prices([1.0, 2.0, 3.0]), overbought=120)


def test_rsi_rejects_empty_price_series():
    with pytest.raises(ValueError):
        rsi(pd.Series([], dtype="float64"))


# --- MACD ------------------------------------------------------------------


def test_macd_is_the_difference_of_the_two_ema():
    close = prices([100.0, 101.0, 102.5, 99.0, 103.0, 104.0, 102.0, 105.0, 106.0, 104.0])
    result = macd(close, fast=3, slow=6, signal_period=2)
    expected = close.ewm(span=3, adjust=False).mean() - close.ewm(span=6, adjust=False).mean()
    assert result["MACD"].equals(expected)


def test_macd_of_flat_market_has_no_signal():
    result = macd(prices([50.0] * 30))
    assert (result["Signal"] == NO_SIGNAL).all()


def test_macd_signals_a_full_cycle():
    up = [100.0 + i for i in range(30)]
    down = [up[-1] - i for i in range(1, 21)]
    result = macd(prices(up + down), fast=12, slow=26, signal_period=9)
    assert (result["Signal"] == BUY).any()
    assert (result["Signal"] == SELL).any()
    # a signal is only emitted at the crossing itself, not on every later row,
    # so the last sell must come after the price turned from up to down
    last_sell = result.index[result["Signal"] == SELL][-1]
    turn = result.index[len(up) - 1]
    assert last_sell > turn


def test_macd_rejects_fast_not_smaller_than_slow():
    with pytest.raises(ValueError):
        macd(prices([1.0, 2.0, 3.0]), fast=26, slow=12)
    with pytest.raises(ValueError):
        macd(prices([1.0, 2.0, 3.0]), fast=12, slow=12)


@pytest.mark.parametrize("fast,slow,signal_period", [(0, 26, 9), (12, -1, 9), (12, 26, 0)])
def test_macd_rejects_invalid_periods(fast, slow, signal_period):
    with pytest.raises(ValueError):
        macd(prices([1.0, 2.0, 3.0]), fast=fast, slow=slow, signal_period=signal_period)


# --- Bollinger Bands -------------------------------------------------------


def test_bollinger_bands_are_centred_on_the_moving_average():
    close = prices([10.0, 11.0, 9.5, 10.5, 12.0, 11.5, 10.0, 9.0, 9.5, 10.0, 11.0, 12.5])
    result = bollinger_bands(close, period=5, num_std=2.0)
    middle = close.rolling(5).mean()
    deviation = close.rolling(5).std()
    assert result["Middle band"].equals(middle)
    assert result["Upper band"].equals(middle + 2.0 * deviation)
    assert result["Lower band"].equals(middle - 2.0 * deviation)


def test_bollinger_bands_mark_a_crash_as_buy():
    result = bollinger_bands(prices([100.0] * 25 + [80.0]), period=20, num_std=2.0)
    assert result["Signal"].iloc[-1] == BUY


def test_bollinger_bands_mark_a_spike_as_sell():
    result = bollinger_bands(prices([100.0] * 25 + [120.0]), period=20, num_std=2.0)
    assert result["Signal"].iloc[-1] == SELL


def test_bollinger_bands_without_volatility_signal_sell():
    # a flat price touches both collapsed bands at once; the sell wins,
    # matching the original np.where order of the script
    result = bollinger_bands(prices([100.0] * 25), period=20, num_std=2.0)
    assert (result["Signal"].iloc[19:] == SELL).all()


@pytest.mark.parametrize("period", [0, 1])
def test_bollinger_bands_reject_invalid_period(period):
    with pytest.raises(ValueError):
        bollinger_bands(prices([1.0, 2.0, 3.0]), period=period)


def test_bollinger_bands_reject_invalid_num_std():
    with pytest.raises(ValueError):
        bollinger_bands(prices([1.0, 2.0, 3.0]), num_std=0)
    with pytest.raises(ValueError):
        bollinger_bands(prices([1.0, 2.0, 3.0]), num_std=-2.0)


# --- helpers ---------------------------------------------------------------


def test_only_signals_keeps_buy_and_sell_rows():
    frame = rsi(prices([100.0 + i for i in range(30)] + [80.0, 70.0, 60.0]), period=14)
    signals = only_signals(frame)
    assert set(signals["Signal"]) <= {BUY, SELL}  # no '-' rows remain
    assert BUY in set(signals["Signal"])  # the crash must show up
    assert len(signals) < len(frame)


def test_combine_signals_builds_one_table_per_indicator():
    close = prices([100.0 + i for i in range(40)])
    combined = combine_signals(
        {"RSI": rsi(close), "MACD": macd(close), "BB": bollinger_bands(close)}
    )
    assert list(combined.columns) == ["Price", "RSI signals", "MACD signals", "BB signals"]
    assert combined.index.equals(close.index)
    assert len(only_signals(combined, ["RSI signals", "MACD signals", "BB signals"])) > 0


def test_combine_signals_rejects_empty_mapping():
    with pytest.raises(ValueError):
        combine_signals({})
