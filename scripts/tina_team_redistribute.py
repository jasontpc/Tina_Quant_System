# -*- coding: utf-8 -*-
"""
Tina Brain - 新團隊建立與分配
===========================
1. LEO 科技股團隊：加入記憶體/DRAM、半導體設備
2. 新增3個團隊：新能源車、軍工/國防、金融/金控
"""
import json
from pathlib import Path

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

# 更新後的團隊定義
TEAMS = {
    'LEO': {
        'name': 'LEO AI科技波段團隊（擴展版）',
        'strategy': 'AI 供應鏈主軸（算力+封裝+存儲+設備）',
        'rsi_min': 25, 'rsi_max': 40,
        'macd_min': 0,
        'filter': 'vol_1.5x',
        'watch': [
            '3711.TW', '8299.TW', '2467.TW', '5269.TW', '2359.TW', '4966.TWO',
            # 新增：記憶體/DRAM
            '2408.TW', '2344.TW',
            # 新增：半導體設備
            '7730.TW',
        ],
        'notes': '擴展至記憶體/DRAM + 半導體設備'
    },
    'NANA': {
        'name': 'NANA 波段操作團隊',
        'strategy': 'RSI 35-50 + MA20>MA60 多頭排列',
        'rsi_min': 35, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['2464.TW', '3324.TWO', '3037.TW', '1590.TW'],
    },
    'MAGGY': {
        'name': 'MAGGY 美股AI團隊',
        'strategy': 'MACD 金叉 + MA多頭排列（趨勢跟隨）',
        'rsi_min': 0, 'rsi_max': 999,
        'macd_min': 0,
        'macd_cross': True,
        'filter': 'ma20_above_ma60',
        'watch': ['MSFT', 'CRM'],
    },
    'SHERKY': {
        'name': 'SHERKY ETF/能源團隊',
        'strategy': 'RSI<45 + 高殖利率 + 電力基建',
        'rsi_min': 0, 'rsi_max': 45,
        'macd_min': 0,
        'filter': 'none',
        'watch': ['1519.TW'],
    },
    'AION': {
        'name': 'AION 新能源車/電車團隊',
        'strategy': '電車供應鏈 + 售後服務波段操作',
        'rsi_min': 30, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': [
            '2201.TW',  # 和大（電車減速齒輪）
            '2207.TW',  # 裕日車（經銷商）
        ],
        'notes': 'NEW TEAM - 新能源車供應鏈主軸'
    },
    'GUARD': {
        'name': 'GUARD 軍工/國防團隊',
        'strategy': '國防預算成長 + 地緣政治避險',
        'rsi_min': 30, 'rsi_max': 55,
        'macd_min': 0,
        'filter': 'none',
        'watch': [
            '2634.TW',  # 漢翔（航太零組件）
            '2313.TW',  # 拓凱（複材）
        ],
        'notes': 'NEW TEAM - 軍工/國防主軸'
    },
    'FINMAX': {
        'name': 'FINMAX 金融/金控團隊',
        'strategy': '降息前佈局金融股波段操作',
        'rsi_min': 35, 'rsi_max': 55,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': [
            '2881.TW',  # 富邦金
            '2882.TW',  # 國泰金
            '2883.TW',  # 華南金
            '2884.TW',  # 玉山金
            '2885.TW',  # 開發金
            '2891.TW',  # 第一金
            '2892.TW',  # 中信金
        ],
        'notes': 'NEW TEAM - 金融/金控波段操作'
    },
}


def main():
    print('='*60)
    print('  Tina Brain - 團隊重新分配')
    print('='*60)

    # 1. 更新 team_watch_list.json
    watch_data = {
        'updated': '2026-05-03',
        'updated_by': 'tina_team_redistribute.py',
        'complete_watch': {},
        'all_symbols': [],
    }

    for team, cfg in TEAMS.items():
        watch_data['complete_watch'][team] = cfg['watch']
        watch_data['all_symbols'].extend(cfg['watch'])
        print(f"\n【{team}】{cfg['name']}")
        print(f"  策略: {cfg['strategy']}")
        print(f"  觀察: {cfg['watch']}")

    watch_data['all_symbols'] = list(set(watch_data['all_symbols']))

    with open(DATA / 'team_watch_list.json', 'w', encoding='utf-8') as f:
        json.dump(watch_data, f, ensure_ascii=False, indent=2)

    print(f"\n  → 已寫入: data/team_watch_list.json")
    print(f"\n  總觀察符號: {len(watch_data['all_symbols'])}")

    # 2. 更新 team_learning_results.json 結構（容納新團隊）
    empty_results = {
        'date': '2026-05-03',
        'teams': {team: {'stocks': [], 'strategy': cfg['strategy']} for team, cfg in TEAMS.items()}
    }

    with open(DATA / 'team_learning_results.json', 'w', encoding='utf-8') as f:
        json.dump(empty_results, f, ensure_ascii=False, indent=2)

    print(f"  → 已重置: data/team_learning_results.json")
    print(f"\n  新團隊總數: {len(TEAMS)}")
    print(f"  LEO 擴展: +3 檔（記憶體+設備）")
    print(f"  AION 新增: 2 檔（新能源車）")
    print(f"  GUARD 新增: 2 檔（軍工/國防）")
    print(f"  FINMAX 新增: 7 檔（金融/金控）")


if __name__ == '__main__':
    main()