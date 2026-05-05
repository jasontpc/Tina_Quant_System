# -*- coding: utf-8 -*-
"""
Trade History Updater - Tina Quant System
Updates historical price data and computes technical indicators.
Stores to data/trade_history.db
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = f"{BASE}\\data"

# Stock pools
TW_STOCKS = ["2330", "2382", "2454", "2317", "3034", "3665", "4961", "3231", "3017", "3717"]
US_STOCKS = ["D", "BMY", "SO", "DXCM", "COIN", "NET", "RIVN", "SOFI"]


def compute_indicators(df):
    """Add technical indicators to OHLCV dataframe"""
    close = df['close'].astype(float)

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # RSI-5
    gain5 = delta.clip(lower=0).rolling(5).mean()
    loss5 = (-delta.clip(upper=0)).rolling(5).mean()
    rs5 = gain5 / loss5.replace(0, np.nan)
    df['rsi_5'] = 100 - (100 / (1 + rs5))

    # MA
    df['sma_5'] = close.rolling(5).mean()
    df['sma_10'] = close.rolling(10).mean()
    df['sma_20'] = close.rolling(20).mean()
    df['sma_60'] = close.rolling(60).mean()

    # EMA
    df['ema_12'] = close.ewm(span=12).mean()
    df['ema_26'] = close.ewm(span=26).mean()

    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # KDJ
    low14 = df['low'].astype(float).rolling(14).min()
    high14 = df['high'].astype(float).rolling(14).max()
    rsv = (close - low14) / (high14 - low14 + 1e-9) * 100
    df['k'] = rsv.ewm(com=2).mean()
    df['d'] = df['k'].ewm(com=2).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']

    # Bollinger Bands
    df['bb_mid'] = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * std20
    df['bb_lower'] = df['bb_mid'] - 2 * std20

    # ATR
    high_l = df['high'].astype(float)
    low_l = df['low'].astype(float)
    tr1 = high_l - low_l
    tr2 = (high_l - close.shift(1)).abs()
    tr3 = (low_l - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    # Zone classification
    def zone(rsi):
        if pd.isna(rsi): return 'N'
        if rsi >= 80: return 'OB'
        if rsi >= 65: return 'OH'
        if rsi <= 20: return 'OS'
        if rsi <= 35: return 'OB'
        return 'N'
    df['zone'] = df['rsi_14'].apply(zone)

    return df


def update_tw_stocks():
    """Update Taiwan stocks via yfinance"""
    log.info("[Trade Updater] Starting TW stock updates...")
    db_path = f"{DATA_DIR}\\tw_history.db"
    updated = 0

    for sym in TW_STOCKS:
        try:
            ticker = yf.Ticker(f"{sym}.TW")
            df = ticker.history(period="2y", interval="1d")
            if df.empty:
                log.warning(f"  {sym}.TW: no data")
                continue

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = compute_indicators(df)
            df['symbol'] = sym

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            for _, row in df.iterrows():
                dt = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
                cur.execute("""
                    INSERT OR REPLACE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume,
                     rsi_5, rsi_14, sma_5, sma_10, sma_20, sma_60,
                     ema_12, ema_26, macd, macd_signal, macd_hist,
                     k, d, bb_upper, bb_mid, bb_lower, atr, zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sym, dt, row['open'], row['high'], row['low'], row['close'], row['volume'],
                      row.get('rsi_5', np.nan), row.get('rsi_14', np.nan),
                      row.get('sma_5', np.nan), row.get('sma_10', np.nan),
                      row.get('sma_20', np.nan), row.get('sma_60', np.nan),
                      row.get('ema_12', np.nan), row.get('ema_26', np.nan),
                      row.get('macd', np.nan), row.get('macd_signal', np.nan), row.get('macd_hist', np.nan),
                      row.get('k', np.nan), row.get('d', np.nan),
                      row.get('bb_upper', np.nan), row.get('bb_mid', np.nan), row.get('bb_lower', np.nan),
                      row.get('atr', np.nan), row.get('zone', 'N')))

            conn.commit()
            conn.close()
            updated += 1
            log.info(f"  {sym} updated ({len(df)} rows)")
            time.sleep(0.3)

        except Exception as e:
            log.error(f"  {sym} failed: {e}")

    log.info(f"[Trade Updater] TW: {updated}/{len(TW_STOCKS)} stocks updated")
    return updated


def update_us_stocks():
    """Update US stocks via yfinance"""
    log.info("[Trade Updater] Starting US stock updates...")
    db_path = f"{DATA_DIR}\\us_history.db"
    updated = 0

    for sym in US_STOCKS:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period="2y", interval="1d")
            if df.empty:
                log.warning(f"  {sym}: no data")
                continue

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = compute_indicators(df)
            df['symbol'] = sym

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            for _, row in df.iterrows():
                dt = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
                cur.execute("""
                    INSERT OR REPLACE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume,
                     sma_20, sma_60, ema_12, ema_26,
                     rsi_14, rsi_7, macd_line, macd_signal, macd_hist,
                     bb_upper, bb_middle, bb_lower, atr_14,
                     kdj_k, kdj_d, kdj_j, zone, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sym, dt, row['open'], row['high'], row['low'], row['close'], row['volume'],
                      row.get('sma_20', np.nan), row.get('sma_60', np.nan),
                      row.get('ema_12', np.nan), row.get('ema_26', np.nan),
                      row.get('rsi_14', np.nan), row.get('rsi_5', np.nan),
                      row.get('macd', np.nan), row.get('macd_signal', np.nan), row.get('macd_hist', np.nan),
                      row.get('bb_upper', np.nan), row.get('bb_mid', np.nan), row.get('bb_lower', np.nan),
                      row.get('atr', np.nan),
                      row.get('k', np.nan), row.get('d', np.nan), row.get('j', np.nan),
                      row.get('zone', 'N'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            conn.close()
            updated += 1
            log.info(f"  {sym} updated ({len(df)} rows)")
            time.sleep(0.3)

        except Exception as e:
            log.error(f"  {sym} failed: {e}")

    log.info(f"[Trade Updater] US: {updated}/{len(US_STOCKS)} stocks updated")
    return updated


def main():
    log.info("=== Trade History Updater ===")
    start = datetime.now()
    tw = update_tw_stocks()
    us = update_us_stocks()
    elapsed = (datetime.now() - start).total_seconds()
    log.info(f"Done. TW={tw}, US={us} | Time={elapsed:.1f}s")
    return {"tw_updated": tw, "us_updated": us, "elapsed_s": elapsed}


if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")