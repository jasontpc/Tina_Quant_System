# -*- coding: utf-8 -*-
"""
Leo 市場溫度計
根據 TWII RSI 調整全系統仓位和進場策略

使用方式：
  python leo_market_temp.py              # 全市場掃描
  python leo_market_temp.py --alert      # 發送通知
  python leo_market_temp.py --slack      # 發送到 Slack（如有設定）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime

import yfinance as yf
import numpy as np

# TWII RSI 門檻
RSI_THRESHOLDS = {
    'extreme_heat': 85,   # 極度過熱
    'overheat': 70,       # 過熱
    'neutral': 50,        # 中性
    'cool': 35,           # 偏涼
    'extreme_cold': 0,    # 極低
}

# 仓位調整係數
POSITION_MULTIPLIERS = {
    'extreme_heat': 0.0,   # 不進場
    'overheat': 0.5,       # 減半
    'neutral': 1.0,        # 正常
    'cool': 1.5,           # 增加
    'extreme_cold': 2.0,   # 重倉
}

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\data'


def calc_rsi(prices, period=14):
    """計算 RSI"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    return float(100 - (100 / (1 + avg_gain / avg_loss)))


def get_market_status(rsi):
    """根據 RSI 取得市場狀態"""
    if rsi >= RSI_THRESHOLDS['extreme_heat']:
        return 'extreme_heat'
    elif rsi >= RSI_THRESHOLDS['overheat']:
        return 'overheat'
    elif rsi >= RSI_THRESHOLDS['neutral']:
        return 'neutral'
    elif rsi >= RSI_THRESHOLDS['cool']:
        return 'cool'
    else:
        return 'extreme_cold'


def get_status_display(status):
    """取得狀態顯示名稱"""
    names = {
        'extreme_heat': '🔴 極度過熱',
        'overheat': '🟠 過熱',
        'neutral': '🟡 中性',
        'cool': '🟢 偏涼',
        'extreme_cold': '🔵 極低',
    }
    return names.get(status, '❓ 未知')


def get_market_temperature():
    """取得市場溫度"""
    try:
        # TWII
        twii = yf.download('^TWII', period='1mo', progress=False)
        twii_close = twii['Close'].squeeze().values
        twii_price = float(twii_close[-1])
        twii_prev = float(twii_close[-2]) if len(twii_close) > 1 else twii_price
        twii_change = (twii_price / twii_prev - 1) * 100
        twii_rsi = calc_rsi(twii_close, 14)
        
        # SPY (美股指標)
        try:
            spy = yf.download('SPY', period='1mo', progress=False)
            spy_close = spy['Close'].squeeze().values
            spy_price = float(spy_close[-1])
            spy_rsi = calc_rsi(spy_close, 14)
        except Exception:
            spy_price = None
            spy_rsi = None
        
        return {
            'twii_price': twii_price,
            'twii_change': twii_change,
            'twii_rsi': twii_rsi,
            'spy_price': spy_price,
            'spy_rsi': spy_rsi,
        }
    except Exception as e:
        print(f"❌ 取得市場資料失敗: {e}")
        return None


def analyze_and_display():
    """分析並顯示市場溫度"""
    print("\n🌡️ Leo 市場溫度計")
    print("="*70)
    
    market = get_market_temperature()
    if not market:
        return None
    
    twii_rsi = market['twii_rsi']
    twii_price = market['twii_price']
    twii_change = market['twii_change']
    spy_rsi = market['spy_rsi']
    
    status = get_market_status(twii_rsi)
    status_display = get_status_display(status)
    multiplier = POSITION_MULTIPLIERS[status]
    
    # TWII
    print(f"\n📊 台灣加權指數（TWII）")
    print(f"  現價: {twii_price:,.0f} ({twii_change:+.2f}%)")
    print(f"  RSI(14): {twii_rsi:.1f}")
    print(f"  市場狀態: {status_display}")
    
    # SPY
    if spy_rsi:
        print(f"\n📊 美股 S&P500（SPY）")
        print(f"  RSI(14): {spy_rsi:.1f}")
        
        # 跨市場驗證
        if twii_rsi > 85 and spy_rsi < 50:
            print(f"  ⚠️ 台股過熱但美股健康 → 考慮美股標的")
        elif twii_rsi < 35 and spy_rsi > 70:
            print(f"  ⚠️ 台股低點但美股高點 → 等待美股回調")
    
    # 系統建議
    print(f"\n{'='*70}")
    print(f"🎯 系統建議")
    print(f"{'='*70}")
    print(f"  市場狀態: {status_display}")
    print(f"  仓位係數: {multiplier:.1f}x")
    
    if status == 'extreme_heat':
        print(f"  操作建議: 全面觀望，不進場")
        print(f"  原因: TWII RSI {twii_rsi:.0f} > 85，市場極度過熱")
    elif status == 'overheat':
        print(f"  操作建議: 减半進場，嚴格停利")
        print(f"  原因: TWII RSI {twii_rsi:.0f} > 70，市場過熱")
    elif status == 'neutral':
        print(f"  操作建議: 正常操作，依系統參數")
        print(f"  原因: TWII RSI {twii_rsi:.0f} 在中性區間")
    elif status == 'cool':
        print(f"  操作建議: 慢慢建倉，逢低加碼")
        print(f"  原因: TWII RSI {twii_rsi:.0f} < 50，市場偏涼")
    else:
        print(f"  操作建議: 重倉進場，等待反彈")
        print(f"  原因: TWII RSI {twii_rsi:.0f} < 35，市場極低")
    
    # 調整停利停損
    print(f"\n📋 調整後停利停損建議")
    if multiplier > 1.0:
        print(f"  停利: 可設宽一點（+8-10%）")
        print(f"  停損: 不變（-8%），但可分批進場")
    elif multiplier == 0:
        print(f"  停利: N/A")
        print(f"  停損: N/A")
    else:
        print(f"  停利: 標準（+5-8%）")
        print(f"  停損: 標準（-8%）")
    
    # 儲存結果
    result = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'twii_price': twii_price,
        'twii_change': twii_change,
        'twii_rsi': round(twii_rsi, 1),
        'spy_rsi': round(spy_rsi, 1) if spy_rsi else None,
        'status': status,
        'status_display': status_display,
        'multiplier': multiplier,
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filepath = os.path.join(OUTPUT_DIR, f'leo_market_temp_{timestamp}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 資料已儲存: {filepath}")
    print("="*70)
    
    return result


def main():
    if len(sys.argv) == 1:
        analyze_and_display()
    
    elif '--alert' in sys.argv:
        result = analyze_and_display()
        if result:
            print("\n📱 通知内容:")
            print(f"🌡️ 市場溫度：{result['status_display']}")
            print(f"TWII RSI: {result['twii_rsi']}")
            print(f"仓位係數: {result['multiplier']}x")
    
    elif '--slack' in sys.argv:
        result = analyze_and_display()
        if result:
            # Slack webhook（如果有的話）
            webhook = os.getenv('SLACK_WEBHOOK')
            if webhook:
                import requests
                payload = {
                    'text': f"🌡️ 市場溫度：{result['status_display']}\nTWII RSI: {result['twii_rsi']}\n仓位係數: {result['multiplier']}x"
                }
                try:
                    requests.post(webhook, json=payload, timeout=10)
                    print("✅ 已發送 Slack 通知")
                except Exception as e:
                    print(f"❌ Slack 發送失敗: {e}")
            else:
                print("⚠️ 未設定 SLACK_WEBHOOK")


if __name__ == '__main__':
    main()
