# -*- coding: utf-8 -*-
"""
Leo 科技股波段 v7.0 — 整合版
功能：
  - 結合：進場面 + 停利/停損 + 類證券法人流向
  - WFA 最優參數
  - 自動進場條件判斷
  - 觸發停利/停損 時自動平倉
  - 產出完整分析報告
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os

# === WFA 最優參數 ===
RSI_PERIOD = 12
RSI_THRESHOLD = 40
HOLD_DAYS = 10
TAKE_PROFIT = 0.10
STOP_LOSS = 0.08

STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎'
}

TRADE_FILE = 'leos_trades.json'
OUTPUT_FILE = 'leos_analysis_report.json'

def load_trades():
    if os.path.exists(TRADE_FILE):
        try:
            with open(TRADE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
    return {'positions': [], 'closed_trades': []}

def save_trades(data):
    with open(TRADE_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))

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

def calc_volatility(prices, days=20):
    return prices.pct_change().rolling(window=days).std() * np.sqrt(252) * 100

def get_institutional_score(ticker):
    """類證券法人評分（0-100）"""
    try:
        df = yf.download(f"{ticker}.TW", period='5d', progress=False)
        if df.empty:
            return 50, []
        
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        
        # 近5日法人活動模擬（使用成交量變化）
        vol_change = (volume.iloc[-1] / volume.iloc[-5].mean() - 1) * 100 if len(volume) >= 5 else 0
        price_change = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
        
        rsi = calc_rsi(close, 12).iloc[-1]
        
        score = 50  # 基準
        tags = []
        
        # 放量上漲
        if vol_change > 20 and price_change > 2:
            score += 25
            tags.append("法人買超")
        elif vol_change > 10 and price_change > 1:
            score += 15
            tags.append("溫和買超")
        
        # 法人賣超
        if vol_change > 20 and price_change < -2:
            score -= 25
            tags.append("法人賣超")
        
        # RSI 評分
        if rsi > 70:
            score -= 15
            tags.append("RSI過熱")
        elif rsi < 30:
            score += 20
            tags.append("RSI超賣")
        elif rsi < 40:
            score += 10
            tags.append("RSI偏低")
        
        # 限制範圍
        score = max(0, min(100, score))
        
        return score, tags
    except Exception as e:
        return 50, [f"錯誤: {e}"]

def analyze_stock(ticker, name):
    """完整分析一檔股票"""
    try:
        df = yf.download(f"{ticker}.TW", period='6mo', progress=False)
        if df.empty or len(df) < 30:
            return None
        
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        volume = df['Volume'].squeeze()
        
        # 技術指標
        rsi = calc_rsi(close, RSI_PERIOD)
        ma20 = calc_ma(close, 20)
        ma60 = calc_ma(close, 60)
        ma120 = calc_ma(close, 120)
        momentum = calc_momentum(close, 5)
        vol_20 = calc_volatility(close, 20)
        
        # 當前值
        price = close.iloc[-1]
        crsi = rsi.iloc[-1]
        cma20 = ma20.iloc[-1]
        cma60 = ma60.iloc[-1]
        cma120 = ma120.iloc[-1]
        cmom = momentum.iloc[-1]
        
        # 法人評分
        inst_score, inst_tags = get_institutional_score(ticker)
        
        # 支撐/阻力
        support = low.dropna().rolling(window=20).min().iloc[-1]
        resistance = high.dropna().rolling(window=20).max().iloc[-1]
        
        # MA 多頭排列
        ma_bullish = (price > cma60 and cma60 > cma120) if not (pd.isna(cma60) or pd.isna(cma120)) else False
        
        # 進場評估
        entry_score = 0
        entry_signals = []
        
        if crsi < RSI_THRESHOLD:
            entry_score += 30
            entry_signals.append(f"RSI偏低({crsi:.0f})")
        
        if not pd.isna(cma60) and price > cma60:
            entry_score += 25
            entry_signals.append("MA60多頭")
        
        if cmom > 2:
            entry_score += 20
            entry_signals.append(f"動量正向({cmom:.1f}%)")
        
        if ma_bullish:
            entry_score += 15
            entry_signals.append("多頭排列")
        
        # 法人評分加成
        entry_score += (inst_score - 50) * 0.3
        
        # 狀態判斷
        if crsi < 35 and price > cma60 and cmom > 2:
            status = "進場"
        elif any(p['ticker'] == ticker for p in load_trades().get('positions', [])):
            status = "持倉"
        else:
            status = "觀望"
        
        # 漲跌停風險
        limit_up = close.iloc[-1] * 1.10
        limit_down = close.iloc[-1] * 0.90
        
        return {
            'ticker': ticker,
            'name': name,
            'price': price,
            'rsi': crsi,
            'ma20': cma20,
            'ma60': cma60,
            'ma120': cma120,
            'momentum': cmom,
            'volatility': vol_20.iloc[-1] if not pd.isna(vol_20.iloc[-1]) else 0,
            'support': support,
            'resistance': resistance,
            'ma_bullish': ma_bullish,
            'inst_score': inst_score,
            'inst_tags': inst_tags,
            'entry_score': entry_score,
            'entry_signals': entry_signals,
            'status': status
        }
    except Exception as e:
        return {'ticker': ticker, 'name': name, 'error': str(e)}

def check_portfolio_management(positions):
    """檢查持倉並執行停利/停損"""
    updated = []
    closed = []
    
    for p in positions:
        ticker = p['ticker']
        try:
            df = yf.download(f"{ticker}.TW", period='5d', progress=False)
            if df.empty:
                updated.append(p)
                continue
            
            close = df['Close'].squeeze()
            current_price = close.iloc[-1]
            entry_price = p['entry_price']
            
            pnl_pct = (current_price - entry_price) / entry_price * 100
            hold_days = (datetime.now() - datetime.strptime(p['entry_date'], '%Y-%m-%d')).days
            
            exit_reason = None
            if pnl_pct >= TAKE_PROFIT * 100:
                exit_reason = '停利'
            elif pnl_pct <= -STOP_LOSS * 100:
                exit_reason = '停損'
            elif hold_days >= HOLD_DAYS:
                exit_reason = '到期'
            
            if exit_reason:
                closed.append({
                    **p,
                    'exit_date': datetime.now().strftime('%Y-%m-%d'),
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                })
            else:
                p['current_price'] = current_price
                p['pnl_pct'] = pnl_pct
                p['hold_days'] = hold_days
                updated.append(p)
        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
            updated.append(p)
    
    return updated, closed

def main():
    print("=" * 60)
    print("Leo 科技股波段 v7.0 — 整合分析系統")
    print("=" * 60)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"WFA 參數: RSI_P={RSI_PERIOD}, Thresh={RSI_THRESHOLD}, Hold={HOLD_DAYS}d, TP={TAKE_PROFIT*100}%, SL={STOP_LOSS*100}%")
    print()
    
    # 載入持倉
    data = load_trades()
    positions = data.get('positions', [])
    closed_trades = data.get('closed_trades', [])
    
    # 檢查持倉停利/停損
    if positions:
        print("📊 檢查持倉...")
        positions, new_closed = check_portfolio_management(positions)
        closed_trades.extend(new_closed)
        for c in new_closed:
            print(f"  🔚 {c['ticker']} {c['name']}: {c['exit_reason']}, 報酬={c['pnl_pct']:.2f}%")
    
    # 分析所有股票
    print("\n🔍 掃描股票...")
    results = []
    
    for ticker, name in STOCKS.items():
        analysis = analyze_stock(ticker, name)
        if analysis:
            results.append(analysis)
            if 'error' in analysis:
                print(f"  ⚠️ {ticker}: {analysis['error']}")
            else:
                status_icon = "✅" if analysis['status'] == '進場' else ("📌" if analysis['status'] == '持倉' else "👀")
                print(f"  {status_icon} {ticker} {name}: 價格={analysis['price']:.2f}, RSI={analysis['rsi']:.0f}, 評分={analysis['entry_score']:.0f}, 狀態={analysis['status']}")
    
    # 排序
    results.sort(key=lambda x: x.get('entry_score', 0), reverse=True)
    
    # 產出報告
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'params': {
            'RSI_Period': RSI_PERIOD,
            'RSI_Threshold': RSI_THRESHOLD,
            'Hold_Days': HOLD_DAYS,
            'Take_Profit': TAKE_PROFIT * 100,
            'Stop_Loss': STOP_LOSS * 100
        },
        'positions': positions,
        'closed_trades': closed_trades[-20:],  # 只留最近20筆
        'analysis': results,
        'summary': {
            'total_stocks': len(results),
            'entry_ready': len([r for r in results if r['status'] == '進場']),
            'holding': len([r for r in results if r['status'] == '持倉']),
            'watching': len([r for r in results if r['status'] == '觀望'])
        }
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 顯示摘要
    print("\n" + "=" * 60)
    print("📋 每日分析摘要")
    print("=" * 60)
    
    print(f"\n{'代碼':<6} {'名稱':<8} {'價格':>8} {'RSI':>5} {'動量':>6} {'法人':>5} {'評分':>5} {'狀態':<6} {'信號'}")
    print("-" * 75)
    
    for r in results:
        signals = ', '.join(r.get('entry_signals', [])[:2])
        print(f"{r['ticker']:<6} {r['name']:<8} {r['price']:>8.2f} {r['rsi']:>5.0f} {r['momentum']:>6.1f} {r['inst_score']:>5.0f} {r['entry_score']:>5.0f} {r['status']:<6} {signals}")
    
    # 推薦
    entry_stocks = [r for r in results if r['status'] == '進場']
    if entry_stocks:
        print("\n▎🎯 進場推薦")
        for s in entry_stocks[:3]:
            print(f"  ★ {s['ticker']} {s['name']}: 評分={s['entry_score']:.0f}, 信號={' / '.join(s['entry_signals'])}")
    
    # 績效
    if closed_trades:
        wins = [t for t in closed_trades if t.get('pnl_pct', 0) > 0]
        wr = len(wins) / len(closed_trades) * 100 if closed_trades else 0
        total_pnl = sum(t.get('pnl_pct', 0) for t in closed_trades)
        print(f"\n▎📈 交易統計: {len(closed_trades)}筆, 勝率={wr:.0f}%, 總報酬={total_pnl:.1f}%")
    
    print(f"\n✅ 分析報告已存: {OUTPUT_FILE}")
    print("=" * 60)
    
    # 更新持倉
    data['positions'] = positions
    data['closed_trades'] = closed_trades
    save_trades(data)

if __name__ == '__main__':
    main()