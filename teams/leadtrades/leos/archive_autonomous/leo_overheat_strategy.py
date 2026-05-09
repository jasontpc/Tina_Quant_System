# -*- coding: utf-8 -*-
"""
Leo 市場過熱應變策略分析
當 TWII RSI 長期 > 85 時的分析與應變
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

def get_twii_rsi_history(months=24):
    """取得 TWII 歷史 RSI"""
    try:
        df = yf.download('^TWII', period=f'{months}mo', progress=False)
        if df.empty:
            return None
        
        close = df['Close'].squeeze()
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.dropna()
    except Exception as e:
        print(f"取得 TWII 資料失敗: {e}")
        return None


def analyze_overheated_periods(rsi_series):
    """分析過熱時期"""
    df = pd.DataFrame({'rsi': rsi_series})
    df['is_overheated'] = df['rsi'] > 85
    df['is_hot'] = df['rsi'] > 70
    df['is_bull'] = df['rsi'] > 50
    
    # 找出連續過熱區間
    df['overheated_group'] = (df['is_overheated'] != df['is_overheated'].shift()).cumsum()
    overheating_periods = []
    
    for group_id in df[df['is_overheated']]['overheated_group'].unique():
        group_df = df[df['overheated_group'] == group_id]
        if len(group_df) > 0:
            start = group_df.index[0]
            end = group_df.index[-1]
            days = (end - start).days + 1
            max_rsi = group_df['rsi'].max()
            avg_rsi = group_df['rsi'].mean()
            overheating_periods.append({
                'start': start,
                'end': end,
                'days': days,
                'max_rsi': max_rsi,
                'avg_rsi': avg_rsi
            })
    
    return overheating_periods, df


def calculate_market_adaptation_score(rsi):
    """計算市場適應性分數"""
    if rsi > 90:
        return {
            'score': 0,
            'status': '極度過熱',
            'action': '觀望',
            'allocation': '0%'
        }
    elif rsi > 85:
        return {
            'score': 20,
            'status': '過熱',
            'action': '極度謹慎，極低倉位',
            'allocation': '0-10%'
        }
    elif rsi > 80:
        return {
            'score': 40,
            'status': '偏高',
            'action': '謹慎，短線操作',
            'allocation': '10-20%'
        }
    elif rsi > 70:
        return {
            'score': 60,
            'status': '中立',
            'action': '正常操作，嚴格停損',
            'allocation': '30-50%'
        }
    elif rsi > 60:
        return {
            'score': 80,
            'status': '偏多',
            'action': '積極操作',
            'allocation': '50-70%'
        }
    else:
        return {
            'score': 100,
            'status': '正常',
            'action': '全力操作',
            'allocation': '70-100%'
        }


def analyze_us_etf_opportunities():
    """分析美股 ETF 機會（過熱時的替代方案）"""
    us_etfs = {
        'QQQ': '納斯達克100',
        'SPY': 'S&P 500',
        'VTI': '整體市場',
    }
    
    results = []
    try:
        for ticker, name in us_etfs.items():
            df = yf.download(ticker, period='3mo', progress=False)
            if df.empty or len(df) < 30:
                continue
            
            close = df['Close'].squeeze()
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            
            # 計算 MA 狀態
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
            
            results.append({
                'ticker': ticker,
                'name': name,
                'price': float(close.iloc[-1]),
                'rsi': float(rsi),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'above_ma20': float(close.iloc[-1]) > ma20,
                'above_ma60': float(close.iloc[-1]) > ma60,
            })
    except Exception as e:
        print(f"分析美股 ETF 失敗: {e}")
    
    return results


def generate_adaptation_params(overheated_days):
    """根據過熱天數生成調整參數"""
    if overheated_days >= 30:
        # 嚴重過熱：大幅降低倉位，增加動量要求
        return {
            'description': '嚴重過熱（>30天）',
            'position_reduce': 0.5,  # 倉位砍半
            'rsi_threshold_adjust': -10,  # 提高進場門檻
            'momentum_min': 0,  # 動量必須為正
            'ma_bull_strict': True,  # 嚴格多頭排列
            'use_us_etf': True,  # 考慮美股 ETF
        }
    elif overheated_days >= 14:
        # 中度过熱
        return {
            'description': '中度過熱（14-30天）',
            'position_reduce': 0.7,
            'rsi_threshold_adjust': -5,
            'momentum_min': -2,
            'ma_bull_strict': True,
            'use_us_etf': True,
        }
    else:
        # 輕度過熱
        return {
            'description': '輕度過熱（<14天）',
            'position_reduce': 0.8,
            'rsi_threshold_adjust': 0,
            'momentum_min': -3,
            'ma_bull_strict': False,
            'use_us_etf': False,
        }


def run_analysis():
    print("=" * 70)
    print("Leo 市場過熱應變策略分析")
    print("=" * 70)

    # 1. 取得 TWII 歷史 RSI
    print("\n【1. TWII 歷史分析】")
    rsi_series = get_twii_rsi_history(24)
    
    if rsi_series is None or len(rsi_series) == 0:
        print("無法取得 TWII 資料")
        return
    
    current_rsi = rsi_series.iloc[-1]
    print(f"  目前 TWII RSI: {current_rsi:.1f}")
    
    # 2. 分析過熱時期
    print("\n【2. 過熱時期分析】")
    periods, rsi_df = analyze_overheated_periods(rsi_series)
    
    if periods:
        print(f"  過去24個月過熱次數（RSI>85）: {len(periods)} 次")
        total_overheated_days = sum(p['days'] for p in periods)
        print(f"  總過熱天數: {total_overheated_days} 天")
        print(f"  最長過熱期間: {max(p['days'] for p in periods)} 天")
        print(f"  平均過熱期間: {sum(p['days'] for p in periods) / len(periods):.1f} 天")
        
        print("\n  過熱區間詳情:")
        for i, p in enumerate(periods[-5:], 1):  # 只顯示最近5次
            print(f"    {i}. {p['start'].strftime('%Y-%m-%d')} ~ {p['end'].strftime('%Y-%m-%d')}: {p['days']}天, 最高RSI={p['max_rsi']:.1f}")
    else:
        print("  過去24個月無過熱記錄")
    
    # 3. 市場適應性分數
    print("\n【3. 市場適應性評估】")
    adaptation = calculate_market_adaptation_score(current_rsi)
    print(f"  當前狀態: {adaptation['status']}")
    print(f"  適應性分數: {adaptation['score']}/100")
    print(f"  建議動作: {adaptation['action']}")
    print(f"  建議倉位: {adaptation['allocation']}")
    
    # 4. 生成調整參數
    overheated_days = sum(p['days'] for p in periods) if periods else 0
    print("\n【4. 參數調整建議】")
    params = generate_adaptation_params(overheated_days)
    print(f"  調整策略: {params['description']}")
    print(f"  倉位調整: {params['position_reduce'] * 100:.0f}%")
    print(f"  RSI 閾值調整: {params['rsi_threshold_adjust']:+.0f}")
    print(f"  最低動量要求: >{params['momentum_min']}%")
    print(f"  嚴格多頭排列: {'是' if params['ma_bull_strict'] else '否'}")
    print(f"  考慮美股 ETF: {'是' if params['use_us_etf'] else '否'}")
    
    # 5. 美股 ETF 機會
    print("\n【5. 美股 ETF 替代方案】")
    us_etfs = analyze_us_etf_opportunities()
    if us_etfs:
        print(f"  {'代碼':<6} {'名稱':<12} {'價格':<12} {'RSI':<8} {'MA20':<8} {'MA60':<8}")
        print("  " + "-" * 60)
        for etf in us_etfs:
            rsi_ok = "✅" if etf['rsi'] < 60 else "⚠️"
            ma20_ok = "✅" if etf['above_ma20'] else "❌"
            ma60_ok = "✅" if etf['above_ma60'] else "❌"
            print(f"  {etf['ticker']:<6} {etf['name']:<12} {etf['price']:<12.2f} {etf['rsi']:>6.1f}{rsi_ok}  MA20:{ma20_ok}  MA60:{ma60_ok}")
    else:
        print("  無法取得美股 ETF 資料")
    
    # 6. 過熱時的波段策略
    print("\n【6. 過熱市場波段策略】")
    print("""
  當市場過熱時（TWII RSI > 85）：

  A. 等待策略
     - 停用新進場，直到 RSI < 70
     - 現有倉位提高停損（SL 收緊至 5%）
     - 積極停利，縮短持有時間

  B. 短線策略
     - 如果一定要進場，選擇 RSI < 40 的極低估區間
     - 持有天數縮短至 7-14 天
     - 動量過濾從 -5% 提高到 +2%

  C. 多空對沖
     - 考慮使用反向 ETF（如 TWM、T50 反向）
     - 或配置美股 QQQ/SQQQ 對沖

  D. 美股替代
     - 將部分資金配置到美股 ETF（QQQ, SPY）
     - 美股估值合理時可分散風險
    """)
    
    # 7. 調整後的進場參數
    print("\n【7. 調整後進場參數（過熱市場）】")
    adjusted_params = {
        '2330': {
            'rsi_threshold': 50 + params['rsi_threshold_adjust'],
            'hold_days': max(14, 30 - overheated_days // 3),
            'take_profit': 5,
            'stop_loss': max(5, 8 - (params['position_reduce'] - 1) * 10),
            'position_weight': params['position_reduce'],
        },
        '2382': {
            'rsi_threshold': 50 + params['rsi_threshold_adjust'],
            'hold_days': max(14, 30 - overheated_days // 3),
            'take_profit': 5,
            'stop_loss': max(5, 8 - (params['position_reduce'] - 1) * 10),
            'position_weight': params['position_reduce'],
        },
        '3665': {
            'rsi_threshold': 50 + params['rsi_threshold_adjust'],
            'hold_days': max(21, 45 - overheated_days // 3),
            'take_profit': 6,
            'stop_loss': max(6, 10 - (params['position_reduce'] - 1) * 10),
            'position_weight': params['position_reduce'] * 0.5,
        },
        '2317': {
            'rsi_threshold': 55 + params['rsi_threshold_adjust'],
            'hold_days': max(21, 45 - overheated_days // 3),
            'take_profit': 5,
            'stop_loss': max(6, 10 - (params['position_reduce'] - 1) * 10),
            'position_weight': params['position_reduce'] * 0.8,
        },
        '3034': {
            'rsi_threshold': 40 + params['rsi_threshold_adjust'],
            'hold_days': max(14, 30 - overheated_days // 3),
            'take_profit': 5,
            'stop_loss': max(5, 8 - (params['position_reduce'] - 1) * 10),
            'position_weight': params['position_reduce'],
        },
    }
    
    print(f"  {'股票':<8} {'新RSI閾值':<12} {'新持有天數':<12} {'新停損':<8} {'倉位權重'}")
    print("  " + "-" * 55)
    for ticker, p in adjusted_params.items():
        print(f"  {ticker:<8} {p['rsi_threshold']:<12} {p['hold_days']:<12} {p['stop_loss']}%     {p['position_weight']:.1f}x")
    
    return adjusted_params, params, adaptation


if __name__ == '__main__':
    run_analysis()