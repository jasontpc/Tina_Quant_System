"""
AI 工廠七層蛋糕 — 實時追蹤腳本
stores/portfolio/ai_seven_layer_tracker.py

用法：
  python ai_seven_layer_tracker.py          # 完整分析報告
  python ai_seven_layer_tracker.py momentum  # 動能輪動分析
  python ai_seven_layer_tracker.py watchlist # 觀察清單報價
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# ─── 七層股票池 ───
LAYERS = {
    'L1_Energy': {
        'name': 'Energy & Power',
        'stocks': {'CEG':'Constellation Energy','BE':'Bloom Energy','VST':'Vistra Corp'},
        'key_metric': 'Nuclear/SMR contract news',
        'indicator': 'Energy equity momentum vs SPX',
        'tier_note': 'Base of the cake',
    },
    'L2_Compute': {
        'name': 'Compute Silicon',
        'stocks': {'NVDA':'NVIDIA','INTC':'Intel','AMD':'AMD'},
        'key_metric': 'Rubin platform shipment data',
        'indicator': 'NVDA earnings date 5/28',
        'tier_note': 'GPU still core',
    },
    'L3_Memory': {
        'name': 'Memory & Storage',
        'stocks': {'MU':'Micron','SNDK':'SanDisk','WDC':'Western Digital','STX':'Seagate'},
        'key_metric': 'HBM4 pricing / DRAM spot price',
        'indicator': 'SNDK +400% in 2026',
        'tier_note': 'Current strongest momentum',
    },
    'L4_Networking': {
        'name': 'Networking & Interconnect',
        'stocks': {'AVGO':'Broadcom','MRVL':'Marvell','ANET':'Arista'},
        'key_metric': 'NVLink 6 spec / 800G transceiver',
        'indicator': 'Arista backlog',
        'tier_note': 'GPU traffic bottleneck',
    },
    'L5_Cooling': {
        'name': 'Systems & Cooling',
        'stocks': {'VRT':'Vertiv','SMCI':'Super Micro','3515.TW':'奇鋐','6235.TW':'健策'},
        'key_metric': 'VRT backlog / Blackwell rack delivery',
        'indicator': 'Real AI Factory build temperature',
        'tier_note': 'Liquid cooling now MANDATORY',
    },
    'L6_Foundation': {
        'name': 'Foundation Models & MLOps',
        'stocks': {'MSFT':'Microsoft','META':'Meta','GOOGL':'Alphabet'},
        'key_metric': 'OpenAI/Azure revenue growth',
        'indicator': 'Llama 4 / open model adoption',
        'tier_note': 'Model layer differentiation',
    },
    'L7_Agentic': {
        'name': 'Agentic AI & Apps',
        'stocks': {'PLTR':'Palantir','CRWD':'CrowdStrike','NOW':'ServiceNow'},
        'key_metric': 'PLTR/NOW contract signings',
        'indicator': 'Agentic AI monetization',
        'tier_note': 'Economic value inflection point',
    },
}

def fetch_layer_data(layer_key, period='5d'):
    """抓取單層所有股票數據"""
    layer = LAYERS[layer_key]
    results = {}
    for sym, name in layer['stocks'].items():
        try:
            df = yf.download(sym, period=period, interval='1d', auto_adjust=True, progress=False, timeout=10)
            if df.empty:
                results[sym] = None
                continue
            df.columns = [c[0] for c in df.columns] if isinstance(df.columns, pd.MultiIndex) else df.columns
            close = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            chg = (close / prev - 1) * 100 if prev > 0 else 0
            # 20d for momentum
            if len(df) >= 20:
                ret_20d = float((df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100)
            else:
                ret_20d = None
            results[sym] = {'close': close, 'chg_1d': chg, 'ret_20d': ret_20d, 'name': name}
        except Exception as e:
            results[sym] = None
    return results

def calc_layer_momentum(data):
    """計算層級動能分數（0-100）"""
    valid = {k:v for k,v in data.items() if v is not None}
    if not valid:
        return 0, 'NODATA'
    avg_chg = sum(v['chg_1d'] for v in valid.values()) / len(valid)
    avg_20d = sum(v['ret_20d'] for v in valid.values()) / len(valid)
    score = avg_chg * 30 + avg_20d * 0.7
    return score, ('POSITIVE' if avg_chg > 0 else 'NEGATIVE')

def score_momentum(score):
    """動能評級"""
    if score >= 3: return 'STRONG', '🔴'
    if score >= 1: return 'MODERATE', '🟡'
    if score >= 0: return 'WEAK', '🟢'
    return 'NEGATIVE', '⚫'

def main():
    mode = 'report'
    if len(__import__('sys').argv) > 1:
        mode = __import__('sys').argv[1]

    print("=" * 65)
    print("  AI FACTORY 7-LAYER CAKE TRACKER  %s" % datetime.now().strftime('%Y-%m-%d %H:%M'))
    print("=" * 65)

    layer_scores = {}
    all_data = {}

    for layer_key in ['L1_Energy','L2_Compute','L3_Memory','L4_Networking','L5_Cooling','L6_Foundation','L7_Agentic']:
        layer = LAYERS[layer_key]
        data = fetch_layer_data(layer_key, '5d')
        all_data[layer_key] = data
        score, direction = calc_layer_momentum(data)
        emoji = score_momentum(score)[1]
        layer_scores[layer_key] = {'score': score, 'direction': direction, 'data': data}

    if mode == 'report':
        print("\n[LAYER MOMENTUM SCORES]")
        sorted_layers = sorted(layer_scores.items(), key=lambda x: -x[1]['score'])
        for rank, (lk, ls) in enumerate(sorted_layers, 1):
            layer = LAYERS[lk]
            score, direction = ls['score'], ls['direction']
            emoji, label = score_momentum(score)
            print("  %d. %s %-12s %+.1f  [%s] %s" % (rank, emoji, lk, score, direction, layer['name']))

        print("\n[DETAILED VIEW BY LAYER]")
        for layer_key in ['L1_Energy','L2_Compute','L3_Memory','L4_Networking','L5_Cooling','L6_Foundation','L7_Agentic']:
            layer = LAYERS[layer_key]
            ls = layer_scores[layer_key]
            data = ls['data']
            print("\n  --- %s | %s ---" % (layer_key, layer['name']))
            print("  Key Metric: %s" % layer['key_metric'])
            for sym, d in data.items():
                if d:
                    m20 = "%+.1f%% 20D" % d['ret_20d'] if d['ret_20d'] is not None else "N/A 20D"
                    print("  %-6s %-25s $%-8.2f  %+5.1f%%  %s" % (sym, d['name'], d['close'], d['chg_1d'], m20))
                else:
                    print("  %-6s %-25s FAILED TO FETCH" % (sym, layer['stocks'].get(sym,'')))

        # Rotation analysis
        print("\n" + "=" * 65)
        print("  [MOMENTUM ROTATION ANALYSIS]")
        print("=" * 65)
        top_layer = sorted_layers[0][0]
        bottom_layer = sorted_layers[-1][0]
        top_score = layer_scores[top_layer]['score']
        bottom_score = layer_scores[bottom_layer]['score']
        print("  Strongest:  %s (%+.1f)" % (top_layer, top_score))
        print("  Weakest:     %s (%+.1f)" % (bottom_layer, bottom_score))
        print("  Spread:      %+.1f" % (top_score - bottom_score))

        if top_score > 3 and bottom_score < 0:
            print("  Signal:      ROTATION IN PROGRESS")
            print("  -> Money flowing from weak layer to strong layer")
            print("  -> Strong layer leader: %s" % top_layer)
            winner = LAYERS[top_layer]['name']
            loser = LAYERS[bottom_layer]['name']
            print("  -> Loser: %s" % loser)
        elif top_score < 1:
            print("  Signal:      BROAD MARKET ROTATION")
            print("  -> No clear leader, defensive positioning")
        else:
            print("  Signal:      MIXED / NEUTRAL")

    elif mode == 'momentum':
        print("\n[MOMENTUM HEATMAP]")
        for layer_key in ['L1_Energy','L2_Compute','L3_Memory','L4_Networking','L5_Cooling','L6_Foundation','L7_Agentic']:
            ls = layer_scores[layer_key]
            score = ls['score']
            emoji, label = score_momentum(score)
            bar = '#' * max(0, int(score * 2))
            bar_neg = '-' * max(0, int(abs(score) * 2)) if score < 0 else ''
            print("  %-12s %s %-5s %s%s" % (layer_key, emoji, label, bar, bar_neg))

    elif mode == 'watchlist':
        print("\n[WATCHLIST — Key Level Indicators]")
        watch = [
            ('MU', 'L3_Memory', 'HBM4 anchor'),
            ('SNDK', 'L3_Memory', 'Supercycle leader'),
            ('CEG', 'L1_Energy', 'Nuclear leader'),
            ('VRT', 'L5_Cooling', 'Backlog barometer'),
            ('PLTR', 'L7_Agentic', 'AIP monetization'),
            ('NVDA', 'L2_Compute', 'Earnings 5/28'),
        ]
        for sym, layer, note in watch:
            d = layer_scores[layer]['data'].get(sym)
            if d:
                m20 = "%+.1f%%" % d['ret_20d'] if d['ret_20d'] else 'N/A'
                print("  %-6s %-8s $%-8.2f  %+5.1f%%  20D:%s  [%s]" % (
                    sym, layer.replace('L_','L'), d['close'], d['chg_1d'], m20, note))
            else:
                print("  %-6s %-8s FAILED" % (sym, layer))

    print("\n" + "=" * 65)
    print("  Generated: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 65)

if __name__ == '__main__':
    main()