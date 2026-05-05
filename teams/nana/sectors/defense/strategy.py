SECTOR_STRATEGY = {
    'name': 'Defense/國防概念',
    'atr_stop': 2.5,
    'hold_days': {'tier1': 3, 'tier2': 4, 'tier3': 7},
    'target_return': {'tier1': 0.025, 'tier2': 0.02, 'tier3': 0.015},
    'rsi_entry_max': 60,
    'entry_vol_min_pct': 30,
    'note': '2026-04-24 重新正名為國防概念，原台泥/中鋼移至stocks_old.json'
}

import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\sectors\defense"

def get_stocks():
    with open(rf"{BASE_PATH}\stocks.json", encoding="utf-8") as f:
        return json.load(f)

def run():
    stocks = get_stocks()
    print("=" * 60)
    print(f"Nana Defense/國防概念 板塊分析 | {datetime.now().strftime('%Y-%m-%d')}")
    print(f"股票數: {len(stocks)}")
    print("=" * 60)
    for s in stocks:
        print(f"  [Tier{s['tier']}] {s['id']} {s['name']} ${s['price']} ({s['note']})")
    return stocks

if __name__ == "__main__":
    run()
