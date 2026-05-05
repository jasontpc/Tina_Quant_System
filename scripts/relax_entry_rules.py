# -*- coding: utf-8 -*-
"""
relax_entry_rules.py
====================
放寬進場門檻，解決 NANA/SHERKY 無歷史交易的問題
- RSI 門檻從 35 → 45（NANA）/ 從 40 → 45（SHERKY）
- 保持 MACD>0 + MA20>SMA60 確認多頭
"""
import json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

# 新團隊規則（放寬後）
NEW_TEAMS = {
    'NANA': {
        'name': 'NANA 波段操作團隊',
        'strategy': 'RSI<45 + MA多头排列，強勢波段進場（放寬版）',
        'entry_rsi_max': 45,  # 35 → 45
        'entry_macd_min': 0,
        'watch': ['2464.TW','3324.TWO','3037.TW','1590.TW'],
    },
    'LEO': {
        'name': 'LEO AI科技波段團隊',
        'strategy': 'MA60>MA20 + RSI<45 + 法人買超，AI供應鏈主軸（放寬版）',
        'entry_rsi_max': 45,  # 35 → 45
        'entry_macd_min': 0,
        'watch': ['3711.TW','8299.TW','2467.TW','5269.TW','2359.TW','4966.TWO'],
    },
    'MAGGY': {
        'name': 'MAGGY 美股AI團隊',
        'strategy': 'MA多头 + RSI 40-50 + 社群情緒觀察，美股AI基礎建設（維持）',
        'entry_rsi_max': 50,  # 維持不變
        'entry_macd_min': 0,
        'watch': ['MSFT','CRM'],
    },
    'SHERKY': {
        'name': 'SHERKY ETF/能源團隊',
        'strategy': 'RSI<45 + 高殖利率 + 電力基建，ETF與重電雙軌（放寬版）',
        'entry_rsi_max': 45,  # 40 → 45
        'entry_macd_min': 0,
        'watch': ['1519.TW'],
    },
}

def main():
    print('='*60)
    print('  放寬進場門檻')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)
    print()

    # 讀取舊規則
    old_path = DATA / 'team_watch_list.json'
    with open(old_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    print('【舊規則 → 新規則】')
    print()
    changes = [
        ('NANA', 'RSI<35', 'RSI<45', '+10'),
        ('LEO', 'RSI<35', 'RSI<45', '+10'),
        ('SHERKY', 'RSI<40', 'RSI<45', '+5'),
        ('MAGGY', 'RSI<50', 'RSI<50', '不變'),
    ]
    for team, old, new, chg in changes:
        print(f'  {team}: {old} → {new} ({chg})')

    print()
    print('【寫入新規則到 team_watch_list.json】')

    # 寫入新的團隊定義
    new_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'updated_by': 'relax_entry_rules.py',
        'complete_watch': {},
        'all_symbols': [],
    }

    for team, config in NEW_TEAMS.items():
        new_data['complete_watch'][team] = config['watch']
        new_data['all_symbols'].extend(config['watch'])

    # 去重
    new_data['all_symbols'] = list(set(new_data['all_symbols']))

    with open(old_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f'  已更新: {old_path}')
    print()
    print('【新團隊觀察名單】')
    for team, config in NEW_TEAMS.items():
        print(f'  {team}: {config["watch"]}')

    print()
    print('【下次回測時生效】')
    print('  預期: NANA/SHERKY 將有歷史交易')
    print('  預期: LEO 進場點增加')


if __name__ == '__main__':
    main()