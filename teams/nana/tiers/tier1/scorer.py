"""
Nana Tier1 Scorer
"""
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\tiers\tier1"

def score_stock(stock):
    """評分函數：WR×0.5 + 穩定性加成"""
    score = min(stock.get("wr", 0), 85) * 0.5
    return score

def run():
    with open(rf"{BASE_PATH}\stocks.json", encoding="utf-8") as f:
        stocks = json.load(f)

    print("Tier1 評分:")
    for s in stocks:
        print(f"  [{s['tier']}] {s['id']} {s['name']} WR={s['wr']}% Score={score_stock(s):.1f}")

if __name__ == "__main__":
    run()
