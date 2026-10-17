"""Stock Analyzer – command line interface.

Two ways to use it:

* interactive: ``python3 stock_analyser.py`` – menu guided, ``q`` quits
* scripted:    ``python3 stock_analyser.py AAPL 1y rsi --signals-only``

The actual work happens in :mod:`market_data` (downloading) and
:mod:`indicators` (calculation); this module only asks, prints and dispatches.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

import pandas as pd

import indicators
from market_data import MarketDataError, StockData, fetch_stock_data

QUIT_WORDS = frozenset({"q", "quit", "exit"})
INDICATOR_ALIASES = {
    "rsi": "rsi",
    "macd": "macd",
    "bollinger": "bollinger",
    "bollinger bands": "bollinger",
    "bb": "bollinger",
    "all": "all",
    "all indicators": "all",
}
INDICATOR_LABELS = {
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "Bollinger Bands",
    "all": "All indicators",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_analyser.py",
        description=(
            "Analyse stock prices with RSI, MACD or Bollinger Bands (data from Yahoo Finance). "
            "Without arguments the program asks for the missing values interactively."
        ),
        epilog="The output is a technical analysis, not investment advice.",
    )
    parser.add_argument("ticker", nargs="?", help="ticker symbol, e.g. AAPL")
    parser.add_argument(
        "period",
        nargs="?",
        default="1y",
        help="history period, e.g. 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max (default: 1y)",
    )
    parser.add_argument(
        "indicator",
        nargs="?",
        type=str.lower,
        metavar="INDICATOR",
        help="one of: rsi, macd, bollinger, all",
    )
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="print only rows with a buy/sell signal",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=50,
        metavar="N",
        help="number of recent rows to print (default: 50)",
    )

    rsi_group = parser.add_argument_group("RSI")
    rsi_group.add_argument("--rsi-period", type=int, default=14, help="period in days (default: 14)")
    rsi_group.add_argument("--rsi-oversold", type=float, default=30.0, help="buy below (default: 30)")
    rsi_group.add_argument("--rsi-overbought", type=float, default=70.0, help="sell above (default: 70)")

    macd_group = parser.add_argument_group("MACD")
    macd_group.add_argument("--macd-fast", type=int, default=12, help="fast EMA period (default: 12)")
    macd_group.add_argument("--macd-slow", type=int, default=26, help="slow EMA period (default: 26)")
    macd_group.add_argument("--macd-signal", type=int, default=9, help="signal EMA period (default: 9)")

    bb_group = parser.add_argument_group("Bollinger Bands")
    bb_group.add_argument("--bb-period", type=int, default=20, help="middle band period (default: 20)")
    bb_group.add_argument("--bb-std", type=float, default=2.0, help="standard deviations (default: 2.0)")
    return parser


def normalize_indicator(raw: str) -> str | None:
    """Map user input to a canonical indicator name, or None if unknown."""
    return INDICATOR_ALIASES.get(raw.strip().lower())


def calculate(indicator: str, close: pd.Series, args: argparse.Namespace) -> tuple[pd.DataFrame, list[str]]:
    """Calculate one indicator (or all combined) for a price series.

    Returns the result frame and the names of its signal columns.
    """
    if indicator == "rsi":
        frame = indicators.rsi(close, args.rsi_period, args.rsi_oversold, args.rsi_overbought)
        return frame, ["Signal"]
    if indicator == "macd":
        frame = indicators.macd(close, args.macd_fast, args.macd_slow, args.macd_signal)
        return frame, ["Signal"]
    if indicator == "bollinger":
        frame = indicators.bollinger_bands(close, args.bb_period, args.bb_std)
        return frame, ["Signal"]
    if indicator == "all":
        combined = indicators.combine_signals(
            {
                "RSI": indicators.rsi(close, args.rsi_period, args.rsi_oversold, args.rsi_overbought),
                "MACD": indicators.macd(close, args.macd_fast, args.macd_slow, args.macd_signal),
                "BB": indicators.bollinger_bands(close, args.bb_period, args.bb_std),
            }
        )
        return combined, [column for column in combined.columns if column.endswith("signals")]
    raise ValueError(f"unknown indicator {indicator!r}")


def run_analysis(data: StockData, indicator: str, args: argparse.Namespace) -> None:
    """Print the result table for one already downloaded ticker."""
    frame, signal_columns = calculate(indicator, data.history["Close"], args)
    view = indicators.only_signals(frame, signal_columns) if args.signals_only else frame
    print(f"\n{INDICATOR_LABELS[indicator]} – {data.ticker} ({data.period})")
    print(f"\n{view.tail(args.tail).to_string()}")
    if args.signals_only and view.empty:
        print("\n(no buy/sell signal in the selected period)")


def print_overview(data: StockData) -> None:
    """Print company info and the most recent prices."""
    from market_data import overview_frame

    print(f"\n======= Overview about {data.ticker} ({data.period}) =======\n")
    print(overview_frame(data.info).to_string(index=False))
    print("\nMost recent prices:\n")
    print(data.history.tail(20).to_string())


def _configure_display() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", None)
    pd.set_option("display.expand_frame_repr", False)
    # yfinance logs retries, HTTP 404s and "possibly delisted" hints that
    # would only duplicate our own error messages
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def _analyze_ticker(data: StockData, indicator: str, args: argparse.Namespace) -> None:
    print_overview(data)
    run_analysis(data, indicator, args)


def _interactive(args: argparse.Namespace) -> int:
    print(
        "\nStock Analyzer – technical analysis, not investment advice.\n"
        "Enter 'q' at any prompt to quit."
    )
    ticker_hint = args.ticker
    indicator_hint = args.indicator
    while True:
        if ticker_hint is not None:
            raw_ticker, ticker_hint = ticker_hint, None
        else:
            raw_ticker = input("\nWhich stock should be researched? Ticker symbol, e.g. AAPL: ").strip()
        if raw_ticker.lower() in QUIT_WORDS:
            return 0

        period = input("Over what time period, e.g. 1y, 3mo? [1y]: ").strip() or args.period
        if period.lower() in QUIT_WORDS:
            return 0

        if indicator_hint is not None:
            raw_indicator, indicator_hint = indicator_hint, None
        else:
            raw_indicator = input("Which indicator? (RSI, MACD, Bollinger Bands, All): ").strip()
        if raw_indicator.lower() in QUIT_WORDS:
            return 0

        indicator = normalize_indicator(raw_indicator)
        if indicator is None:
            print(f"Unknown indicator {raw_indicator!r}. Please use RSI, MACD, Bollinger Bands or All.")
            continue

        try:
            data = fetch_stock_data(raw_ticker, period)
        except MarketDataError as exc:
            print(exc)
            continue

        try:
            _analyze_ticker(data, indicator, args)
        except ValueError as exc:
            print(f"Invalid parameter: {exc}")
            continue


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.tail < 1:
        parser.error("--tail must be >= 1")

    _configure_display()

    if not args.ticker or not args.indicator:
        return _interactive(args)

    indicator = normalize_indicator(args.indicator)
    if indicator is None:
        parser.error(f"unknown indicator {args.indicator!r}; use rsi, macd, bollinger or all")

    try:
        data = fetch_stock_data(args.ticker, args.period)
        _analyze_ticker(data, indicator, args)
    except MarketDataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:  # invalid indicator parameters, e.g. --rsi-period 1
        print(f"Error: invalid parameter: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
