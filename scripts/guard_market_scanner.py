# -*- coding: utf-8 -*-
"""
GUARD Market Scanner - 軍工國防市場動態掃描
=========================================
地緣政治事件驅動 + 技術面進場
"""
import sqlite3, json, sys, yfinance
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

GUARD_STOCKS = ['2634.TW', '2313.TW']
TWII_SYMBOL = '^TWII'


def get_twii():
    """取得加權指數"""
    try:
        tk = yfinance.Ticker(TWII_SYMBOL)
        h = tk.history(period='5d')
        return float(h['Close'].iloc[-1])
    except:
        return None


def get_guard_indicators():
    """取得軍工股指標"""
    results = []

    for sym in GUARD_STOCKS:
        try:
            tk = yfinance.Ticker(sym)
            h = tk.history(period='90d')
            if len(h) < 30:
                continue

            prices = list(h['Close'])
            highs = list(h['High'])
            lows = list(h['Low'])
            vols = list(h['Volume'])
            s = pd.Series(prices)

            # RSI
            delta = s.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # MACD
            ema12 = s.ewm(span=12, adjust=False).mean()
            ema26 = s.ewm(span=26, adjust=False).mean()
            macd_l = ema12 - ema26
            macd_s = macd_l.ewm(span=9, adjust=False).mean()
            macd_h = float((macd_l - macd_s).iloc[-1])

            # ATR
            tr = pd.Series([max(highs[i]-lows[i], abs(highs[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))])
            atr = tr.ewm(span=14, adjust=False).mean()
            atr_pct = float(atr.iloc[-1] / prices[-1] * 100)

            # Vol ratio
            vol20 = pd.Series(vols).rolling(20).mean().iloc[-1]
            vol_r = vols[-1] / vol20 if vol20 > 0 else 1.0

            # 5日/20日動能
            chg_5d = (prices[-1] / prices[-6] - 1) * 100 if len(prices) >= 6 else 0
            chg_20d = (prices[-1] / prices[-21] - 1) * 100 if len(prices) >= 21 else 0

            # 52週高低
            high_52w = max(highs)
            low_52w = min(highs[-252:]) if len(highs) >= 252 else min(prices)
            pos_in_range = (prices[-1] - low_52w) / (high_52w - low_52w) * 100 if high_52w > low_52w else 50

            results.append({
                'symbol': sym,
                'price': prices[-1],
                'rsi': round(rsi, 1),
                'macd': round(macd_h, 3),
                'atr_pct': round(atr_pct, 1),
                'vol_r': round(vol_r, 2),
                'chg_5d': round(chg_5d, 1),
                'chg_20d': round(chg_20d, 1),
                'pos_52w': round(pos_in_range, 1),
                'high_52w': high_52w,
            })

        except Exception as e:
            continue

    return results


def main():
    print('='*60)
    print('  GUARD 軍工國防市場掃描')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    twii = get_twii()
    print(f'\n【宏觀環境】')
    if twii:
        print(f"  TWII: {twii:.2f}")
    print(f"  地緣政治: {'⚠️ 台海局勢緊張' if True else '✅ 相對穩定'}")
    print(f"  國防預算: 📈 2026年國防預算新高")

    stocks = get_guard_indicators()
    print(f'\n【軍工股掃描】({len(stocks)} 檔)')

    buy_signals = []
    watch_signals = []

    for s in stocks:
        rsi_icon = '🔴' if s['rsi'] > 75 else ('⚠️' if s['rsi'] > 65 else '🟢')
        macd_icon = '▲' if s['macd'] > 0 else '▼'
        vol_icon = '🔥' if s['vol_r'] > 2 else ''
        print(f"\n  {s['symbol']}: ${s['price']:.2f}")
        print(f"    RSI: {rsi_icon}{s['rsi']} | MACD: {macd_icon}{s['macd']} | ATR: {s['atr_pct']}%")
        print(f"    5日: {s['chg_5d']:+.1f}% | 20日: {s['chg_20d']:+.1f}%")
        print(f"    52w位置: {s['pos_52w']:.0f}% | Vol: {vol_icon}{s['vol_r']}x")

        # 進場條件：RSI 30-55 + MACD 多頭
        if 30 <= s['rsi'] <= 55 and s['macd'] > 0:
            buy_signals.append(s)
        elif s['rsi'] < 60 and s['macd'] > 0:
            watch_signals.append(s)

    print(f'\n【信號】')
    if buy_signals:
        print(f"  🟢 進場:")
        for s in sorted(buy_signals, key=lambda x: -x['rsi']):
            print(f"    {s['symbol']}: RSI={s['rsi']} MACD={s['macd']} ATR={s['atr_pct']}%")
    else:
        print(f"  ⚪ 無進場（等待 RSI 回調至 30-55 區間）")

    if watch_signals:
        print(f"  🟡 觀望:")
        for s in sorted(watch_signals, key=lambda x: x['rsi']):
            print(f"    {s['symbol']}: RSI={s['rsi']}")


if __name__ == '__main__':
    main()