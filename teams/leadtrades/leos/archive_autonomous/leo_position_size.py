# -*- coding: utf-8 -*-
"""
Leo 動態仓位計算系統
根據 RSI 動態調整進場仓位

使用方式：
  python leo_position_size.py                    # 計算所有 Leo 股票
  python leo_position_size.py 2330 --base 100000  # 計算單一股票
  python leo_position_size.py --summary          # 顯示摘要
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime

import yfinance as yf
import numpy as np

# Leo 追蹤名單與參數
LEO_STOCKS = {
    '2330': {'name': '台積電', 'rsi_th': 50, 'tp': 0.05, 'sl': 0.08},
    '2382': {'name': '廣達', 'rsi_th': 50, 'tp': 0.05, 'sl': 0.08},
    '3665': {'name': '穎崴', 'rsi_th': 50, 'tp': 0.08, 'sl': 0.10},
    '2317': {'name': '鴻海', 'rsi_th': 55, 'tp': 0.05, 'sl': 0.10},
    '3034': {'name': '緯穎', 'rsi_th': 40, 'tp': 0.05, 'sl': 0.08},
}

# RSI 仓位權重表
RSI_WEIGHTS = {
    (0, 35): 1.5,    # RSI < 35：重倉 1.5x
    (35, 45): 1.0,   # RSI 35-45：正常 1.0x
    (45, 55): 0.7,   # RSI 45-55：减少 0.7x
    (55, 100): 0,    # RSI > 55：觀望
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


def get_rsi(code):
    """取得 RSI"""
    try:
        tk = yf.download(f'{code}.TW', period='3mo', progress=False)
        if tk.empty:
            return None
        close = tk['Close'].squeeze().values
        return calc_rsi(close, 14)
    except Exception:
        return None


def get_rsi_weight(rsi):
    """根據 RSI 取得仓位權重"""
    for (low, high), weight in RSI_WEIGHTS.items():
        if low <= rsi < high:
            return weight
    return 0  # RSI >= 55


def calculate_position(code, base_amount, rsi=None):
    """計算單一股票仓位"""
    if rsi is None:
        rsi = get_rsi(code)
    
    if rsi is None:
        return None
    
    # 取得現價
    try:
        tk = yf.download(f'{code}.TW', period='1d', progress=False)
        price = float(tk['Close'].squeeze().values[-1])
    except Exception:
        return None
    
    # 根據 RSI 計算權重
    weight = get_rsi_weight(rsi)
    stock_info = LEO_STOCKS.get(code, {})
    tp = stock_info.get('tp', 0.05)
    sl = stock_info.get('sl', 0.08)
    
    # 計算仓位
    invest_amount = base_amount * weight
    shares = int(invest_amount / price)
    actual_invest = shares * price
    
    # 預期獲利/損失
    expected_return = actual_invest * tp
    expected_loss = actual_invest * sl
    
    return {
        'code': code,
        'name': stock_info.get('name', 'N/A'),
        'price': price,
        'rsi': round(rsi, 1),
        'weight': weight,
        'base_amount': base_amount,
        'invest_amount': actual_invest,
        'shares': shares,
        'tp_pct': tp * 100,
        'sl_pct': sl * 100,
        'expected_return': expected_return,
        'expected_loss': expected_loss,
        'action': 'BUY' if weight > 0 else 'WAIT',
    }


def calculate_all(base_amount=100000):
    """計算所有股票"""
    print(f"\n📊 動態仓位計算（基準金额: {base_amount:,}）")
    print("="*80)
    
    results = []
    
    for code in LEO_STOCKS.keys():
        result = calculate_position(code, base_amount)
        if result:
            results.append(result)
    
    # 排序（依權重）
    results = sorted(results, key=lambda x: (x['weight'], x['rsi']), reverse=True)
    
    # 顯示
    print(f"\n{'代號':<6} {'名稱':<8} {'現價':>8} {'RSI':>6} {'權重':>5} {'投入金額':>12} {'股數':>6} {'建議':<8}")
    print("-"*80)
    
    total_invest = 0
    for r in results:
        weight_str = f"{r['weight']:.1f}x" if r['weight'] > 0 else "WAIT"
        print(f"{r['code']:<6} {r['name']:<8} {r['price']:>8,.0f} {r['rsi']:>6.1f} {weight_str:>5} {r['invest_amount']:>12,.0f} {r['shares']:>6} {r['action']:<8}")
        total_invest += r['invest_amount']
    
    print("-"*80)
    print(f"總投入金額: {total_invest:,.0f} / 基準 {base_amount:,}")
    
    # 儲存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filepath = os.path.join(OUTPUT_DIR, f'leo_position_{timestamp}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return results


def print_summary(results):
    """顯示摘要"""
    print("\n\n📋 仓位權重對照表")
    print("="*60)
    print("| RSI 區間   | 權重   | 建議                |")
    print("|-----------|--------|---------------------|")
    print("| RSI < 35   | 1.5x   | 難得低點，重倉進場   |")
    print("| RSI 35-45  | 1.0x   | 理想進場點          |")
    print("| RSI 45-55  | 0.7x   | 偏高，减少投入      |")
    print("| RSI > 55   | 0x     | 觀望，不進場        |")
    print("="*60)


def main():
    if len(sys.argv) == 1:
        results = calculate_all()
        print_summary(results)
    
    elif '--summary' in sys.argv:
        results = calculate_all()
        print_summary(results)
    
    elif '--base' in sys.argv:
        idx = sys.argv.index('--base')
        base = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 100000
        results = calculate_all(base)
        print_summary(results)
    
    else:
        code = sys.argv[1]
        base = 100000
        if '--base' in sys.argv:
            idx = sys.argv.index('--base')
            base = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 100000
        
        result = calculate_position(code, base)
        if result:
            print(f"\n{'='*60}")
            print(f"【{result['code']}】{result['name']}")
            print(f"{'='*60}")
            print(f"  現價: {result['price']:,.0f}")
            print(f"  RSI: {result['rsi']}")
            print(f"  仓位權重: {result['weight']:.1f}x")
            print(f"  投入金額: {result['invest_amount']:,.0f}")
            print(f"  買入股數: {result['shares']}")
            print(f"  停利: {result['tp_pct']:.0f}% = {result['expected_return']:,.0f}")
            print(f"  停損: {result['sl_pct']:.0f}% = {result['expected_loss']:,.0f}")
            print(f"  建議: {result['action']}")
            print(f"{'='*60}")
        else:
            print("❌ 無法取得資料")


if __name__ == '__main__':
    main()
