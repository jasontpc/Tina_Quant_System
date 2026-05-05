"""
RAY 資料庫更新腳本
更新 ETF 資料（0050, 00646, 00713, 0056）、DCA 分數、價值評估
產出: data/ray_watchlist.json
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [RAY] %(levelname)s %(message)s')
log = logging.getLogger('ray_db_updater')

DATA_DIR = Path(__file__).parent.parent / 'data'
OUT_FILE = DATA_DIR / 'ray_watchlist.json'

ETFS = ['0050.TW', '00646.TW', '00713.TW', '0056.TW']

def calc_dca_score(prices, lookback=60):
    """DCA 分數: 均線偏離 + 波動率舒適度"""
    ma = float(prices.rolling(lookback).mean().iloc[-1])
    dev = abs((float(prices.iloc[-1]) - ma) / ma)
    vol = float(prices.pct_change().rolling(lookback).std().iloc[-1])
    # 低偏離 + 低波動 = 高分
    comfort = max(0, 1 - (dev * 10 + vol * 50))
    return round(float(comfort), 4)

def calc_value_score(df):
    """價值評估: PE/PB/殖利率 proxy"""
    try:
        info = df['Close'].squeeze().dropna()
        ret_1y = float(info.iloc[-1] / info.iloc[-252] - 1) if len(info) >= 252 else 0
        ret_3m = float(info.iloc[-1] / info.iloc[-63] - 1) if len(info) >= 63 else 0
        vol = float(info.pct_change().rolling(20).std().iloc[-1])
        return {
            'return_3m': round(ret_3m, 4),
            'return_1y': round(ret_1y, 4),
            'volatility_20d': round(vol, 4)
        }
    except Exception as e:
        log.warning(f'Value score error: {e}')
        return {'return_3m': 0, 'return_1y': 0, 'volatility_20d': 0}

def build_watchlist():
    log.info(f'Building RAY watchlist for {ETFS}')
    watchlist = []

    for symbol in ETFS:
        sid = symbol.replace('.TW', '')
        try:
            df = yf.download(symbol, period='2y', interval='1d', auto_adjust=True, progress=False)
            if df.empty:
                log.warning(f'No data for {symbol}')
                continue
            prices = df['Close'].squeeze().dropna()
            latest_price = float(prices.iloc[-1])
            prev_price = float(prices.iloc[-2]) if len(prices) > 1 else latest_price
            change_pct = (latest_price - prev_price) / prev_price * 100

            dca_score = calc_dca_score(prices)
            value = calc_value_score(df)

            entry = {
                'symbol': sid,
                'name': _get_name(sid),
                'price': latest_price,
                'change_pct': round(change_pct, 2),
                'dca_score': dca_score,
                'value': value,
                'updated_at': datetime.now().isoformat()
            }
            watchlist.append(entry)
            log.info(f'  {sid}: price={latest_price} DCA={dca_score} 3m={value["return_3m"]*100:.1f}%')
        except Exception as e:
            log.error(f'Error processing {symbol}: {e}')

    result = {
        'team': 'ray',
        'updated_at': datetime.now().isoformat(),
        'etfs': watchlist
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f'Written to {OUT_FILE}')
    return result

def _get_name(sid):
    names = {
        '0050': '元大台灣50', '00646': '元大S&P500', '00713': '元大高股息', '0056': '元大高股息'
    }
    return names.get(sid, sid)

if __name__ == '__main__':
    log.info('=== RAY DB Updater Start ===')
    result = build_watchlist()
    log.info(f"Done. {len(result['etfs'])} ETFs updated.")