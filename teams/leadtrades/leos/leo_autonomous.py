# -*- coding: utf-8 -*-
"""
Leo 主動分析學習系統
功能：
  - 每日掃描 + 學習優化參數
  - 分析錯誤交易記錄
  - 自動調整進場條件
  - 生成學習報告
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os

STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎'
}

TRADE_FILE = 'leos_trades.json'
LEARN_FILE = 'leos_learning.json'

# WFA 最優參數
RSI_PERIOD = 12
RSI_THRESHOLD = 40
HOLD_DAYS = 10
TAKE_PROFIT = 0.10
STOP_LOSS = 0.08

def load_trades():
    if os.path.exists(TRADE_FILE):
        try:
            with open(TRADE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {'positions': [], 'closed_trades': data}
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return {'positions': [], 'closed_trades': []}

def save_learning(report):
    with open(LEARN_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2))

def calc_rsi(prices, period=12):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_ma(prices, period):
    return prices.rolling(window=period).mean()

def calc_momentum(prices, days=5):
    return prices.pct_change(days) * 100

def analyze_errors(trades):
    """分析錯誤交易（虧損交易）"""
    errors = [t for t in trades if t.get('pnl_pct', 0) < 0]
    if not errors:
        return {'total_errors': 0, 'patterns': [], 'suggestions': []}
    
    patterns = []
    suggestions = []
    
    sl_trades = [t for t in errors if t.get('exit_reason') == 'SL']
    hold_trades = [t for t in errors if t.get('exit_reason') == 'HOLD']
    
    if len(sl_trades) > len(errors) * 0.5:
        patterns.append(f"停損觸發過多: {len(sl_trades)}筆")
        suggestions.append("建議提高 RSI_Threshold 至 45 或放寬停損至 10%")
    
    if len(hold_trades) > 0:
        patterns.append(f"持有期滿虧損: {len(hold_trades)}筆")
        suggestions.append("建議縮短持有期至 7 天或提高進場動量門檻")
    
    return {
        'total_errors': len(errors),
        'patterns': patterns,
        'suggestions': suggestions
    }

def quick_backtest(rsi_t, start_date='2023-01-01'):
    """快速回測（單一參數）"""
    total_pnl = 0
    wins = 0
    total = 0
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    
    for ticker in STOCKS.keys():
        try:
            df = yf.download(f"{ticker}.TW", start=start_date, end=end_date, progress=False)
            if df.empty or len(df) < 60:
                continue
            
            close = df['Close'].squeeze()
            rsi = calc_rsi(close, 12)
            ma60 = calc_ma(close, 60)
            momentum = calc_momentum(close, 5)
            
            for i in range(60, len(df) - HOLD_DAYS):
                price = close.iloc[i]
                crsi = rsi.iloc[i]
                cma = ma60.iloc[i]
                cmom = momentum.iloc[i]
                
                if crsi < rsi_t and not pd.isna(cma) and price > cma and cmom > 2:
                    entry_price = price
                    
                    for j in range(i + 1, min(i + HOLD_DAYS + 1, len(df))):
                        p = close.iloc[j]
                        pnl = (p - entry_price) / entry_price * 100
                        
                        if pnl >= TAKE_PROFIT * 100:
                            total_pnl += pnl
                            wins += 1
                            total += 1
                            break
                        elif pnl <= -STOP_LOSS * 100:
                            total_pnl += pnl
                            total += 1
                            break
                    else:
                        pnl = (close.iloc[i + HOLD_DAYS] - entry_price) / entry_price * 100
                        total_pnl += pnl
                        if pnl > 0:
                            wins += 1
                        total += 1
        except:
            pass
    
    if total == 0:
        return 0, 0, 0
    
    win_rate = wins / total * 100
    avg_return = total_pnl / total
    
    return win_rate, avg_return, total

def optimize_rsi_threshold():
    """優化 RSI 門檻參數"""
    print("\n🔬 執行參數優化...")
    
    results = []
    for rsi_t in [30, 35, 40, 45, 50]:
        wr, avg, count = quick_backtest(rsi_t)
        score = wr * 0.4 + avg * 5 * 0.3 + min(count / 30, 1) * 0.3
        results.append({
            'rsi_threshold': rsi_t,
            'win_rate': wr,
            'avg_return': avg,
            'total_trades': count,
            'score': score
        })
        print(f"  RSI_Threshold={rsi_t}: 勝率={wr:.0f}%, 平均={avg:.2f}%, 筆數={count}, 分數={score:.2f}")
    
    results.sort(key=lambda x: x['score'], reverse=True)
    best = results[0]
    
    print(f"\n  ★ 最佳 RSI_Threshold: {best['rsi_threshold']} (分數={best['score']:.2f})")
    
    return best

def run_daily_scan():
    """每日掃描"""
    print("=" * 60)
    print("Leo 主動分析學習系統 v7.0")
    print("=" * 60)
    
    data = load_trades()
    closed_trades = data.get('closed_trades', [])
    
    print(f"\n📊 分析交易記錄: {len(closed_trades)} 筆")
    
    # 分析錯誤
    error_report = analyze_errors(closed_trades)
    print(f"\n▎錯誤分析")
    print("-" * 40)
    print(f"  虧損交易: {error_report['total_errors']} 筆")
    for p in error_report['patterns']:
        print(f"  • {p}")
    for s in error_report['suggestions']:
        print(f"  ➤ {s}")
    
    # 參數優化
    best_params = optimize_rsi_threshold()
    
    # 掃描當前機會
    print("\n🔍 掃描當前進場機會...")
    opportunities = []
    
    for ticker, name in STOCKS.items():
        try:
            df = yf.download(f"{ticker}.TW", period='5d', progress=False)
            if df.empty or len(df) < 20:
                continue
            
            close = df['Close'].squeeze()
            rsi = calc_rsi(close, RSI_PERIOD)
            ma60 = calc_ma(close, 60)
            momentum = calc_momentum(close, 5)
            
            price = close.iloc[-1]
            crsi = rsi.iloc[-1]
            cma = ma60.iloc[-1]
            cmom = momentum.iloc[-1]
            
            score = 0
            tags = []
            
            if crsi < 30:
                score += 30
                tags.append("RSI超賣")
            elif crsi < RSI_THRESHOLD:
                score += 15
                tags.append("RSI偏低")
            elif crsi > 70:
                score -= 20
                tags.append("RSI偏高")
            
            if not pd.isna(cma) and price > cma:
                score += 25
                tags.append("MA60多頭")
            
            if cmom > 5:
                score += 20
                tags.append("動量很強")
            elif cmom > 2:
                score += 10
                tags.append("動量正向")
            
            if crsi < best_params['rsi_threshold']:
                opportunities.append({
                    'ticker': ticker,
                    'name': name,
                    'price': price,
                    'rsi': crsi,
                    'momentum': cmom,
                    'score': score,
                    'tags': tags
                })
        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
    
    # 排序
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n▎進場機會排序")
    print("-" * 50)
    print(f"{'代碼':<6} {'名稱':<8} {'價格':>8} {'RSI':>6} {'動量':>6} {'評分':>5} {'標籤'}")
    print("-" * 50)
    for o in opportunities[:5]:
        print(f"{o['ticker']:<6} {o['name']:<8} {o['price']:>8.2f} {o['rsi']:>6.1f} {o['momentum']:>6.2f} {o['score']:>5} {', '.join(o['tags'])}")
    
    # 學習報告
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_trades_analyzed': len(closed_trades),
        'error_analysis': error_report,
        'best_params': best_params,
        'opportunities': opportunities[:5]
    }
    save_learning(report)
    
    print(f"\n✅ 學習報告已存: {LEARN_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    run_daily_scan()