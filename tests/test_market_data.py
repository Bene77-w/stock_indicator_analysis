"""Tests for the Yahoo Finance wrapper (network stubbed out)."""

import pandas as pd
import pytest

from market_data import (
    MarketDataError,
    StockData,
    fetch_stock_data,
    overview_frame,
)


class FakeTicker:
    """Stand-in for yfinance.Ticker with recorded calls."""

    instances: list = []

    def __init__(self, symbol, history_frame=None, info=None, error=None):
        self.symbol = symbol
        self.history_frame = history_frame
        self._info = info
        self.error = error
        self.history_calls: list[str] = []
        type(self).instances.append(self)

    def history(self, period="1mo", **kwargs):
        self.history_calls.append(period)
        if self.error is not None:
            raise self.error
        return self.history_frame

    @property
    def info(self):
        if isinstance(self._info, Exception):
            raise self._info
        return self._info


def history_frame(values=(10.0, 11.0, 12.0)) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.DataFrame({"Close": list(values)}, index=index)


@pytest.fixture(autouse=True)
def _clear_instances():
    FakeTicker.instances.clear()


def _patch_ticker(monkeypatch, **kwargs):
    monkeypatch.setattr("market_data.yf.Ticker", lambda symbol: FakeTicker(symbol, **kwargs))


def test_fetch_downloads_history_and_info_in_one_pass(monkeypatch):
    _patch_ticker(monkeypatch, history_frame=history_frame(), info={"longName": "Test Inc"})

    data = fetch_stock_data("aapl", "6mo")

    assert isinstance(data, StockData)
    assert data.ticker == "AAPL"
    assert data.period == "6mo"
    assert data.info["longName"] == "Test Inc"
    assert not data.history.empty
    assert len(FakeTicker.instances) == 1  # one request, not two
    assert FakeTicker.instances[0].history_calls == ["6mo"]


def test_fetch_tolerates_failing_company_info(monkeypatch):
    _patch_ticker(monkeypatch, history_frame=history_frame(), info=RuntimeError("rate limited"))

    data = fetch_stock_data("AAPL", "1y")

    assert data.info == {}
    assert not data.history.empty


def test_fetch_rejects_empty_ticker(monkeypatch):
    _patch_ticker(monkeypatch, history_frame=history_frame(), info={})
    with pytest.raises(MarketDataError):
        fetch_stock_data("   ")
    assert FakeTicker.instances == []


def test_fetch_rejects_unknown_period_before_downloading(monkeypatch):
    _patch_ticker(monkeypatch, history_frame=history_frame(), info={})
    with pytest.raises(MarketDataError) as excinfo:
        fetch_stock_data("AAPL", "3 weeks")
    assert "3 weeks" in str(excinfo.value)
    assert FakeTicker.instances == []


def test_fetch_reports_empty_history(monkeypatch):
    _patch_ticker(monkeypatch, history_frame=pd.DataFrame(), info={})
    with pytest.raises(MarketDataError) as excinfo:
        fetch_stock_data("TSLA", "1y")
    assert "TSLA" in str(excinfo.value)


def test_fetch_wraps_download_errors(monkeypatch):
    _patch_ticker(monkeypatch, error=ConnectionError("no route to host"))
    with pytest.raises(MarketDataError) as excinfo:
        fetch_stock_data("AAPL", "1y")
    assert "no route to host" in str(excinfo.value)


# --- overview formatting ---------------------------------------------------


def test_overview_frame_tolerates_completely_empty_info():
    frame = overview_frame({})
    assert list(frame["Value"]) == ["N/A"] * 7


def test_overview_frame_tolerates_none_values():
    # yfinance returns None (not a missing key) for many fields
    frame = overview_frame({"longName": "Test Inc", "currentPrice": None, "marketCap": None})
    value = dict(zip(frame["Field"], frame["Value"]))
    assert value["Name"] == "Test Inc"
    assert value["Current value"] == "N/A"
    assert value["Market cap"] == "N/A"


def test_overview_frame_formats_prices_and_market_cap():
    frame = overview_frame(
        {"currentPrice": 123.456, "marketCap": 2.5e12, "fiftyTwoWeekLow": 99.5}
    )
    value = dict(zip(frame["Field"], frame["Value"]))
    assert value["Current value"] == "$123.46"
    assert value["Market cap"] == "$2.50T"
    assert value["52 week low"] == "$99.50"
