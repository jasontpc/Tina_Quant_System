# -*- coding: utf-8 -*-
"""
Tina Brain - CPO 散熱產業專屬開發專案規劃
========================================
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB = DATA / "yfinance.db"

# CPO/散熱產業鏈
CPO_CHAIN = {
    '散熱模組': ['6230.TW', '3324.TWO', '6278.TWO', '3653.TW', '6120.TW'],
    '風扇/馬達': ['6592.TW', '6236.TW'],
    'VC/均熱板': ['3711.TW', '6269.TW'],
    '導熱管': ['3017.TW', '2486.TW'],
    '散熱膏/材料': ['3128.TW', '4908.TW'],
    '基板/模造': ['5227.TW', '6109.TW', '6243.TW'],
}

CPO_ALL = [s for stocks in CPO_CHAIN.values() for s in stocks]


# ============================================================
# 開發專案
# ============================================================
CPO_PROJECTS = {
    'CPO_DEDICATED_TEAM': {
        'name': 'CPO 散熱產業專屬團隊',
        'category': '散熱',
        'core_stocks': ['6230.TW', '3324.TWO', '6278.TWO', '3653.TW', '3711.TW'],
        'expand_stocks': ['6120.TW', '6592.TW', '3017.TW', '5227.TW'],
        'strategy': 'RSI 30-50 + MACD>0 + MA多頭 + Vol放量',
        'backtest_period': '90d',
        'notes': 'AI伺服器 HBM 熱密度飆升，散熱需求爆發'
    },
    'CPO_DB_BUILDER': {
        'name': 'CPO 產業資料庫擴充',
        'purpose': '建立 CPO 完整歷史資料',
        'priority': 'HIGH',
        'notes': '補足 CPO 所有個股的 SMA20/SMA60/RSI/MACD'
    },
    'CPO_LEARNING_ENGINE': {
        'name': 'CPO 學習引擎',
        'purpose': 'CPO 專屬回測 + 參數優化',
        'schedule': 'weekly Sunday 10:00',
        'priority': 'HIGH'
    }
}

# ============================================================
# 待建立腳本
# ============================================================
CPO_SCRIPTS = {
    'cpo_sector_analysis.py': {
        'purpose': 'CPO 散熱產業技術面掃描',
        'team': 'CPO',
        'status': '✅ 已建立',
        'schedule': 'daily 09:00 + 14:00'
    },
    'cpo_learning_engine.py': {
        'purpose': 'CPO 專屬學習引擎（與 team_learning 整合）',
        'team': 'CPO',
        'status': '待建立',
        'schedule': 'weekly Sunday 10:00'
    },
    'cpo_db_builder.py': {
        'purpose': 'CPO 個股 yfinance 資料庫建立/更新',
        'team': 'CPO',
        'status': '待建立',
        'schedule': 'weekly'
    },
    'cpo_sentiment_tracker.py': {
        'purpose': 'CPO 社群情緒追蹤（散熱/AI伺服器關鍵字）',
        'team': 'CPO',
        'status': '待建立',
        'schedule': 'daily 07:30'
    },
    'cpo_event_trigger.py': {
        'purpose': 'CPO 事件驅動（GB200出貨、NVIDIA財報、CoWoS產能）',
        'team': 'CPO',
        'status': '待建立',
        'trigger': 'event-driven'
    }
}

# ============================================================
# 數據缺口
# ============================================================
CPO_DATA_GAPS = {
    '3324.TWO': {'in_db': True, 'rows': 60, 'issue': '資料期太短'},
    '6278.TWO': {'in_db': False, 'issue': '完全缺失'},
    '6120.TW': {'in_db': False, 'issue': '完全缺失'},
    '6592.TW': {'in_db': False, 'issue': '完全缺失'},
    '6269.TW': {'in_db': False, 'issue': '完全缺失'},
    '2486.TW': {'in_db': False, 'issue': '完全缺失'},
    '3128.TW': {'in_db': False, 'issue': '完全缺失'},
    '5227.TW': {'in_db': False, 'issue': '完全缺失'},
    '6109.TW': {'in_db': False, 'issue': '完全缺失'},
    '6243.TWO': {'in_db': False, 'issue': '完全缺失'},
}

# ============================================================
# 策略建議
# ============================================================
CPO_STRATEGY = {
    'entry': {
        'rsi_min': 30,
        'rsi_max': 50,
        'macd_positive': True,
        'ma_bull': True,
        'vol_ratio_min': 1.3
    },
    'exit': {
        'take_profit': '3x ATR',
        'stop_loss': '1.5x ATR',
        'max_hold_days': 10
    },
    'position': {
        'max_single': 10,
        'max_total': 40
    },
    'expected_winrate': 65,
    'expected_trades_per_quarter': 8
}


# ============================================================
# 主程式
# ============================================================
def check_db_coverage():
    """檢查 DB 中 CPO 覆蓋"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    results = {}
    for sym in CPO_ALL:
        c.execute("SELECT COUNT(*), MAX(date) FROM daily_ohlcv WHERE symbol=?", (sym,))
        cnt, mx = c.fetchone()
        results[sym] = {'in_db': cnt > 0, 'rows': cnt, 'latest': mx}
    conn.close()
    return results


