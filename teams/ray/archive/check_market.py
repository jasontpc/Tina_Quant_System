import yfinance as yf
import json

tw = yf.Ticker('^TWII').history(period='1mo')
sp = yf.Ticker('SPY').history(period='1mo')
tw_close = float(tw['Close'].iloc[-1])
tw_high = float(tw['High'].max())
tw_low = float(tw['Low'].min())
sp_close = float(sp['Close'].iloc[-1])

tw_pos = (tw_close - tw_low) / (tw_high - tw_low) * 100

print(f'TWII: {tw_close:.2f} (52W high: {tw_high:.2f})')
print(f'SPY: {sp_close:.2f}')
print(f'TWII 位置: {tw_pos:.1f}%')
print(f'市場狀態: {"過熱 OVERBOUGHT" if tw_pos > 70 else "偏熱" if tw_pos > 50 else "中性" if tw_pos > 30 else "偏冷" if tw_pos > 10 else "過冷 OVERSOLD"}')
