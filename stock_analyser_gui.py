"""Stock Analyzer – web GUI based on Flask and Chart.js.

Start it with::

    python3 stock_analyser_gui.py

and open http://127.0.0.1:5000 in a browser.

The GUI reuses :mod:`market_data` (downloading) and :mod:`indicators`
(calculation); it only reads form input, renders pages and prepares chart
data. It is meant as a local tool, not as a public web service.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
from flask import Flask, render_template, request

import indicators
from market_data import VALID_PERIODS, MarketDataError, StockData, fetch_stock_data, overview_frame

app = Flask(__name__)

INDICATORS: dict[str, str] = {
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "Bollinger Bands",
    "all": "All indicators",
}
PARAMETER_DEFAULTS: dict[str, float] = {
    "rsi_period": 14,
    "rsi_oversold": 30.0,
    "rsi_overbought": 70.0,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2.0,
}
CACHE_TTL_SECONDS = 300.0
CHART_MAX_POINTS = 252  # keep the browser fast for long periods
SIGNAL_ROWS_MAX = 100

_cache: dict[tuple[str, str], tuple[float, StockData]] = {}


def get_stock(ticker: str, period: str) -> StockData:
    """Download once and reuse the result for a few minutes.

    Changing only an indicator parameter must not hit Yahoo Finance again.
    """
    key = (ticker.strip().upper(), period)
    entry = _cache.get(key)
    if entry is not None and time.time() - entry[0] < CACHE_TTL_SECONDS:
        return entry[1]
    data = fetch_stock_data(ticker, period)
    _cache[key] = (time.time(), data)
    return data


def clear_cache() -> None:
    _cache.clear()


def read_form(form: Any) -> tuple[str, str, str, dict[str, float]]:
    """Read and validate the form fields.

    Returns ticker, period, indicator and the indicator parameters.
    """
    ticker = (form.get("ticker") or "").strip()
    period = form.get("period") or "1y"
    indicator = (form.get("indicator") or "rsi").strip().lower()
    if indicator not in INDICATORS:
        raise ValueError(f"unknown indicator {indicator!r}; use one of: {', '.join(INDICATORS)}")
    if period not in VALID_PERIODS:
        raise ValueError(f"unknown period {period!r}; use one of: {', '.join(VALID_PERIODS)}")

    params = {name: _form_number(form, name, default) for name, default in PARAMETER_DEFAULTS.items()}
    return ticker, period, indicator, params


def _form_number(form: Any, name: str, default: float) -> float:
    raw = (form.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    if not value.is_integer():
        return value
    return int(value)


def build_frames(indicator: str, close: pd.Series, params: dict[str, float]) -> dict[str, pd.DataFrame]:
    """Calculate the requested indicators for a price series."""
    frames: dict[str, pd.DataFrame] = {}
    if indicator in ("rsi", "all"):
        frames["RSI"] = indicators.rsi(
            close, params["rsi_period"], params["rsi_oversold"], params["rsi_overbought"]
        )
    if indicator in ("macd", "all"):
        frames["MACD"] = indicators.macd(
            close, params["macd_fast"], params["macd_slow"], params["macd_signal"]
        )
    if indicator in ("bollinger", "all"):
        frames["Bollinger"] = indicators.bollinger_bands(close, params["bb_period"], params["bb_std"])
    return frames


def chart_specs(history: pd.DataFrame, frames: dict[str, pd.DataFrame], params: dict[str, float]) -> list[dict[str, Any]]:
    """Browser-ready chart descriptions: price chart plus one per indicator."""
    price = history["Close"].tail(CHART_MAX_POINTS)
    labels = [timestamp.strftime("%Y-%m-%d") for timestamp in price.index]

    price_datasets: list[dict[str, Any]] = [{"label": "Price", "data": _numbers(price)}]
    if "Bollinger" in frames:
        bands = frames["Bollinger"].tail(CHART_MAX_POINTS)
        for column in ("Upper band", "Middle band", "Lower band"):
            price_datasets.append(
                {"label": column, "data": _numbers(bands[column]), "dashed": column != "Middle band"}
            )

    specs: list[dict[str, Any]] = [
        {"title": "Price", "labels": labels, "datasets": price_datasets, "thresholds": []}
    ]

    if "RSI" in frames:
        rsi_frame = frames["RSI"].tail(CHART_MAX_POINTS)
        column = _rsi_column(rsi_frame)
        specs.append(
            {
                "title": "RSI",
                "labels": labels,
                "datasets": [{"label": column, "data": _numbers(rsi_frame[column])}],
                "thresholds": [
                    {"value": float(params["rsi_oversold"]), "label": "oversold"},
                    {"value": float(params["rsi_overbought"]), "label": "overbought"},
                ],
                "bounds": [0, 100],
            }
        )

    if "MACD" in frames:
        macd_frame = frames["MACD"].tail(CHART_MAX_POINTS)
        specs.append(
            {
                "title": "MACD",
                "labels": labels,
                "datasets": [
                    {"label": "MACD", "data": _numbers(macd_frame["MACD"])},
                    {"label": "Signal line", "data": _numbers(macd_frame["Signal line"]), "dashed": True},
                ],
                "thresholds": [],
            }
        )
    return specs


def _rsi_column(frame: pd.DataFrame) -> str:
    return next(column for column in frame.columns if column.startswith("RSI"))


def _numbers(series: pd.Series) -> list[float | None]:
    return [None if pd.isna(value) else round(float(value), 4) for value in series]


def table_payload(frame: pd.DataFrame, rows: int = 20) -> dict[str, Any]:
    """Columns and rows of the tail of a frame, ready for the HTML table.

    The date index becomes the first column – a signal without a date is
    useless to the reader.
    """
    tail = frame.reset_index(names="Date").tail(rows)
    return {
        "columns": [str(column) for column in tail.columns],
        "rows": [[_cell(value) for value in row] for row in tail.itertuples(index=False, name=None)],
    }


def _cell(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def signals_payload(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Only the rows with a buy/sell signal, combined across indicators."""
    if len(frames) == 1:
        view = indicators.only_signals(next(iter(frames.values())))
    else:
        combined = indicators.combine_signals(frames)
        columns = [f"{name} signals" for name in frames]
        view = indicators.only_signals(combined, columns)
    payload = table_payload(view, rows=SIGNAL_ROWS_MAX)
    payload["hidden"] = view.empty
    payload["truncated"] = len(view) > SIGNAL_ROWS_MAX
    payload["total"] = len(view)
    return payload


