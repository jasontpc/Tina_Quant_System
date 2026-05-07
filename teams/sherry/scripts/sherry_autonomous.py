# -*- coding: utf-8 -*-
"""Sherry ETF DCA 自主學習系統 v2
===================================
每週自動更新 ETF 觀察名單，根據市場狀況動態調整
"""
import sqlite3
import yfinance as yf
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA_DIR = WORKSPACE / "data"
DB = DATA_DIR / "sherry_etf.db"

# Sherry — 美股 Sector 輪動專家（不再管 VOO/QQQ — 由 Ray DCA 接管）
WATCHLIST = [
    # 科技/半導體
    'XLK',   # Technology
    'XSD',   # Semiconductors
    'SOXX',  # SOX Semiconductor
    # 金融
    'XLF',   # Financials
    'VFH',   # Vanguard Financials
    # 醫療/防守
    'XLV',   # HealthCare
    'VHT',   # Vanguard HealthCare
    # 能源
    'XLE',   # Energy
    'VDE',   # Vanguard Energy
    # 消費
    'XLY',   # Cons Discretionary
    'VCR',   # Vanguard Cons Disc
    # 房地產
    'XLRE',  # Real Estate
    # 工業
    'XLI',   # Industrials
    'VIS',   # Vanguard Industrials
    # 防禦/宏觀
    'GLD',   # Gold（宏觀避險）
    'TLT',   # 20年債（利率風險）
    'LQD',   # 投資等級債
    'HYG',   # 高收益債
    # 全球市場
    'EEM',   # 新興市場
    'VWO',   # Vanguard FTSE EM
    'VEA',   # 發達市場 ex-US
]

def fetch_etf_data(symbols):
    """yfinance 批量抓取"""
    results = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="3mo")
            if len(hist) < 30:
                continue
            close = hist['Close']
            delta = close.diff()
            gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = round(rsi.iloc[-1], 1) if len(rsi) > 0 else 50
            results[sym] = {
                'price': round(float(close.iloc[-1]), 2),
                'rsi': rsi_val,
                'high52w': round(float(hist['High'].max()), 2),
                'low52w': round(float(hist['Low'].min()), 2),
            }
        except Exception as e:
            print(f'  {sym}: error {e}')
    return results


def build_db():
    """建立/更新 Sherry ETF 資料庫"""
    print('[Sherry v2] 自主學習系統啟動')
    print(f'Scanning {len(WATCHLIST)} ETFs...')

    data = fetch_etf_data(WATCHLIST)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS etf_summary (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            current_price REAL,
            current_rsi REAL,
            current_zone TEXT,
            high_52w REAL,
            low_52w REAL,
            yield_12m REAL,
            updated_at TEXT
        )
    ''')

    for sym, d in data.items():
        rsi = d['rsi']
        if rsi < 40:
            zone = 'OVERSOLD'
        elif rsi > 70:
            zone = 'OVERBOUGHT'
        else:
            zone = 'NEUTRAL'

        # Categorize
        if sym in ('TLT', 'LQD', 'AGG', 'BND', 'HYG'):
            cat = 'Bond'
        elif sym in ('XLV', 'VHT'):
            cat = 'Health'
        elif sym in ('GLD', 'SLV'):
            cat = 'Commodity'
        elif sym in ('USO'):
            cat = 'Energy'
        else:
            cat = 'Index'

        from_high = ((d['price'] - d['high52w']) / d['high52w'] * 100) if d['high52w'] else 0

        c.execute('''
            INSERT OR REPLACE INTO etf_summary
            (symbol, name, category, current_price, current_rsi, current_zone,
             high_52w, low_52w, yield_12m, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sym, '', cat, d['price'], rsi, zone, d['high52w'], d['low52w'],
              from_high, datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print(f'DB updated: {DB}')
    print(f'Total ETFs: {len(data)}')


def daily_signal():
    """產出 DCA 信號（被 cron 呼叫）"""
    import subprocess
    result = subprocess.run(
        ['python', str(WORKSPACE / 'teams/sherry/scripts/sherry_daily_check.py')],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=60
    )
    print(result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr[:200])


if __name__ == '__main__':
    build_db()
    daily_signal()
