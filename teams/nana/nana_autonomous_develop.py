# -*- coding: utf-8 -*-
"""
Nana 自主學習開發系統 v1.0
功能：
  1. 自動分析市場環境與股票技能缺口
  2. 自動學習所需的技術指標與策略
  3. 自動開發/改進交易系統
  4. 自動分析表現並調整Cron排程
  5. 迭代優化策略參數
"""

import sys, os, json, yfinance as yf, pandas as pd, numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

# === 路徑 ===
BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana'
SKILLS_FILE = os.path.join(BASE_DIR, 'nana_skills.json')
LEARNINGS_FILE = os.path.join(BASE_DIR, 'nana_learnings.json')
SYSTEM_FILE = os.path.join(BASE_DIR, 'nana_autonomous_system.py')
EVOLutions_FILE = os.path.join(BASE_DIR, 'nana_evolutions.json')
SCHEDULE_FILE = os.path.join(BASE_DIR, 'nana_schedule.json')

# ── 評分系統知識庫 ─────────────────────────────
SCORING_RULES = {
    '法人(40%)': {
        '外資+投信>=6張': 60,
        '外資+投信>=4張': 50,
        '外資+投信>=3張': 40,
        '外資+投信>=2張': 15,
        '外資+投信>=1張': 10,
    },
    '技術(35%)': {
        'RSI_40-75': 20, 'RSI_30-40': 12, 'RSI_75-80': 10,
        'RSI_80-85': 5, 'RSI_>85或<30': 3,
        'Bias_-3%~+5%': 15, 'Bias_+5%~+8%': 10, 'Bias_-5%~-3%': 8,
        'ATR>=0.5%': 10, 'ATR>=0.3%': 5,
    },
    '趨勢(25%)': {
        'MA20>MA60': 15, '20日漲幅>0': 10,
    }
}

# 進場/出场參數知識
ENTRY_PARAMS = {
    'RSI_max': {'OVERBOUGHT': 60, 'BULL': 65, 'NEUTRAL': 65, 'BEAR': 60},
    'Bias_max': 10.0,
    'Vol_min': 0.8,
    'Score_min': 25,
}
EXIT_PARAMS = {
    'ATR_stop': 1.5,
    'ATR_target': 3.0,
    'Bias_exit': 5.0,
    'Hold_days_max': 10,
}

# ── 技能缺口分析 ───────────────────────────────
def analyze_skill_gaps():
    """分析當前系統的技能缺口"""
    print('[Step 1] 分析技能缺口...')
    gaps = []
    
    # 檢查是否有足夠的技術指標
    required_indicators = ['RSI', 'BIAS', 'ATR', 'MA20', 'MA60', 'Vol_ratio', 'ADX', 'MACD']
    
    # 檢查市場體制判斷
    if not os.path.exists(os.path.join(BASE_DIR, 'market_regime.json')):
        gaps.append({'skill': 'market_regime_detection', 'priority': 'HIGH', 'desc': '市場體制偵測'})
    
    # 檢查學習機制
    if not os.path.exists(LEARNINGS_FILE):
        gaps.append({'skill': 'learning_mechanism', 'priority': 'HIGH', 'desc': '學習機制'})
    
    # 檢查策略優化
    if not os.path.exists(EVOLutions_FILE):
        gaps.append({'skill': 'strategy_evolution', 'priority': 'MEDIUM', 'desc': '策略迭代優化'})
    
    print(f'  發現 {len(gaps)} 個技能缺口: {[g["skill"] for g in gaps]}')
    return gaps

