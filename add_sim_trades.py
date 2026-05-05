import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, yfinance
from datetime import datetime

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
SIM_DB = f'{DATA_DIR}\\maggy_sim_trades.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def add_sim_trade(symbol, entry_price, entry_rsi, qty, name):
    conn = sqlite3.connect(SIM_DB)
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    value = entry_price * qty
    cur.execute('''INSERT INTO sim_trades 
        (symbol, entry_date, entry_price, quantity, entry_rsi, status)
        VALUES (?, ?, ?, ?, ?, 'OPEN')''',
        (symbol, today, entry_price, qty, entry_rsi))
    conn.commit()
    conn.close()
    return value

# Candidates
candidates = [
    ('XOM', 'Exxon', 148, 23.9, 10000),
    ('JNJ', 'Johnson & Johnson', 225, 29.7, 10000),
    ('XLE', 'Energy Sector ETF', 57, 31.8, 10000),
    ('EOG', 'EOG Resources', 133, 32.3, 10000),
]

print('╔══════════════════════════════════════════════════════╗')
print('║     Maggy 模擬進場 — 新增4檔倉位                  ║')
print('╚══════════════════════════════════════════════════════╝')
print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')

total_value = 0
positions = []

for sym, name, price, rsi, amount in candidates:
    qty = int(amount / price)
    value = add_sim_trade(sym, price, rsi, qty, name)
    total_value += value
    positions.append({'symbol': sym, 'name': name, 'price': price, 'rsi': rsi, 'qty': qty, 'value': value})
    print(f'✅ 新增倉位: {sym} {name}')
    print(f'   進場價: ${price:.2f} x {qty}股 = ${value:,.0f}')
    print(f'   RSI: {rsi:.1f} (< 35 進場)')
    print()

print('=' * 50)
print(f'總投入: ${total_value:,.0f}')
print(f'策略: RSI<35 進場, RSI>65 出場, 最多20天')
print(f'停損: RSI 重新突破 50 或 持有20天')
print()

# Show current portfolio
print('=== 當前模擬倉位 ===')
conn = sqlite3.connect(SIM_DB)
cur = conn.cursor()
cur.execute("SELECT symbol, entry_date, entry_price, quantity, entry_rsi FROM sim_trades WHERE status='OPEN'")
open_pos = cur.fetchall()
print(f'總倉位: {len(open_pos)}檔')
print()
print(f'{"股票":<8} {"進場日":<12} {"進場價":>10} {"股數":>6} {"金額":>12} {"RSI":>6}')
print('-' * 60)
total = 0
for r in open_pos:
    sym, dt, px, qty, rsi = r
    val = px * qty
    total += val
    print(f'{sym:<8} {dt:<12} ${px:>9.2f} {qty:>6} ${val:>11,.0f} {rsi:>6.1f}')
print('-' * 60)
print(f'{"總計":<8} {"":<12} {"":>10} {"":>6} ${total:>11,.0f}')
conn.close()

# Save portfolio report
report = {
    'date': datetime.now().isoformat(),
    'total_value': total_value,
    'positions': positions,
    'strategy': 'RSI<35進場, RSI>65出场, 最多20天',
    'stop_loss': 'RSI重新突破50或持有20天',
}
import json
with open(f'{DATA_DIR}\\maggy_portfolio.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'\n✅ 倉位已儲存: maggy_portfolio.json')