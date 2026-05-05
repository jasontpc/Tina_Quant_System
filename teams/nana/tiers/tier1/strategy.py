SECTOR_STRATEGY = {
    'name': 'Tier1',
    'atr_stop': 1.5,
    'hold_days': {'tier1': 3, 'tier2': 4, 'tier3': 7},
    'target_return': {'tier1': 0.04, 'tier2': 0.03, 'tier3': 0.02},
    'rsi_entry_max': 70,
    'entry_vol_min_pct': 50,
}

import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\tiers\tier1"

def get_stocks():
    with open(rf"{BASE_PATH}\stocks.json", encoding="utf-8") as f:
        return json.load(f)

def run():
    stocks = get_stocks()
    print("=" * 60)
    print(f"Nana Tier1 等級分析 | {datetime.now().strftime('%Y-%m-%d')}")
    print(f"股票數: {len(stocks)}")
    print("=" * 60)
    for s in stocks:
        print(f"  [{s['tier']}] {s['id']} {s['name']} WR={s['wr']}%")
    return stocks

if __name__ == "__main__":
    run()
