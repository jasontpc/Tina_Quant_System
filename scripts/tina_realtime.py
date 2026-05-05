# -*- coding: utf-8 -*-
"""
Tina 即時分析工具 v1.0
======================
用途：直接連線 yfinance 即時分析美股/台股
用法：python tina_realtime.py [股票代碼]
     python tina_realtime.py --all（全部分析）
     python tina_realtime.py --market [us|tw]（市場概況）
"""
import yfinance as yf
import numpy as np
import sys
from datetime import datetime

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(close, fast=12, slow=26, signal=9):
    ema12 = close.ewm(span=fast, adjust=False).mean()
    ema26 = close.ewm(span=slow, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.values[-1], signal_line.values[-1]

def calc_atr(h, period=14):
    tr = np.maximum(h['High']-h['Low'], 
                    np.maximum(abs(h['High']-h['Close'].shift(1)), 
                               abs(h['Low']-h['Close'].shift(1))))
    return tr.rolling(period).mean()

def analyze_stock(sym, name=None, period="3mo"):
    try:
        t = yf.Ticker(sym)
        h = t.history(period=period)
        if h is None or len(h) < 30:
            return {"error": f"無資料：{sym}"}
        
        close = h["Close"]
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        chg = (price - prev) / prev * 100
        rsi = float(calc_rsi(close).iloc[-1])
        macd_val, sig_val = calc_macd(close)
        hist = macd_val - sig_val
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
        atr = float(calc_atr(h).iloc[-1])
        atr_pct = atr / price * 100
        sl = price * (1 - atr_pct * 2.5 / 100)
        high = float(h["High"].max())
        low = float(h["Low"].min())
        pct = (price - low) / (high - low) * 100
        volume_avg = h["Volume"].iloc[-20:].mean()
        
        return {
            "symbol": sym,
            "name": name or sym,
            "price": price,
            "chg": chg,
            "rsi": rsi,
            "macd_hist": hist,
            "ma20": ma20,
            "ma60": ma60,
            "atr_pct": atr_pct,
            "stop_loss": sl,
            "high": high,
            "low": low,
            "pct": pct,
            "volume_avg": volume_avg,
        }
    except Exception as e:
        return {"error": str(e)}

def get_tier(rsi, macd_hist):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def print_analysis(d):
    if "error" in d:
        print(f"  ❌ {d['symbol']}: {d['error']}")
        return
    
    tier = get_tier(d['rsi'], d['macd_hist'])
    icon = {"A":"🥇","B":"🥈","C":"🥉","D":"❌"}.get(tier,"?")
    
    # 進場評估
    if tier == "A":
        entry = "🥇 超跌，建議觀察"
    elif tier == "B":
        if d['macd_hist'] > 0:
            entry = "✅ 可進場"
        else:
            entry = "⏸️ 等 MACD 轉正"
    elif tier == "C":
        entry = "⏸️ 觀望"
    else:
        entry = "❌ 過熱，觀望"
    
    # MA 多頭
    ma_bull = "✅" if (d['ma60'] and d['ma20'] > d['ma60']) else "❌"
    
    print(f"{icon} {d['name']} [{d['symbol']}]")
    print(f"   價格: ${d['price']:.2f} ({d['chg']:+.2f}%)")
    print(f"   RSI: {d['rsi']:.1f} | MACD: {d['macd_hist']:+.2f}")
    ma60_str = f"${d['ma60']:.2f}" if d['ma60'] else "N/A"
    print(f"   MA20: ${d['ma20']:.2f} | MA60: {ma60_str}")
    print(f"   MA多頭: {ma_bull} | ATR: {d['atr_pct']:.1f}%")
    print(f"   停損: ${d['stop_loss']:.2f} ({d['atr_pct']*2.5:.1f}%)")
    print(f"   區間: {d['pct']:.0f}%")
    print(f"   評估: {entry}")
    print()

def analyze_us_market():
    print("="*65)
    print("  美股即時分析")
    print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*65)
    print()
    
    print("【美股指數】")
    indices = [
        ("^DJI","道瓊"),("^IXIC","Nasdaq"),("^GSPC","S&P 500"),("^VIX","VIX")
    ]
    for sym, name in indices:
        d = analyze_stock(sym)
        if "error" not in d:
            status = "🔴" if d['rsi'] > 70 else ("⚠️" if d['rsi'] > 60 else "✅")
            rsi_str = f"RSI {d['rsi']:.1f}" if not np.isnan(d['rsi']) else ""
            print(f"  {status} {name}: {d['price']:,.2f} ({d['chg']:+.2f}%) {rsi_str}")
    print()
    
    print("【AI/科技股】")
    stocks = [
        ("AAPL","Apple"),("MSFT","Microsoft"),("NVDA","Nvidia"),
        ("GOOGL","Google"),("AMZN","Amazon"),("META","Meta"),
        ("TSLA","Tesla"),("AVGO","Broadcom"),("AMD","AMD"),
        ("INTC","Intel"),("ASML","ASML"),("LRCX","Lam Res"),
        ("PLTR","Palantir"),("MSTR","MicroStrategy"),("COIN","Coinbase"),
    ]
    for sym, name in stocks:
        d = analyze_stock(sym, name)
        print_analysis(d)

