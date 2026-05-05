# -*- coding: utf-8 -*-
"""
TW Strategy Optimizer — 策略優化器
根據市場環境和三層過濾結果，動態調整篩選條件
"""

import sqlite3
import yfinance as yf
import pandas as pd
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'

DB_PATH = DATA_DIR / 'tw_value_growth.db'
STOCK_PARAMS_PATH = DATA_DIR / 'tw_stock_params.json'

# 4檔完全通過篩選股票的專屬策略
STOCK_STRATEGIES = {
    '5203': {
        'name': '大冢',
        'style': '價值成長',
        'rsi_enter_max': 55,
        'rsi_enter_min': 30,
        'stop_loss': -0.05,
        'take_profit': 0.15,
        'max_hold_days': 45,
        'pe_ideal': (10, 25),
        'roe_min': 8,
        'vol_surge_min': 1.5,
        'bias20_max': 15,
        'note': '價值成長型，RSI低於55時進場，目標+15%'
    },
    '2303': {
        'name': '聯電',
        'style': '價值',
        'rsi_enter_max': 60,
        'rsi_enter_min': 25,
        'stop_loss': -0.08,
        'take_profit': 0.12,
        'max_hold_days': 60,
        'pe_ideal': (5, 20),
        'roe_min': 5,
        'vol_surge_min': 1.5,
        'bias20_max': 15,
        'note': '價值型，PE 5-20理想，RSI<60進場'
    },
    '2884': {
        'name': '玉山金',
        'style': '價值超賣',
        'rsi_enter_max': 40,
        'rsi_enter_min': 20,
        'stop_loss': -0.07,
        'take_profit': 0.20,
        'max_hold_days': 90,
        'pe_ideal': (8, 18),
        'roe_min': 6,
        'vol_surge_min': 1.3,
        'bias20_max': 12,
        'note': '價值超賣型，RSI<40才進場，目標+20%，可持有較久'
    },
    '2885': {
        'name': '元大金',
        'style': '穩健',
        'rsi_enter_max': 65,
        'rsi_enter_min': 30,
        'stop_loss': -0.06,
        'take_profit': 0.15,
        'max_hold_days': 50,
        'pe_ideal': (8, 22),
        'roe_min': 5,
        'vol_surge_min': 1.5,
        'bias20_max': 15,
        'note': '穩健型，RSI<65進場，適合多頭市場'
    }
}

# 動態市場環境參數
MARKET_REGIME_PARAMS = {
    'bull': {
        'rsi_enter_adj': +5,
        'bias20_max_adj': +5,
        'vol_surge_adj': -0.2,
        'pe_max_adj': +5,
        'stop_loss_tighten': 0.02,
        'take_profit_extend': 0.05,
        'description': '多頭市場：MA20>MA60，動能強勁，放寬進場條件'
    },
    'normal': {
        'rsi_enter_adj': 0,
        'bias20_max_adj': 0,
        'vol_surge_adj': 0,
        'pe_max_adj': 0,
        'stop_loss_tighten': 0,
        'take_profit_extend': 0,
        'description': '正常市場：標準參數'
    },
    'bear': {
        'rsi_enter_adj': -10,
        'bias20_max_adj': -5,
        'vol_surge_adj': +0.5,
        'pe_max_adj': -5,
        'stop_loss_tighten': 0.01,
        'take_profit_extend': -0.03,
        'description': '熊市市場：MA20<MA60，動能弱，收緊進場條件'
    }
}


def load_stock_params():
    if STOCK_PARAMS_PATH.exists():
        with open(STOCK_PARAMS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_stock_params(params):
    with open(STOCK_PARAMS_PATH, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2, ensure_ascii=False)

def get_market_regime():
    """根據加權指數判斷市場環境"""
    try:
        idx = yf.Ticker('^TWII')
        h = idx.history(period='3mo')
        if h is None or h.empty:
            return 'normal'
        prices = h['Close']
        ma20 = prices.rolling(20).mean().iloc[-1]
        ma60 = prices.rolling(60).mean().iloc[-1] if len(prices) >= 60 else ma20
        price = prices.iloc[-1]
        rsi14 = calc_rsi(prices.values, 14)
        
        mom20 = (price / prices.iloc[-21] - 1) * 100 if len(prices) >= 21 else 0
        
        if price > ma20 > ma60 and mom20 > 5 and rsi14 and rsi14 > 50:
            return 'bull'
        elif price < ma20 or mom20 < -5 or (rsi14 and rsi14 < 40):
            return 'bear'
        return 'normal'
    except:
        return 'normal'

def calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])

