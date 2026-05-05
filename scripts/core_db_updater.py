"""
CORE 資料庫更新腳本
更新全市場狀態（TWII, Nasdaq, S&P500）、市場體制判定、VIX 恐懼指標
產出: data/market_regime.json
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [CORE] %(levelname)s %(message)s')
log = logging.getLogger('core_db_updater')

DATA_DIR = Path(__file__).parent.parent / 'data'
OUT_FILE = DATA_DIR / 'market_regime.json'

MARKETS = {
    '^TWII': 'TWII',
    '^IXIC': 'Nasdaq',
    '^GSPC': 'S&P500',
    '^VIX': 'VIX'
}

def classify_regime(df, symbol):
    """市場體制分類: OVERBOUGHT / OVERSOLD / NEUTRAL"""
    try:
        prices = df['Close'].squeeze().dropna()
        ma20 = float(prices.rolling(20).mean().iloc[-1])
        ma60 = float(prices.rolling(60).mean().iloc[-1]) if len(prices) >= 60 else ma20
        rsi_val = float(_calc_rsi(prices).iloc[-1])
        current = float(prices.iloc[-1])

        if current > ma20 and rsi_val > 65:
            regime = 'OVERBOUGHT'
        elif current < ma20 and rsi_val < 35:
            regime = 'OVERSOLD'
        else:
            regime = 'NEUTRAL'

        # 趨勢
        if ma20 > ma60:
            trend = 'UP'
        elif ma20 < ma60:
            trend = 'DOWN'
        else:
            trend = 'SIDEWAYS'

        return regime, trend, rsi_val
    except Exception as e:
        log.warning(f'Regime classification error for {symbol}: {e}')
        return 'NEUTRAL', 'SIDEWAYS', 50.0

def _calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def build_regime():
    log.info('Building market regime data')
    regime_data = {}
    vix_value = None

    for symbol, name in MARKETS.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', auto_adjust=True, progress=False)
            if df.empty:
                log.warning(f'No data for {symbol}')
                continue
            prices = df['Close'].squeeze().dropna()
            latest = float(prices.iloc[-1])
            prev = float(prices.iloc[-2]) if len(prices) > 1 else latest
            change_pct = (latest - prev) / prev * 100

            regime, trend, rsi = classify_regime(df, symbol)

            regime_data[name] = {
                'symbol': symbol,
                'price': latest,
                'change_pct': round(change_pct, 2),
                'regime': regime,
                'trend': trend,
                'rsi': round(rsi, 2),
                'updated_at': datetime.now().isoformat()
            }
            log.info(f'  {name}: price={latest} regime={regime} trend={trend} RSI={rsi:.1f}')

            if name == 'VIX':
                vix_value = latest
        except Exception as e:
            log.error(f'Error processing {symbol}: {e}')

    # 恐懼指數評級
    if vix_value is not None:
        if vix_value > 30:
            fear_level = 'EXTREME_FEAR'
        elif vix_value > 20:
            fear_level = 'FEAR'
        elif vix_value > 15:
            fear_level = 'NEUTRAL'
        else:
            fear_level = 'GREED'
    else:
        fear_level = 'UNKNOWN'

    result = {
        'market_regime': regime_data,
        'vix': vix_value,
        'fear_level': fear_level,
        'updated_at': datetime.now().isoformat()
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f'Written to {OUT_FILE}')
    return result

if __name__ == '__main__':
    log.info('=== CORE DB Updater Start ===')
    result = build_regime()
    log.info(f"Done. VIX={result['vix']} Fear={result['fear_level']}")