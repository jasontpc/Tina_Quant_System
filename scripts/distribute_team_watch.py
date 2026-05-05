# -*- coding: utf-8 -*-
"""
Tina Brain - 團隊觀察名單分配
=============================
根據 Jo 的指示，將熱門產業候選分配給各團隊
"""
import json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

# 團隊職責對照
TEAM_SCOPE = {
    'NANA': '波段操作（個股），RSI<35+MA多头',
    'LEO': 'AI科技股波段，MA60>MA20+RSI<35+法人',
    'MAGGY': '美股AI，MA多头+RSI 40-50+社群觀察',
    'SHERKY': 'ETF DCA，RSI<40+yield',
}

# 觀察名單分配
WATCH_LIST = {
    'NANA 波段': [
        {'symbol': '2464.TW', 'name': '盟立', 'price': 114, 'score': 50, 'rsi': 78.2, 'reason': '機器人/具身智能，MACD多頭，量能1.9x'},
        {'symbol': '3037.TW', 'name': '欣興', 'price': 883, 'score': 50, 'rsi': 80.0, 'reason': 'PCB/載板，MACD多頭，量能1.5x'},
        {'symbol': '3324.TWO', 'name': '雙鴻', 'price': 1140, 'score': 45, 'rsi': 59.3, 'reason': '散熱/液冷，MACD多頭，MA20多頭'},
    ],
    'LEO AI科技': [
        {'symbol': '2359.TW', 'name': '所羅門', 'price': 119, 'score': 60, 'rsi': 59.5, 'reason': '機器人/具身智能，量能3.9x，MACD多頭，Score 60最強'},
        {'symbol': '2467.TW', 'name': '志聖', 'price': 609, 'score': 50, 'rsi': 69.5, 'reason': '先進封裝設備，MACD多頭，量能1.8x'},
        {'symbol': '8299.TW', 'name': '群聯', 'price': 1900, 'score': 60, 'rsi': 59.2, 'reason': 'HBM/存儲控制，MACD多頭，Score 60'},
        {'symbol': '4966.TWO', 'name': '譜瑞-KY', 'price': 575, 'score': 45, 'rsi': 58.8, 'reason': '高速傳輸/CPO，Edge AI，MACD多頭'},
    ],
    'MAGGY 美股AI': [
        {'symbol': 'MSFT', 'name': 'Microsoft', 'price': 414, 'score': 45, 'rsi': 56.6, 'reason': 'AI平台/軟體，MACD多頭，MA20多頭'},
        {'symbol': 'CRM', 'name': 'Salesforce', 'price': 184, 'score': 45, 'rsi': 56.2, 'reason': 'AI Agent平台，MACD多頭'},
    ],
    'SHERKY ETF/能源': [
        {'symbol': '1519.TW', 'name': '華城', 'price': 888, 'score': 45, 'rsi': 59.4, 'reason': '智慧能源/變壓器，MACD多頭，MA20多頭'},
    ],
}

# 未分類的補充觀察
SUPPLEMENT = [
    {'symbol': '5269.TW', 'name': '祥碩', 'price': 1365, 'score': 50, 'rsi': 69.9, 'reason': 'Edge AI，MACD多頭，等RSI回調'},
    {'symbol': '1590.TW', 'name': '亞德客-KY', 'price': 1455, 'score': 50, 'rsi': 75.3, 'reason': '機器人，MACD多頭，量能1.8x，等RSI回調'},
]


def main():
    print('='*60)
    print('  Tina Brain - 團隊觀察名單分配')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)
    print()

    for team, stocks in WATCH_LIST.items():
        print(f'【{team}】')
        for s in stocks:
            print(f"  {s['symbol']} {s['name']:<8} ${s['price']:>6} | RSI {s['rsi']:>5.1f} | Score {s['score']} | {s['reason']}")
        print()

    print(f"【補充觀察（待分類）】")
    for s in SUPPLEMENT:
        print(f"  {s['symbol']} {s['name']:<8} ${s['price']:>6} | RSI {s['rsi']:>5.1f} | Score {s['score']} | {s['reason']}")

    # Write to file
    out = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'teams': WATCH_LIST,
        'supplement': SUPPLEMENT
    }
    out_path = WORKSPACE / 'data' / 'team_watch_list.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print()
    print('='*60)
    print(f'  已寫入: {out_path}')
    print(f'  分配: {len(WATCH_LIST)} 團隊 / {sum(len(v) for v in WATCH_LIST.values())} 檔 / {len(SUPPLEMENT)} 檔補充')
    print('='*60)
    print()
    print('【團隊職責摘要】')
    for team, scope in TEAM_SCOPE.items():
        count = len(WATCH_LIST.get(team.split()[0] + ' ' + team.split()[1], [])) if len(team.split()) > 1 else 0
        print(f"  {team}: {scope}")


if __name__ == '__main__':
    main()