# ── 自主學習市場知識 ───────────────────────────
def learn_market_knowledge():
    """自動學習市場知識"""
    print('[Step 2] 學習市場知識...')
    
    learnings = []
    
    # 1. 學習當前市場狀態
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) > 0:
        closes = twii['Close'].dropna()
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        ma20 = closes.rolling(20).mean().iloc[-1]
        ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else None
        
        ma60_val = ma60 if ma60 else ma20
        regime = 'BULL' if ma20 > ma60_val and rsi > 50 else 'BEAR' if ma20 < ma60_val and rsi < 50 else 'NEUTRAL'
        if rsi > 80:
            regime = 'OVERBOUGHT'
        elif rsi < 40:
            regime = 'OVERSOLD'
            
        market_state = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'regime': regime,
            'rsi': round(float(rsi), 1),
            'ma20': round(float(ma20), 2) if ma20 else None,
            'ma60': round(float(ma60), 2) if ma60 else None,
            'close': round(float(closes.iloc[-1]), 2),
        }
        learnings.append({'type': 'market_state', 'data': market_state})
        print(f'  市場狀態: {regime} (RSI={rsi:.1f})')
    
    # 2. 學習市場體制參數
    regime_params = {
        'OVERBOUGHT': {'entry_rsi_max': 60, 'max_positions': 2, 'strategy': '禁止進場'},
        'BULL': {'entry_rsi_max': 65, 'max_positions': 5, 'strategy': '順勢而為'},
        'NEUTRAL': {'entry_rsi_max': 65, 'max_positions': 3, 'strategy': '區間操作'},
        'BEAR': {'entry_rsi_max': 60, 'max_positions': 2, 'strategy': '觀望'},
    }
    learnings.append({'type': 'regime_params', 'data': regime_params})
    
    # 3. 學習BIAS離場規則（v5.39發現）
    bias_rule = {
        'desc': 'BIAS>5.0時離場，歷史勝率97.4%，平均報酬6.54%',
        'threshold': 5.0,
        'source': 'v5.39_backtest',
        'applies_to': 'all_entries',
    }
    learnings.append({'type': 'bias_exit_rule', 'data': bias_rule})
    
    # 4. 學習ATR停損停利規則
    atr_rule = {
        'desc': 'ATR 1.5x停損，ATR 3.0x目標',
        'atr_stop': 1.5,
        'atr_target': 3.0,
        'source': 'v5.28_strategy',
    }
    learnings.append({'type': 'atr_rule', 'data': atr_rule})
    
    save_learnings(learnings)
    print(f'  完成: {len(learnings)} 項知識')
    return learnings

def save_learnings(learnings: List[Dict]):
    """儲存學習結果"""
    existing = []
    if os.path.exists(LEARNINGS_FILE):
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    existing.extend(learnings)
    
    # 只保留最近100條
    with open(LEARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing[-100:], f, ensure_ascii=False, indent=2)

