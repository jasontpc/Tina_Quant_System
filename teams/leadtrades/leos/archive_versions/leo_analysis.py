# -*- coding: utf-8 -*-
"""
Leo 每日主動分析報告
功能：
  - 8檔科技股深度分析
  - RSI/MA/動量/法人/支撐阻力 全部覆蓋
  - 進場/持倉/觀望 三種狀態
  - 主動推薦最佳標的
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime
import os

STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎'
}

TRADE_FILE = 'leos_trades.json'
REPORT_FILE = 'leos_analysis_report.json'

RSI_PERIOD = 12
RSI_THRESHOLD = 40

def load_positions():
    if os.path.exists(TRADE_FILE):
        with open(TRADE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [p['ticker'] for p in data.get('positions', [])]
    return []

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

def get_support_resistance(df, lookback=60):
    """計算支撐與阻力位"""
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    
    resistance = high.rolling(window=lookback).max().iloc[-1]
    support = low.rolling(window=lookback).min().iloc[-1]
    
    # 第二層支撐/阻力
    resistance2 = high.rolling(window=lookback).max().iloc[-30:-10].max()
    support2 = low.rolling(window=lookback).min().iloc[-30:-10].min()
    
    return support, resistance, support2, resistance2

def get_volume_profile(df, periods=20):
    """成交量分布分析"""
    volume = df['Volume'].squeeze()
    
    avg_vol = volume.tail(periods).mean()
    current_vol = volume.iloc[-1]
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
    
    # 過去5日成交量變化
    vol_change = (volume.iloc[-1] / volume.iloc[-5].mean() - 1) * 100 if len(volume) >= 5 else 0
    
    return avg_vol, current_vol, vol_ratio, vol_change

def get_trend(prices, ma20, ma60, ma120):
    """判斷趨勢"""
    price = prices.iloc[-1]
    
    if pd.isna(ma120) or pd.isna(ma60):
        return "未知"
    
    if price > ma60 and ma60 > ma120:
        return "多頭"
    elif price < ma60 and ma60 < ma120:
        return "空頭"
    else:
        return "整理"

def get_institutional_signal(df):
    """類證券法人訊號"""
    close = df['Close'].squeeze()
    volume = df['Volume'].squeeze()
    
    if len(close) < 5:
        return "N/A", 0
    
    price_chg = (close.iloc[-1] / close.iloc[-5] - 1) * 100
    vol_chg = (volume.iloc[-1] / volume.iloc[-5].mean() - 1) * 100 if len(volume) >= 5 else 0
    
    signal = "持平"
    score = 0
    
    if price_chg > 3 and vol_chg > 15:
        signal = "法人偏多"
        score = 20
    elif price_chg > 1 and vol_chg > 10:
        signal = "溫和偏多"
        score = 10
    elif price_chg < -3 and vol_chg > 15:
        signal = "法人偏空"
        score = -20
    elif price_chg < -1 and vol_chg > 10:
        signal = "溫和偏空"
        score = -10
    
    return signal, score

def analyze_stock(ticker, name):
    """深度分析單一股票"""
    try:
        df = yf.download(f"{ticker}.TW", period='3mo', progress=False)
        if df.empty or len(df) < 30:
            return {'ticker': ticker, 'name': name, 'error': '資料不足'}
        
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        
        # 基本資訊
        price = close.iloc[-1]
        price_chg_1d = close.pct_change().iloc[-1] * 100
        price_chg_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
        price_chg_20d = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0
        
        # 技術指標
        rsi = calc_rsi(close, RSI_PERIOD).iloc[-1]
        ma20 = calc_ma(close, 20).iloc[-1]
        ma60 = calc_ma(close, 60).iloc[-1]
        ma120 = calc_ma(close, 120).iloc[-1]
        momentum = calc_momentum(close, 5).iloc[-1]
        volatility = calc_volatility(close, 20).iloc[-1]
        
        # 支撐/阻力
        support, resistance, support2, resistance2 = get_support_resistance(df)
        
        # 成交量
        avg_vol, current_vol, vol_ratio, vol_change = get_volume_profile(df)
        
        # 趨勢
        trend = get_trend(close, ma20, ma60, ma120)
        
        # 法人訊號
        inst_signal, inst_score = get_institutional_signal(df)
        
        # MA 多頭排列
        ma_bullish = (not pd.isna(ma60) and not pd.isna(ma120) and 
                      price > ma60 and ma60 > ma120)
        
        # 進場評估
        entry_score = 0
        entry_reasons = []
        
        # RSI 評分
        if rsi < 30:
            entry_score += 35
            entry_reasons.append(f"RSI超賣({rsi:.0f})")
        elif rsi < RSI_THRESHOLD:
            entry_score += 25
            entry_reasons.append(f"RSI偏低({rsi:.0f})")
        elif rsi > 70:
            entry_score -= 25
            entry_reasons.append(f"RSI過熱({rsi:.0f})")
        
        # 價格 vs MA
        if not pd.isna(ma60):
            if price > ma60:
                entry_score += 20
                entry_reasons.append("站上MA60")
            else:
                entry_score -= 10
                entry_reasons.append("低於MA60")
        
        # 多頭排列
        if ma_bullish:
            entry_score += 15
            entry_reasons.append("MA多頭排列")
        
        # 動量
        if momentum > 3:
            entry_score += 15
            entry_reasons.append(f"動量充沛({momentum:.1f}%)")
        elif momentum > 1:
            entry_score += 8
            entry_reasons.append(f"動量正向({momentum:.1f}%)")
        
        # 法人訊號
        entry_score += inst_score
        
        # 計算風險回報
        risk_reward = 0
        if price > support and price < resistance:
            risk = price - support
            reward = resistance - price
            risk_reward = reward / risk if risk > 0 else 0
        
        # 判斷狀態
        holding_tickers = load_positions()
        
        if ticker in holding_tickers:
            status = "持倉"
        elif rsi < RSI_THRESHOLD and not pd.isna(ma60) and price > ma60 and momentum > 2:
            status = "進場"
        else:
            status = "觀望"
        
        return {
            'ticker': ticker,
            'name': name,
            'price': round(price, 2),
            'price_chg_1d': round(price_chg_1d, 2),
            'price_chg_5d': round(price_chg_5d, 2),
            'price_chg_20d': round(price_chg_20d, 2),
            'rsi': round(rsi, 1),
            'ma20': round(ma20, 2) if not pd.isna(ma20) else None,
            'ma60': round(ma60, 2) if not pd.isna(ma60) else None,
            'ma120': round(ma120, 2) if not pd.isna(ma120) else None,
            'momentum': round(momentum, 2),
            'volatility': round(volatility, 1),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'support2': round(support2, 2),
            'resistance2': round(resistance2, 2),
            'avg_volume': round(avg_vol, 0),
            'vol_ratio': round(vol_ratio, 2),
            'vol_change': round(vol_change, 1),
            'trend': trend,
            'ma_bullish': ma_bullish,
            'inst_signal': inst_signal,
            'entry_score': round(entry_score, 1),
            'entry_reasons': entry_reasons,
            'risk_reward': round(risk_reward, 2),
            'status': status
        }
    except Exception as e:
        return {'ticker': ticker, 'name': name, 'error': str(e)}

def generate_report():
    """生成每日分析報告"""
    print("=" * 70)
    print("Leo 科技股每日主動分析報告 v7.0")
    print("=" * 70)
    print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %A')}")
    print(f"⏰ 時間: {datetime.now().strftime('%H:%M')}")
    print()
    
    results = []
    
    print("🔍 深度分析 8 檔科技股...")
    print("-" * 70)
    
    for ticker, name in STOCKS.items():
        analysis = analyze_stock(ticker, name)
        results.append(analysis)
        
        if 'error' in analysis:
            print(f"  ⚠️  {ticker} {name}: {analysis['error']}")
        else:
            status_icon = {"進場": "✅", "持倉": "📌", "觀望": "👀"}.get(analysis['status'], "❓")
            print(f"  {status_icon} {ticker} {name}: {analysis['price']}元, RSI={analysis['rsi']}, 評分={analysis['entry_score']}")
    
    # 排序
    results.sort(key=lambda x: x.get('entry_score', 0), reverse=True)
    
    # 顯示完整報告
    print("\n" + "=" * 70)
    print("📊 完整分析報告")
    print("=" * 70)
    
    for r in results:
        if 'error' in r:
            continue
        
        status_icon = {"進場": "✅", "持倉": "📌", "觀望": "👀"}.get(r['status'], "❓")
        
        print(f"\n{status_icon} {r['ticker']} {r['name']} | 現價: {r['price']} | 狀態: {r['status']}")
        print("-" * 60)
        
        print(f"  📈 價格變化: 今日 {r['price_chg_1d']:+.2f}% | 5日 {r['price_chg_5d']:+.2f}% | 20日 {r['price_chg_20d']:+.2f}%")
        print(f"  📉 RSI(12): {r['rsi']} | 動量(5日): {r['momentum']:+.2f}% |  volatility: {r['volatility']:.1f}%")
        
        print(f"  📊 均線: MA20={r['ma20']} | MA60={r['ma60']} | MA120={r['ma120']}")
        print(f"  {'✅' if r['ma_bullish'] else '❌'} MA多頭排列: {'是' if r['ma_bullish'] else '否'} | 趨勢: {r['trend']}")
        
        print(f"  🏛️  支撐: {r['support']} | 阻力: {r['resistance']}")
        print(f"  📐 次級支撐: {r['support2']} | 次級阻力: {r['resistance2']}")
        print(f"  ⚖️  風險報酬比: {r['risk_reward']:.2f}")
        
        print(f"  📦 成交量: 平均={r['avg_volume']:.0f} | 今日比率={r['vol_ratio']:.2f}x | 5日變化={r['vol_change']:+.1f}%")
        print(f"  🏢 法人訊號: {r['inst_signal']}")
        
        print(f"  🎯 進場評分: {r['entry_score']} | {' / '.join(r['entry_reasons']) if r['entry_reasons'] else '無信號'}")
    
    # 推薦
    print("\n" + "=" * 70)
    print("🎯 進場推薦")
    print("=" * 70)
    
    entry_stocks = [r for r in results if r.get('status') == '進場']
    
    if entry_stocks:
        print(f"\n{'排名':<4} {'代碼':<6} {'名稱':<8} {'價格':>8} {'RSI':>5} {'評分':>5} {'進場理由'}")
        print("-" * 65)
        
        for i, s in enumerate(entry_stocks[:5], 1):
            reasons = ', '.join(s['entry_reasons'][:2])
            print(f"#{i:<3} {s['ticker']:<6} {s['name']:<8} {s['price']:>8.2f} {s['rsi']:>5.1f} {s['entry_score']:>5.0f} {reasons}")
        
        # 最佳推薦
        best = entry_stocks[0]
        print(f"\n★ 最佳標的: {best['ticker']} {best['name']}")
        print(f"  價格: {best['price']} | 評分: {best['entry_score']}")
        print(f"  理由: {' / '.join(best['entry_reasons'])}")
        print(f"  支撐: {best['support']} | 阻力: {best['resistance']}")
        print(f"  風險報酬比: {best['risk_reward']}")
    else:
        print("\n  👀 目前無符合進場條件的股票")
        print("  建議: 等待 RSI < 40 且價格站上 MA60 的機會")
    
    # 持倉建議
    holding_stocks = [r for r in results if r.get('status') == '持倉']
    if holding_stocks:
        print("\n" + "=" * 70)
        print("📌 持倉管理")
        print("=" * 70)
        
        for s in holding_stocks:
            print(f"\n  {s['ticker']} {s['name']}: 現價 {s['price']}")
            print(f"    RSI={s['rsi']} | 動量={s['momentum']:+.2f}%")
            
            # 停利停損建議
            if s['rsi'] > 75:
                print(f"    ⚠️  RSI 過熱，建議關注停利機會")
            elif s['rsi'] < 35:
                print(f"    💡 RSI 超賣，可能有撐")
            
            # 支撐/阻力
            if s['price'] > s['resistance']:
                print(f"    🔴 已突破阻力 {s['resistance']}，注意可能回調")
            if s['price'] < s['support']:
                print(f"    🔴 跌破支撐 {s['support']}，謹慎觀察")
    
    # 觀望名單
    watch_stocks = [r for r in results if r.get('status') == '觀望']
    if watch_stocks:
        print("\n" + "=" * 70)
        print("👀 觀望名單")
        print("=" * 70)
        
        for s in watch_stocks[:5]:
            print(f"  {s['ticker']} {s['name']}: 評分={s['entry_score']:.0f}, 趨勢={s['trend']}")
    
    # 儲存報告
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'results': results,
        'recommendations': {
            'entry': [r for r in results if r.get('status') == '進場'],
            'holding': [r for r in results if r.get('status') == '持倉'],
            'watch': [r for r in results if r.get('status') == '觀望']
        }
    }
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2))
    
    print(f"\n✅ 分析報告已存: {REPORT_FILE}")
    print("=" * 70)

if __name__ == '__main__':
    generate_report()