def get_current_params(stock=None, regime='normal'):
    """取得當前（可能經過優化的）參數"""
    saved = load_stock_params()
    base = STOCK_STRATEGIES.copy()
    
    # 套用市場環境調整
    reg_adj = MARKET_REGIME_PARAMS.get(regime, MARKET_REGIME_PARAMS['normal'])
    
    if stock and stock in base:
        p = base[stock]
        if stock in saved:
            p = {**p, **saved[stock]}
        # 市場環境調整
        p['rsi_enter_max'] += reg_adj['rsi_enter_adj']
        p['bias20_max'] += reg_adj['bias20_max_adj']
        p['vol_surge_min'] += reg_adj['vol_surge_adj']
        return p
    return base

def analyze_screener_results():
    """分析最近一次篩選結果"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    cur.execute('''
        SELECT symbol, base_pass, fund_pass, tech_pass,
               fund_score, tech_score, mom_score, total_score, signal
        FROM scores ORDER BY total_score DESC LIMIT 30
    ''')
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return None
    
    result = {
        'total_candidates': len(rows),
        'base_pass': sum(1 for r in rows if r[1]),
        'fund_pass': sum(1 for r in rows if r[2]),
        'tech_pass': sum(1 for r in rows if r[3]),
        'strong_buy': sum(1 for r in rows if r[8] == 'STRONG_BUY'),
        'buy': sum(1 for r in rows if r[8] == 'BUY'),
        'top5': [{'symbol': r[0], 'score': r[7], 'signal': r[8]} for r in rows[:5]],
        'stocks_4': {
            '5203': next((r for r in rows if r[0] == '5203'), None),
            '2303': next((r for r in rows if r[0] == '2303'), None),
            '2884': next((r for r in rows if r[0] == '2884'), None),
            '2885': next((r for r in rows if r[0] == '2885'), None),
        }
    }
    return result

def optimize_for_stock(stock, screener_result, regime):
    """針對單一股票優化策略參數"""
    base = STOCK_STRATEGIES.get(stock, {})
    if not base:
        return None
    
    scr = screener_result['stocks_4'].get(stock) if screener_result else None
    
    adj = MARKET_REGIME_PARAMS.get(regime, MARKET_REGIME_PARAMS['normal'])
    
    optimized = {
        'stock': stock,
        'regime': regime,
        'base_style': base['style'],
        'optimized_params': {
            'rsi_enter_max': base['rsi_enter_max'] + adj['rsi_enter_adj'],
            'rsi_enter_min': base['rsi_enter_min'],
            'stop_loss': base['stop_loss'] - adj['stop_loss_tighten'],
            'take_profit': base['take_profit'] + adj['take_profit_extend'],
            'max_hold_days': base['max_hold_days'],
            'bias20_max': base['bias20_max'] + adj['bias20_max_adj'],
            'vol_surge_min': base['vol_surge_min'] + adj['vol_surge_adj'],
        },
        'screener_status': {
            'base_pass': bool(scr[1]) if scr else None,
            'fund_pass': bool(scr[2]) if scr else None,
            'tech_pass': bool(scr[3]) if scr else None,
            'score': scr[7] if scr else None,
            'signal': scr[8] if scr else None,
        },
        'regime_note': adj['description'],
        'entry_signal': 'WAIT',
        'note': base.get('note', '')
    }
    
    # 根據條件判斷進場信號
    if scr:
        score = scr[7]
        base_pass, fund_pass, tech_pass = scr[1], scr[2], scr[3]
        rsi_max = optimized['optimized_params']['rsi_enter_max']
        
        if score >= 80 and base_pass and fund_pass and tech_pass:
            optimized['entry_signal'] = 'STRONG_BUY'
        elif score >= 60 and base_pass and fund_pass:
            optimized['entry_signal'] = 'BUY'
        elif base_pass and fund_pass:
            optimized['entry_signal'] = 'CONDITIONAL_BUY'
        else:
            optimized['entry_signal'] = 'WAIT'
    
    return optimized

def optimize_all_stocks():
    """針對所有4檔股票優化並產出報告"""
    screener = analyze_screener_results()
    regime = get_market_regime()
    results = {}
    
    for stock in STOCK_STRATEGIES:
        opt = optimize_for_stock(stock, screener, regime)
        if opt:
            results[stock] = opt
    
    return results, regime, screener

def get_layer_adjustments(regime):
    """取得三層過濾條件的動態調整"""
    adj = MARKET_REGIME_PARAMS.get(regime, MARKET_REGIME_PARAMS['normal'])
    
    return {
        'layer1': {
            'price_max': 100,
            'vol_min': 500000,
            'mcap_min': 1e9,
            'note': '第一層（基礎）通常不變'
        },
        'layer2': {
            'pe_max': 30 + adj['pe_max_adj'],
            'pe_min': 0,
            'roe_min': 5,
            'rev_growth_min': 0,
            'op_margin_min': 0,
            'debt_ratio_max': 80,
            'div_yield_min': 0,
            'note': adj['description']
        },
        'layer3': {
            'rsi_min': 30,
            'rsi_max': 70 + adj['rsi_enter_adj'],
            'bias20_max': 15 + adj['bias20_max_adj'],
            'vol_surge': 1.5 + adj['vol_surge_adj'],
            'note': f'市場環境調整: RSI最大+{adj["rsi_enter_adj"]}, BIAS20+{adj["bias20_max_adj"]}, Vol+{adj["vol_surge_adj"]:.1f}'
        }
    }


def generate_optimizer_report():
    """產出完整的策略優化報告"""
    print('=' * 65)
    print(f'TW STRATEGY OPTIMIZER — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    print()
    
    # 1. 市場環境判定
    regime = get_market_regime()
    print(f'[1] 市場環境: {regime.upper()}')
    print(f'    {MARKET_REGIME_PARAMS[regime]["description"]}')
    
    # 2. 三層過濾調整
    print()
    print('[2] 三層過濾條件調整')
    layers = get_layer_adjustments(regime)
    for layer, params in layers.items():
        print(f'  【{layer.upper()}】')
        for k, v in params.items():
            if k != 'note':
                print(f'    {k}: {v}')
        print(f'    → {params["note"]}')
    
    # 3. 分析篩選結果
    print()
    print('[3] 篩選結果分析')
    screener = analyze_screener_results()
    if screener:
        print(f'  候選股票: {screener["total_candidates"]} 檔')
        print(f'  第一層通過: {screener["base_pass"]} 檔')
        print(f'  第二層通過: {screener["fund_pass"]} 檔')
        print(f'  第三層通過: {screener["tech_pass"]} 檔')
        print(f'  STRONG_BUY: {screener["strong_buy"]} 檔 | BUY: {screener["buy"]} 檔')
        print()
        print('  Top 5:')
        for s in screener['top5']:
            print(f'    {s["symbol"]}: Score={s["score"]:.0f} | {s["signal"]}')
    
    # 4. 4檔股票專屬策略優化
    print()
    print('[4] 4檔股票專屬策略優化')
    opts, _, _ = optimize_all_stocks()
    for stock, opt in opts.items():
        strat = opt['optimized_params']
        scr_st = opt['screener_status']
        print()
        print(f'  【{stock}】{STOCK_STRATEGIES[stock]["name"]} — {opt["base_style"]}')
        print(f'    進場信號: {opt["entry_signal"]}')
        print(f'    RSI範圍: {strat["rsi_enter_min"]}–{strat["rsi_enter_max"]:.0f}')
        print(f'    停損: {strat["stop_loss"]:.1%} | 停利: {strat["take_profit"]:.1%} | 最大持有: {strat["max_hold_days"]}天')
        print(f'    BIAS20上限: {strat["bias20_max"]:.1f}% | 成交量突破: {strat["vol_surge_min"]:.1f}x')
        print(f'    三層通過: Base={scr_st["base_pass"]} Fund={scr_st["fund_pass"]} Tech={scr_st["tech_pass"]}')
        if scr_st['score']:
            print(f'    評分: {scr_st["score"]:.0f} | 信號: {scr_st["signal"]}')
        print(f'    註: {opt["note"]}')
    
    # 5. 儲存優化結果
    print()
    print('[5] 儲存優化結果')
    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'market_regime': regime,
        'layer_adjustments': layers,
        'screener_summary': screener,
        'stock_optimizations': opts
    }
    
    report_path = REPORT_DIR / f'tw_strategy_optimizer_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'  已保存: {report_path.name}')
    
    # 6. 產出可直接使用的篩選條件
    print()
    print('[6] 當前適用的篩選條件（可直接複製到 tw_value_growth_screener.py）')
    l3 = layers['layer3']
    l2 = layers['layer2']
    print(f'''
# ===== 動態調整後的篩選參數（市場環境: {regime.upper()}）=====
# 第三層
TECH_RSI_MAX = {l3['rsi_max']:.0f}       # (+{MARKET_REGIME_PARAMS[regime]["rsi_enter_adj"]:+.0f} 調整)
TECH_BIAS20_MAX = {l3['bias20_max']:.1f}   # (+{MARKET_REGIME_PARAMS[regime]["bias20_max_adj"]:+.1f} 調整)
TECH_VOL_SURGE = {l3['vol_surge']:.1f}    # (+{MARKET_REGIME_PARAMS[regime]["vol_surge_adj"]:+.1f} 調整)

# 第二層（PE 調整）
FUND_PE_MAX = {l2['pe_max']:.0f}         # (+{MARKET_REGIME_PARAMS[regime]["pe_max_adj"]:+.0f} 調整)
''')
    
    print()
    print('=' * 65)
    return report


if __name__ == '__main__':
    report = generate_optimizer_report()
    print()
    print('策略優化完成')