# ── 自動開發交易系統 ───────────────────────────
def develop_trading_system():
    """自動開發交易系統"""
    print('[Step 3] 自動開發交易系統...')
    
    # 讀取現有系統
    existing_version = 'v5.8'
    version_num = 58
    
    # 根據學習結果優化
    regime_file = os.path.join(BASE_DIR, 'market_regime.json')
    regime_data = {}
    if os.path.exists(regime_file):
        with open(regime_file, 'r', encoding='utf-8') as f:
            regime_data = json.load(f)
    
    current_regime = regime_data.get('current_state', {}).get('regime', 'NEUTRAL')
    regime_params = regime_data.get('param_recommendations', {})
    
    # 生成的系統代碼
    system_code = f'''# -*- coding: utf-8 -*-
"""
Nana 自主開發交易系統 v{version_num+1}.0
自動生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
市場體制: {current_regime}
基於知識: Nana_skills.json + learnings
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime, date
import yfinance as yf
import pandas as pd
import numpy as np

BASE_DIR = r'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\nana'

# === 策略參數（來自學習優化）===
ENTRY_RSI_MAX = {ENTRY_PARAMS['RSI_max'].get(current_regime, 65)}
ENTRY_BIAS_MAX = {ENTRY_PARAMS['Bias_max']}
ENTRY_SCORE_MIN = {ENTRY_PARAMS['Score_min']}
ATR_STOP = {EXIT_PARAMS['ATR_stop']}
ATR_TARGET = {EXIT_PARAMS['ATR_target']}
BIAS_EXIT = {EXIT_PARAMS['Bias_exit']}
HOLD_DAYS_MAX = {EXIT_PARAMS['Hold_days_max']}
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000

def get_market_regime():
    """根據學習結果自動設定市場體制"""
    REGIME_FILE = os.path.join(BASE_DIR, 'market_regime.json')
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cs = data.get('current_state', {{}})
            return cs.get('regime', 'NEUTRAL'), cs.get('rsi', 50)
    return 'NEUTRAL', 50

def calculate_indicators(ticker_str):
    """計算完整技術指標"""
    try:
        ticker = yf.Ticker(ticker_str)
        h = ticker.history(period='3mo')
        if h.empty or len(h) < 30:
            return None
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
        
        # ADX
        adx = 100 - (100 / (1 + np.abs(c.diff().rolling(14).mean()) / (np.abs(c.diff().rolling(14).mean()) + 0.001)))
        
        # MACD
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26
        
        return {{
            'close': round(float(last), 2),
            'rsi': round(float(rsi.iloc[-1]), 2),
            'bias': round(float(bias.iloc[-1]), 2),
            'atr': round(float(atr.iloc[-1]), 2),
            'ma20': round(float(ma20.iloc[-1]), 2),
            'ma60': round(float(ma60.iloc[-1]), 2) if len(c) >= 60 and not pd.isna(ma60.iloc[-1]) else None,
            'adx': round(float(adx.iloc[-1]), 2) if not pd.isna(adx.iloc[-1]) else None,
            'macd': round(float(macd.iloc[-1]), 2),
            'vol_ratio': round(float(v.iloc[-1] / vol_ma.iloc[-1]), 2) if vol_ma.iloc[-1] > 0 else 1.0,
        }}
    except Exception as e:
        return None

def calculate_score(ind, regime):
    """根據市場體制動態評分"""
    score = 0
    rsi = ind.get('rsi', 50)
    bias = ind.get('bias', 0)
    vol = ind.get('vol_ratio', 1)
    
    # RSI評分（動態門檻）
    entry_rsi_max = {ENTRY_PARAMS['RSI_max'].get(current_regime, 65)}
    if 40 <= rsi < 50:
        score += 30
    elif 50 <= rsi < entry_rsi_max:
        score += 25 if rsi < 60 else 15
    
    # BIAS評分
    if bias < -5: score += 20
    elif bias < 0: score += 15
    elif bias < 5: score += 10
    
    # Vol評分
    if vol >= 1.5: score += 25
    elif vol >= 1.2: score += 20
    elif vol >= 0.8: score += 10
    
    # ADX評分
    if ind.get('adx', 0) > 25: score += 15
    
    # MACD方向評分
    if ind.get('macd', 0) > 0: score += 10
    
    return score

def check_entry(ind, regime):
    """檢查進場條件"""
    entry_rsi_max = {ENTRY_PARAMS['RSI_max'].get(current_regime, 65)}
    return (
        ind.get('rsi', 100) < entry_rsi_max
        and abs(ind.get('bias', 100)) < {ENTRY_PARAMS['Bias_max']}
        and ind.get('vol_ratio', 0) >= {ENTRY_PARAMS['Vol_min']}
        and regime != 'OVERBOUGHT'
    )

def check_exit(ind, entry_price, entry_atr, entry_date_str=None):
    """檢查出場條件"""
    cur = ind.get('close', entry_price)
    atr = ind.get('atr', entry_atr)
    bias = ind.get('bias', 0)
    
    stop = entry_price - (atr * {EXIT_PARAMS['ATR_stop']})
    target = entry_price + (atr * {EXIT_PARAMS['ATR_target']})
    
    days = 0
    if entry_date_str:
        try:
            days = (datetime.now().date() - datetime.strptime(entry_date_str, '%Y-%m-%d').date()).days
        except:
            days = 0
    
    return {{
        'stop_loss': cur <= stop,
        'target': cur >= target,
        'bias_exit': bias > {EXIT_PARAMS['Bias_exit']},
        'hold_max': days >= {EXIT_PARAMS['Hold_days_max']},
        'stop_price': round(stop, 2),
        'target_price': round(target, 2),
        'return_pct': round(((cur - entry_price) / entry_price) * 100, 2),
        'hold_days': days,
    }}

if __name__ == '__main__':
    print('=== Nana 自主開發系統 v{version_num+1}.0 ===')
    regime, market_rsi = get_market_regime()
    print(f'市場體制: {{regime}} | RSI: {{market_rsi}}')
    print('系統已準備就緒')
'''
    
    # 寫入新系統
    with open(SYSTEM_FILE, 'w', encoding='utf-8') as f:
        f.write(system_code)
    
    print(f'  已生成: nana_autonomous_system.py (v{version_num+1}.0)')
    return f'v{version_num+1}.0'

