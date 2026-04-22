"""
v3.14 系統 - 升級版參數
基於 v3.12 + 優化分析結果

升級內容:
- Score: 72 → 75
- RSI: 78 → 75  
- 持有天數: 5天 → 4天
- MA20 市場濾鏡: 加入

預期勝率: 73-75% (原本 67.8%)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

# === v3.14 核心參數 ===
VERSION = 'v3.14'
VERSION_NOTES = '升級版 - 優化分析後調整'

# 評分參數
PARAMS = {
    # 進場閾值
    'score_threshold': 75,      # 原本 72 → 75
    'rsi_threshold': 75,        # 原本 78 → 75
    'atr_threshold': 30,         # 維持不變
    
    # 持有設定
    'hold_days': 4,             # 原本 5 → 4
    
    # 市場濾鏡
    'use_market_filter': True,  # 新增: 僅在 0050 > MA20 時進場
    'market_etf': '0050.TW',
    
    # 停損停利
    'stop_loss_atr': 2.0,       # ATR 2x 停損
    'trailing_stop': 'MA20',    # 跌破 MA20 全出
    
    # 黑名單
    'blacklist': ['1590', '2308'],  # 維持不變
    
    # 交易成本
    'transaction_cost': 0.0045,  # 0.45%
}

# RSI 評分
RSI_SCORE = {
    range(50, 71): 15,   # 50-70: 15分
    range(30, 50): 10,    # 30-50: 10分
    else: 5                # 其他: 5分
}

# VIF 評分
VIF_SCORE = {
    '>=2.5': 15,
    '>=2.0': 10,
    '>=1.5': 5,
    '<1.5': 0
}

# 偏離度評分
BIAS_SCORE = {
    '<=3%': 15,
    '<=6%': 10,
    '>6%': 5
}

def calc_score(rsi, vif, bias):
    """計算總分"""
    # RSI 分數
    if 50 <= rsi <= 70:
        rs = 15
    elif 30 <= rsi < 50:
        rs = 10
    else:
        rs = 5
    
    # VIF 分數 (法人籌碼 65分)
    if vif >= 2.5:
        vs = 25
    elif vif >= 2.0:
        vs = 20
    elif vif >= 1.5:
        vs = 15
    else:
        vs = 0
    
    # 偏離度分數 (15分)
    abs_bias = abs(bias)
    if abs_bias <= 3:
        bs = 15
    elif abs_bias <= 6:
        bs = 10
    else:
        bs = 5
    
    return rs + vs + bs + 65  # 法人基礎 65分

def check_entry_conditions(score, rsi, atr, price, ma20, market_above_ma20=True):
    """檢查進場條件"""
    # 基本條件
    if score < PARAMS['score_threshold']:
        return False, f"Score {score} < {PARAMS['score_threshold']}"
    if rsi >= PARAMS['rsi_threshold']:
        return False, f"RSI {rsi} >= {PARAMS['rsi_threshold']}"
    if atr < PARAMS['atr_threshold']:
        return False, f"ATR {atr} < {PARAMS['atr_threshold']}"
    if price <= ma20:
        return False, "Price <= MA20"
    
    # 市場濾鏡
    if PARAMS['use_market_filter'] and not market_above_ma20:
        return False, "Market below MA20"
    
    return True, "OK"

def check_exit_conditions(price, ma20, entry_price, atr, hold_days_elapsed):
    """檢查出場條件"""
    # MA20 停損
    if price <= ma20:
        return True, "MA20 trailing stop"
    
    # ATR 停損
    if entry_price > 0:
        loss_pct = (entry_price - price) / entry_price * 100
        if loss_pct >= atr * PARAMS['stop_loss_atr']:
            return True, f"ATR stop loss ({loss_pct:.1f}%)"
    
    # 持有天數到期
    if hold_days_elapsed >= PARAMS['hold_days']:
        return True, f"Hold days ({PARAMS['hold_days']}) reached"
    
    return False, "Hold"

# 版本資訊
if __name__ == '__main__':
    print("=" * 60)
    print(f" {VERSION} 系統參數")
    print("=" * 60)
    print()
    for key, value in PARAMS.items():
        print(f"  {key}: {value}")
    print()
    print("  預期勝率: 73-75%")
    print("=" * 60)
