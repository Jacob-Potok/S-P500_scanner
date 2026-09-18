from unittest.mock import patch, MagicMock
import pandas as pd
import SP500_NASDAQ100_SCAN as s
from streamlit.testing.v1 import AppTest

def test_symbols():
    assert s.normalize_tickers(['BRK.B', 'AAPL', None, 'AAPL']) == ['AAPL', 'BRK-B']

def test_retry():
    s.get_sp500_tickers.clear()
    with patch.object(s, 'read_ticker_tables', side_effect=[OSError('outage'), [pd.DataFrame({'Symbol':['AAPL']})]]) as read:
        try: s.get_sp500_tickers()
        except OSError: pass
        assert s.get_sp500_tickers() == ['AAPL']
        assert read.call_count == 2
    s.get_sp500_tickers.clear()

def test_history():
    with patch.object(s, 'fetch_data', return_value=pd.DataFrame()) as fetch:
        s.analyze_ticker('AAPL',20,200,4)
        assert fetch.call_args.kwargs['weeks'] >= 50

def test_ui():
    prices=pd.DataFrame({'Close':range(100,400)},index=pd.bdate_range('2025-01-01',periods=300))
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'<table><tr><th>Symbol</th></tr><tr><td>AAPL</td></tr></table>'
    with patch('urllib.request.urlopen',return_value=response), patch.object(s.yf,'download',return_value=prices):
        app=AppTest.from_file('SP500_NASDAQ100_SCAN.py').run()
        assert not app.exception
        app.sidebar.button[0].click().run()
        assert not app.exception
        assert 'Found 1 matching' in app.success[0].value

def test_outage_ui():
    s.st.cache_data.clear()
    s.get_sp500_tickers.clear()
    s.get_nasdaq100_tickers.clear()
    with patch('urllib.request.urlopen',side_effect=OSError('outage')):
        app=AppTest.from_file('SP500_NASDAQ100_SCAN.py').run()
        assert not app.exception
        assert app.button[0].label == 'Retry ticker loading'
