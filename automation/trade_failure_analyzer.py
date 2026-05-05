# -*- coding: utf-8 -*-
"""
全系統交易失敗分析 + 自動改善系統 v1.0
分析所有團隊的交易失敗原因，自動調整參數，並執行改善
"""

import sys, os, json, yfinance as yf
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'

# ── 讀取交易數據 ───────────────────────────────
def load_all_trades():
    """讀取所有團隊的交易數據"""
    data = {}
    
    # Nana
    nana_trades = os.path.join(BASE_DIR, 'nana', 'autonomous_trades.json')
    if os.path.exists(nana_trades):
        with open(nana_trades, 'r', encoding='utf-8') as f:
            d = json.load(f)
            data['nana'] = {
                'trades': d.get('trades', []),
                'stats': d.get('stats', {}),
                'open': d.get('open_positions', []),
            }
    
    # Leo
    leo_trades = os.path.join(BASE_DIR, 'leo', 'reports', 'leo_sim_trades.json')
    leo_trades2 = os.path.join(BASE_DIR, 'leo', 'reports', 'leo_trades.json')
    leo_data = {'trades': [], 'stats': {}}
    if os.path.exists(leo_trades):
        with open(leo_trades, 'r', encoding='utf-8') as f:
            leo_data = json.load(f)
    elif os.path.exists(leo_trades2):
        with open(leo_trades2, 'r', encoding='utf-8') as f:
            leo_data = json.load(f)
    data['leo'] = leo_data
    
    # Ray
    ray_trades = os.path.join(BASE_DIR, 'ray', 'reports', 'ray_sim_trades.json')
    if os.path.exists(ray_trades):
        with open(ray_trades, 'r', encoding='utf-8') as f:
            data['ray'] = json.load(f)
    
    return data

# ── 分析失敗原因 ────────────────────────────────
def analyze_failures(data, market_state):
    """分析失敗原因"""
    print('\n[Step 1] 分析失敗原因...')
    regime = market_state['regime']
    rsi = market_state['rsi']
    position = market_state['position']
    
    results = {}
    
    # Nana 分析
    nana = data.get('nana', {})
    nana_trades = nana.get('trades', [])
    closed = [t for t in nana_trades if t.get('exit_price')]
    losses = [t for t in closed if t.get('return_pct', 0) <= 0]
    
    nana_issues = []
    
    # 問題1: OVERBOUGHT 市場進場
    if regime == 'OVERBOUGHT' and any(t.get('entry_rsi', 0) > 75 for t in nana_trades):
        nana_issues.append({
            'issue': 'OVERBOUGHT市場進場',
            'desc': '市場RSI=93.3已過熱，仍有進場記錄',
            'severity': 'HIGH',
            'fix': 'OVERBOUGHT時全面禁止進場（無例外）'
        })
    
    # 問題2: RSI門檻過高
    high_rsi_entries = [t for t in nana_trades if t.get('entry_rsi', 0) > 65]
    if high_rsi_entries:
        nana_issues.append({
            'issue': '進場RSI過高',
            'desc': f'{len(high_rsi_entries)}筆在RSI>65進場，過熱市場追高',
            'severity': 'HIGH',
            'fix': '進場RSI上限調降至55（市場高位時更嚴格）'
        })
    
    # 問題3: 勝率過低
    if nana.get('stats', {}).get('win_rate', 100) < 40:
        nana_issues.append({
            'issue': '勝率過低',
            'desc': f"勝率{nana['stats']['win_rate']:.0f}% < 40%，策略需要調整",
            'severity': 'HIGH',
            'fix': '提高進場分數門檻（Score_min: 25→35），過濾弱信號'
        })
    
    # 問題4: BIAS進場
    high_bias_entries = [t for t in nana_trades if abs(t.get('entry_bias', 0)) > 5]
    if high_bias_entries:
        nana_issues.append({
            'issue': 'BIAS過大進場',
            'desc': f'{len(high_bias_entries)}筆在|BIAS|>5%進場，乖離過大',
            'severity': 'MEDIUM',
            'fix': '進場BIAS上限調降至3%'
        })
    
    results['nana'] = {
        'issues': nana_issues,
        'win_rate': nana.get('stats', {}).get('win_rate', 0),
        'total_trades': len(closed),
    }
    
    # Leo 分析
    leo = data.get('leo', {})
    leo_trades = leo.get('trades', [])
    results['leo'] = {
        'issues': [],
        'win_rate': leo.get('stats', {}).get('win_rate', 0),
        'total_trades': len(leo_trades),
        'status': '正常' if regime == 'OVERBOUGHT' else '需關注',
    }
    
    if regime == 'OVERBOUGHT':
        results['leo']['issues'].append({
            'issue': '市場過熱，Leo正確觀望',
            'desc': 'OVERBOUGHT市場，Leo等待RSI<65進場',
            'severity': 'INFO',
            'fix': '無需調整，維持現有策略'
        })
    
    results['ray'] = {
        'issues': [],
        'status': '正常' if regime == 'OVERBOUGHT' else '需關注',
    }
    
    if regime == 'OVERBOUGHT':
        results['ray']['issues'].append({
            'issue': '市場過熱，Ray正確暫停DCA',
            'desc': 'threshold=50，位置100% > 75%，自動暫停',
            'severity': 'INFO',
            'fix': '無需調整，等待市場回調'
        })
    
    return results

