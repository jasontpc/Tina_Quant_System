"""
LEO 資料庫更新腳本
更新科技股資料（2454, 2345, 3017, 3034, 4961）、法人流向追蹤、VIF 評分
產出: data/leo_watchlist.json
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import json
import logging
import requests
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [LEO] %(levelname)s %(message)s')
log = logging.getLogger('leo_db_updater')

DATA_DIR = Path(__file__).parent.parent / 'data'
OUT_FILE = DATA_DIR / 'leo_watchlist.json'
DB_FILE = DATA_DIR / 'tw_history.db'

STOCKS = ['2454.TW', '2345.TW', '3017.TW', '3034.TW', '4961.TW']
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_vif(df, period=20):
    """簡易 VIF proxy: 採用價格動量與波動率 ratio"""
    prices = df['Close'].squeeze().dropna()
    ret = prices.pct_change().dropna()
    mom = ret.rolling(period).mean().iloc[-1]
    vol = ret.rolling(period).std().iloc[-1]
    score = mom / vol if vol != 0 else 0
    return float(score) if not np.isnan(score) else 0.0

def fetch_institutional():
    """FinMind 法人買賣超"""
    date = datetime.now().strftime('%Y-%m-%d')
    results = {}
    for sid in STOCKS:
        symbol = sid.replace('.TW', '')
        try:
            url = 'https://api.finmindtrade.com/api/v4/data'
            params = {
                'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
                'data_date': date,
                'stock_id': symbol,
                'token': FINMIND_TOKEN
            }
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
            results[symbol] = {'buy': 0, 'sell': 0, 'net': 0}
    return results

def build_watchlist():
    log.info(f'Building LEO watchlist for {STOCKS}')
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
            mom_score = calc_vif(df)

            # 簡易法人分數
            net = inst_data.get(sid, {}).get('net', 0)
            inst_score = 1 if net > 0 else (-1 if net < 0 else 0)

            entry = {
                'symbol': sid,
                'name': _get_name(sid),
                'price': latest_price,
                'change_pct': round(change_pct, 2),
                'rsi': round(rsi, 2),
                'vif_score': round(mom_score, 4),
                'institutional': inst_data.get(sid, {'buy': 0, 'sell': 0, 'net': 0}),
                'inst_score': inst_score,
                'updated_at': datetime.now().isoformat()
            }
            watchlist.append(entry)
            log.info(f'  {sid}: price={latest_price} RSI={rsi:.1f} VIF={mom_score:.3f}')
        except Exception as e:
            log.error(f'Error processing {symbol}: {e}')

    result = {
        'team': 'leo',
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
        '2454': '聯發科', '2345': '智邦', '3017': '嘉澤', '3034': '緯穎', '4961': '天璣'
    }
    return names.get(sid, sid)

if __name__ == '__main__':
    log.info('=== LEO DB Updater Start ===')
    result = build_watchlist()
    log.info(f"Done. {len(result['stocks'])} stocks updated.")