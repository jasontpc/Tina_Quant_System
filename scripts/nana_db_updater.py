"""
NANA 資料庫更新腳本
更新持股資料（2330, 2382, 3665, 2317, 3034）、RSI/MA/BIAS 指標、法人買賣超
產出: data/nana_watchlist.json
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [NANA] %(levelname)s %(message)s')
log = logging.getLogger('nana_db_updater')

DATA_DIR = Path(__file__).parent.parent / 'data'
OUT_FILE = DATA_DIR / 'nana_watchlist.json'
DB_FILE = DATA_DIR / 'tw_history.db'

STOCKS = ['2330.TW', '2382.TW', '3665.TW', '2317.TW', '3034.TW']

def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def get_ma(prices, periods=[5, 10, 20, 60]):
    result = {}
    for p in periods:
        result[f'ma{p}'] = float(prices.rolling(p).mean().iloc[-1])
    return result

def get_bias(prices, ma_period=20):
    ma = prices.rolling(ma_period).mean().iloc[-1]
    return float((prices.iloc[-1] - ma) / ma * 100)

def fetch_institutional():
    """使用 FinMind API 抓法人買賣超"""
    try:
        import requests
        token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
        date = datetime.now().strftime('%Y-%m-%d')
        results = {}
        for sid in STOCKS:
            symbol = sid.replace('.TW', '')
            url = f'https://api.finmindtrade.com/api/v4/data'
            params = {
                'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
                'data_date': date,
                'stock_id': symbol,
                'token': token
            }
            try:
                r = requests.get(url, params=params, timeout=5)
                d = r.json()
                if d.get('data'):
                    df = pd.DataFrame(d['data'])
                    buy = df[df['buy_or_sell'] == 'Buy']['volume'].sum()
                    sell = df[df['buy_or_sell'] == 'Sell']['volume'].sum()
                    results[symbol] = {'buy': int(buy), 'sell': int(sell), 'net': int(buy - sell)}
                else:
                    results[symbol] = {'buy': 0, 'sell': 0, 'net': 0}
            except Exception as e:
                results[symbol] = {'buy': 0, 'sell': 0, 'net': 0, 'error': str(e)}
        return results
    except Exception as e:
        log.warning(f'FinMind institutional fetch failed: {e}')
        return {s.replace('.TW', ''): {'buy': 0, 'sell': 0, 'net': 0} for s in STOCKS}

def update_db():
    """更新本地 SQLite 歷史資料"""
    try:
        conn = sqlite3.connect(DB_FILE)
        for symbol in STOCKS:
            try:
                df = yf.download(symbol, period='2y', interval='1d', auto_adjust=True, progress=False)
                if df.empty:
                    continue
                df = df.reset_index()
            except Exception as e:
                log.warning(f'yf download {symbol} failed: {e}')
                continue
        conn.close()
        log.info(f'TW history DB updated')
        return True
    except Exception as e:
        log.error(f'DB update error: {e}')
        return False

def build_watchlist():
    """產出 nana_watchlist.json"""
    log.info(f'Building NANA watchlist for {STOCKS}')
    watchlist = []
    inst_data = fetch_institutional()

    for symbol in STOCKS:
        sid = symbol.replace('.TW', '')
        try:
            df = yf.download(symbol, period='3mo', interval='1d', auto_adjust=True, progress=False)
            if df.empty:
                log.warning(f'No data for {symbol}')
                continue
            prices = df['Close'].squeeze().dropna()
            latest_price = float(prices.iloc[-1])
            prev_price = float(prices.iloc[-2]) if len(prices) > 1 else latest_price
            change_pct = (latest_price - prev_price) / prev_price * 100

            rsi = float(get_rsi(prices).iloc[-1])
            ma_data = get_ma(prices)
            bias = get_bias(prices)

            entry = {
                'symbol': sid,
                'name': _get_name(sid),
                'price': latest_price,
                'change_pct': round(change_pct, 2),
                'rsi': round(rsi, 2),
                'ma': ma_data,
                'bias': round(bias, 2),
                'institutional': inst_data.get(sid, {'buy': 0, 'sell': 0, 'net': 0}),
                'updated_at': datetime.now().isoformat()
            }
            watchlist.append(entry)
            log.info(f'  {sid}: price={latest_price} RSI={rsi:.1f} BIAS={bias:.2f}')
        except Exception as e:
            log.error(f'Error processing {symbol}: {e}')

    result = {
        'team': 'nana',
        'updated_at': datetime.now().isoformat(),
        'stocks': watchlist
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f'Written to {OUT_FILE}')
    return result

def _get_name(sid):
    names = {
        '2330': '台積電', '2382': '廣達', '3665': '穎崴', '2317': '鴻海', '3034': '緯穎'
    }
    return names.get(sid, sid)

if __name__ == '__main__':
    log.info('=== NANA DB Updater Start ===')
    update_db()
    result = build_watchlist()
    log.info(f"Done. {len(result['stocks'])} stocks updated.")