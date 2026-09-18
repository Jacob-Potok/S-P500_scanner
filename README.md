# S&P 500 & Nasdaq 100 Scanner

A Python and Streamlit dashboard that screens S&P 500 and Nasdaq 100 stocks for bullish technical setups using daily price data from Yahoo Finance via `yfinance`.

Choose individual stocks or scan both indexes. Adjust the moving-average and momentum windows, review matching stocks, and download results as a CSV.

## How it works

A stock matches when its close is above the short moving average, the short average is above the long average, the close is within 5% of its lookback closing high, and its lookback price change exceeds 5%. The defaults are 20- and 50-day averages and a 20-week momentum window. The output includes the latest close and a suggested exit reference based on the greater of the short moving average and 93% of the current close; it does not track a live trailing stop.

Index membership comes from Wikipedia and refreshes daily. Price downloads refresh after 15 minutes. Share-class symbols are converted to Yahoo Finance format, such as `BRK-B`. Failed ticker-list requests can be retried without caching an empty list.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run SP500_NASDAQ100_SCAN.py
```

## Streamlit Community Cloud

Select this repository, the `main` branch, and **`SP500_NASDAQ100_SCAN.py`** as the main file. Dependencies are in the root `requirements.txt`. No API key is required. External data sources may reject or rate-limit requests, and scanning the entire universe can take several minutes.

This is an educational screening project, not a tested trading strategy or a guarantee of returns.
