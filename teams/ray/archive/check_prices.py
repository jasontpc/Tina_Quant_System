import yfinance as yf
import pandas as pd

etfs = ['0050','0056','00878','00891','00919','00927','00713','00646','00662','00757','00923','00915','00917','00918','00920']
for etf in etfs:
    try:
        sym = etf + '.TW'
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close']
        if isinstance(close, pd.DataFrame):
            close = close.squeeze()
        price = close.iloc[-1] if len(close) > 0 else None
        valid = close.dropna()
        last_date = close.index[-1] if len(close) > 0 else 'N/A'
        print(f'{etf}: price={price}, valid={len(valid)}/{len(close)}, last={last_date}')
    except Exception as e:
        print(f'{etf}: ERROR - {e}')
