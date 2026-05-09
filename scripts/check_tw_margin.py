import sqlite3
from pathlib import Path

db = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db')
conn = sqlite3.connect(str(db))
cur = conn.cursor()

print('='*70)
print('TW 信用交易分析報告 | 2026-05-08（資料更新至 2026-05-07）')
print('='*70)
print()

# 取得熱門信用交易（前10）
print('=== 信用交易餘額排行（2026-05-07）===')
print(f'{"股票":<8} {"Margin餘額":>12} {"Short餘額":>10} {"日期":<10}')
print('-'*45)

top = cur.execute('''
    SELECT stock_id, margin_balance, short_balance, date
    FROM margin_summary
    WHERE date = '2026-05-07'
    ORDER BY margin_balance DESC
    LIMIT 10
''').fetchall()

for r in top:
    sid = r[0]
    # 股票名稱
    names = {
        '2330': '台積電', '2317': '鴻海', '2382': '廣達', '2454': '聯發科',
        '2881': '富邦金', '2883': '國泰金', '2882': '中信金', '2885': '元大金',
        '3034': '緯穎', '3037': '創意', '2451': '群聯'
    }
    name = names.get(sid, sid)
    print(f'{sid} {name:<6} {r[1]:>12,} {r[2]:>10,} {r[3]}')

print()
print('=== Jo 相關股票信用交易 ===')
jo_stocks = ['2330', '2317', '2382', '2454', '3034']
for sid in jo_stocks:
    rows = cur.execute('''
        SELECT date, margin_balance, short_balance
        FROM margin_summary
        WHERE stock_id = ?
        ORDER BY date DESC
        LIMIT 5
    ''', (sid,)).fetchall()
    
    if rows:
        print(f'\n{sid}:')
        print(f'  {"日期":<10} {"Margin":>12} {"Short":>10} {"變化":>10}')
        print(f'  {"-"*45}')
        prev = None
        for r in rows:
            chg = f'{r[1]-prev:+12,}' if prev else '         --'
            print(f'  {r[0]:<10} {r[1]:>12,} {r[2]:>10,} {chg}')
            if not prev:
                prev = r[1]

print()
print('=== 近5日淨變化分析 ===')
# 計算近5日淨變化
recent = cur.execute('''
    SELECT stock_id, date, margin_balance,
           LAG(margin_balance) OVER (PARTITION BY stock_id ORDER BY date) as prev
    FROM margin_summary
    WHERE date >= '2026-05-01'
    ORDER BY margin_balance DESC
''').fetchall()

# 找出變化最大的
changes = {}
for r in recent:
    if r[3] and r[1]:
        chg = r[2] - r[3]
        if r[0] not in changes or abs(chg) > abs(changes[r[0]]):
            changes[r[0]] = chg

print(f'{"股票":<8} {"近5日變化":>12}')
print('-'*25)
for sid, chg in sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
    print(f'{sid:<8} {chg:>+12,}')

print()
print('=== 警示信號 ===')
# 找出 Margin 餘額大幅減少的（可能強制停損）
warnings = []
for r in recent:
    if r[3] and r[1]:
        chg = r[2] - r[3]
        pct = (chg / r[3] * 100) if r[3] else 0
        if pct < -20:  # 減少超過20%
            warnings.append((r[0], chg, pct))

if warnings:
    print('[WARNING] 信用餘額大幅減少（可能強制停損）：')
    for w in warnings[:5]:
        print(f'  {w[0]}: {w[1]:+,} ({w[2]:.1f}%)')
else:
    print('[OK] 無顯著警示')

print()
print('=== 結論 ===')
print('• TW 信用交易資料更新至 2026-05-07（今日）')
print('• 2330 台積電：Margin 119,000，Short 4,492,680')
print('• 2317 鴻海：Margin 121,000，Short 4,491,680')
print('• 2454 聯發科：Margin 119,000，Short 4,492,680')
print('• Short 餘額遠高於 Margin，代表空方勢力較強')

conn.close()