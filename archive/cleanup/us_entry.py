import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT symbol, name, current_price, current_rsi, high_52w, low_52w FROM stock_summary WHERE current_rsi < 40 ORDER BY current_rsi ASC")
rows = cur.fetchall()
print('=== 低檔候選（RSI < 40）===')
for r in rows:
    sym, name, price, rsi, high, low = r
    from_high = ((price - high) / high * 100) if high else 0
    from_low = ((price - low) / low * 100) if low else 0
    print(f'{sym} {name}: price={price:.0f} RSI={rsi:.1f} from_high={from_high:+.1f}% from_low={from_low:+.1f}%')

# Get config
import json
config_file = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    params = config.get('optimized_params', {})
    print(f'\n=== Maggy 策略參數 ===')
    print(f'進場 RSI: < {params.get("entry_rsi", "N/A")}')
    print(f'出廠 RSI: > {params.get("exit_rsi", "N/A")}')
    print(f'持倉: {params.get("max_hold_days", "N/A")}天')
except:
    pass

conn.close()