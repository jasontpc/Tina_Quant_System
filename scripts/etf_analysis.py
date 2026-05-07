# -*- coding: utf-8 -*-
"""
Tina ETF 分析腳本 — 標準化版本 v1.0
===================================
每日 16:30 TW 收盤後自動分析 TW + US ETF
輸出建議並推送到 Telegram

使用方式:
  python etf_analysis.py          # 完整分析（TW + US）
  python etf_analysis.py --quick   # 快速分析（US only）
  python etf_analysis.py --cron   # Cron 模式（輸出 + Telegram）
"""

import sys
import json
import os
import time
import argparse
from datetime import datetime
from pathlib import Path

import yfinance as yf
import numpy as np

# ==== 設定 ====
WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
CHAT_ID = '1616824689'
REPORT_FILE = WORKSPACE / 'data' / 'etf_signals.json'

# TW ETF 清單
ETF_LIST_TW = [
    ('0050', '元大台灣50'),
    ('0056', '元大高股息'),
    ('00646', '富邦S&P500'),
    ('00662', '富邦NASDAQ100'),
    ('00713', '元大高息低波'),
    ('00757', '統一大FANG+'),
    ('00919', '群益台灣精選高息'),
    ('00927', '統一手創未來'),
    ('00981A', '國泰5G+'),
    ('00952', '凱基台灣AI50'),
]

# US ETF 清單（擴大覆盖）
ETF_LIST_US = [
    ('VTI', 'Vanguard Total Stock'),
    ('VEA', 'Vanguard Dev Ex-NA'),
    ('BND', 'Vanguard Total Bond'),
    ('SCHD', 'Schwab US Dividend'),
    ('SPY', 'SPDR S&P 500'),
    ('QQQ', 'Invesco QQQ'),
    ('VIG', 'Vanguard Dividend Appreciation'),
    ('VWO', 'Vanguard Emg Mkts'),
]

# 標準評分權重
SCORE_RSI_LOW    = 30   # RSI 35-50（進場區間）
SCORE_RSI_HIGH   = 0    # RSI > 70（過熱）
SCORE_MACD_POS   = 20   # MACD > 0
SCORE_MA_BULL    = 15   # MA20 > MA60
SCORE_RETURN_6M  = 25   # 6M 報酬 > 15%
SCORE_YIELD_HIGH = 10   # 殖利率 > 3%

BUY_THRESHOLD   = 60
WATCH_THRESHOLD = 40

# =====================


def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 50.0


def get_ma(closes, period):
    if len(closes) < period:
        return closes[-1]
    return float(np.mean(closes[-period:]))


