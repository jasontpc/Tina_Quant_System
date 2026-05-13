# -*- coding: utf-8 -*-
"""supply_chain_scanner.py — 15:00 產業鏈掃描（無 LLM 版測試）"""
import sys, json, os, time, sqlite3
import yfinance as yf
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
RAM_CACHE = os.path.join(AGENTS_DIR, "supply_chain_ram.json")

def get_rsi(c, p=14):
    if len(c) < p + 1:
        return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

def get_top_movers(n=5):
    symbols = ["NVDA", "TSLA", "META", "MSFT", "AAPL", "AMZN"]
    movers = []
    for sym in symbols:
        try:
            h = yf.Ticker(sym).history(period="5d")
            if h is None or h.empty or len(h) < 5:
                continue
            close = h['Close'].values
            pct = (close[-1] - close[-2]) / close[-2] * 100 if len(close) >= 2 else 0
            movers.append({"symbol": sym, "day_pct": pct, "price": close[-1]})
        except:
            continue
    movers.sort(key=lambda x: x["day_pct"], reverse=True)
    return movers[:n]

def load_chain():
    if os.path.exists(RAM_CACHE):
        with open(RAM_CACHE, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    return {}

def save_chain(data):
    with open(RAM_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 靜態產業鏈（已知核心數據）
STATIC_CHAIN = {
    "NVDA": {
        "upstream": ["台積電(TSM)", "SK海力士", "美光"],
        "downstream": ["微軟Azure", "亞馬遜AWS", "Google Cloud"],
        "competitors": ["AMD", "Intel"],
    },
    "TSM": {
        "upstream": ["ASML", "應用材料", "科林研發"],
        "downstream": ["Apple", "NVDA", "AMD", "Qualcomm"],
        "competitors": ["三星電子"],
    },
    "META": {
        "upstream": ["AWS/Azure/GCP"],
        "downstream": ["廣告主", "用戶"],
        "competitors": ["TikTok(ByteDance)", "Google"],
    },
    "MSFT": {
        "upstream": ["NVIDIA GPU", "AMD GPU"],
        "downstream": ["企業SaaS", "Azure客戶"],
        "competitors": ["Google Cloud", "AWS"],
    },
    "AAPL": {
        "upstream": ["台積電(TSM)", "鴻海", "三星顯示"],
        "downstream": ["消費者", "企業"],
        "competitors": ["三星", "Google Pixel"],
    },
    "AMZN": {
        "upstream": ["NVIDIA GPU", "AMD GPU"],
        "downstream": ["電商消費者", "AWS客戶"],
        "competitors": ["Google Cloud", "Azure"],
    },
    "TSLA": {
        "upstream": ["Panasonic", "LG Energy", "NVIDIA DRIVE"],
        "downstream": ["消費者", "租車公司"],
        "competitors": ["比亞迪", "Rivian"],
    },
}

def main():
    print("=" * 60)
    print(" 15:00 產業鏈掃描（ray-deep-v1）")
    print(f" Time: {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    movers = get_top_movers(5)
    if not movers:
        print("[-] 無大漲股資料")
        return

    print(f"\n[*] 今日大漲股：")
    for m in movers:
        print(f"  {m['symbol']}: {m['day_pct']:+.2f}% price={m['price']:.2f}")

    chain = load_chain()

    for m in movers:
        sym = m["symbol"]
        static = STATIC_CHAIN.get(sym, {})
        chain[sym] = {
            "upstream": static.get("upstream", []),
            "downstream": static.get("downstream", []),
            "competitors": static.get("competitors", []),
            "notes": f"今日漲幅 {m['day_pct']:+.2f}%",
            "price": m["price"],
            "day_pct": round(m["day_pct"], 2),
            "last_scan": time.strftime("%Y-%m-%d %H:%M")
        }
        print(f"  ✅ {sym} → 上游: {static.get('upstream', [])[:2]}")

    save_chain(chain)
    print(f"\n[+] 產業鏈 RAM 快取已更新：{len(chain)} 檔")

    print("=" * 60)

if __name__ == "__main__":
    main()