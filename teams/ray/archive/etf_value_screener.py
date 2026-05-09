# -*- coding: utf-8 -*-
"""
Ray ETF Value Screener — 多 ETF DCA 價值篩選器
掃描所有主要 TW ETF，計算 DCA 價值分數，輸出 Top 3 標的
用法: python scripts/etf_value_screener.py
"""
import yfinance as yf
import pandas as pd
import sys
import os
import requests
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

# 主要 TW ETF 清單
MAJOR_ETFS = [
    '0050', '0056', '00878', '00881', '00891',
    '00915', '00919', '00923', '00927',
    '00713', '00646', '00662', '00757',
    '00762', '00895'
]

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00881': '國泰台灣5G', '00891': '中信低碳', '00915': '富邦台灣永續高息',
    '00919': '群益台灣精選', '00923': '群益台灣ESG低碳', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00762': '元大石油', '00895': '富邦上証',
    # ── US Core ETF ─
    'VTI': 'Vanguard 全美市場', 'VOO': 'Vanguard S&P500',
    'QQQ': 'Invesco QQQ', 'VEA': 'Vanguard 發達市場', 'BND': 'Vanguard 綜合債券',
}

SCREENER_REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
SCREENER_REPORT_FILE = os.path.join(SCREENER_REPORT_DIR, 'etf_value_screener.json')
os.makedirs(SCREENER_REPORT_DIR, exist_ok=True)


def get_etf_data(etf_id):
    """一次抓完一個 ETF 的所有數據"""
    # US ETF: no .TW suffix; TW ETF: .TW suffix
    is_us = etf_id in ('VTI', 'VOO', 'QQQ', 'VEA', 'BND')
    sym = etf_id if is_us else (etf_id + '.TW')
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        if len(close) < 30:
            return None
    except:
        return None

    price = close.iloc[-1]
    low = close.min()
    high = close.max()
    avg = close.mean()
    position_pct = (price - low) / (high - low) * 100 if high > low else 50

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # 法人
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': etf_id,
        'start_date': start,
        'end_date': end,
        'token': TOKEN
    }
    fi_net = 0
    it_net = 0
    fi_days = 0
    try:
        r = requests.get(FINMIND_URL, params=params, timeout=10)
        data = r.json().get('data', [])
        fi_net = sum(r['buy'] - r['sell'] for r in data if r['name'] == 'Foreign_Investor')
        it_net = sum(r['buy'] - r['sell'] for r in data if r['name'] == 'Investment_Trust')
        fi_days = sum(1 for r in data if r['name'] == 'Foreign_Investor' and r['buy'] - r['sell'] > 0)
    except:
        pass

    # 近期表現
    recent_5d = close.tail(5)
    recent_pct = (recent_5d.iloc[-1] / recent_5d.iloc[0] - 1) * 100 if len(recent_5d) >= 2 else 0

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'price': float(price),
        'low_1y': float(low),
        'high_1y': float(high),
        'avg_1y': float(avg),
        'position_pct': round(position_pct, 1),
        'rsi': round(float(rsi), 1),
        'fi_net': int(fi_net),
        'it_net': int(it_net),
        'fi_days': fi_days,
        'recent_5d_pct': round(recent_pct, 2)
    }


def calc_dca_score(data):
    """
    計算 DCA 價值分數 (0-100)
    愈低價、機構支持、愈值得 DCA
    """
    score = 50

    # 位置越低分數越高 (權重 40%)
    pos = data['position_pct']
    score += (50 - pos) * 0.5  # 0% => +25分, 100% => -25分

    # 機構支持 (權重 20%)
    fi = data['fi_net'] / 1000000  # 百萬
    if fi > 0:
        score += min(fi, 500) * 0.02  # 最多 +10分
    elif fi < -200:
        score -= 5  # 外資倒貨太多

    # 投信支持 (權重 10%)
    it = data['it_net'] / 1000000
    if it > 0:
        score += min(it, 200) * 0.025

    # RSI 輔助 (權重 15%)
    rsi = data['rsi']
    if rsi < 40:
        score += 10
    elif rsi < 50:
        score += 5
    elif rsi > 75:
        score -= 5

    # 近期跌幅 (權重 15%)
    recent = data['recent_5d_pct']
    if recent < -5:
        score += 7.5
    elif recent < -2:
        score += 4
    elif recent > 10:
        score -= 5  # 近期漲太多，會稍等

    return max(0, min(100, round(score, 1)))


def screen_etfs():
    """掃描所有 ETF，返回排序結果"""
    print('\n=== Ray ETF DCA 價值篩選 ===')
    print(f'  掃描時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'  掃描標的: {len(MAJOR_ETFS)} 檔')
    print()

    results = []
    for etf_id in MAJOR_ETFS:
        print(f'  抓取 {etf_id}...', end='', flush=True)
        data = get_etf_data(etf_id)
        if data:
            score = calc_dca_score(data)
            data['dca_score'] = score
            results.append(data)
            print(f' OK (位置={data["position_pct"]}%, DCA分={score})')
        else:
            print(f' 失敗')

    # 按 DCA 分數排序（越高越推薦）
    results.sort(key=lambda x: x['dca_score'], reverse=True)

    print()
    print('='*70)
    print(' DCA 價值排名 (Top 3)')
    print('='*70)

    top3 = results[:3]
    for i, r in enumerate(top3, 1):
        entry = '積極買進' if r['position_pct'] < 40 else ('普通' if r['position_pct'] < 60 else '觀望')
        print(f'\n  #{i} {r["name"]} ({r["etf_id"]})')
        print(f'     DCA分: {r["dca_score"]} | 位置: {r["position_pct"]}% | 價格: ${r["price"]:.2f}')
        print(f'     近1年區間: ${r["low_1y"]:.2f} ~ ${r["high_1y"]:.2f}')
        print(f'     外資: {r["fi_net"]//1000000:+d}M | 投信: {r["it_net"]//1000000:+d}M')
        print(f'     RSI: {r["rsi"]} | 5日: {r["recent_5d_pct"]:+.2f}%')
        print(f'     建議: {entry}')

    print()
    print('='*70)
    print(' 完整排名')
    print('='*70)
    for i, r in enumerate(results, 1):
        entry = '積極買進' if r['position_pct'] < 40 else ('普通' if r['position_pct'] < 60 else '觀望')
        print(f'  {i:2d}. {r["etf_id"]} {r["name"]:<12s} DCA分={r["dca_score"]:5.1f} 位置={r["position_pct"]:5.1f}% {entry}')

    print()

    # 寫入報告
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'top3': top3,
        'all': results
    }
    with open(SCREENER_REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return results


if __name__ == '__main__':
    screen_etfs()