def analyze_tw_market():
    print("="*65)
    print("  台股即時分析")
    print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*65)
    print()
    
    print("【加權指數】")
    d = analyze_stock("^TWII")
    if "error" not in d:
        status = "🔴" if d['rsi'] > 85 else ("⚠️" if d['rsi'] > 70 else "✅")
        print(f"  {status} TWII: {d['price']:,.2f} ({d['chg']:+.2f}%) RSI {d['rsi']:.1f}")
    print()
    
    print("【台股科技股】")
    stocks = [
        ("2330.TW","台積電"),("2454.TW","聯發科"),("2317.TW","鴻海"),
        ("2382.TW","广達"),("3231.TW","緯創"),("3665.TW","穎崴"),
        ("3034.TW","聯發科"),("2379.TW","瑞昱"),("3037.TW","欣興"),
        ("6442.TW","光聖"),("2360.TW","致茂"),
    ]
    for sym, name in stocks:
        d = analyze_stock(sym, name)
        print_analysis(d)

def analyze_etf():
    print("="*65)
    print("  ETF 即時分析")
    print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*65)
    print()
    
    etfs = [
        # 美股ETF
        ("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2000"),
        ("SOXX","iShares 費半"),("SMH","VanEck 半導體"),
        ("TQQQ","3x Nasdaq"),("SOXL","3x 半導體"),
        # 台股ETF
        ("0050.TW","元大台灣50"),("0056.TW","元大高股息"),
        ("00713.TW","元大高息低波"),("00646.TW","元大S&P500"),
    ]
    for sym, name in etfs:
        d = analyze_stock(sym, name)
        print_analysis(d)

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python tina_realtime.py --us      美股分析")
        print("  python tina_realtime.py --tw      台股分析")
        print("  python tina_realtime.py --etf     ETF分析")
        print("  python tina_realtime.py --all     全部分析")
        print("  python tina_realtime.py [代碼]    單一股票分析")
        print()
        print("範例:")
        print("  python tina_realtime.py AAPL")
        print("  python tina_realtime.py 2330.TW")
        print("  python tina_realtime.py --us")
        return
    
    arg = sys.argv[1].upper()
    
    if arg == "--US":
        analyze_us_market()
    elif arg == "--TW":
        analyze_tw_market()
    elif arg == "--ETF":
        analyze_etf()
    elif arg == "--ALL":
        analyze_us_market()
        print("\n" + "="*65 + "\n")
        analyze_tw_market()
    elif arg.startswith("--"):
        print(f"未知參數: {arg}")
    else:
        # 單一股票
        sym = arg if "." in arg else arg
        d = analyze_stock(sym)
        print_analysis(d)

if __name__ == "__main__":
    main()