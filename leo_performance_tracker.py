# -*- coding: utf-8 -*-
"""
Leo v6.5 成績追蹤系統 — 從 2026-05-07 起的新制
==============================================
規則：
- 基準日：2026-05-07
- 已入倉（entry_date >= 2026-05-07，仍持有）→ 計入成績
- 已出倉（exit_date >= 2026-05-07）→ 計入成績
- 之前已出倉（exit_date < 2026-05-07）→ 不計
"""

import sqlite3, json, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH = BASE_DIR / 'data' / 'sherry_sim_trades.db'
BASELINE_DATE = '2026-05-07'

# ── helpers ────────────────────────────────────────────

def get_open_positions_since(conn, since):
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, entry_date, entry_price, shares, amount, entry_rsi, strategy, updated_at
        FROM open_positions
        WHERE entry_date >= ?
        ORDER BY entry_date DESC
    """, (since,))
    return cur.fetchall()

def get_closed_positions_since(conn, since):
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, entry_date, exit_date, entry_price, exit_price, 
               shares, return_pct, return_amount, exit_reason, strategy
        FROM closed_positions
        WHERE exit_date >= ?
        ORDER BY exit_date DESC
    """, (since,))
    return cur.fetchall()

def calc_stats(positions, pnl_col=7, return_col=6):
    if not positions:
        return {'count': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'total_pnl': 0.0, 'avg_return': 0.0}
    wins = sum(1 for p in positions if p[return_col] > 0)
    losses = len(positions) - wins
    total_pnl = sum(p[pnl_col] for p in positions if p[pnl_col] is not None)
    avg_return = sum(p[return_col] for p in positions if p[return_col] is not None) / len(positions)
    return {
        'count': len(positions),
        'wins': wins,
        'losses': losses,
        'win_rate': wins / len(positions) * 100,
        'total_pnl': total_pnl,
        'avg_return': avg_return,
    }

# ── main ──────────────────────────────────────────────

def main():
    print(f'=== Leo v6.5 成績報告（{BASELINE_DATE} 起）===')
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # 在倉（基準日起）
    open_pos = get_open_positions_since(conn, BASELINE_DATE)
    open_stats = calc_stats(open_pos, pnl_col=4, return_col=None)  # open has no return_pct
    
    # 已出倉（基準日起）
    closed_pos = get_closed_positions_since(conn, BASELINE_DATE)
    closed_stats = calc_stats(closed_pos, pnl_col=7, return_col=6)
    
    # 總成績（入倉 + 已出倉）
    total_count = open_stats['count'] + closed_stats['count']
    total_wins = closed_stats['wins']
    total_losses = closed_stats['losses']
    total_pnl = open_stats['total_pnl'] + closed_stats['total_pnl']
    
    # 計算仍持有的倉位市值（amount = 已投入成本）
    open_invested = sum(p[4] for p in open_pos)  # amount column
    
    print(f'\n📊 成績概況（{BASELINE_DATE} 起）')
    print(f'───')
    print(f'在倉：{open_stats["count"]} 檔（已入倉，仍持有）')
    print(f'已出：{closed_stats["count"]} 檔（已結算）')
    print(f'總計：{total_count} 檔交易')
    print(f'')
    print(f'勝率：{total_wins}/{total_wins+total_losses} = {total_wins/(total_wins+total_losses)*100:.1f}%' if total_wins+total_losses > 0 else '勝率：N/A')
    print(f'累計PnL：NT$ {total_pnl:,.0f}')
    print(f'在倉總投入：NT$ {open_invested:,.0f}')
    
    if closed_pos:
        print(f'\n🚪 已出倉交易（{len(closed_pos)} 檔）')
        for p in closed_pos:
            status = '🟢' if p[6] > 0 else '🔴'
            print(f'  {status} {p[0]} exit={p[2]} ret={p[6]:.2f}% pnl={p[7]:,.0f} reason={p[8]}')
    
    if open_pos:
        print(f'\n📈 在倉倉位（{len(open_pos)} 檔）')
        for p in open_pos[:10]:
            print(f'  📌 {p[0]} entry={p[1]} price={p[2]:.2f} shares={p[3]:.2f} amount={p[4]:,.0f} RSI={p[5]:.1f}')
        if len(open_pos) > 10:
            print(f'  ...還有 {len(open_pos)-10} 檔')

    conn.close()
    print(f'\nDone')

if __name__ == '__main__':
    main()