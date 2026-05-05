# -*- coding: utf-8 -*-
"""法人資金流向分析（使用 yfinance + FinMind）"""
import sys, json, os
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 100

# 法人重點追蹤股（包含所有團隊）
FOCUS_STOCKS = [
    ('2330', '台積電', '半導體'),
    ('2454', '聯發科', 'IC設計'),
    ('2317', '鴻海', '電子代工'),
    ('2382', '廣達', 'AI伺服器'),
    ('3034', '緯穎', 'AI伺服器'),
    ('2379', '瑞昱', 'IC設計'),
    ('2376', '技嘉', 'AI板卡'),
    ('3665', '穎崴', '半導體測試'),
    ('2881', '國泰金', '金控'),
    ('2882', '兆豐金', '金控'),
    ('2890', '中信金', '金控'),
    ('0050', '元大台灣50', 'ETF'),
    ('0056', '元大高股息', 'ETF'),
    ('00878', '國泰永續高息', 'ETF'),
]

print('=' * 70)
print('  法人資金流向分析')
print('  時間: 2026-04-26 16:03')
print('=' * 70)
print()

results = []

for sym, name, sector in FOCUS_STOCKS:
    try:
        ticker = yf.Ticker(f'{sym}.TW')
        h = ticker.history(period='5d')
        if h.empty or len(h) < 2:
            continue

        closes = h['Close'].values
        volumes = h['Volume'].values

        price = float(closes[-1])
        prev = float(closes[-2]) if len(closes) > 1 else price
        change = (price - prev) / prev * 100

        # 法人借券 / 成交量分析（使用5日均量）
        vol5_avg = np.mean(volumes[-5:]) if len(volumes) >= 5 else np.mean(volumes)
        vol_today = volumes[-1]
        vol_ratio = vol_today / vol5_avg if vol5_avg > 0 else 1

        # RSI
        rsi = get_rsi(closes, 14)

        # 20日均線
        ma20_vals = ticker.history(period='30d')['Close']
        ma20 = float(ma20_vals.rolling(20).mean().iloc[-1]) if len(ma20_vals) >= 20 else price
        pos_ma20 = (price / ma20 - 1) * 100

        # 評估法人動向（模擬）
        # 價格上漲 + 成交量增加 = 法人買超
        # 價格上漲 + 成交量萎縮 = 散戶跟進
        # 價格下跌 + 成交量增加 = 法人賣超

        if change > 0 and vol_ratio > 1.2:
            flow = '法人買超'
            flow_score = 3
        elif change > 0 and vol_ratio < 0.8:
            flow = '散戶跟進'
            flow_score = 1
        elif change < 0 and vol_ratio > 1.2:
            flow = '法人賣超'
            flow_score = -3
        elif change < 0 and vol_ratio < 0.8:
            flow = '散戶賣出'
            flow_score = -1
        else:
            flow = '觀望'
            flow_score = 0

        results.append({
            'symbol': sym, 'name': name, 'sector': sector,
            'price': price, 'change': round(change, 2),
            'vol_ratio': round(vol_ratio, 2),
            'rsi': round(rsi, 1),
            'pos_ma20': round(pos_ma20, 1),
            'flow': flow, 'flow_score': flow_score
        })
    except Exception as e:
        pass

# 排序：法人買超優先
results.sort(key=lambda x: x['flow_score'], reverse=True)

print('SYMBOL  NAME       PRICE      CHANGE    VOLx5   RSI    MA20%   FLOW')
print('-' * 75)

for r in results:
    ch = '{:+.2f}%'.format(r['change'])
    vol = '{:.1f}x'.format(r['vol_ratio'])
    ma20 = '{:+.1f}%'.format(r['pos_ma20'])
    flow_icon = '法人買超' if r['flow'] == '法人買超' else (
                '法人賣超' if r['flow'] == '法人賣超' else r['flow'])
    print('{:<8}{:<10}{:<10}{:<8}{:<6}{:>5}   {:>6}   {}'.format(
        r['symbol'], r['name'], r['price'], ch, vol, r['rsi'], ma20, flow_icon))

print()
print('=' * 70)
print('  法人重點追蹤')
print('=' * 70)

# 法人買超族群
buys = [r for r in results if r['flow'] == '法人買超']
if buys:
    print()
    print('【法人買超】')
    for r in buys[:5]:
        print(f'  {r["name"]} ({r["symbol"]}) - 價格 ${r["price"]} {r["change"]:+.2f}%')

# 散戶跟進（警示）
follow = [r for r in results if r['flow'] == '散戶跟進']
if follow:
    print()
    print('【散戶跟進 - 警示】')
    for r in follow[:5]:
        print(f'  {r["name"]} ({r["symbol"]}) - 價格 ${r["price"]} {r["change"]:+.2f}%')

# 法人賣超
sells = [r for r in results if r['flow'] == '法人賣超']
if sells:
    print()
    print('【法人賣超】')
    for r in sells[:5]:
        print(f'  {r["name"]} ({r["symbol"]}) - 價格 ${r["price"]} {r["change"]:+.2f}%')

print()
print('Note: 法人流向為模擬判斷，基於價格變化 + 成交量關係。')
print('      實際法人進出需以三大法人資料為準。')