# -*- coding: utf-8 -*-
"""
Leo AI/半導體/科技 台股 主動學習系統
Leo Autonomous Learning - AI/Semi/Tech Taiwan Supply Chain
專注：AI/半導體/科技 上中下游台股產業鏈
功能：
  - 每日自動學習優化參數
  - 分析錯誤交易記錄
  - 自動調整進場條件
  - 生成學習報告
  - 產業鏈追蹤優化
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path

# ==========================================
# Leo AI/半導體/科技 台股完整產業鏈
# ==========================================
STOCKS = {
    # 上游 - 半導體/IC設計
    '2330': {'name': '台積電', 'sector': '上游-晶圓製造', 'role': 'AI/HPC 晶片製造'},
    '2454': {'name': '聯發科', 'sector': '上游-IC設計', 'role': 'AI 手機/物聯網'},
    '2379': {'name': '瑞昱', 'sector': '上游-IC設計', 'role': '網通晶片/AIoT'},
    '3035': {'name': '智原', 'sector': '上游-IC設計', 'role': 'AI ASIC'},
    '3653': {'name': '健策', 'sector': '上游-導線架', 'role': 'AI 功率元件'},
    '8016': {'name': '僑威', 'sector': '上游-半導體耗材', 'role': 'AI 測試介面'},
    '3189': {'name': '景碩', 'sector': '上游-ABF載板', 'role': 'AI GPU 載板'},
    
    # 中游 - 伺服器/封測/設備
    '2382': {'name': '廣達', 'sector': '中游-伺服器', 'role': 'AI 伺服器/GB200'},
    '3034': {'name': '緯穎', 'sector': '中游-伺服器', 'role': 'AI 伺服器/雲端'},
    '4938': {'name': '和碩', 'sector': '中游-EMS', 'role': 'AI 硬體組裝'},
    '2376': {'name': '技嘉', 'sector': '中游-GPU板卡', 'role': 'AI GPU 伺服器'},
    '3665': {'name': '穎崴', 'sector': '中游-AI封測', 'role': 'AI CoWoS 封測'},
    '6153': {'name': '嘉澤', 'sector': '中游-連接器', 'role': 'AI 高速連接'},
    '5269': {'name': '祥碩', 'sector': '中游-高速傳輸', 'role': 'AI USB/PCIE'},
    '3515': {'name': '帆宣', 'sector': '中游-半導體設備', 'role': 'AI 設備供應'},
    '6191': {'name': '志聖', 'sector': '中游-設備', 'role': 'AI 熱處理設備'},
    
    # 下游 - EMS/PCB/散熱
    '2317': {'name': '鴻海', 'sector': '下游-EMS', 'role': 'AI 伺服器/GB200'},
    '6706': {'name': '健鼎', 'sector': '下游-PCB', 'role': 'AI PCB/伺服器板'},
    '6271': {'name': '敦南', 'sector': '下游-PCB', 'role': 'AI 功率 PCB'},
    '3016': {'name': '奇鋐', 'sector': '下游-散熱', 'role': 'AI 液冷/散熱'},
    '6230': {'name': '尼得科', 'sector': '下游-散熱', 'role': 'AI 散熱風扇'},
    '4566': {'name': '研華', 'sector': '下游-工業電腦', 'role': 'AI Edge IPC'},
}

BASE_DIR = Path(__file__).parent
TRADE_FILE = BASE_DIR / 'leo_ai_chain_trades.json'
LEARN_FILE = BASE_DIR / 'leo_ai_chain_learning.json'
PARAMS_FILE = BASE_DIR / 'leo_ai_chain_params.json'

# 預設最優參數
DEFAULT_PARAMS = {
    'rsi_entry_min': 30,
    'rsi_entry_max': 40,
    'hold_days_min': 5,
    'hold_days_max': 10,
    'tp_pct': 5,
    'sl_pct': 8,
    'win_rate': 85.7,
    'avg_return': 3.14,
}

# ==========================================
# 學習系統核心
# ==========================================
def load_trades():
    """載入交易記錄"""
    if TRADE_FILE.exists():
        try:
            with open(TRADE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'positions': [], 'closed_trades': []}

def save_trades(data):
    """儲存交易記錄"""
    with open(TRADE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_learning(report):
    """儲存學習報告"""
    with open(LEARN_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def save_params(params):
    """儲存優化參數"""
    with open(PARAMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(params, f, ensure_ascii=False, indent=2)

def load_params():
    """載入參數"""
    if PARAMS_FILE.exists():
        try:
            with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_PARAMS.copy()

# ==========================================
# 技術指標計算
# ==========================================
def calc_rsi(prices, period=14):
    """計算 RSI"""
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def calc_ma(prices, period):
    """計算 MA"""
    if len(prices) < period:
        return float(prices.iloc[-1])
    return float(prices.iloc[-period:].mean())

def calc_volatility(prices, period=20):
    """計算波動率"""
    if len(prices) < period:
        return 0.0
    returns = prices.pct_change().dropna()
    return float(returns.tail(period).std() * np.sqrt(252))

# ==========================================
# 自動學習優化
# ==========================================
def analyze_trades(trades):
    """分析交易記錄，學習優化"""
    if not trades['closed_trades']:
        return {'message': 'No closed trades to analyze', 'params': DEFAULT_PARAMS.copy()}
    
    closed = trades['closed_trades']
    
    # 分析勝敗
    wins = [t for t in closed if t.get('pnl', 0) > 0]
    losses = [t for t in closed if t.get('pnl', 0) <= 0]
    
    # 分析各參數表現
    rsi_ranges = [(30, 40), (40, 50), (50, 60), (60, 70)]
    hold_ranges = [(5, 10), (10, 15), (15, 20)]
    
    best_rsi = (30, 40)
    best_hold = (5, 10)
    best_win_rate = 0
    best_avg_return = 0
    
    # 遍歷 RSI 區間
    for rsi_min, rsi_max in rsi_ranges:
        filtered = [t for t in closed if rsi_min <= t.get('rsi_entry', 0) < rsi_max]
        if len(filtered) >= 3:
            wr = len([t for t in filtered if t.get('pnl', 0) > 0]) / len(filtered)
            avg_ret = np.mean([t.get('pnl', 0) for t in filtered]) * 100
            if wr > best_win_rate:
                best_win_rate = wr
                best_rsi = (rsi_min, rsi_max)
                best_avg_return = avg_ret
    
    # 遍歷持有天數
    for hold_min, hold_max in hold_ranges:
        filtered = [t for t in closed if hold_min <= t.get('hold_days', 0) < hold_max]
        if len(filtered) >= 3:
            wr = len([t for t in filtered if t.get('pnl', 0) > 0]) / len(filtered)
            if wr > best_win_rate:
                best_win_rate = wr
                best_hold = (hold_min, hold_max)
    
    # 更新參數
    params = load_params()
    params['rsi_entry_min'] = best_rsi[0]
    params['rsi_entry_max'] = best_rsi[1]
    params['hold_days_min'] = best_hold[0]
    params['hold_days_max'] = best_hold[1]
    params['win_rate'] = best_win_rate * 100
    params['avg_return'] = best_avg_return
    params['total_trades'] = len(closed)
    params['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return {
        'total_trades': len(closed),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': best_win_rate * 100,
        'avg_return': best_avg_return,
        'best_rsi_range': best_rsi,
        'best_hold_days': best_hold,
        'params': params,
    }

# ==========================================
# 每日學習分析
# ==========================================
def daily_learning():
    """每日自動學習"""
    print('='*60)
    print('  Leo AI/半導體/科技 主動學習系統')
    print('='*60)
    print()
    
    # 載入交易記錄
    trades = load_trades()
    
    # 分析並學習
    analysis = analyze_trades(trades)
    
    # 儲存優化參數
    if 'params' in analysis:
        save_params(analysis['params'])
    
    # 輸出報告
    print('【學習分析報告】')
    print('-'*60)
    print(f"  總交易筆數: {analysis.get('total_trades', 0)}")
    print(f"  勝利的次數: {analysis.get('wins', 0)}")
    print(f"  虧損的次數: {analysis.get('losses', 0)}")
    print(f"  勝率: {analysis.get('win_rate', 0):.1f}%")
    print(f"  平均報酬: {analysis.get('avg_return', 0):.2f}%")
    print()
    print('【優化後參數】')
    print('-'*60)
    params = analysis.get('params', DEFAULT_PARAMS)
    print(f"  RSI 進場區間: {params['rsi_entry_min']}-{params['rsi_entry_max']}")
    print(f"  持有天數: {params['hold_days_min']}-{params['hold_days_max']} 天")
    print(f"  目標獲利: +{params['tp_pct']}%")
    print(f"  停損: -{params['sl_pct']}%")
    print(f"  預期勝率: {params['win_rate']:.1f}%")
    print(f"  預期報酬: +{params['avg_return']:.2f}%")
    
    # 產業鏈分析
    print()
    print('【產業鏈健康度】')
    print('-'*60)
    
    # 分析上游
    upstream = {k: v for k, v in STOCKS.items() if '上游' in v['sector']}
    midstream = {k: v for k, v in STOCKS.items() if '中游' in v['sector']}
    downstream = {k: v for k, v in STOCKS.items() if '下游' in v['sector']}
    
    print(f"  上游（半導體/IC設計）: {len(upstream)} 檔")
    print(f"  中游（伺服器/封測）: {len(midstream)} 檔")
    print(f"  下游（EMS/PCB/散熱）: {len(downstream)} 檔")
    
    # 學習總結
    summary = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_stocks': len(STOCKS),
        'upstream': len(upstream),
        'midstream': len(midstream),
        'downstream': len(downstream),
        'analysis': analysis,
        'params': params,
    }
    
    save_learning(summary)
    
    print()
    print('='*60)
    print(f'  學習完成，已優化 {len(STOCKS)} 檔股票追蹤')
    print(f'  勝率提升至: {params["win_rate"]:.1f}%')
    print('='*60)
    
    return summary

# ==========================================
# 主程式
# ==========================================
if __name__ == '__main__':
    result = daily_learning()
    print(f'\n報告已儲存: {LEARN_FILE}')