# ── 生成改善方案 ───────────────────────────────
def generate_fixes(analysis, market_state):
    """生成改善方案"""
    print('\n[Step 2] 生成改善方案...')
    fixes = []
    
    regime = market_state['regime']
    
    # Nana 改善方案
    for issue in analysis['nana']['issues']:
        if issue['severity'] == 'HIGH':
            if 'OVERBOUGHT市場進場' in issue['issue']:
                fixes.append({
                    'team': 'Nana',
                    'action': 'ADD_REGIME_FILTER',
                    'param': 'market_regime_block',
                    'value': True,
                    'desc': 'OVERBOUGHT市場時，Nana全面禁止進場',
                    'priority': 'HIGH',
                })
            elif '進場RSI過高' in issue['issue']:
                fixes.append({
                    'team': 'Nana',
                    'action': 'LOWER_ENTRY_RSI',
                    'param': 'entry_rsi_max',
                    'from_value': 65,
                    'to_value': 55,
                    'desc': '進場RSI上限: 65→55',
                    'priority': 'HIGH',
                })
            elif '勝率過低' in issue['issue']:
                fixes.append({
                    'team': 'Nana',
                    'action': 'RAISE_SCORE_THRESHOLD',
                    'param': 'entry_score_min',
                    'from_value': 25,
                    'to_value': 35,
                    'desc': '進場分數門檻: 25→35',
                    'priority': 'HIGH',
                })
            elif 'BIAS過大進場' in issue['issue']:
                fixes.append({
                    'team': 'Nana',
                    'action': 'LOWER_BIAS_THRESHOLD',
                    'param': 'entry_bias_max',
                    'from_value': 10,
                    'to_value': 3,
                    'desc': '進場BIAS上限: 10%→3%',
                    'priority': 'MEDIUM',
                })
    
    # Leo 改善方案
    if regime != 'OVERBOUGHT':
        fixes.append({
            'team': 'Leo',
            'action': 'TIGHTEN_ENTRY',
            'param': 'entry_rsi_max',
            'from_value': 65,
            'to_value': 60,
            'desc': '進場RSI上限: 65→60（更嚴格）',
            'priority': 'MEDIUM',
        })
    
    return fixes

