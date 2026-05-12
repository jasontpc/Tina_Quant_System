# -*- coding: utf-8 -*-
"""
ray_memory_bridge.py — 三層記憶體系統
L1: RAM Cache (即時K線)
L2: SQLite WAL (短期修正)
L3: Modelfile (長期固化)
"""
import sys, sqlite3, json, time
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np

DB = 'ray_wisdom.db'

# ============================================================
# L1: RAM Cache（即時記憶）
# ============================================================
class L1_RAM_Cache:
    """32GB RAM 快取，1分鐘內不重複抓取"""

    def __init__(self):
        self.cache = {}  # symbol -> {time, data}

    def get_kline(self, symbol, period="1d", interval="5m"):
        """取得即時K線（5分鐘週期）"""
        now = datetime.now()
        key = f"{symbol}_{period}_{interval}"

        # 檢查快取（1分鐘內直接回傳）
        if key in self.cache:
            cached_time, cached_data = self.cache[key]
            if (now - cached_time).total_seconds() < 60:
                return cached_data

        # 抓取新數據
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                # 只保留最後5根K線
                tail = df.tail(5)[['Open', 'High', 'Low', 'Close', 'Volume']]
                self.cache[key] = (now, tail)
                return tail
        except:
            pass
        return None

    def get_indicators(self, symbol):
        """計算即時指標"""
        df = self.get_kline(symbol)
        if df is None or df.empty:
            return {}

        closes = df['Close'].values
        price = closes[-1]

        # RSI
        delta = np.diff(closes)
        gain = np.clip(delta, 0, None).mean()
        loss = np.clip(-delta, 0, None).mean()
        rs = gain / loss if loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "rsi": round(rsi, 1),
            "change": round((closes[-1] / closes[0] - 1) * 100, 2),
            "kline": f"{closes[-1]:.2f} ({'+' if closes[-1] >= closes[0] else ''}{((closes[-1] / closes[0] - 1) * 100):.2f}%)"
        }

# ============================================================
# L2: SQLite WAL（短期修正）
# ============================================================
class L2_SQLite_WAL:
    """從 wisdom_corrections 檢索 7B 的歷史修正"""

    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.conn.execute("PRAGMA journal_mode=WAL")

    def get_relevant_corrections(self, symbol=None, rsi_state=None, limit=5):
        """根據當前狀態檢索相關修正"""
        query = """
            SELECT diagnosis, corrected_json, confidence, meta_label
            FROM wisdom_corrections
            WHERE confidence >= 0.7
        """
        params = []

        if symbol:
            query += " AND (symbol=? OR symbol='GLOBAL' OR symbol='WEB_SOURCE')"
            params.append(symbol)

        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        c = self.conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()

        if not rows:
            return "無相關修正記憶，遵循標準量化邏輯。"

        results = []
        for row in rows:
            results.append(f"- [{row[2]:.2f}] {row[0][:100]}")

        return "\n".join(results)

    def get_taleb_warnings(self):
        """取得 Taleb 相關警示"""
        c = self.conn.cursor()
        c.execute("""
            SELECT diagnosis, confidence
            FROM wisdom_corrections
            WHERE (meta_label LIKE '%TALEB%' OR meta_label LIKE '%web_learner%')
            AND confidence >= 0.7
            ORDER BY confidence DESC
            LIMIT 3
        """)
        rows = c.fetchall()
        if not rows:
            return "無 Taleb 警示"
        return "\n".join([f"- {r[0][:80]}" for r in rows])

    def get_recent_wisdom(self, limit=5):
        """取得最近修正"""
        c = self.conn.cursor()
        c.execute("""
            SELECT symbol, diagnosis, confidence
            FROM wisdom_corrections
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        return [(r[0], r[1][:50], r[2]) for r in rows]

    def close(self):
        self.conn.close()

# ============================================================
# L3: Modelfile（長期固化）
# ============================================================
class L3_Modelfile:
    """讀取 Modelfile 中的固化規則"""

    def __init__(self):
        self.files = ['ray-v1.Modelfile', 'ray-deep-v1.Modelfile']

    def get_golden_rules(self):
        """讀取 Modelfile 中的黃金心法"""
        rules = []
        for f in self.files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                    # 找出 SYSTEM 或 PARAMETER 區塊
                    if 'SYSTEM' in content.upper():
                        rules.append(f"{f}: 已固化")
            except:
                pass
        return rules if rules else ["Modelfile 正常運行"]

# ============================================================
# 整合記憶橋接器
# ============================================================
class RayMemoryBridge:
    """三層記憶整合橋接器"""

    def __init__(self):
        self.l1 = L1_RAM_Cache()
        self.l2 = L2_SQLite_WAL()
        self.l3 = L3_Modelfile()

    def get_full_context(self, symbol):
        """取得完整上下文（用於 Prompt）"""

        # L1: 即時數據
        l1_data = self.l1.get_indicators(symbol)

        # L2: 歷史修正
        rsi_state = "oversold" if l1_data.get("rsi", 50) < 35 else "overbought" if l1_data.get("rsi", 50) > 65 else "neutral"
        l2_corrections = self.l2.get_relevant_corrections(symbol=symbol, rsi_state=rsi_state)
        l2_taleb = self.l2.get_taleb_warnings()

        # L3: 固化規則
        l3_rules = self.l3.get_golden_rules()

        # 組合上下文
        context = {
            "L1_RAM": l1_data,
            "L2_SQLite": {
                "corrections": l2_corrections,
                "taleb_warnings": l2_taleb
            },
            "L3_Modelfile": l3_rules,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return context

    def format_for_llm(self, symbol):
        """格式化為 LLM Prompt"""
        ctx = self.get_full_context(symbol)

        l1 = ctx["L1_RAM"]
        l2 = ctx["L2_SQLite"]
        l3 = ctx["L3_Modelfile"]

        prompt = f"""你是 Ray 三層記憶系統。

【L1 即時數據】
標的：{symbol}
價格：{l1.get('price')}
RSI：{l1.get('rsi')}
K線：{l1.get('kline')}

【L2 短期修正】
{l2.get('corrections')}

【L3 Taleb 警示】
{l2.get('taleb_warnings')}

【L3 固化規則】
{chr(10).join(l3)}

根據以上三層記憶，給出交易決策：

輸出 JSON：
{{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "reason": "原因"}}
"""
        return prompt

    def close(self):
        self.l2.close()

# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    print("=== Ray 三層記憶系統測試 ===")
    print()

    bridge = RayMemoryBridge()

    # 測試符號
    symbol = "VOO"

    print(f"取得 {symbol} 三層記憶...")
    ctx = bridge.get_full_context(symbol)

    print()
    print("【L1 RAM 即時數據】")
    l1 = ctx["L1_RAM"]
    for k, v in l1.items():
        print(f"  {k}: {v}")

    print()
    print("【L2 SQLite 短期修正】")
    print(ctx["L2_SQLite"]["corrections"][:200])

    print()
    print("【L3 Modelfile 固化】")
    for r in ctx["L3_Modelfile"]:
        print(f"  {r}")

    print()
    print("【格式化 Prompt】")
    prompt = bridge.format_for_llm(symbol)
    print(prompt[:500])

    bridge.close()
    print()
    print("=== 完成 ===")