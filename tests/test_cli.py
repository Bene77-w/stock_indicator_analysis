"""Tests for the command line interface (network stubbed out)."""

import pandas as pd
import pytest

import stock_analyser
from market_data import MarketDataError, StockData


def fake_data(ticker="AAPL", period="1y") -> StockData:
    index = pd.date_range("2024-01-01", periods=60, freq="D")
    close = [100.0 + i for i in range(57)] + [95.0, 90.0, 85.0]
    history = pd.DataFrame({"Close": close}, index=index)
    info = {"longName": "Test Inc", "currentPrice": 85.0, "marketCap": 1e12}
    return StockData(ticker=ticker, period=period, info=info, history=history)


def test_build_parser_defaults():
    args = stock_analyser.build_parser().parse_args(["AAPL", "3mo", "bb"])
    assert args.ticker == "AAPL"
    assert args.period == "3mo"
    assert args.indicator == "bb"
    assert args.signals_only is False
    assert args.rsi_period == 14
    assert args.macd_fast == 12
    assert args.macd_slow == 26
    assert args.macd_signal == 9
    assert args.bb_period == 20
    assert args.bb_std == 2.0
    assert args.tail == 50


def test_build_parser_with_flags():
    args = stock_analyser.build_parser().parse_args(
        ["MSFT", "1y", "rsi", "--signals-only", "--tail", "10", "--rsi-period", "21"]
    )
    assert args.signals_only is True
    assert args.tail == 10
    assert args.rsi_period == 21


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("rsi", "rsi"),
        ("RSI", "rsi"),
        ("MACD", "macd"),
        ("bollinger", "bollinger"),
        ("Bollinger Bands", "bollinger"),
        ("bb", "bollinger"),
        ("all", "all"),
        ("All Indicators", "all"),
        ("  macd ", "macd"),
        ("dow jones", None),
    ],
)
def test_normalize_indicator(raw, expected):
    assert stock_analyser.normalize_indicator(raw) == expected


def test_main_runs_analysis_non_interactively(monkeypatch, capsys):
    monkeypatch.setattr(stock_analyser, "fetch_stock_data", lambda ticker, period: fake_data(ticker, period))

    exit_code = stock_analyser.main(["AAPL", "1y", "rsi"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Overview about AAPL" in out
    assert "RSI – AAPL (1y)" in out
    assert "Test Inc" in out


def test_main_all_indicators_combines_signals(monkeypatch, capsys):
    monkeypatch.setattr(stock_analyser, "fetch_stock_data", lambda ticker, period: fake_data(ticker, period))

    exit_code = stock_analyser.main(["AAPL", "1y", "all", "--signals-only"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "RSI signals" in out
    assert "MACD signals" in out
    assert "BB signals" in out


def test_main_returns_error_code_for_unusable_ticker(monkeypatch, capsys):
    def boom(ticker, period):
        raise MarketDataError("No price data for 'ZZZZ'.")

    monkeypatch.setattr(stock_analyser, "fetch_stock_data", boom)

    exit_code = stock_analyser.main(["ZZZZ", "1y", "rsi"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ZZZZ" in captured.err


def test_main_rejects_unknown_indicator():
    with pytest.raises(SystemExit):
        stock_analyser.main(["AAPL", "1y", "dow jones"])


def test_main_rejects_invalid_tail():
    with pytest.raises(SystemExit):
        stock_analyser.main(["AAPL", "1y", "rsi", "--tail", "0"])


def test_main_quits_from_interactive_menu(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "q")
    assert stock_analyser.main([]) == 0


def test_interactive_loop_retries_after_bad_ticker(monkeypatch, capsys):
    answers = iter(["ZZZZ", "1y", "rsi", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    def boom(ticker, period):
        raise MarketDataError("No price data for 'ZZZZ'.")

    monkeypatch.setattr(stock_analyser, "fetch_stock_data", boom)

    assert stock_analyser.main([]) == 0
    assert "No price data" in capsys.readouterr().out


def test_interactive_loop_retries_after_unknown_indicator(monkeypatch, capsys):
    answers = iter(["dow jones", "1y", "bitcoin", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert stock_analyser.main([]) == 0
    assert "Unknown indicator" in capsys.readouterr().out