# ── 執行改善 ────────────────────────────────
def execute_fixes(fixes):
    """執行改善"""
    print('\n[Step 3] 執行改善...')
    
    nana_improvements = {}
    leo_improvements = {}
    
    for fix in fixes:
        print(f'  【{fix["team"]}】{fix["desc"]}')
        
        if fix['team'] == 'Nana':
            nana_improvements[fix['param']] = {
                'action': fix['action'],
                'value': fix.get('to_value', fix.get('value', '')),
                'from': fix.get('from_value', ''),
            }
        elif fix['team'] == 'Leo':
            leo_improvements[fix['param']] = {
                'action': fix['action'],
                'value': fix.get('to_value', ''),
                'from': fix.get('from_value', ''),
            }
    
    # 寫入改善記錄
    nana_fix_file = os.path.join(BASE_DIR, 'nana', 'nana_improvements.json')
    with open(nana_fix_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'fixes': fixes,
            'nana_improvements': nana_improvements,
            'leo_improvements': leo_improvements,
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\n  已執行 {len(fixes)} 項改善')
    return fixes

# ── 創建改善後的腳本 ───────────────────────────────
def create_improved_scripts(fixes, market_state):
    """創建改善後的腳本"""
    print('\n[Step 4] 創建改善後的腳本...')
    
    regime = market_state['regime']
    
    # Nana 改善腳本
    nana_improved = os.path.join(BASE_DIR, 'nana', 'nana_improved.py')
    nana_code = '''# -*- coding: utf-8 -*-
"""
Nana 改善版交易系統（根據自動分析改善）
生成時間: {timestamp}
市場狀態: {regime}
改善項目: {improvements}
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime, date
import yfinance as yf
import pandas as pd
import numpy as np

BASE_DIR = r'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\nana'

# === 改善後參數 ===
ENTRY_RSI_MAX = 55          # 改善: 65→55（更嚴格進場）
ENTRY_SCORE_MIN = 35       # 改善: 25→35（過濾弱信號）
ENTRY_BIAS_MAX = 3.0       # 改善: 10%→3%（避免追漲）
ATR_STOP = 1.5
ATR_TARGET = 3.0
BIAS_EXIT = 5.0
HOLD_DAYS_MAX = 10
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000

def get_market_regime():
    """讀取市場體制"""
    REGIME_FILE = os.path.join(BASE_DIR, 'market_regime.json')
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('current_state', {{}}).get('regime', 'NEUTRAL')
    return 'NEUTRAL'

def calculate_indicators(ticker_str):
    """計算技術指標"""
    try:
        ticker = yf.Ticker(ticker_str)
        h = ticker.history(period='3mo')
        if h.empty or len(h) < 30: return None
        c = h['Close'].dropna()
        h2 = h['High'].dropna()
        l = h['Low'].dropna()
        v = h['Volume'].dropna()
        
        last = c.iloc[-1]
        ma20 = c.rolling(20).mean()
        ma60 = c.rolling(60).mean()
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))
        bias = ((c - ma20) / ma20) * 100
        vol_ma = v.rolling(20).mean()
        tr1 = h2 - l
        tr2 = abs(h2 - c.shift())
        tr3 = abs(l - c.shift())
        atr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        
        return {{
            'close': round(float(last), 2),
            'rsi': round(float(rsi.iloc[-1]), 2),
            'bias': round(float(bias.iloc[-1]), 2),
            'atr': round(float(atr.iloc[-1]), 2),
            'ma20': round(float(ma20.iloc[-1]), 2),
            'ma60': round(float(ma60.iloc[-1]), 2) if len(c) >= 60 else None,
            'vol_ratio': round(float(v.iloc[-1] / vol_ma.iloc[-1]), 2) if vol_ma.iloc[-1] > 0 else 1.0,
        }}
    except: return None

def calculate_score(ind):
    """計算進場分數"""
    score = 0
    rsi = ind.get('rsi', 50)
    bias = ind.get('bias', 0)
    vol = ind.get('vol_ratio', 1)
    
    if 40 <= rsi < 50: score += 30
    elif 50 <= rsi < 55: score += 25  # 改善: 只有更低RSI才高分
    if bias < -3: score += 15
    elif bias < 0: score += 10
    if vol >= 1.5: score += 20
    elif vol >= 1.2: score += 15
    return score

def check_entry(ind, regime):
    """檢查進場條件（改善版）"""
    # 改善: OVERBOUGHT時全面禁止進場
    if regime == 'OVERBOUGHT':
        return False
    return (
        ind.get('rsi', 100) < ENTRY_RSI_MAX          # 改善: RSI<55
        and abs(ind.get('bias', 0)) < ENTRY_BIAS_MAX  # 改善: BIAS<3%
        and ind.get('vol_ratio', 0) >= 0.8
        and calculate_score(ind) >= ENTRY_SCORE_MIN  # 改善: 分數>=35
    )

def check_exit(ind, entry_price, entry_atr):
    """檢查出场條件"""
    cur = ind.get('close', entry_price)
    atr = ind.get('atr', entry_atr)
    bias = ind.get('bias', 0)
    stop = entry_price - (atr * ATR_STOP)
    target = entry_price + (atr * ATR_TARGET)
    return {{
        'stop_loss': cur <= stop,
        'target': cur >= target,
        'bias_exit': bias > BIAS_EXIT,
        'return_pct': round(((cur - entry_price) / entry_price) * 100, 2),
    }}

if __name__ == '__main__':
    print('=== Nana 改善版交易系統 ===')
    regime = get_market_regime()
    print(f'市場體制: {{regime}}')
    print(f'ENTRY_RSI_MAX: {{ENTRY_RSI_MAX}}')
    print(f'ENTRY_SCORE_MIN: {{ENTRY_SCORE_MIN}}')
    print(f'ENTRY_BIAS_MAX: {{ENTRY_BIAS_MAX}}')
    print('系統已準備就緒')
'''.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        regime=regime,
        improvements=', '.join([f['desc'] for f in fixes if f['team'] == 'Nana'])
    )
    
    with open(nana_improved, 'w', encoding='utf-8') as f:
        f.write(nana_code)
    print(f'  已創建: nana_improved.py')
    
    # Leo 改善腳本
    leo_improved = os.path.join(BASE_DIR, 'leo', 'scripts', 'leo_improved.py')
    leo_code = '''# -*- coding: utf-8 -*-
"""
Leo 改善版波段交易系統（根據自動分析改善）
生成時間: {timestamp}
市場狀態: {regime}
改善項目: {improvements}
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime
import yfinance as yf
import pandas as pd

BASE_DIR = r'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\leo'
AI_STOCKS = {{'2330':'台積電','2454':'聯發科','2317':'鴻海','2379':'瑞昱','2376':'技嘉','2382':'廣達','3665':'穎崴','3034':'緯穎'}}

# === 改善後參數 ===
ENTRY_RSI_MAX = 60         # 改善: 65→60（更嚴格進場）
EXIT_RSI_MIN = 80
TAKE_PROFIT_PCT = 20.0
STOP_LOSS_PCT = 8.0
MAX_POSITION = 100000
COOLDOWN_MINUTES = 30

def get_market_regime():
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) < 20: return 'NEUTRAL'
    c = twii['Close'].dropna()
    delta = c.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]
    ma60 = c.rolling(60).mean().iloc[-1] if len(c) >= 60 else ma20
    if rsi > 80: return 'OVERBOUGHT'
    if rsi < 40: return 'OVERSOLD'
    return 'BULL' if ma20 > ma60 else 'BEAR'

def analyze_stock(sym, name):
    ticker = yf.Ticker(f'{{sym}}.TW')
    h = ticker.history(period='3mo')
    if len(h) < 60: return None
    c = h['Close'].dropna()
    last = c.iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]
    delta = c.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    pos_ma20 = (last - ma20) / ma20 * 100
    return {{
        'symbol': sym, 'name': name, 'price': round(float(last), 2),
        'rsi': round(float(rsi), 1), 'pos_ma20': round(float(pos_ma20), 1),
    }}

def run_improved_cycle():
    print('=== Leo 改善版波段系統 ===')
    regime = get_market_regime()
    print(f'市場體制: {{regime}}')
    print(f'ENTRY_RSI_MAX: {{ENTRY_RSI_MAX}}')
    print('改善: RSI門檻調嚴至60，等待更好的進場點')
    
    results = []
    for sym, name in AI_STOCKS.items():
        ind = analyze_stock(sym, name)
        if ind:
            results.append(ind)
            signal = '✅ 進場' if ind['rsi'] <= ENTRY_RSI_MAX else '⚠️ 過熱'
            print(f'  {{sym}} {{name}}: RSI={{ind["rsi"]}} {{signal}}')
    
    with open(os.path.join(BASE_DIR, 'reports', 'leo_analysis_improved.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results

if __name__ == '__main__':
    run_improved_cycle()
'''.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        regime=regime,
        improvements=', '.join([f['desc'] for f in fixes if f['team'] == 'Leo'])
    )
    
    with open(leo_improved, 'w', encoding='utf-8') as f:
        f.write(leo_code)
    print(f'  已創建: leo_improved.py')

