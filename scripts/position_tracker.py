# -*- coding: utf-8 -*-
"""
Tina 即時持倉追蹤系統
====================
每 15 分鐘更新，即時追蹤持倉狀態

功能：
1. 讀取持倉設定
2. 計算即時損益
3. 檢查風控條件
4. 寫入 position_tracker.json
"""

import sys, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
TRACKER_FILE = WORKSPACE / 'data' / 'position_tracker.json'
MEMORY_FILE = WORKSPACE / 'MEMORY.md'

# 當前持倉設定
POSITIONS = {
    "00713": {
        "name": "元大高息低波",
        "shares": 300,
        "cost": 53.22,
        "target": 55.50,
        "stop_loss": 51.00,
        "entry_date": "2026-04-30"
    },
    "META": {
        "name": "META",
        "shares": 1,
        "cost": 606.00,
        "target": 640,
        "stop_loss": 570,
        "entry_date": "2026-04-30"
    },
    "MSFT": {
        "name": "MSFT",
        "shares": 2,
        "cost": 410.14,
        "target": 430,
        "stop_loss": 380,
        "entry_date": "2026-04-30"
    }
}

def calculate_pnl(symbol: str, current_price: float) -> dict:
    """計算損益"""
    pos = POSITIONS.get(symbol)
    if not pos:
        return {}
    
    cost_total = pos["shares"] * pos["cost"]
    current_total = pos["shares"] * current_price
    pnl = current_total - cost_total
    pnl_pct = (current_price - pos["cost"]) / pos["cost"] * 100
    
    days_held = (datetime.now() - datetime.strptime(pos["entry_date"], "%Y-%m-%d")).days
    
    # 風控檢查
    risk_status = "PASS"
    risk_alert = None
    
    if pnl_pct <= -8:
        risk_status = "STOP_LOSS"
        risk_alert = "虧損超過 8%，建議止損"
    elif current_price <= pos["stop_loss"]:
        risk_status = "STOP_LOSS"
        risk_alert = f"觸及停損價 ${pos['stop_loss']}"
    elif pnl_pct >= pos["target"] - pos["cost"]:
        risk_status = "TARGET"
        risk_alert = f"達到目標價 ${pos['target']}"
    elif days_held > 30 and pnl_pct < 0:
        risk_status = "DANGER"
        risk_alert = f"持有超過 30 天且虧損，危險組合"
    
    return {
        "symbol": symbol,
        "name": pos["name"],
        "shares": pos["shares"],
        "cost": pos["cost"],
        "current_price": current_price,
        "cost_total": round(cost_total, 2),
        "current_total": round(current_total, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "days_held": days_held,
        "target": pos["target"],
        "stop_loss": pos["stop_loss"],
        "risk_status": risk_status,
        "risk_alert": risk_alert
    }

def update_tracker():
    """更新持倉追蹤"""
    print('='*60)
    print('Tina 即時持倉追蹤')
    print(f'時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)
    print()
    
    # 讀取 MEMORY.md 確認持倉
    memory_positions = {}
    if MEMORY_FILE.exists():
        content = MEMORY_FILE.read_text(encoding='utf-8')
        # 解析持倉表格
        for line in content.split('\n'):
            if '00713' in line:
                memory_positions['00713'] = True
            elif 'META' in line and 'MSFT' not in line:
                memory_positions['META'] = True
            elif 'MSFT' in line:
                memory_positions['MSFT'] = True
    
    # 模擬價格（實際使用 yfinance）
    prices = {
        "00713": 54.75,
        "META": 616.81,
        "MSFT": 420.77
    }
    
    results = []
    total_pnl = 0
    total_cost = 0
    
    print('【持倉狀態】')
    print('-'*60)
    print(f'{"股票":<8} {"成本":>8} {"現價":>8} {"損益":>8} {"天數":>4} {"狀態":<10}')
    print('-'*60)
    
    for symbol, price in prices.items():
        result = calculate_pnl(symbol, price)
        if result:
            results.append(result)
            total_pnl += result["pnl"]
            total_cost += result["cost_total"]
            
            status_emoji = {
                "PASS": "✅",
                "TARGET": "🎯",
                "STOP_LOSS": "🛑",
                "DANGER": "⚠️"
            }.get(result["risk_status"], "❓")
            
            print(f'{result["symbol"]:<8} ${result["cost"]:>7.2f} ${result["current_price"]:>7.2f} {result["pnl_pct"]:>+6.2f}% {result["days_held"]:>3}d {status_emoji} {result["risk_status"]}')
            
            if result["risk_alert"]:
                print(f'           ⚠️ {result["risk_alert"]}')
    
    print('-'*60)
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    print(f'總損益：{total_pnl:+.2f} USD（{total_pnl_pct:+.2f}%）')
    print()
    
    # 寫入追蹤檔案
    tracker_data = {
        "timestamp": datetime.now().isoformat(),
        "positions": results,
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "total_cost": round(total_cost, 2),
            "position_count": len(results),
            "risk_count": sum(1 for r in results if r["risk_status"] != "PASS")
        }
    }
    
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracker_data, f, ensure_ascii=False, indent=2)
    
    print(f'已寫入：{TRACKER_FILE.name}')
    print('='*60)
    
    return tracker_data

if __name__ == '__main__':
    update_tracker()
