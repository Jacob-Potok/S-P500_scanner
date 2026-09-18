import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from urllib.request import Request, urlopen
import math

# Configuration defaults
TICKERS_URL_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
TICKERS_URL_NASDAQ100 = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
DEFAULT_SMA_SHORT = 20
DEFAULT_SMA_LONG = 50
DEFAULT_AROC_WEEKS = 20

def read_ticker_tables(url):
    # Wikipedia rejects the default Python user agent on some cloud hosts.
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; StockScanner/1.0)"
    })
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8")
    return pd.read_html(StringIO(html), flavor="lxml")


def normalize_tickers(values):
    return sorted({str(value).strip().replace(".", "-")
                   for value in values if pd.notna(value) and str(value).strip()})


@st.cache_data(show_spinner=False, ttl=86400)
def get_sp500_tickers():
    for table in read_ticker_tables(TICKERS_URL_SP500):
        if "Symbol" in table.columns:
            tickers = normalize_tickers(table["Symbol"])
            if tickers:
                return tickers
    raise ValueError("Could not find S&P 500 constituent symbols.")


@st.cache_data(show_spinner=False, ttl=86400)
def get_nasdaq100_tickers():
    for table in read_ticker_tables(TICKERS_URL_NASDAQ100):
        for col in table.columns:
            if isinstance(col, str) and col in ("Ticker", "Symbol"):
                tickers = normalize_tickers(table[col])
                if tickers:
                    return tickers
    raise ValueError("Could not find Nasdaq 100 constituent symbols.")

def get_all_tickers():
    combined = set()
    for name, loader in (("S&P 500", get_sp500_tickers), ("Nasdaq 100", get_nasdaq100_tickers)):
        try:
            combined.update(loader())
        except Exception as exc:
            st.warning(f"Could not load {name} tickers: {exc}. Please retry shortly.")
    combined = list(combined)
    combined.sort()
    return combined

@st.cache_data(show_spinner=False, ttl=900)
def fetch_data(ticker, weeks):
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=weeks)
    try:
        df = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False, auto_adjust=True, timeout=20)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.warning(f"Error fetching data for {ticker}: {e}")
        return None

def calc_indicators(df, sma_short, sma_long, aroc_weeks):
    try:
        df["SMA_short"] = df["Close"].rolling(window=sma_short).mean()
        df["SMA_long"] = df["Close"].rolling(window=sma_long).mean()
        window = aroc_weeks * 5  # Approx. trading days in N weeks
        df["20w_high"] = df["Close"].rolling(window=window).max()
        df["AROC"] = ((df["Close"] - df["Close"].shift(window)) / df["Close"].shift(window)) * 100
        return df
    except Exception as e:
        st.warning(f"Indicator calculation error: {e}")
        return df

def analyze_ticker(ticker, sma_short, sma_long, aroc_weeks):
    # SMA windows count trading days, while the download range counts weeks.
    required_days = max(sma_short, sma_long, aroc_weeks * 5 + 1)
    weeks = math.ceil(required_days / 5) + 10
    df = fetch_data(ticker, weeks=weeks)
    if df is None or df.empty:
        return None
    df = calc_indicators(df, sma_short, sma_long, aroc_weeks)
    latest = df.iloc[-1]
    if latest[["Close", "SMA_short", "SMA_long", "20w_high", "AROC"]].isna().any():
        return None
    try:
        # Combined entry logic
        entry_signal = (
            latest["Close"] > latest["SMA_short"]
            and latest["SMA_short"] > latest["SMA_long"]
            and latest["Close"] >= 0.95 * latest["20w_high"]
            and latest["AROC"] > 5
        )
        if entry_signal:
            entry_price = latest["Close"]
            sma_exit = latest["SMA_short"]
            trailing_stop_exit = entry_price * 0.93  # 7% trailing stop
            sell_recommendation = max(sma_exit, trailing_stop_exit)
            return {
                "Ticker": ticker,
                "Date": df.index[-1].strftime("%Y-%m-%d"),
                "Close": latest["Close"],
                "SMA_short": latest["SMA_short"],
                "SMA_long": latest["SMA_long"],
                "20w_high": latest["20w_high"],
                "AROC": latest["AROC"],
                "Entry Recommendation": entry_price,
                "Sell Recommendation": sell_recommendation,
            }
    except Exception as e:
        st.warning(f"Error processing {ticker}: {e}")
    return None

def main():
    st.title("S&P 500 & Nasdaq 100 Technical Scanner")
    st.write("Scan S&P 500 and Nasdaq 100 stocks for bullish technical setups.")

    tickers = get_all_tickers()
    if not tickers:
        st.error("Ticker lists are temporarily unavailable. Retry to load them again.")
        if st.button("Retry ticker loading"):
            st.rerun()
        st.stop()

    with st.sidebar:
        st.header("Scan Settings")
        selected_tickers = st.multiselect(
            "Select tickers (leave empty for all)",
            options=tickers,
            default=[],
            help="Choose one or more tickers, or leave empty to scan all S&P 500 and Nasdaq 100."
        )
        sma_short = st.number_input("SMA Short Window", min_value=5, max_value=100, value=DEFAULT_SMA_SHORT)
        sma_long = st.number_input("SMA Long Window", min_value=10, max_value=200, value=DEFAULT_SMA_LONG)
        aroc_weeks = st.number_input("AROC/High Weeks", min_value=4, max_value=52, value=DEFAULT_AROC_WEEKS)
        run_scan = st.button("Run Scan")

    if run_scan:
        to_scan = selected_tickers if selected_tickers else tickers
        results = []
        progress = st.progress(0)
        status = st.empty()
        for i, ticker in enumerate(to_scan):
            status.text(f"Analyzing {ticker} ({i+1}/{len(to_scan)})...")
            result = analyze_ticker(ticker, sma_short, sma_long, aroc_weeks)
            if result:
                results.append(result)
            progress.progress((i+1)/len(to_scan))
        status.text("")
        progress.empty()
        if results:
            df_results = pd.DataFrame(results)
            st.success(f"Found {len(df_results)} matching tickers.")
            st.dataframe(df_results)
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "scan_output.csv", "text/csv")
        else:
            st.info("No tickers matched the criteria.")

if __name__ == "__main__":
    main()
