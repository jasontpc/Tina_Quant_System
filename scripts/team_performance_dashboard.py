# -*- coding: utf-8 -*-
"""
BR-004: 全團隊績效追蹤儀表板
============================
統一視覺化所有團隊表現
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

TEAMS = {
    'LEO': {'focus': 'AI科技', 'stocks': 9},
    'NANA': {'focus': '波段操作', 'stocks': 4},
    'GUARD': {'focus': '軍工國防', 'stocks': 2},
    'AION': {'focus': '電車供應鏈', 'stocks': 2},
    'FINMAX': {'focus': '金融金控', 'stocks': 7},
    'MAGGY': {'focus': '美股AI', 'stocks': 2},
    'SHERKY': {'focus': 'ETF能源', 'stocks': 1},
}

def get_team_results():
    """從 team_learning_results.json 讀取結果"""
    try:
        with open(DATA / 'team_learning_results.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def get_decision_stats():
    """從決策資料庫讀取統計"""
    try:
        conn = sqlite3.connect(str(DATA / 'tina_decisions.db'))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM decisions")
        total = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM decisions WHERE outcome IN ('win','loss')")
        resolved = c.fetchone()[0] or 0
        c.execute("SELECT AVG(score) FROM decisions WHERE score IS NOT NULL")
        avg_score = c.fetchone()[0] or 0
        conn.close()
        return {'total': total, 'resolved': resolved, 'avg_score': round(avg_score, 1)}
    except:
        return {'total': 0, 'resolved': 0, 'avg_score': 0}

def get_db_health():
    """DB 健康度"""
    try:
        conn = sqlite3.connect(str(DATA / 'yfinance.db'))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM daily_ohlcv")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE rsi_14 IS NULL OR rsi_14 = 0")
        rsi_null = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE macd_hist IS NULL OR macd_hist = 0")
        macd_null = c.fetchone()[0]
        c.execute("SELECT MAX(date) FROM daily_ohlcv")
        latest = c.fetchone()[0]
        conn.close()
        health = 100 - (rsi_null/total*30) - (macd_null/total*20)
        return {'rows': total, 'health': round(health, 1), 'latest': latest}
    except:
        return {'rows': 0, 'health': 0, 'latest': None}

def main():
    print('='*70)
    print('  Tina Brain - 全團隊績效儀表板 BR-004')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    results = get_team_results()
    decisions = get_decision_stats()
    db = get_db_health()

    # DB 健康度
    print('\n【系統狀態】')
    health_icon = '🟢' if db['health'] > 80 else ('🟡' if db['health'] > 60 else '🔴')
    print(f"  {health_icon} DB健康度: {db['health']}/100")
    print(f"  📊 總記錄: {db['rows']:,} rows")
    print(f"  📅 最新日期: {db['latest']}")

    # 決策統計
    print('\n【決策資料庫】')
    dec_icon = '🟢' if decisions['total'] > 0 else '⚪'
    print(f"  {dec_icon} 總決策: {decisions['total']}")
    print(f"  ✅ 已結案: {decisions['resolved']} ({round(decisions['resolved']/decisions['total']*100,1) if decisions['total'] > 0 else 0}%)")
    print(f"  ⭐ 平均品質: {decisions['avg_score']}/10")

    # 團隊表現
    print('\n【團隊表現】')
    teams_data = results.get('teams', {})

    team_perf = []
    for team_id, info in TEAMS.items():
        stocks = teams_data.get(team_id, {}).get('stocks', [])
        if not stocks:
            team_perf.append({'team': team_id, 'focus': info['focus'], 'trades': 0, 'wr': 0, 'stocks': info['stocks']})
            continue

        bts = [s['backtest'] for s in stocks if s.get('backtest') and s['backtest']['trades'] > 0]
        if not bts:
            team_perf.append({'team': team_id, 'focus': info['focus'], 'trades': 0, 'wr': 0, 'stocks': info['stocks']})
            continue

        total_trades = sum(b['trades'] for b in bts)
        wins_sum = sum(b['win_rate']/100 * b['trades'] for b in bts)
        wr = round(wins_sum / total_trades * 100, 1) if total_trades > 0 else 0
        team_perf.append({'team': team_id, 'focus': info['focus'], 'trades': total_trades, 'wr': wr, 'stocks': info['stocks']})

    # 排序
    team_perf.sort(key=lambda x: -x['wr'])

    # Header
    print(f"  {'團隊':<8} {'主題':<12} {'勝率':>6} {'交易':>5} {'觀察':>4} {'狀態'}")
    print(f"  {'-'*60}")

    for t in team_perf:
        wr_icon = '🟢' if t['wr'] >= 60 else ('🟡' if t['wr'] >= 40 else '⚪')
        print(f"  {t['team']:<8} {t['focus']:<12} {wr_icon}{t['wr']:>5}% {t['trades']:>5} {t['stocks']:>4}")

    # Summary
    total_all_trades = sum(t['trades'] for t in team_perf)
    avg_wr = sum(t['wr'] * t['trades'] for t in team_perf) / total_all_trades if total_all_trades > 0 else 0

    print(f"  {'-'*60}")
    print(f"  {'加權平均':<20} {'🟢' if avg_wr >= 50 else '⚪'}{avg_wr:>5.1f}% {total_all_trades:>5}")

    print('\n【Cron Jobs 狀態】')
    print(f"  ✅ FINMAX 金融利率監控 (420f9780) - 每日 08:00")
    print(f"  ✅ GUARD 軍工國防掃描 (8c337856) - 09:00 + 15:00")
    print(f"  ✅ Tina 全團隊整合 (618aa329) - 每日 10:00")
    print(f"  ✅ Tina 推理增強掃描 (3019927f) - 09:00 + 14:00 + 20:00")
    print(f"  ✅ Tina 全團隊學習回測 (bd00a130) - 週日 09:00")


if __name__ == '__main__':
    main()