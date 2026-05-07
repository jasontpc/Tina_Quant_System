import yfinance as yf

twii = yf.Ticker('^TWII').history(period='1mo')
print('TWII 1mo:')
print(f'First close: {twii["Close"].iloc[0]:,.2f}')
print(f'Last close: {twii["Close"].iloc[-1]:,.2f}')
print(f'Prev close: {twii["Close"].iloc[-2]:,.2f}')
print(f'Month chg: {(twii["Close"].iloc[-1]/twii["Close"].iloc[0]-1)*100:.2f}%')
print(f'Day chg: {(twii["Close"].iloc[-1]/twii["Close"].iloc[-2]-1)*100:.2f}%')
print(f'Dates: {twii.index[0]} to {twii.index[-1]}')

spy = yf.Ticker('^GSPC').history(period='1mo')
print()
print('SPX 1mo:')
print(f'First close: {spy["Close"].iloc[0]:,.2f}')
print(f'Last close: {spy["Close"].iloc[-1]:,.2f}')
print(f'Month chg: {(spy["Close"].iloc[-1]/spy["Close"].iloc[0]-1)*100:.2f}%')
print(f'Dates: {spy.index[0]} to {spy.index[-1]}')