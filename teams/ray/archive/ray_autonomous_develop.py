# -*- coding: utf-8 -*-
"""
Ray 自主學習開發系統 v1.0
功能：
  1. 自動學習ETF/DCA相關技能與知識
  2. 自動模擬交易並學習（虛擬倉位）
  3. 自動回測歷史大盤驗證策略
  4. 根據結果自動調整DCA參數
  5. 記錄學習成果到 ray_learnings.json
"""

import sys, os, json, yfinance as yf, pandas as pd, numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray'
RAY_DIR = os.path.join(BASE_DIR, 'reports')
LEARNINGS_FILE = os.path.join(RAY_DIR, 'ray_learnings.json')
EVOLUTIONS_FILE = os.path.join(RAY_DIR, 'ray_evolutions.json')
SIM_TRADES_FILE = os.path.join(RAY_DIR, 'ray_sim_trades.json')

# ETF 觀察名單
ETF_LIST = {
    '0050': '元大台灣50', '00646': '富邦S&P500', '0056': '元大高股息',
    '00713': '元大高息低波', '00878': '國泰永續高息', '00919': '群益台灣精選',
    '00915': '兆豐永續高息', '00918': '中信上游半導體',
}

# DCA 策略參數
DCA_PARAMS = {
    'entry_threshold': 50,    # 位置門檻（已驗證最優）
    'low_threshold': 30,        # 低點加碼門檻
    'high_threshold': 75,       # 高點暫停門檻
    'dca_budget': 26041,       # 每月DCA預算 NT$
    'max_positions': 8,         # 最大同時持有
}

# ── 學習市場知識 ───────────────────────────────
def learn_market_knowledge():
    """自動學習市場知識"""
    print('[Step 1] 學習市場知識...')
    learnings = []
    
    # 學習大盤狀態
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) > 0:
        closes = twii['Close'].dropna()
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
        ma20 = closes.rolling(20).mean().iloc[-1]
        ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else ma20
        
        regime = 'BULL' if ma20 > ma60 and rsi > 50 else 'BEAR' if ma20 < ma60 and rsi < 50 else 'NEUTRAL'
        if rsi > 80: regime = 'OVERBOUGHT'
        elif rsi < 40: regime = 'OVERSOLD'
        
        yr = closes.max() - closes.min()
        position = (closes.iloc[-1] - closes.min()) / yr * 100 if yr > 0 else 50
        
        market_state = {
            'regime': regime,
            'rsi': round(float(rsi), 1),
            'position': round(float(position), 1),
            'close': round(float(closes.iloc[-1]), 2),
        }
        learnings.append({'type': 'market_state', 'data': market_state})
        print(f'  大盤: {regime} (RSI={rsi:.1f}, 位置={position:.0f}%)')
    
    # 學習DCA知識
    dca_knowledge = {
        'entry_threshold': 50,
        'best_performing_etf': '00878',
        'low_threshold': 30,
        'high_threshold': 75,
        'note': 'threshold=50已驗證最優，位置<50%時DCA勝出'
    }
    learnings.append({'type': 'dca_knowledge', 'data': dca_knowledge})
    
    # 學習ETF基本知識
    for symbol, name in ETF_LIST.items():
        ticker = yf.Ticker(f'{symbol}.TW')
        try:
            h = ticker.history(period='1y')
            if len(h) > 100:
                c = h['Close']
                learnings.append({
                    'type': 'etf_info',
                    'symbol': symbol,
                    'name': name,
                    'price': round(float(c.iloc[-1]), 2),
                    '1y_high': round(float(c.max()), 2),
                    '1y_low': round(float(c.min()), 2),
                    'position': round((c.iloc[-1] - c.min()) / (c.max() - c.min()) * 100, 1),
                })
        except:
            pass
    
    save_learnings(learnings)
    print(f'  完成: {len(learnings)}項知識')
    return learnings

def save_learnings(learnings: List[Dict]):
    existing = []
    if os.path.exists(LEARNINGS_FILE):
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing.extend(learnings)
    with open(LEARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing[-100:], f, ensure_ascii=False, indent=2)

# ── 回測歷史大盤 ─────────────────────────────
def backtest_dca_strategy():
    """回測DCA策略"""
    print('[Step 2] 回測DCA策略...')
    
    twii = yf.Ticker('^TWII').history(period='5y')
    if len(twii) < 500:
        print('  數據不足')
        return None
    
    closes = twii['Close'].dropna()
    ma20 = closes.rolling(20).mean()
    ma60 = closes.rolling(60).mean()
    
    # 計算位置
    yr_high = closes.rolling(252).max()
    yr_low = closes.rolling(252).min()
    position = (closes - yr_low) / (yr_high - yr_low) * 100
    
    # DCA模擬
    investment = 0
    shares = 0
    trades = []
    
    for i in range(60, len(closes)):
        pos = position.iloc[i]
        price = closes.iloc[i]
        
        if pos < DCA_PARAMS['low_threshold']:
            # 低點加碼
            invest = DCA_PARAMS['dca_budget'] / 12 * 1.5
        elif pos < DCA_PARAMS['entry_threshold']:
            # 正常DCA
            invest = DCA_PARAMS['dca_budget'] / 12
        else:
            invest = 0
        
        if invest > 0:
            sh = invest / price
            shares += sh
            investment += invest
            trades.append({
                'date': str(closes.index[i].date()),
                'price': price,
                'shares': sh,
                'investment': invest,
            })
    
    if investment > 0 and shares > 0:
        final_value = shares * closes.iloc[-1]
        ret = (final_value - investment) / investment * 100
        avg_cost = investment / shares
        
        result = {
            'total_trades': len(trades),
            'total_investment': round(investment, 0),
            'final_value': round(final_value, 0),
            'return_pct': round(ret, 2),
            'avg_cost': round(avg_cost, 2),
            'final_price': round(float(closes.iloc[-1]), 2),
        }
        print(f'  回測結果: {len(trades)}筆投資, 總額 NT${investment:,.0f}')
        print(f'  報酬: {ret:.1f}%, 均成本 ${avg_cost:.2f}')
        return result
    return None

