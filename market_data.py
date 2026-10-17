"""Fetching stock data from Yahoo Finance.

This is the only module that talks to the network. Everything else in the
project works on plain :class:`pandas` objects, which keeps the indicator
calculations testable without a connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

import pandas as pd
import yfinance as yf

VALID_PERIODS: Final[tuple[str, ...]] = (
    "1d",
    "5d",
    "1mo",
    "3mo",
    "6mo",
    "1y",
    "2y",
    "5y",
    "10y",
    "ytd",
    "max",
)


class MarketDataError(RuntimeError):
    """Raised when no usable market data is available for a ticker."""


@dataclass(frozen=True)
class StockData:
    """Market data of one ticker for one period."""

    ticker: str
    period: str
    info: Mapping[str, Any]
    history: pd.DataFrame


def fetch_stock_data(ticker: str, period: str = "1y") -> StockData:
    """Download price history and company info for ``ticker`` in one pass."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise MarketDataError("The ticker symbol must not be empty.")
    if period not in VALID_PERIODS:
        raise MarketDataError(
            f"Unknown period {period!r}. Valid periods: {', '.join(VALID_PERIODS)}"
        )

    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)
        info = stock.info or {}
    except Exception as exc:  # yfinance raises a mix of request and parse errors
        raise MarketDataError(f"Fetching data for {ticker} failed: {exc}") from exc

    if history.empty:
        raise MarketDataError(
            f"No price data for {ticker!r} (period {period}). Please check the ticker symbol."
        )
    return StockData(ticker=ticker, period=period, info=info, history=history)


def overview_frame(info: Mapping[str, Any]) -> pd.DataFrame:
    """Format company info as a two column table, tolerating missing values."""
    rows = [
        ("Name", info.get("longName") or "N/A"),
        ("Sector", info.get("sector") or "N/A"),
        ("Industry", info.get("industry") or "N/A"),
        ("Current value", _format_price(info.get("currentPrice"))),
        ("Market cap", _format_market_cap(info.get("marketCap"))),
        ("52 week high", _format_price(info.get("fiftyTwoWeekHigh"))),
        ("52 week low", _format_price(info.get("fiftyTwoWeekLow"))),
    ]
    return pd.DataFrame(rows, columns=["Field", "Value"])


def _format_price(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _format_market_cap(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(number) >= divisor:
            return f"${number / divisor:,.2f}{suffix}"
    return f"${number:,.2f}"
