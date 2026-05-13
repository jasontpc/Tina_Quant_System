# -*- coding: utf-8 -*-
"""
自動套用最佳參數腳本
功能：讀取 best_params.json 並更新 Nana/Leo 系統配置
用法：python apply_best_params.py [nana|leo|all]
"""
import os, json, sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'

def apply_nana_params(params):
    """更新 Nana v6.py 的核心參數"""
    nana_file = os.path.join(BASE_DIR, 'nana', 'nana_v6.py')
    if not os.path.exists(nana_file):
        print(f'找不到 {nana_file}')
        return False

    with open(nana_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新 Entry 參數
    replacements = {
        'ENTRY_RSI_MIN = 40': f'ENTRY_RSI_MIN = {params["rsi_entry_min"]}',
        'ENTRY_RSI_MAX = 55': f'ENTRY_RSI_MAX = {params["rsi_entry_max"]}',
        'ENTRY_SCORE_MIN = 38': f'ENTRY_SCORE_MIN = {params["score_min"]}',
        'ATR_TAKE_PROFIT = 3.0': f'ATR_TAKE_PROFIT = {params["atr_tp_mult"]}',
        'ATR_STOP_LOSS = 1.0': f'ATR_STOP_LOSS = {params["atr_sl_mult"]}',
        'HOLD_DAYS_MAX = 7': f'HOLD_DAYS_MAX = {params["hold_days"]}',
        'TRAILING_ATR = 2.0': f'TRAILING_ATR = {params["trailing_atr"]}',
    }

    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            print(f'  ✅ {old} → {new}')

    with open(nana_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 更新 config
    config_file = os.path.join(BASE_DIR, 'nana', 'nana_v6_config.json')
    config = {
        'timestamp': params.get('timestamp', ''),
        'source': 'backtest_optimizer grid_search',
        'version': '6.3',
        'best_params': params,
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f'  ✅ Config 寫入: {config_file}')

    return True

def apply_leo_params(params):
    """更新 Leo 系統的 ATR 停利/停損參數"""
    leo_file = os.path.join(BASE_DIR, 'leo', 'scripts', 'leo_autonomous_cycle.py')
    if not os.path.exists(leo_file):
        print(f'找不到 {leo_file}')
        return False

    with open(leo_file, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = {
        'TAKE_PROFIT_PCT = 20.0': f'TAKE_PROFIT_PCT = {params["atr_tp_mult"] * 100:.1f}',
        'STOP_LOSS_PCT = 8.0': f'STOP_LOSS_PCT = {params["atr_sl_mult"] * 100:.1f}',
    }

    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            print(f'  ✅ {old} → {new}')

    with open(leo_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 更新 config
    config_file = os.path.join(BASE_DIR, 'leo', 'reports', 'leo_best_params.json')
    config = {
        'timestamp': params.get('timestamp', ''),
        'source': 'backtest_optimizer grid_search',
        'best_params': params,
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f'  ✅ Leo Config 寫入: {config_file}')
    return True

def main():
    team = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if team in ['nana', 'all']:
        params_file = os.path.join(BASE_DIR, 'nana', 'best_params.json')
        if os.path.exists(params_file):
            with open(params_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            params = data.get('best_config', {})
            print('\n套用 Nana 最佳參數:')
            apply_nana_params(params)
        else:
            print('找不到 Nana best_params.json')

    if team in ['leo', 'all']:
        params_file = os.path.join(BASE_DIR, 'leo', 'best_params.json')
        if os.path.exists(params_file):
            with open(params_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            params = data.get('best_config', {})
            print('\n套用 Leo 最佳參數:')
            apply_leo_params(params)
        else:
            print('找不到 Leo best_params.json')

    print('\n✅ 參數套用完成')

if __name__ == '__main__':
    main()
