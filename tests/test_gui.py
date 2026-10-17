"""Tests for the Flask web GUI (network stubbed out)."""

import pandas as pd
import pytest

import stock_analyser_gui as gui
from market_data import MarketDataError, StockData


def fake_data(ticker="AAPL", period="1y", rows=60) -> StockData:
    index = pd.date_range("2024-01-01", periods=rows, freq="D")
    # long rise and a crash at the end so that signals exist
    close = [100.0 + i for i in range(rows - 3)] + [95.0, 90.0, 85.0]
    history = pd.DataFrame({"Close": close}, index=index)
    info = {"longName": "Test Inc", "currentPrice": 85.0, "marketCap": 1e12}
    return StockData(ticker=ticker.upper(), period=period, info=info, history=history)


@pytest.fixture
def client(monkeypatch):
    gui.clear_cache()
    monkeypatch.setattr(gui, "get_stock", lambda ticker, period: fake_data(ticker, period))
    gui.app.config["TESTING"] = True
    with gui.app.test_client() as test_client:
        yield test_client
    gui.clear_cache()


def test_index_shows_the_form_without_a_ticker(client):
    response = client.get("/")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'name="ticker"' in page
    assert "Analyse" in page
    assert "<canvas" not in page  # no charts before a request


def test_analyse_rsi_renders_overview_chart_and_table(client):
    response = client.get("/?ticker=AAPL&period=1y&indicator=rsi")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Test Inc" in page
    assert "AAPL – RSI (1y)" in page
    assert '"title": "Price"' in page
    assert '"title": "RSI"' in page
    assert "Most recent values" in page


def test_analyse_all_indicators_renders_three_charts(client):
    response = client.get("/?ticker=AAPL&period=1y&indicator=all")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '"title": "Price"' in page
    assert '"title": "RSI"' in page
    assert '"title": "MACD"' in page
    assert "Upper band" in page  # Bollinger bands are drawn on the price chart
    assert "RSI signals" in page and "MACD signals" in page and "Bollinger signals" in page


def test_signals_table_lists_the_crash(client):
    response = client.get("/?ticker=AAPL&period=1y&indicator=rsi")

    page = response.get_data(as_text=True)
    assert "<h3>Signals</h3>" in page
    assert ">buy<" in page


def test_error_message_is_shown_instead_of_a_crash(client, monkeypatch):
    def boom(ticker, period):
        raise MarketDataError("No price data for 'ZZZ'.")

    monkeypatch.setattr(gui, "get_stock", boom)

    response = client.get("/?ticker=ZZZ&period=1y&indicator=rsi")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No price data for &#39;ZZZ&#39;." in page
    assert "<canvas" not in page


def test_invalid_parameter_is_reported(client):
    response = client.get("/?ticker=AAPL&period=1y&indicator=bollinger&bb_std=0")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "bb_std" in page


def test_non_numeric_parameter_is_reported(client):
    response = client.get("/?ticker=AAPL&period=1y&indicator=rsi&rsi_period=abc")

    page = response.get_data(as_text=True)
    assert "rsi_period" in page


def test_form_values_are_kept_after_a_request(client):
    response = client.get("/?ticker=AAPL&period=3mo&indicator=rsi&rsi_period=21")

    page = response.get_data(as_text=True)
    assert 'value="AAPL"' in page
    assert 'value="21"' in page
    assert 'value="3mo"' in page  # selected option


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.get_json() == {"status": "ok"}


# --- unit tests for the helpers ---------------------------------------------


def test_read_form_rejects_unknown_indicator():
    with pytest.raises(ValueError):
        gui.read_form({"ticker": "AAPL", "indicator": "dow jones"})


def test_read_form_rejects_unknown_period():
    with pytest.raises(ValueError):
        gui.read_form({"ticker": "AAPL", "period": "3 weeks"})


def test_read_form_uses_defaults_for_empty_fields():
    ticker, period, indicator, params = gui.read_form({"ticker": " aapl "})

    assert ticker == "aapl"
    assert period == "1y"
    assert indicator == "rsi"
    assert params["rsi_period"] == 14
    assert params["macd_fast"] == 12
    assert params["bb_std"] == 2.0


def test_chart_specs_limit_the_number_of_points():
    history = fake_data(rows=400).history
    specs = gui.chart_specs(history, {"RSI": gui.build_frames("rsi", history["Close"], _params())[ "RSI"]}, _params())

    assert len(specs[0]["labels"]) == gui.CHART_MAX_POINTS
    assert len(specs[0]["datasets"][0]["data"]) == gui.CHART_MAX_POINTS


def test_chart_specs_use_the_given_rsi_thresholds():
    params = _params(rsi_oversold=20.0, rsi_overbought=80.0)
    history = fake_data().history
    frames = gui.build_frames("rsi", history["Close"], params)

    specs = gui.chart_specs(history, frames, params)

    rsi_spec = next(spec for spec in specs if spec["title"] == "RSI")
    assert [threshold["value"] for threshold in rsi_spec["thresholds"]] == [20.0, 80.0]
    assert rsi_spec["bounds"] == [0, 100]


def test_nan_values_become_null_in_chart_data():
    specs = gui.chart_specs(
        fake_data().history, gui.build_frames("rsi", fake_data().history["Close"], _params()), _params()
    )

    rsi_spec = next(spec for spec in specs if spec["title"] == "RSI")
    assert rsi_spec["datasets"][0]["data"][:13] == [None] * 13  # warm-up rows


def test_cache_reuses_the_download(monkeypatch):
    calls: list[tuple[str, str]] = []

    def record(ticker, period):
        calls.append((ticker, period))
        return fake_data(ticker, period)

    gui.clear_cache()
    monkeypatch.setattr(gui, "fetch_stock_data", record)
    gui.app.config["TESTING"] = True
    with gui.app.test_client() as test_client:
        assert test_client.get("/?ticker=AAPL&period=1y&indicator=rsi").status_code == 200
        assert test_client.get("/?ticker=aapl&period=1y&indicator=macd").status_code == 200

    # two page views, one download – the cache key is case insensitive
    assert calls == [("AAPL", "1y")]
    gui.clear_cache()


def _params(**overrides) -> dict:
    params = dict(gui.PARAMETER_DEFAULTS)
    params.update(overrides)
    return params