def analyze_etf(symbol, is_tw=False):
    """分析單一 ETF"""
    suffix = '.TW' if is_tw else ''
    ticker = yf.Ticker(symbol + suffix)

    try:
        h = ticker.history(period='6mo')
    except:
        return None

    if h.empty or len(h) < 60:
        return None

    closes = h['Close'].values
    price = float(closes[-1])
    prev_price = float(closes[-2])
    chg_pct = (price - prev_price) / prev_price * 100

    ma20 = get_ma(closes, 20)
    ma60 = get_ma(closes, 60)
    rsi = get_rsi(closes)

    # MACD
    ema12 = float(yf.download(symbol + suffix, period='6mo', auto_adjust=True)['Close'].ewm(span=12).mean().iloc[-1])
    ema26 = float(yf.download(symbol + suffix, period='6mo', auto_adjust=True)['Close'].ewm(span=26).mean().iloc[-1])
    macd_val = ema12 - ema26

    # 6M 報酬
    ret_6m = (price / closes[-126] - 1) * 100 if len(closes) >= 126 else 0

    # 殖利率
    try:
        div_yield = ticker.info.get('dividendYield', 0) or 0
    except:
        div_yield = 0

    # Score 計算
    score = 0
    if 35 <= rsi <= 50:
        score += SCORE_RSI_LOW
    elif rsi < 35:
        score += SCORE_RSI_LOW + 10
    elif rsi > 70:
        score += SCORE_RSI_HIGH
    if macd_val > 0:
        score += SCORE_MACD_POS
    if ma20 > ma60:
        score += SCORE_MA_BULL
    if ret_6m > 15:
        score += SCORE_RETURN_6M
    elif ret_6m > 5:
        score += 10
    if div_yield > 0.03:
        score += SCORE_YIELD_HIGH

    verdict = 'BUY' if score >= BUY_THRESHOLD else ('WATCH' if score >= WATCH_THRESHOLD else 'HOLD')

    return {
        'symbol': symbol,
        'price': round(price, 2),
        'chg_pct': round(chg_pct, 2),
        'rsi': round(rsi, 1),
        'macd': round(macd_val, 3),
        'ma20': round(ma20, 2),
        'ma60': round(ma60, 2),
        'ret_6m': round(ret_6m, 1),
        'yield': round(div_yield * 100, 2) if div_yield else 0,
        'score': score,
        'verdict': verdict,
        'is_tw': is_tw,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def build_report(results):
    """建立標準報告"""
    buys = [r for r in results if r and r['verdict'] == 'BUY']
    watches = [r for r in results if r and r['verdict'] == 'WATCH']
    overbought = [r for r in results if r and r['rsi'] > 70]

    lines = []
    lines.append('=' * 65)
    lines.append(f'  Tina ETF 分析報告 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('=' * 65)
    lines.append('')

    # BUY 清單
    if buys:
        lines.append('✅ 建議進場（高Score）')
        lines.append(f'| {"ETF":<8} | {"價格":>9} | {"RSI":>4} | {"Score":>5} | {"6M報酬":>7} |')
        lines.append(f'| {"-"*8} | {"-"*9} | {"-"*4} | {"-"*5} | {"-"*7} |')
        for r in sorted(buys, key=lambda x: x['score'], reverse=True):
            name = r['symbol']
            if not r['is_tw']:
                name += '.US'
            lines.append(f"| {name:<8} | {r['price']:>9.2f} | {r['rsi']:>4.1f} | {r['score']:>5} | {ret_6m:>+7.1f}% |")
        lines.append('')

    # 過熱
    if overbought:
        lines.append('⚠️ 過熱觀望（RSI > 70）')
        names = []
        for r in overbought:
            n = r['symbol']
            if not r['is_tw']:
                n += '.US'
            names.append(n)
        lines.append(', '.join(names))
        lines.append('')

    # 排名
    if buys:
        lines.append('🏆 最高報酬策略排名')
        sorted_by_ret = sorted(buys, key=lambda x: x['ret_6m'], reverse=True)
        for i, r in enumerate(sorted_by_ret[:3], 1):
            verdict = '💰 建議進場' if r['score'] >= 60 else '🟡 觀望'
            lines.append(f'{i}. {r["symbol"]} → RSI {r["rsi"]:.0f}，6M報酬 {r["ret_6m"]:+.1f}% {verdict}')

    return '\n'.join(lines)


def push_telegram(msg):
    """發送到 Telegram"""
    import urllib.request
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': msg}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get('ok', False)
    except Exception as e:
        print(f'Telegram error: {e}')
        return False


def save_signals(results):
    """寫入信號資料庫"""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    signals = [r for r in results if r]
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'), 'signals': signals}, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='US only, no TW')
    parser.add_argument('--cron', action='store_true', help='Cron mode: push Telegram')
    args = parser.parse_args()

    print(f'Tina ETF 分析 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    results = []

    # TW ETF 分析
    if not args.quick:
        print('[1/2] 分析 TW ETF...')
        for sym, name in ETF_LIST_TW:
            r = analyze_etf(sym, is_tw=True)
            if r:
                r['name'] = name
                results.append(r)
                print(f'  {sym}: RSI={r["rsi"]:.0f} Score={r["score"]} {r["verdict"]}')

    # US ETF 分析
    print('[2/2] 分析 US ETF...')
    for sym, name in ETF_LIST_US:
        r = analyze_etf(sym, is_tw=False)
        if r:
            r['name'] = name
            results.append(r)
            print(f'  {sym}: RSI={r["rsi"]:.0f} Score={r["score"]} {r["verdict"]}')

    # 建立報告
    report = build_report(results)
    print()
    print(report)

    # 寫入 DB
    save_signals(results)
    print(f'[OK] Signals saved to {REPORT_FILE}')

    # Cron 模式：推 Telegram
    if args.cron:
        ok = push_telegram(report)
        print(f'[Telegram] {"OK" if ok else "FAILED"}')


if __name__ == '__main__':
    main()