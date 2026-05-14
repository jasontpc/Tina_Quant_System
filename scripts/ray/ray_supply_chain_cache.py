# -*- coding: utf-8 -*-
"""
ray_supply_chain_cache.py — 產業鏈 RAM 快取
非同步流水線：
  17:00 → 7B 蒸餾產業新聞 → 輸出供應鏈映射表（JSON）
  21:30 / 09:00 → 4B 直接從 RAM 載入映射表，快速決策

目的：4B 模型只需「檢索」不需「推理」產業關係
"""
import json, os, sys, sqlite3, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
RAM_CACHE = os.path.join(AGENTS_DIR, "supply_chain_ram.json")
WISDOM_DB = os.path.join(AGENTS_DIR, "ray_wisdom.db")

def load_from_db():
    """從 wisdom_corrections 讀取所有產業相關規則"""
    conn = sqlite3.connect(WISDOM_DB)
    c = conn.cursor()
    c.execute("""
        SELECT symbol, diagnosis, corrected_json, confidence, market_regime
        FROM wisdom_corrections
        WHERE symbol IS NOT NULL AND diagnosis IS NOT NULL
        ORDER BY confidence DESC, created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def build_supply_chain():
    """建構供應鏈映射表（RAM cache）"""
    rows = load_from_db()

    supply_chain = {}
    for symbol, diagnosis, corrected_json, confidence, regime in rows:
        if not symbol or symbol == "WEB_SOURCE":
            continue

        # 解析 corrected_json（假設是 JSON 字串）
        try:
            details = json.loads(corrected_json) if corrected_json else {}
        except:
            details = {}

        # 建立產業鏈節點
        if symbol not in supply_chain:
            supply_chain[symbol] = {
                "confidence": float(confidence or 0),
                "regime": regime or "unknown",
                "rules": [],
                "上下游": [],
                "最後更新": ""
            }

        supply_chain[symbol]["rules"].append({
            "diagnosis": diagnosis[:200],
            "confidence": float(confidence or 0),
            "details": details
        })

    # 加入靜態上下游關係（手動維護的核心產業鏈）
    static_relationships = {
        "NVDA": {
            "上游": ["台積電(TSM)", "SK海力士", "美光"],
            "下游": ["CUDA生態系", "雲端服務商(Azure/GCP/AWS)"],
            "替代": ["AMD GPU"]
        },
        "TSM": {
            "上游": ["應用材料", "科林研發", "ASML"],
            "下游": ["Apple", "NVDA", "AMD", "Qualcomm"],
            "替代": ["三星"]
        },
        "AAPL": {
            "上游": ["台積電(TSM)", "鴻海", "三星顯示"],
            "下游": ["消費者", "企業"],
            "替代": ["三星", "Google Pixel"]
        },
        "META": {
            "上游": ["AWS/GCP/Azure"],
            "下游": ["廣告主"],
            "替代": ["Google Ads", "TikTok"]
        },
        "MSFT": {
            "上游": ["NVIDIA GPU", "AMD GPU"],
            "下游": ["企業SaaS", "Azure客戶"],
            "替代": ["Google Cloud", "AWS"]
        }
    }

    for sym, data in static_relationships.items():
        if sym in supply_chain:
            supply_chain[sym]["上下游"] = data
        else:
            supply_chain[sym] = {
                "confidence": 0.5,
                "regime": "static",
                "rules": [],
                "上下游": data,
                "最後更新": "static"
            }

    return supply_chain

def save_ram_cache():
    """建構並保存 RAM 快取"""
    print("[Supply Chain] 建構 RAM 快取...")
    data = build_supply_chain()

    with open(RAM_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[Supply Chain] ✅ 已保存 {len(data)} 個產業鏈節點 → {RAM_CACHE}")
    return data

def load_ram_cache():
    """4B 快速載入（無需 LLM 推理）"""
    if not os.path.exists(RAM_CACHE):
        return None
    with open(RAM_CACHE, 'r', encoding='utf-8', errors='replace') as f:
        return json.load(f)

def lookup(symbol: str):
    """給定symbol，回傳最快可用的產業鏈資訊"""
    cache = load_ram_cache()
    if not cache:
        return None
    return cache.get(symbol)

if __name__ == "__main__":
    save_ram_cache()