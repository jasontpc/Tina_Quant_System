# -*- coding: utf-8 -*-
import sys, sqlite3, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== 增加交易信號建議 ===")
print()

now = time.strftime("%Y-%m-%d %H:%M:%S")

c.execute("SELECT symbol FROM signals_log")
existing = set([r[0] for r in c.fetchall()])
print(f"現有信號: {existing}")
print()

high_potential = [
    ("AMD", 0.85, "MOMENTUM_60", "Sharpe 1.36, 低交易次數高效益"),
    ("NVDA", 0.80, "MOMENTUM_60", "Sharpe 1.30, MDD 0.28%"),
    ("GLD", 0.78, "MOMENTUM_60", "Sharpe 1.08, 黃金避險"),
    ("SPY", 0.75, "MOMENTUM_5", "Sharpe 1.13, 低MDD"),
    ("VOO", 0.72, "MOMENTUM_5", "Sharpe 1.18, 穩健DCA"),
]

print("🎯 新增信號建議:")
new_signals = []
for sym, score, tag, note in high_potential:
    if sym not in existing:
        new_signals.append((sym, score, tag, note))
        print(f"   + {sym} (score:{score}, {tag}) - {note}")

if not new_signals:
    print("   (全部已存在)")

print()

if new_signals:
    print("寫入新信號...")
    for sym, score, tag, note in new_signals:
        try:
            c.execute(f'''INSERT INTO signals_log (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (now, sym, "STRATEGY_REVIEW", score, 1.36, 0.5, 0.5, tag, 0, note))
            print(f"   已寫入: {sym}")
        except Exception as e:
            print(f"   寫入失敗 {sym}: {e}")
    conn.commit()

c.execute("SELECT symbol, source, score, signal_tag, approved FROM signals_log ORDER BY timestamp DESC")
all_signals = c.fetchall()
print()
print(f"📋 signals_log 目前 ({len(all_signals)} 筆):")
for r in all_signals:
    approved = "✅" if r[4] else "⏳"
    print(f"   {approved} {r[0]} | {r[1]} | score:{r[2]} | {r[3]}")

conn.close()
print()
print("=== 信號增加完成 ===")