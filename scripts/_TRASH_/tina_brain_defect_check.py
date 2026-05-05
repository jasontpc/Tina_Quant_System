# -*- coding: utf-8 -*-
"""
Tina Brain - 系統缺陷自我檢測 v1.0
==================================
全面檢查系統缺陷、未覆蓋區域，並生成優化腳本
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

def check_db_coverage():
    """檢查 DB 覆蓋缺口"""
    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()

    # 1. 檢查技術指標缺口（MACD/RSI 為 NULL）
    c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE rsi_14 IS NULL OR rsi_14 = 0")
    rsi_null = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE macd_hist IS NULL OR macd_hist = 0")
    macd_null = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM daily_ohlcv")
    total = c.fetchone()[0]

    # 2. 找出哪些 symbol 缺 MACD
    c.execute("""SELECT symbol, COUNT(*) as cnt FROM daily_ohlcv 
        WHERE (macd_hist IS NULL OR macd_hist = 0) 
        AND rsi_14 IS NOT NULL
        GROUP BY symbol HAVING cnt > 50
        ORDER BY cnt DESC LIMIT 20""")
    macd_missing = [(r[0], r[1]) for r in c.fetchall()]

    conn.close()

    return {
        'total_rows': total,
        'rsi_null_pct': round(rsi_null/total*100, 1),
        'macd_null_pct': round(macd_null/total*100, 1),
        'macd_missing_symbols': macd_missing,
    }


def check_sector_coverage():
    """檢查產業覆蓋缺口"""
    # 從 Jo 提供的分類檢查
    TW_SECTORS = {
        '算力核心': ['2330', '3711', '3661', '3443'],
        'Edge AI': ['2454', '5269', '4966', '2379', '2458'],
        '機器人/具身': ['2359', '2049', '1590', '6188', '2464'],
        '先進封裝': ['3131', '6187', '6640', '2467', '1560'],
        '高速傳輸/CPO': ['2345', '3081', '3363', '3163', '4908', '6442'],
        '散熱/液冷': ['3017', '3324', '3653', '2308', '2301', '8996'],
        'PCB/載板': ['2368', '2383', '3037', '3189', '8046', '6274'],
        '電力/變壓器': ['1519', '1503', '1513', '1514'],
        'HBM/存儲': ['8299', '3260', '4967', '2408', '2344'],
        '伺服器': ['2382', '3231', '6669', '2356', '2376', '3706'],
    }

    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()

    coverage = {}
    for sector, syms in TW_SECTORS.items():
        covered = []
        missing = []
        for s in syms:
            sym_with_tw = s + '.TW'
            c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=?", (sym_with_tw,))
            if c.fetchone()[0] > 100:
                covered.append(s)
            else:
                # Try TWO
                sym_tw = s + '.TWO'
                c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=?", (sym_tw,))
                if c.fetchone()[0] > 100:
                    covered.append(s + '.TWO')
                else:
                    missing.append(s)
        coverage[sector] = {'covered': covered, 'missing': missing, 'pct': round(len(covered)/len(syms)*100)}

    conn.close()
    return coverage


def check_entry_logic_gaps():
    """檢查進場邏輯缺陷"""
    # 讀取觀察名單
    with open(DATA / 'team_watch_list.json', 'r', encoding='utf-8') as f:
        watch = json.load(f)

    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()

    gaps = []

    for team, syms in watch.get('complete_watch', {}).items():
        for sym in syms:
            c.execute("""SELECT date, close, rsi_14, macd_hist, sma_20, sma_60 
                FROM daily_ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 5""", (sym,))
            rows = c.fetchall()

            if not rows:
                gaps.append({'type': 'no_data', 'sym': sym, 'team': team})
                continue

            # 檢查 DB 指標 vs 計算指標差異
            latest = rows[0]
            db_rsi = latest[2]
            db_macd = latest[3]

            # 重新計算
            c.execute("SELECT close, high, low FROM daily_ohlcv WHERE symbol=? ORDER BY date", (sym,))
            all_rows = c.fetchall()
            prices = [r[0] for r in all_rows]
            highs = [r[1] for r in all_rows]
            lows = [r[2] for r in all_rows]

            if len(prices) < 30:
                continue

            s = pd.Series(prices)
            delta = s.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            calc_rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            ema12 = s.ewm(span=12, adjust=False).mean()
            ema26 = s.ewm(span=26, adjust=False).mean()
            macd_l = ema12 - ema26
            macd_s = macd_l.ewm(span=9, adjust=False).mean()
            calc_macd = float((macd_l - macd_s).iloc[-1])

            rsi_diff = abs(db_rsi - calc_rsi) if db_rsi else 99
            macd_diff = abs((db_macd or 0) - calc_macd)

            if rsi_diff > 5:
                gaps.append({'type': 'rsi_bias', 'sym': sym, 'team': team, 'diff': round(rsi_diff, 1)})

    conn.close()
    return gaps


def check_backtest_gaps():
    """檢查回測系統缺陷"""
    with open(DATA / 'team_learning_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)

    bts_by_team = {}
    for team, data in results.get('teams', {}).items():
        bts = [s['backtest'] for s in data.get('stocks', []) if s.get('backtest')]
        total_trades = sum(b['trades'] for b in bts if b)
        if total_trades == 0:
            bts_by_team[team] = {'status': 'no_trades', 'trades': 0}
        else:
            wins_sum = sum(b['win_rate'] * b['trades'] for b in bts if b and b['trades'] > 0)
            wr = round(wins_sum / total_trades, 1)
            bts_by_team[team] = {'status': 'ok', 'trades': total_trades, 'wr': wr}

    return bts_by_team


def main():
    print('='*70)
    print('  Tina Brain - 系統缺陷自我檢測')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)
    print()

    # 1. DB 覆蓋檢查
    print('[1/5] DB 覆蓋缺口檢查...')
    db_info = check_db_coverage()
    print(f'  總 rows: {db_info["total_rows"]:,}')
    print(f'  RSI NULL: {db_info["rsi_null_pct"]}%')
    print(f'  MACD NULL: {db_info["macd_null_pct"]}%')
    if db_info['macd_missing_symbols']:
        print(f'  MACD 嚴重缺失 ({len(db_info["macd_missing_symbols"])} 檔):')
        for sym, cnt in db_info['macd_missing_symbols'][:5]:
            print(f'    {sym}: {cnt} rows missing MACD')
    print()

    # 2. 產業覆蓋檢查
    print('[2/5] 產業覆蓋檢查...')
    sectors = check_sector_coverage()
    low_pct = [(k, v) for k, v in sectors.items() if v['pct'] < 80]
    for sector, info in sorted(sectors.items(), key=lambda x: x[1]['pct']):
        status = '✅' if info['pct'] == 100 else ('⚠️' if info['pct'] < 80 else '🟡')
        miss_str = f" (missing: {', '.join(info['missing'])})" if info['missing'] else ''
        print(f'  {status} {sector:<15} {info["pct"]}% covered{miss_str}')
    print()

    # 3. 進場邏輯缺口
    print('[3/5] 進場邏輯缺口...')
    logic_gaps = check_entry_logic_gaps()
    if logic_gaps:
        print(f'  發現 {len(logic_gaps)} 個邏輯缺口:')
        for g in logic_gaps[:10]:
            if g['type'] == 'no_data':
                print(f'    [{g["type"]}] {g["sym"]} ({g["team"]}) - 無資料')
            elif g['type'] == 'rsi_bias':
                print(f'    [{g["type"]}] {g["sym"]} ({g["team"]}) - RSI偏差 {g["diff"]}')
    else:
        print('  ✅ 無邏輯缺口')
    print()

    # 4. 回測系統缺陷
    print('[4/5] 回測系統缺陷...')
    bt_status = check_backtest_gaps()
    for team, info in bt_status.items():
        if info['status'] == 'no_trades':
            print(f'  ⚠️  {team}: 無歷史交易（策略門檻過嚴）')
        else:
            print(f'  ✅ {team}: {info["trades"]}筆, WR {info["wr"]}%')
    print()

    # 5. 產出優化腳本建議
    print('[5/5] 缺陷優化腳本生成...')
    fixes = []

    # Fix 1: 補充 MACD
    if db_info['macd_null_pct'] > 20:
        fixes.append({
            'name': 'fix_macd_coverage.py',
            'desc': '補充缺失 MACD 計算（影響 ' + str(len(db_info['macd_missing_symbols'])) + ' 檔）',
            'priority': 'HIGH'
        })

    # Fix 2: 產業缺口
    if low_pct:
        fixes.append({
            'name': 'fill_sector_gaps.py',
            'desc': '補充缺口產業：' + ', '.join([k for k, v in low_pct]),
            'priority': 'MED'
        })

    # Fix 3: 回測門檻
    no_trade_teams = [t for t, i in bt_status.items() if i['status'] == 'no_trades']
    if no_trade_teams:
        fixes.append({
            'name': 'relax_entry_rules.py',
            'desc': '放寬進場門檻（' + ', '.join(no_trade_teams) + '）',
            'priority': 'HIGH'
        })

    print()
    print('【缺陷清單】')
    for i, f in enumerate(fixes, 1):
        print(f'  {i}. [{f["priority"]}] {f["name"]} - {f["desc"]}')

    # 寫入 report
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'db_coverage': db_info,
        'sector_coverage': sectors,
        'logic_gaps': logic_gaps,
        'backtest_status': bt_status,
        'fixes': fixes,
    }
    with open(DATA / 'brain_defect_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print(f'  報告已寫入: data/brain_defect_report.json')
    print('='*70)
    return fixes


if __name__ == '__main__':
    fixes = main()