# ── 分析並規劃Cron排程 ─────────────────────────
def analyze_and_plan_schedule():
    """分析表現並規劃Cron排程"""
    print('[Step 4] 分析表現並規劃排程...')
    
    # 讀取交易記錄
    trades_file = os.path.join(BASE_DIR, 'autonomous_trades.json')
    if os.path.exists(trades_file):
        with open(trades_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            trades = data.get('trades', [])
            open_pos = data.get('open_positions', [])
            stats = data.get('stats', {})
    else:
        trades, open_pos, stats = [], [], {}
    
    # 分析表現
    closed = [t for t in trades if t.get('status') == 'closed' or t.get('exit_price')]
    wins = [t for t in closed if t.get('profit_loss', 0) > 0]
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_return = sum(t.get('return_pct', 0) for t in closed) / len(closed) if closed else 0
    
    performance = {
        'total_trades': len(trades),
        'open_positions': len(open_pos),
        'closed_trades': len(closed),
        'win_rate': round(win_rate, 1),
        'avg_return': round(avg_return, 2),
        'total_profit': stats.get('total_profit', 0),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    
    # 根據表現規劃排程
    schedule_plan = []
    
    if win_rate < 40:
        schedule_plan.append({
            'action': '增加分析頻率',
            'cron': '*/15 * * * *',
            'desc': '勝率低，增加分析密度以捕捉更多機會'
        })
    elif win_rate >= 60:
        schedule_plan.append({
            'action': '維持或降低頻率',
            'cron': '*/30 * * * *',
            'desc': '勝率高，降低交易頻率提高品質'
        })
    
    # 根據市場體制調整
    regime_file = os.path.join(BASE_DIR, 'market_regime.json')
    regime = 'NEUTRAL'
    if os.path.exists(regime_file):
        with open(regime_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            regime = data.get('current_state', {}).get('regime', 'NEUTRAL')
    
    if regime == 'OVERBOUGHT':
        schedule_plan.append({
            'action': '增加預測頻率',
            'cron': '*/10 * * * *',
            'desc': 'OVERBOUGHT市場，高頻監控風險'
        })
    
    schedule_rec = {
        'performance': performance,
        'schedule_plan': schedule_plan,
        'regime': regime,
        'recommended_intervals': {
            'OVERBOUGHT': '*/10',
            'BULL': '*/15',
            'NEUTRAL': '*/20',
            'BEAR': '*/30',
        }
    }
    
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule_rec, f, ensure_ascii=False, indent=2)
    
    print(f'  勝率: {win_rate:.0f}% | 均報酬: {avg_return:.2f}%')
    print(f'  市場: {regime} | 建議間隔: {schedule_rec["recommended_intervals"].get(regime, "*/15")}')
    return schedule_rec

# ── 迭代優化 ───────────────────────────────────
def iterate_optimization():
    """迭代優化"""
    print('[Step 5] 迭代優化...')
    
    evolutions = []
    if os.path.exists(EVOLutions_FILE):
        with open(EVOLutions_FILE, 'r', encoding='utf-8') as f:
            evolutions = json.load(f)
    
    # 學習策略
    new_evolution = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'iteration': len(evolutions) + 1,
        'learnings': [],
        'param_adjustments': [],
        'performance_before': {},
        'performance_after': {},
    }
    
    # 根據勝率調整參數
    trades_file = os.path.join(BASE_DIR, 'autonomous_trades.json')
    if os.path.exists(trades_file):
        with open(trades_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stats = data.get('stats', {})
            win_rate = stats.get('win_rate', 0)
            
            if win_rate < 40:
                new_evolution['learnings'].append('勝率過低，收緊進場條件')
                new_evolution['param_adjustments'].append({
                    'param': 'ENTRY_RSI_MAX',
                    'action': '降低',
                    'reason': '勝率<40%，過度宽进的进场条件导致亏损'
                })
            elif win_rate >= 60:
                new_evolution['learnings'].append('勝率優秀，逐步放寬進場條件增加機會')
                new_evolution['param_adjustments'].append({
                    'param': 'ENTRY_RSI_MAX',
                    'action': '小幅放寬',
                    'reason': '勝率>60%，可适度增加交易机会'
                })
    
    evolutions.append(new_evolution)
    
    with open(EVOLutions_FILE, 'w', encoding='utf-8') as f:
        json.dump(evolutions[-20:], f, ensure_ascii=False, indent=2)
    
    print(f'  迭代 #{new_evolution["iteration"]}: {len(new_evolution["learnings"])} 項學習')
    for adj in new_evolution['param_adjustments']:
        print(f'    - {adj["param"]}: {adj["action"]} ({adj["reason"]})')
    
    return new_evolution

# ── 主循環 ─────────────────────────────────────
def run_autonomous_development():
    """主循環"""
    print('═' * 50)
    print('  Nana 自主學習開發系統 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('═' * 50)
    
    # Step 1: 技能缺口分析
    gaps = analyze_skill_gaps()
    
    # Step 2: 學習市場知識
    learnings = learn_market_knowledge()
    
    # Step 3: 自動開發系統
    new_version = develop_trading_system()
    
    # Step 4: 分析並規劃排程
    schedule_plan = analyze_and_plan_schedule()
    
    # Step 5: 迭代優化
    evolution = iterate_optimization()
    
    print()
    print('═' * 50)
    print('  自主學習完成')
    print('═' * 50)
    print(f'  新系統版本: {new_version}')
    print(f'  技能缺口: {len(gaps)} 個')
    print(f'  新知識: {len(learnings)} 項')
    print(f'  迭代優化: {len(evolution["learnings"])} 項')
    print()
    
    return {
        'version': new_version,
        'gaps': gaps,
        'learnings': learnings,
        'schedule_plan': schedule_plan,
        'evolution': evolution,
    }

if __name__ == '__main__':
    run_autonomous_development()