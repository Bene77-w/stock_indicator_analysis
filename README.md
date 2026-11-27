# Stock Indicator Analysis

A Python tool that fetches stock data from Yahoo Finance and calculates technical indicators from historical closing prices, usable from the command line or in the browser.

## Features

- Display company details, price metrics, and the most recent rows of price history within the selected period.
- Calculate the Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD), or Bollinger Bands with user-specified settings.
- View recent indicator values and optionally list only rows with buy or sell signals. Choose `all` to see the three indicators' signals side by side for dates when at least one generated a signal.
- Browser GUI with price, RSI and MACD charts.

## Requirements

- Python 3 with pip
- Dependencies listed in `requirements.txt` (`pandas`, `numpy`, `yfinance`, `flask`)
- Internet access to retrieve Yahoo Finance data

## Installation

```bash
git clone https://github.com/Bene77-w/stock_indicator_analysis.git
cd stock_indicator_analysis
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Usage

### Interactive

```bash
python3 stock_analyser.py
```

The program asks for a ticker symbol (for example `AAPL`), a history period (for example `1y` or `3mo`) and an indicator. Enter `q` at any prompt to quit. Invalid input (unknown symbol, period or indicator) is caught and the prompt starts again.

### Command line

```bash
python3 stock_analyser.py AAPL 1y rsi                     # RSI (14 days) over 1 year
python3 stock_analyser.py AAPL 6mo macd --signals-only    # only rows with a buy/sell signal
python3 stock_analyser.py AAPL 1y bollinger --bb-std 2.5  # Bollinger Bands with 2.5 standard deviations
python3 stock_analyser.py AAPL 1y all --tail 30           # all indicators combined
python3 stock_analyser.py --help                          # all options
```

Parameters can be overridden, for example `--rsi-period 21`, `--macd-fast 12 --macd-slow 26 --macd-signal 9`, `--bb-period 20 --bb-std 2.0`, `--rsi-oversold 30 --rsi-overbought 70`.

### Browser GUI

```bash
python3 stock_analyser_gui.py
```

Then open http://127.0.0.1:5000 in the browser. The GUI offers the same form as the command line, plus price charts (with Bollinger Bands, RSI with buy/sell thresholds, and MACD), the latest values and a list of signals with their dates. As in the terminal, invalid input is caught and shown as a message instead of crashing. The page only listens on `127.0.0.1`; Chart.js is loaded from a CDN, price data still comes from Yahoo Finance.

Differences from the terminal mode:

- The same ticker/period is fetched at most once every 5 minutes, so switching between indicators is instant but uses data up to 5 minutes old.
- Charts show the last 252 trading days, the signal list the last 100 signals (with a hint when it was truncated). `GET /health` returns `{"status": "ok"}` to check whether the server is running.

## Project structure

| File                    | Purpose                                                      |
| ----------------------- | ------------------------------------------------------------ |
| `stock_analyser.py`     | Command-line interface: input, output, control flow          |
| `stock_analyser_gui.py` | Browser GUI (Flask + Chart.js)                               |
| `market_data.py`        | Yahoo Finance data access (the only module with network access) |
| `indicators.py`         | Pure calculation of RSI, MACD and Bollinger Bands            |
| `templates/index.html`  | Page template of the GUI                                     |
| `tests/`                | pytest tests for all modules, fully offline                  |
| `LICENSE`               | License terms                                                |

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

The tests run offline: network access is replaced by stubs in `tests/test_market_data.py`, `tests/test_cli.py` and `tests/test_gui.py`; the indicator tests use fixed price series.

## Calculations

- **RSI** after Wilder: average gains/losses via exponential smoothing with `alpha = 1/period` (matches TA-Lib and common charting tools); buy below `--rsi-oversold`, sell above `--rsi-overbought`.
- **MACD** = EMA(fast) − EMA(slow), signal line = EMA of the MACD; buy when MACD crosses the signal line from below, sell when it crosses from above. The EMA warm-up phase is ignored.
- **Bollinger Bands** around a simple moving average; buy below the lower band, sell above the upper band. If both bands sit on the price (no volatility), the sell signal wins.

All output consists of technical indicators and is not investment advice.

## License

This project is licensed under the [MIT License](LICENSE).
