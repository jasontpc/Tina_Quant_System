# -*- coding: utf-8 -*-
"""
Tina Brain - 新團隊開發專案規劃系統 v1.0
======================================
為 GUARD、AION、FINMAX 制定開發計劃、自動化排程、學習腳本
"""
import sqlite3, json, sys, subprocess
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"


# ============================================================
# 新團隊開發專案
# ============================================================
TEAM_PROJECTS = {
    'GUARD': {
        'name': 'GUARD 軍工/國防團隊',
        'focus': '國防預算 + 地緣政治避險',
        'core_stocks': ['2634.TW', '2313.TW'],
        'expand_stocks': [
            '2644.TW',  # 景碩（航太）
            '1605.TW',  # 中環（國艦）
            '2013.TW',  # 燁輝（鋼鐵）
        ],
        'key_metrics': ['RSI', 'MACD', 'Sector_RSI', 'TWII_Corr'],
        'cron_schedule': '0 9,15 * * 1-5',
        'strategy': 'RSI 30-55 + 地緣政治事件觸發',
        'notes': '台灣國防預算成長明確，漢翔、拓凱、長榮航太受惠'
    },
    'AION': {
        'name': 'AION 新能源車團隊',
        'focus': '電車供應鏈 + 售後服務',
        'core_stocks': ['2201.TW', '2207.TW'],
        'expand_stocks': [
            '1536.TW',  # 和大
            '2236.TW',  # 敬鵬
            '2347.TW',  # 聯強
        ],
        'key_metrics': ['RSI', 'EV_Sales', 'Battery_Cost', 'Charging_Station'],
        'cron_schedule': '0 10,16 * * 1-5',
        'strategy': '電車滲透率 + RSI 30-50 進場',
        'notes': '全球電車滲透率目標 30%，台灣供應鏈切入美國市場'
    },
    'FINMAX': {
        'name': 'FINMAX 金融/金控團隊',
        'focus': '降息循環 + 金控利差修復',
        'core_stocks': ['2881.TW', '2882.TW', '2883.TW', '2884.TW', '2885.TW', '2891.TW', '2892.TW'],
        'expand_stocks': [
            '5871.TW',  # 中租
            '2890.TW',  # 新光金
            '2886.TW',  # 兆豐金
            '2887.TW',  # 台新金
        ],
        'key_metrics': ['RSI', 'NIM', 'Bond_Yield', 'Interest_Rate'],
        'cron_schedule': '0 11,17 * * 1-5',
        'strategy': 'RSI 35-55 + 降息預期佈局',
        'notes': 'Fed 降息循環啟動，金融股估值修復'
    }
}


# ============================================================
# 學習腳本開發清單
# ============================================================
LEARNING_SCRIPTS = {
    'guard_market_scanner.py': {
        'team': 'GUARD',
        'purpose': '軍工國防市場動態掃描',
        'trigger': '地緣政治事件（中共軍演、美軍售台）',
        'indicators': ['RSI', 'Volume', 'Sector_Breadth', 'TWII'],
        'schedule': 'event-driven + daily 9:00'
    },
    'aion_penetration_tracker.py': {
        'team': 'AION',
        'purpose': '電車滲透率追蹤',
        'trigger': '電車銷售數據發布',
        'indicators': ['Monthly_Sales', 'Market_Share', 'Charging_Infrastructure'],
        'schedule': 'monthly + weekly'
    },
    'finmax_rate_monitor.py': {
        'team': 'FINMAX',
        'purpose': '利率/債券殖利率監控',
        'trigger': 'Fed 利率決策',
        'indicators': ['US10Y', 'Taiwan_Bond_Yield', 'Interest_Rate_Differential'],
        'schedule': 'daily 8:00 + event-driven'
    },
    'guard_learning_engine.py': {
        'team': 'GUARD',
        'purpose': 'GUARD 專屬學習引擎（與 tina_team_learning 整合）',
        'indicators': ['RSI', 'MACD', 'Volume', 'TWII_Corr'],
        'schedule': 'weekly Sunday 09:00'
    },
    'aion_learning_engine.py': {
        'team': 'AION',
        'purpose': 'AION 專屬學習引擎',
        'indicators': ['RSI', 'EV_Index', 'MACD', 'Volume'],
        'schedule': 'weekly Sunday 09:00'
    },
    'finmax_learning_engine.py': {
        'team': 'FINMAX',
        'purpose': 'FINMAX 專屬學習引擎',
        'indicators': ['RSI', 'Bond_Yield', 'NIM', 'MACD'],
        'schedule': 'weekly Sunday 09:00'
    },
}


