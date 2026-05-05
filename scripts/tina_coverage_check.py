# -*- coding: utf-8 -*-
"""
Tina Brain - 技能與覆蓋區域全面檢測
====================================
尋找尚未覆蓋的區域、缺口、待優化項目
"""
import sqlite3, json, sys, os
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
SCRIPTS = WORKSPACE / "scripts"

# 已覆蓋的產業/主題
COVERED_AREAS = {
    # TW 產業（已有完整數據）
    '算力核心': ['2330', '3711', '3443'],
    'Edge AI': ['2454', '5269', '4966', '2379', '2458'],
    '機器人/具身AI': ['2359', '2049', '1590', '6188', '2464'],
    '先進封裝': ['3131', '6187', '6640', '2467', '1560'],
    '高速傳輸/CPO': ['2345', '3081', '3363', '3163', '4908', '6442'],
    '散熱/液冷': ['3017', '3324', '3653', '2308', '8996'],
    'PCB/載板': ['2368', '2383', '3037', '3189', '8046'],
    '電力/變壓器': ['1519', '1503', '1513', '1514'],
    'HBM/存儲': ['8299', '3260', '4967', '2408', '2344'],
    '伺服器': ['2382', '3231', '6669', '2356', '2376', '3706'],
    '光通訊': ['2467', '4966', '6187', '3163', '6442'],
    'AI ETF': ['00713', '0050', '0056', '00646', '00662', '00757', '00927'],
    '美股 AI': ['MSFT', 'CRM', 'NVDA', 'AVGO', 'AMD', 'INTC', 'META'],
}

# 尚未覆蓋的重要區域（建議補充）
MISSING_AREAS = {
    '記憶體/DRAM': {
        'reason': 'DRAM 景氣循環落後 AI 需求，重要觀察指標',
        'symbols': ['2408', '2344'],  # 南亞科、華邦電
        'priority': 'HIGH',
        'why': 'AI 伺服器需要大量 HBM，傳統 DRAM 也受益'
    },
    '新能源車供應鏈': {
        'reason': 'TW 新能源車供應鏈落後中國，但有切入機會',
        'symbols': ['2201', '2207', '2230'],  # 和大、裕日車、創
        'priority': 'MED',
        'why': '售後服務/供應鏈受關注'
    },
    '半導體材料/特用化學': {
        'reason': 'CoWoS 先進封裝需要特用化學材料',
        'symbols': ['1723', '4711', '3189'],  # 台特化、三福化、長興
        'priority': 'MED',
        'why': '先進封裝關鍵材料'
    },
    '低軌衛星': {
        'reason': 'Starlink/OneWeb 需求成長，昇通/人體開始佈局',
        'symbols': ['3490', '5388'],  # 昇達科、同欣電
        'priority': 'MED',
        'why': '地緣政治下供應鏈自主需求'
    },
    '化合物半導體': {
        'reason': 'GaN/SiC 應用於電動車、充電樁',
        'symbols': ['第三代半導體：穩懋、全新、兆遠'],
        'priority': 'LOW',
        'why': '需求起飛中但應用場景仍有限'
    },
    '半導體設備/代理': {
        'reason': '半導體在地化趨勢明確，設備需求增加',
        'symbols': ['7730', '6714'],  # 弘塑、志聖
        'priority': 'HIGH',
        'why': 'CoWoS 擴產直接受益'
    },
    '軍工/國防': {
        'reason': '地緣政治緊張，國防預算增加',
        'symbols': ['ROC 軍工股：漢翔、龍躍、拓凱'],
        'priority': 'MED',
        'why': '長線政策紅利'
    },
    '金融/金控': {
        'reason': '升息結束觀察金融股修復',
        'symbols': ['2881', '2882', '2883', '2884', '2885'],  # 富邦、國泰、華南、玉山、開發金
        'priority': 'MED',
        'why': '降息前佈局金融股'
    },
}


def check_db_coverage():
    """檢查 DB 覆蓋範圍"""
    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()

    c.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE symbol LIKE '%.TW' OR symbol LIKE '%.TWO'")
    tw_syms = set([r[0] for r in c.fetchall()])

    c.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%.TWO' AND symbol NOT LIKE '%.HK'")
    us_syms = set([r[0] for r in c.fetchall()])

    conn.close()

    # 統計覆蓋率
    covered_tw = tw_syms.copy()
    for area, syms in COVERED_AREAS.items():
        for s in syms:
            covered_tw.discard(s + '.TW')
            covered_tw.discard(s + '.TWO')

    return {
        'tw_stocks_in_db': len(tw_syms),
        'us_stocks_in_db': len(us_syms),
        'covered_areas': len(COVERED_AREAS),
        'missing_tw_stocks': len(covered_tw),
        'uncovered_list': sorted(covered_tw)[:20]
    }


def check_scripts_coverage():
    """檢查腳本覆蓋範圍"""
    scripts = {}
    for f in SCRIPTS.glob('*.py'):
        if f.stat().st_size < 100:
            continue
        name = f.stem
        scripts[name] = {
            'size': f.stat().st_size,
            'exists': True
        }
    return scripts