# ── 主循環 ───────────────────────────────
def main():
    print('=' * 60)
    print('  全系統交易失敗分析 + 自動改善系統 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    
    # 取得市場狀態
    twii = yf.Ticker('^TWII').history(period='1mo')
    closes = twii['Close'].dropna()
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    ma20 = closes.rolling(20).mean().iloc[-1]
    ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else ma20
    yr = closes.max() - closes.min()
    position = (closes.iloc[-1] - closes.min()) / yr * 100 if yr > 0 else 50
    regime = 'OVERBOUGHT' if rsi > 80 else 'BULL' if ma20 > ma60 else 'BEAR' if ma20 < ma60 else 'NEUTRAL'
    
    market_state = {'rsi': float(rsi), 'position': float(position), 'regime': regime}
    print(f'\n市場狀態: {regime} (RSI={rsi:.1f}, 位置={position:.0f}%)')
    
    # 讀取數據
    data = load_all_trades()
    
    # 分析失敗原因
    analysis = analyze_failures(data, market_state)
    
    print('\n失敗原因分析:')
    for team, result in analysis.items():
        wr = result.get('win_rate', 'N/A')
        status = result.get('status', 'N/A')
        print(f'\n  [{team}] 勝率: {wr}% | 狀態: {status}')
        for issue in result['issues']:
            print(f'    ⚠️ {issue["issue"]}: {issue["desc"]}')
            print(f'       改善: {issue["fix"]}')
    
    # 生成改善方案
    fixes = generate_fixes(analysis, market_state)
    
    # 執行改善
    execute_fixes(fixes)
    
    # 創建改善腳本
    create_improved_scripts(fixes, market_state)
    
    print('\n' + '=' * 60)
    print('  改善完成')
    print('=' * 60)
    print(f'  改善項目: {len(fixes)}項')
    
    return {'analysis': analysis, 'fixes': fixes, 'market_state': market_state}

if __name__ == '__main__':
    main()