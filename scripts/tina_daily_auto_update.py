# -*- coding: utf-8 -*-
"""
Tina Brain - 每日自動化更新 Cron
===============================
每日 16:00 自動更新所有團隊DB
"""
import yfinance as yf
import numpy as np
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

def calc_rsi(close):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_atr(h):
    tr = np.maximum(h['High']-h['Low'], 
                    np.maximum(abs(h['High']-h['Close'].shift(1)), 
                               abs(h['Low']-h['Close'].shift(1))))
    return tr.rolling(14).mean()

def get_stock_data(sym):
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")
        if h is None or len(h) < 50: return None
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close']).iloc[-1])
        atr = float(calc_atr(h).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        ma60 = float(h['Close'].rolling(60).mean().iloc[-1])
        atr_pct = atr / price * 100
        ma_ok = bool(ma20 > ma60) and not (np.isnan(ma20) or np.isnan(ma60))
        return {'price': price, 'rsi': rsi, 'ma20': ma20, 'ma60': ma60, 'atr_pct': atr_pct, 'ma_ok': ma_ok}
    except: return None

leo_stocks = [('3037.TW','欣興'),('3189.TW','景碩'),('2360.TW','致茂'),('3665.TW','穎崴'),('2345.TW','智邦'),
              ('2383.TW','台光電'),('2449.TW','京元電'),('3017.TW','奇力新'),('2308.TW','台達電'),
              ('3016.TW','嘉晶'),('2330.TW','台積電')]
nana_stocks = [('2454.TW','聯發科'),('6442.TW','光聖'),('2359.TW','所羅門'),('3231.TW','緯創'),
               ('2317.TW','鴻海'),('2382.TW','廣達'),('6239.TW','力成'),('2308.TW','台達電'),
               ('3016.TW','嘉晶'),('2330.TW','台積電')]
hunter_stocks = [('MSFT','Microsoft'),('PLTR','Palantir'),('TSLA','Tesla'),('AMD','AMD'),
                 ('3443.TW','創意'),('3661.TW','世芯-KY'),('3532.TW','台勝科'),('6239.TW','力成'),
                 ('3231.TW','緯創'),('2317.TW','鴻海'),('ASML','ASML'),('SIMO','慧榮')]

def update_db(db_path, team_name, stocks):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for sym, name in stocks:
        d = get_stock_data(sym)
        if not d: continue
        signal = "watch"
        if d['ma_ok'] and d['rsi'] < 35: signal = "buy_a"
        elif d['ma_ok'] and d['rsi'] < 50: signal = "buy_b"
        elif d['rsi'] > 70: signal = "overbought"
        elif not d['ma_ok']: signal = "ma_fail"
        cur.execute("UPDATE stock_tracking SET price=?,rsi=?,ma20=?,ma60=?,atr_pct=?,ma_ok=?,signal=?,updated_at=? WHERE symbol=?",
                    (d['price'],d['rsi'],d['ma20'],d['ma60'],d['atr_pct'],1 if d['ma_ok'] else 0,signal,now,sym))
    cur.execute("UPDATE team_meta SET value=? WHERE key='last_update'", (now,))
    conn.commit()
    conn.close()

update_db(DATA/"leo_stocks.db", "Leo", leo_stocks)
update_db(DATA/"nana_stocks.db", "Nana", nana_stocks)
update_db(DATA/"hunter_stocks.db", "Hunter", hunter_stocks)

print("✅ 團隊DB更新完成")