def main():
    print('='*65)
    print('  Tina Brain - CPO 散熱產業專屬開發專案')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*65)

    db_cov = check_db_coverage()

    # CPO 產業鏈
    print('\n【CPO 散熱產業鏈】')
    for cat, stocks in CPO_CHAIN.items():
        in_db = [s for s in stocks if db_cov.get(s, {}).get('in_db', False)]
        status = '✅' if len(in_db) == len(stocks) else ('⚠️' if in_db else '❌')
        print(f"  {status} {cat}:")
        for s in stocks:
            d = db_cov.get(s, {})
            if d.get('in_db'):
                print(f"      {s}: {d['rows']} rows (最新 {d['latest']})")
            else:
                print(f"      {s}: ❌ 缺失")

    # 待建立腳本
    print('\n【待建立腳本】')
    for script, info in CPO_SCRIPTS.items():
        icon = '✅' if info['status'] == '✅ 已建立' else '⏳'
        print(f"  {icon} {script}")
        print(f"     用途: {info['purpose']}")
        print(f"     排程: {info.get('schedule', info.get('trigger', 'event-driven'))}")

    # 數據缺口
    missing = [s for s, d in CPO_DATA_GAPS.items() if not d.get('in_db', False)]
    print(f'\n【數據缺口】（缺失 {len(missing)} 檔）')
    for sym in missing:
        print(f"  ❌ {sym}")

    # 策略建議
    s = CPO_STRATEGY
    print(f'\n【CPO 策略建議】')
    print(f"  進場: RSI {s['entry']['rsi_min']}-{s['entry']['rsi_max']} + MACD多頭 + MA多頭 + Vol>1.3x")
    print(f"  停利: {s['exit']['take_profit']}")
    print(f"  停損: {s['exit']['stop_loss']}")
    print(f"  預期勝率: {s['expected_winrate']}%")
    print(f"  預期每季交易: {s['expected_trades_per_quarter']} 筆")

    # 寫入計畫
    plan = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'chain': CPO_CHAIN,
        'projects': CPO_PROJECTS,
        'scripts': {k: {kk: vv for kk, vv in v.items() if kk != 'status'} for k, v in CPO_SCRIPTS.items()},
        'strategy': CPO_STRATEGY,
        'data_gaps': CPO_DATA_GAPS,
        'missing_symbols': missing
    }
    with open(DATA / 'cpo_dev_plan.json', 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"\n  → 計劃已寫入: data/cpo_dev_plan.json")


if __name__ == '__main__':
    main()