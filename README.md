# Stock Indicator Analysis

An interactive Python command-line tool that fetches stock data from Yahoo Finance and calculates technical indicators from historical closing prices.

## Features

- Display company details, price metrics, and the 20 most recent rows of price history within the selected period (or fewer if available).
- Calculate the Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD), or Bollinger Bands with user-specified settings.
- View recent indicator values and optionally list only rows with buy or sell signals. Choose `All Indicators` to see the three indicators’ signals side by side for dates when at least one generated a signal.

## Requirements

- Python 3 with pip
- `pandas`, `numpy`, and `yfinance` (listed in `requirements.txt`)
- Internet access to retrieve Yahoo Finance data

## Installation

```bash
git clone https://github.com/Bene77-w/stock_indicator_analysis.git
cd stock_indicator_analysis
python3 -m pip install -r requirements.txt
```

## Usage

```bash
python3 stock_analyser.py
```

At the prompts, enter a ticker such as `AAPL`, a history period such as `1y` or `3mo`, and an indicator. For example, choose `RSI`, enter `14` for the RSI period, then answer `yes` to display the rows with buy or sell signals. The program then prompts for another ticker. Press `Ctrl+C` to exit.

## Project structure

- `stock_analyser.py` — interactive CLI and indicator calculations
- `requirements.txt` — Python dependencies
- `LICENSE` — license terms

## License

This project is licensed under the [MIT License](LICENSE).
