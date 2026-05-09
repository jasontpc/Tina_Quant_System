# -*- coding: utf-8 -*-
"""
Leo 個股參數 v3.0 — 修正 v2.0 邏輯錯誤
根據失敗數據庫：RSI <35 失敗率高 → 提高門檻到 40-45
"""
import json
import os

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
PARAMS_FILE = os.path.join(BASE_DIR, 'leo_per_stock_params.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'leo_per_stock_params_v3.json')

# === v3.0 修正邏輯 ===
# 失敗數據顯示：RSI <35 進場平均虧損 -11.1%
# 正確邏輯：提高進場RSI下限，避免低RSI進場
V3_ADJUSTMENTS = {
    '2330': {
        'rsi_threshold': 40,    # v2.0: 35 → v3.0: 40（提高）
        'rsi_threshold_max': 50,
        'stop_loss': 6,        # 維持6%
        'hold_days_min': 14,
        'weight': 1.0,
    },
    '2382': {
        'rsi_threshold': 40,    # 維持
        'rsi_threshold_max': 55,
        'stop_loss': 6,
        'hold_days_min': 14,
        'weight': 1.0,
    },
    '3665': {
        'rsi_threshold': 45,    # 維持
        'rsi_threshold_max': 55,
        'stop_loss': 6,
        'hold_days_min': 21,
        'weight': 0.5,
    },
    '2317': {
        'rsi_threshold': 45,    # 維持
        'rsi_threshold_max': 55,
        'stop_loss': 8,
        'hold_days_min': 21,
        'weight': 1.0,
    },
    '3034': {
        'rsi_threshold': 40,    # v2.0: 35 → v3.0: 40（提高）
        'rsi_threshold_max': 55,
        'stop_loss': 8,
        'hold_days_min': 14,
        'weight': 1.5,
    },
}

STOCK_NAMES = {'2330': '台積電', '2382': '廣達', '3665': '穎崴', '2317': '鴻海', '3034': '緯穎'}

def apply_v3():
    with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
        original = json.load(f)

    print("=" * 60)
    print("Leo 個股參數 v3.0 — 修正邏輯錯誤")
    print("=" * 60)
    print("修正原則：RSI <35 失敗率高 → 提高進場RSI下限")
    print()

    v3_data = {
        'date': '2026-04-27 06:16',
        'version': 'v3.0',
        'stocks': {}
    }

    for ticker, name in STOCK_NAMES.items():
        orig = original['stocks'][ticker]['params']
        adj = V3_ADJUSTMENTS[ticker]

        print(f"{ticker} {name}")
        print(f"  進場RSI: {orig['rsi_threshold']} → {adj['rsi_threshold']} (max {adj['rsi_threshold_max']})")
        print(f"  停損: {orig['stop_loss']}% → {adj['stop_loss']}%")
        print(f"  倉位權重: {adj['weight']}x")

        v3_data['stocks'][ticker] = {
            'name': name,
            'v1_params': orig,
            'v3_params': adj,
            'v2_flaw': f"v2.0 RSI threshold=35 導致低RSI進場失敗",
        }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(v3_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ v3.0 參數已存: {OUTPUT_FILE}")
    return v3_data


if __name__ == '__main__':
    apply_v3()