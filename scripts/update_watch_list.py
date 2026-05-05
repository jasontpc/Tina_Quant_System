# -*- coding: utf-8 -*-
"""
Tina Brain - 團隊觀察名單更新
=============================
根據 AI 基礎建設分析，將超門檻股票納入持續追蹤
"""
import json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

# 已分配的觀察名單（來自 team_watch_list.json）
EXISTING = {
    'LEO AI科技': ['2359.TW', '8299.TW', '2467.TW', '4966.TWO'],
    'NANA 波段': ['2464.TW', '3037.TW', '3324.TWO'],
    'MAGGY 美股AI': ['MSFT', 'CRM'],
    'SHERKY': ['1519.TW'],
}

# AI 基礎建設 Score >= 45 未分配的新股票
NEW_CANDIDATES = [
    {'symbol': '3711.TW', 'name': '日月光投控', 'score': 50, 'rsi': 72.9, 'reason': '先進封裝，MACD多頭，等RSI回調'},
    {'symbol': '5269.TW', 'name': '祥碩', 'score': 50, 'rsi': 69.9, 'reason': 'Edge AI，MACD多頭，等RSI回調'},
    {'symbol': '1590.TW', 'name': '亞德客-KY', 'score': 50, 'rsi': 75.3, 'reason': '機器人，MACD多頭，量能1.8x，等RSI回調'},
    {'symbol': '2464.TW', 'name': '盟立', 'score': 50, 'rsi': 78.2, 'reason': '機器人，MACD多頭，量能1.9x，等RSI回調'},
    {'symbol': '4966.TWO', 'name': '譜瑞-KY', 'score': 45, 'rsi': 58.8, 'reason': '高速傳輸/CPO，Edge AI，MACD多頭'},
    {'symbol': '3324.TWO', 'name': '雙鴻', 'score': 45, 'rsi': 59.3, 'reason': '散熱/液冷，MACD多頭，MA20多頭'},
    {'symbol': '3037.TW', 'name': '欣興', 'score': 50, 'rsi': 80.0, 'reason': 'PCB/載板，MACD多頭，量能1.5x，等RSI回調'},
    {'symbol': '1519.TW', 'name': '華城', 'score': 45, 'rsi': 59.4, 'reason': '智慧能源/變壓器，MACD多頭'},
]

# 分配到團隊
ASSIGN = {
    'LEO AI科技': ['3711.TW', '5269.TW'],
    'NANA 波段': ['1590.TW'],
    'MAGGY 美股AI': [],  # 已有 MSFT/CRM
    'SHERKY': [],  # 已有 1519.TW
}


def main():
    print('='*60)
    print('  Tina Brain - 持續追蹤名單更新')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)
    print()

    # Build complete watch list
    complete = {}
    for team, syms in ASSIGN.items():
        existing = EXISTING.get(team, [])
        new_syms = syms
        all_syms = list(set(existing + new_syms))
        complete[team] = all_syms
        print(f'【{team}】{len(all_syms)} 檔')
        for s in all_syms:
            info = next((x for x in NEW_CANDIDATES if x['symbol'] == s), None)
            if info:
                print(f"  → {s} {info['name']:<8} Score:{info['score']} RSI:{info['rsi']:.1f} {info['reason']}")
            elif s == '2359.TW':
                print(f"  → {s} 所羅門    Score:60 RSI:59.5 機器人/具身智能，量能3.9x")
            elif s == '8299.TW':
                print(f"  → {s} 群聯      Score:60 RSI:59.2 HBM/存儲控制，MACD多頭")
            elif s == '2467.TW':
                print(f"  → {s} 志聖      Score:50 RSI:69.5 先進封裝設備，MACD多頭")
            elif s == 'MSFT':
                print(f"  → {s} Microsoft Score:45 RSI:56.6 AI平台，MACD多頭")
            elif s == 'CRM':
                print(f"  → {s} Salesforce Score:45 RSI:56.2 AI Agent平台")
            elif s == '1519.TW':
                print(f"  → {s} 華城      Score:45 RSI:59.4 智慧能源/變壓器")
        print()

    # Summary stats
    total = sum(len(v) for v in complete.values())
    print('【持續追蹤統計】')
    for team, syms in complete.items():
        print(f'  {team}: {len(syms)} 檔')
    print(f'  總計: {total} 檔')

    # Write to file
    out = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'complete_watch': complete,
        'all_symbols': list(set(sum(complete.values(), [])))
    }
    out_path = WORKSPACE / 'data' / 'team_watch_list.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print()
    print(f'已寫入: {out_path}')


if __name__ == '__main__':
    main()