# ============================================================
# 大腦建議項目（待開發）
# ============================================================
BRAIN_RECOMMENDATIONS = {
    'HIGH_PRIORITY': [
        {
            'id': 'BR-001',
            'project': 'GUARD 情資觸發系統',
            'reason': '軍工股受地緣政治影響大，需事件驅動',
            'action': '建立 news_sentiment.py 的軍工板塊事件觸發模組',
            'impact': 'High - 可提前 1-3 天捕捉軍工行情',
            'effort': 'MED'
        },
        {
            'id': 'BR-002',
            'project': 'AION 電車滲透率儀表板',
            'reason': '電車數據落後，需追蹤全球數據',
            'action': '串接全球電車銷售數據 API',
            'impact': 'High - 領先指標',
            'effort': 'HIGH'
        },
        {
            'id': 'BR-003',
            'project': 'FINMAX 利率決策日誌',
            'reason': 'Fed 利率影響金控股價最深',
            'action': '建立 Fed Rate Decision Logger',
            'impact': 'High - 掌握利率拐點',
            'effort': 'LOW'
        },
    ],
    'MED_PRIORITY': [
        {
            'id': 'BR-004',
            'project': '全團隊績效追蹤儀表板',
            'reason': '需要統一視覺化所有團隊表現',
            'action': '建立 dashboard.py 輸出 PNG 圖表',
            'impact': 'MED',
            'effort': 'MED'
        },
        {
            'id': 'BR-005',
            'project': '跨團隊相關性分析',
            'reason': '發現 AION/FINMAX 可能與 LEO 有關聯',
            'action': '建立 correlation_matrix.py',
            'impact': 'MED',
            'effort': 'LOW'
        },
        {
            'id': 'BR-006',
            'project': '記憶體景氣循環指標',
            'reason': 'DRAM 景氣落後 AI 需求，需提前佈局',
            'action': '建立 DRAM cycle indicator',
            'impact': 'High',
            'effort': 'MED'
        },
    ],
    'LOW_PRIORITY': [
        {
            'id': 'BR-007',
            'project': '社群情緒軍工關鍵字',
            'reason': 'PTT/Reddit 軍工討論度領先股價',
            'action': '建立 guard_sentiment_tracker.py',
            'impact': 'LOW',
            'effort': 'MED'
        },
    ]
}


# ============================================================
# 排程建議
# ============================================================
CRON_RECOMMENDATIONS = [
    {
        'name': 'GUARD 軍工每日追蹤',
        'schedule': '0 9,15 * * 1-5',
        'script': 'scripts/guard_market_scanner.py',
        'timeout': 60,
        'priority': 'HIGH',
        'status': 'pending'
    },
    {
        'name': 'AION 新能源車每週學習',
        'schedule': '0 10 * * 1',  # 週一 10:00
        'script': 'scripts/aion_learning_engine.py',
        'timeout': 120,
        'priority': 'HIGH',
        'status': 'pending'
    },
    {
        'name': 'FINMAX 金融利率每日監控',
        'schedule': '0 8 * * 1-5',  # 每日 8:00
        'script': 'scripts/finmax_rate_monitor.py',
        'timeout': 60,
        'priority': 'HIGH',
        'status': 'pending'
    },
    {
        'name': 'GUARD 每週學習回測',
        'schedule': '0 9 * * 0',  # 週日 09:00
        'script': 'scripts/guard_learning_engine.py',
        'timeout': 180,
        'priority': 'MED',
        'status': 'pending'
    },
    {
        'name': 'FINMAX 每週學習回測',
        'schedule': '0 10 * * 0',  # 週日 10:00
        'script': 'scripts/finmax_learning_engine.py',
        'timeout': 180,
        'priority': 'MED',
        'status': 'pending'
    },
]


# ============================================================
# 主程式
# ============================================================
def main():
    print('='*70)
    print('  Tina Brain - 新團隊開發規劃系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    # 1. 新團隊開發專案
    print('\n【1/4】新團隊開發專案')
    for team_id, proj in TEAM_PROJECTS.items():
        print(f"\n  【{team_id}】{proj['name']}")
        print(f"    核心: {proj['core_stocks']}")
        print(f"    擴展: {proj['expand_stocks']}")
        print(f"    策略: {proj['strategy']}")
        print(f"    排程: {proj['cron_schedule']}")
        print(f"    備註: {proj['notes']}")

    # 2. 學習腳本清單
    print('\n【2/4】學習腳本開發清單')
    for script, info in LEARNING_SCRIPTS.items():
        print(f"\n  {script}")
        print(f"    團隊: {info['team']}")
        print(f"    目的: {info['purpose']}")
        print(f"    觸發: {info.get('trigger', 'daily')}")
        print(f"    排程: {info['schedule']}")

    # 3. 大腦建議項目
    print('\n【3/4】大腦建議項目（待開發）')
    for priority, items in BRAIN_RECOMMENDATIONS.items():
        icon = {'HIGH_PRIORITY': '🔴', 'MED_PRIORITY': '🟡', 'LOW_PRIORITY': '🟢'}[priority]
        print(f"\n  {icon} {priority}:")
        for item in items:
            print(f"    {item['id']} {item['project']}")
            print(f"       影響: {item['impact']} | 工作量: {item['effort']}")
            print(f"       行動: {item['action']}")

    # 4. 排程建議
    print('\n【4/4】自動化排程建議')
    for cron in CRON_RECOMMENDATIONS:
        status_icon = '⏳' if cron['status'] == 'pending' else '✅'
        print(f"\n  {status_icon} {cron['name']}")
        print(f"     排程: {cron['schedule']}")
        print(f"     腳本: {cron['script']}")
        print(f"     超時: {cron['timeout']}s | 優先: {cron['priority']}")

    # 寫入建議檔案
    plan = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'projects': TEAM_PROJECTS,
        'learning_scripts': LEARNING_SCRIPTS,
        'recommendations': BRAIN_RECOMMENDATIONS,
        'cron_plans': CRON_RECOMMENDATIONS,
    }

    with open(DATA / 'team_dev_plan.json', 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\n  → 計劃已寫入: data/team_dev_plan.json")
    print('\n' + '='*70)
    print('  請告訴 Tina 要先開發哪一個項目？')
    print('='*70)


if __name__ == '__main__':
    main()