def check_missing_sectors():
    """檢查尚未覆蓋的重要區域"""
    missing_info = {}

    for area, info in MISSING_AREAS.items():
        priority_label = {'HIGH': '🔴', 'MED': '🟡', 'LOW': '🟢'}[info['priority']]
        missing_info[area] = {
            'priority': info['priority'],
            'icon': priority_label,
            'reason': info['reason'],
            'why': info['why'],
            'symbols': info['symbols']
        }

    return missing_info


def check_decision_gaps():
    """檢查決策資料庫缺口"""
    try:
        conn = sqlite3.connect(str(DATA / 'tina_decisions.db'))
        c = conn.cursor()

        c.execute("SELECT category, COUNT(*) FROM decisions GROUP BY category")
        by_cat = dict(c.fetchall())

        c.execute("SELECT COUNT(*) FROM decisions WHERE outcome IS NULL OR outcome = 'pending'")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM decisions WHERE score < 5")
        low_score = c.fetchone()[0]

        conn.close()

        return {
            'by_category': by_cat,
            'pending_decisions': pending,
            'low_score_decisions': low_score
        }
    except:
        return {}


def check_team_gaps():
    """檢查團隊覆蓋缺口"""
    teams = {
        'LEO': {'focus': 'AI 科技波段', 'stocks': 6, 'covered': ['5269', '4966', '2359', '3711', '8299', '2467']},
        'NANA': {'focus': '波段操作', 'stocks': 4, 'covered': ['2464', '3324', '3037', '1590']},
        'MAGGY': {'focus': '美股 AI', 'stocks': 2, 'covered': ['MSFT', 'CRM']},
        'SHERKY': {'focus': 'ETF/能源', 'stocks': 1, 'covered': ['1519']},
    }

    # 未分配的產業
    unallocated_sectors = ['記憶體/DRAM', '半導體設備', '新能源車', '低軌衛星', '軍工/國防', '金融/金控']

    return teams, unallocated_sectors


def main():
    print('='*70)
    print('  Tina Brain - 覆蓋區域全面檢測')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    # 1. DB 覆蓋
    print('\n【1/5】資料庫覆蓋範圍')
    db = check_db_coverage()
    print(f"  TW stocks in DB: {db['tw_stocks_in_db']}")
    print(f"  US stocks in DB: {db['us_stocks_in_db']}")
    print(f"  Covered areas: {db['covered_areas']} 個產業")
    print(f"  未覆蓋 TW stocks: {db['missing_tw_stocks']} 檔")

    # 2. 腳本覆蓋
    print('\n【2/5】腳本覆蓋範圍')
    scripts = check_scripts_coverage()
    print(f"  腳本總數: {len(scripts)}")

    categories = {
        'team_learning': [k for k in scripts if 'team' in k or 'learning' in k],
        'health_check': [k for k in scripts if 'health' in k or 'check' in k],
        'reasoning': [k for k in scripts if 'reasoning' in k],
        'market_radar': [k for k in scripts if 'radar' in k or 'growth' in k or 'hunter' in k],
        'data_fix': [k for k in scripts if 'fix' in k or 'repair' in k],
        'entry_signal': [k for k in scripts if 'entry' in k or 'signal' in k or 'scan' in k],
    }

    for cat, names in categories.items():
        if names:
            print(f"  {cat}: {', '.join(names)}")

    # 3. 尚未覆蓋的重要區域
    print('\n【3/5】尚未覆蓋的重要區域（建議補充）')
    missing = check_missing_sectors()
    for area, info in missing.items():
        print(f"  {info['icon']} {info['priority']}: {area}")
        print(f"     原因: {info['why']}")
        print(f"     符號: {info['symbols']}")

    # 4. 團隊覆蓋缺口
    print('\n【4/5】團隊覆蓋缺口')
    teams, unallocated = check_team_gaps()
    for team, info in teams.items():
        print(f"  {team} ({info['stocks']}): {info['focus']}")

    print(f"\n  未分配團隊的產業:")
    for s in unallocated:
        print(f"    - {s}")

    # 5. 決策資料庫缺口
    print('\n【5/5】決策資料庫缺口')
    dec = check_decision_gaps()
    if dec:
        print(f"  總決策類別: {len(dec.get('by_category', {}))}")
        print(f"  待結案: {dec.get('pending_decisions', 0)}")
        print(f"  低品質決策（<5分）: {dec.get('low_score_decisions', 0)}")

        if dec.get('by_category'):
            print(f"  決策分佈:")
            for cat, cnt in dec['by_category'].items():
                print(f"    {cat}: {cnt}")

    # 總結：優先補缺口
    print('\n' + '='*70)
    print('【優先補缺行動】')
    print('='*70)
    high_priority = [k for k, v in MISSING_AREAS.items() if v['priority'] == 'HIGH']
    for area in high_priority:
        info = MISSING_AREAS[area]
        print(f"  🔴 {area}: {info['symbols']}")

    med_priority = [k for k, v in MISSING_AREAS.items() if v['priority'] == 'MED']
    for area in med_priority:
        info = MISSING_AREAS[area]
        print(f"  🟡 {area}: {info['symbols']}")


if __name__ == '__main__':
    main()