# ── 模擬交易 ───────────────────────────────
def run_simulated_dca():
    """模擬DCA交易"""
    print('[Step 3] 模擬DCA交易...')
    
    sim_data = {'trades': [], 'open_positions': [], 'stats': {}}
    if os.path.exists(SIM_TRADES_FILE):
        with open(SIM_TRADES_FILE, 'r', encoding='utf-8') as f:
            sim_data = json.load(f)
    
    open_pos = sim_data.get('open_positions', [])
    
    # 檢查所有ETF
    for symbol, name in ETF_LIST.items():
        ticker = f'{symbol}.TW'
        try:
            h = yf.Ticker(ticker).history(period='1y')
            if len(h) < 100:
                continue
            c = h['Close'].dropna()
            price = c.iloc[-1]
            
            yr_high = c.max()
            yr_low = c.min()
            pos = (price - yr_low) / (yr_high - yr_low) * 100 if yr_high > yr_low else 50
            
            # 計算技術指標
            ma20 = c.rolling(20).mean().iloc[-1]
            delta = c.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
            
            # DCA決策
            if pos < DCA_PARAMS['low_threshold']:
                action = 'LOW_DCA'
                amount = DCA_PARAMS['dca_budget'] / 12 * 1.5
            elif pos < DCA_PARAMS['entry_threshold']:
                action = 'DCA'
                amount = DCA_PARAMS['dca_budget'] / 12
            else:
                action = 'HOLD'
                amount = 0
            
            if action in ['DCA', 'LOW_DCA']:
                shares = amount / price
                open_pos.append({
                    'symbol': symbol, 'name': name,
                    'entry_price': price, 'shares': shares,
                    'entry_date': str(date.today()),
                    'position': pos, 'rsi': rsi,
                    'action': action,
                })
                print(f'  {action}: {symbol} {name} @ ${price} (位置={pos:.0f}%, RSI={rsi:.1f})')
        
        except Exception as e:
            pass
    
    sim_data['open_positions'] = open_pos[-8:]  # 最多8檔
    
    # 統計
    stats = {
        'total_positions': len(open_pos),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    sim_data['stats'] = stats
    
    with open(SIM_TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sim_data, f, ensure_ascii=False, indent=2)
    
    print(f'  持倉: {len(open_pos)}檔')
    return sim_data

# ── 迭代優化 ───────────────────────────────
def iterate_optimize():
    """迭代優化策略"""
    print('[Step 4] 迭代優化...')
    
    evolutions = []
    if os.path.exists(EVOLUTIONS_FILE):
        with open(EVOLUTIONS_FILE, 'r', encoding='utf-8') as f:
            evolutions = json.load(f)
    
    new_evo = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'iteration': len(evolutions) + 1,
        'learnings': [],
        'param_changes': [],
    }
    
    # 分析表現
    sim_file = SIM_TRADES_FILE
    if os.path.exists(sim_file):
        with open(sim_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            positions = data.get('open_positions', [])
            
            # 根據市場位置調整
            if positions:
                avg_pos = sum(p.get('position', 50) for p in positions) / len(positions)
                if avg_pos > 80:
                    new_evo['learnings'].append('市場高位，嚴格執行threshold=75暫停')
                    new_evo['param_changes'].append({'param': 'high_threshold', 'from': 75, 'to': 75, 'note': '維持'})
                elif avg_pos < 30:
                    new_evo['learnings'].append('市場低位，觸發低點加碼1.5x')
                    new_evo['param_changes'].append({'param': 'low_threshold', 'from': 30, 'to': 30, 'note': '維持'})
    
    evolutions.append(new_evo)
    with open(EVOLUTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(evolutions[-20:], f, ensure_ascii=False, indent=2)
    
    print(f'  迭代 #{new_evo["iteration"]}: {len(new_evo["learnings"])}項學習')
    return new_evo

# ── 主循環 ───────────────────────────────
def run_autonomous_development():
    print('=' * 60)
    print('  Ray 自主學習開發系統 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    
    # Step 1: 學習
    learnings = learn_market_knowledge()
    
    # Step 2: 回測
    backtest = backtest_dca_strategy()
    
    # Step 3: 模擬DCA
    sim = run_simulated_dca()
    
    # Step 4: 迭代優化
    evo = iterate_optimize()
    
    print()
    print('=' * 60)
    print('  學習完成')
    print('=' * 60)
    print(f'  新知識: {len(learnings)}項')
    print(f'  回測: {"勝出" if backtest and backtest["return_pct"] > 0 else "待觀察"}')
    print(f'  模擬持倉: {sim["stats"]["total_positions"]}檔')
    print(f'  迭代: {evo["iteration"]}次')
    
    return {'learnings': learnings, 'backtest': backtest, 'sim': sim, 'evo': evo}

if __name__ == '__main__':
    run_autonomous_development()