def overview_rows(info: Any) -> list[tuple[str, str]]:
    frame = overview_frame(info)
    return [(str(field), str(value)) for field, value in frame.itertuples(index=False, name=None)]


def base_context() -> dict[str, Any]:
    context: dict[str, Any] = {
        "indicators": INDICATORS,
        "periods": VALID_PERIODS,
        "ticker": "",
        "period": "1y",
        "indicator": "rsi",
        "error": "",
        "result": None,
    }
    context.update({name: "" for name in PARAMETER_DEFAULTS})
    return context


@app.get("/")
def index() -> str:
    """Main page: form, and – after a request – overview, charts and tables."""
    context = base_context()
    # text inputs keep whatever was typed so the user can correct it;
    # the two selects only accept values that really exist, otherwise the
    # browser would silently show the first option
    for field in ("ticker", *PARAMETER_DEFAULTS):
        value = request.args.get(field)
        if value is not None:
            context[field] = value
    period_arg = request.args.get("period")
    if period_arg in VALID_PERIODS:
        context["period"] = period_arg
    indicator_arg = (request.args.get("indicator") or "").strip().lower()
    if indicator_arg in INDICATORS:
        context["indicator"] = indicator_arg

    ticker = context["ticker"].strip()
    if ticker:
        try:
            ticker, period, indicator, params = read_form(request.args)
            context.update({"ticker": ticker, "period": period, "indicator": indicator})

            data = get_stock(ticker, period)
            close = data.history["Close"]
            frames = build_frames(indicator, close, params)
            context["result"] = {
                "ticker": data.ticker,
                "period": period,
                "indicator": INDICATORS[indicator],
                "overview": overview_rows(data.info),
                "charts": chart_specs(data.history, frames, params),
                "table": table_payload(next(iter(frames.values()))),
                "table_title": next(iter(frames)),
                "signals": signals_payload(frames),
            }
        except (MarketDataError, ValueError) as exc:
            context["error"] = str(exc)

    return render_template("index.html", **context)


@app.get("/health")
def health() -> dict[str, str]:
    """Tiny endpoint so the shell can check that the GUI is running."""
    return {"status": "ok"}


def main() -> None:
    host = "127.0.0.1"
    print(f"Stock Analyzer GUI – http://{host}:5000  (stop with Ctrl+C)")
    app.run(host=host, port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
