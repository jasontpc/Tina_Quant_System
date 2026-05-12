# -*- coding: utf-8 -*-
"""
ray_integrity_booster.py — 整合正確性、完整性、結構性三維優化
作為 Layer 2 (1.5B) 的前端過濾器
"""

import json, re, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"

# ============================================================
# 正確性：RAG 檢索模組
# ============================================================

def get_relevant_corrections(symbol, indicator=None, value=None, limit=5):
    try:
        import sqlite3
        DB_PATH = "ray_wisdom.db"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = '''SELECT diagnosis, corrected_json, confidence, symbol
                    FROM wisdom_corrections
                    WHERE confidence >= 0.7
                    ORDER BY confidence DESC LIMIT ?'''
        params = [limit]

        if symbol:
            symbol_plain = symbol.replace('.TW', '')
            query += ' AND (symbol = ? OR symbol = ?)'
            params.extend([symbol_plain, symbol_plain])

        if indicator and value is not None:
            if 'RSI' in indicator.upper():
                if value < 30:
                    state_filter = '%oversold%'
                elif value > 70:
                    state_filter = '%overbought%'
                else:
                    state_filter = '%RSI%'
                query += ' AND diagnosis LIKE ?'
                params.append(state_filter)

        c.execute(query, params)
        results = c.fetchall()
        conn.close()

        if not results:
            return ""

        lines = ["\n【歷史修正提醒】"]
        for r in results:
            diag = (r['diagnosis'] or '')[:100].replace('\n', ' ')
            lines.append(f"  • [{r['symbol']}] {diag} (conf={r['confidence']:.2f})")
        return "\n".join(lines)
    except Exception as e:
        return f"\n[RAG Error: {e}]\n"

# ============================================================
# 完整性：CoT 多階段 System Instruction
# ============================================================

SYSTEM_INSTRUCTION = """You are Ray, a quantitative trading logic executor.
Output ONLY JSON. No explanation outside JSON.

【MANDATORY CHECKLIST — All fields required】
1. strategy_name (UPPER_SNAKE)
2. indicator (exact: EMA_CROSS / RSI2 / VEGAS_TUNNEL / MOMENTUM / MACD)
3. params (object: period/threshold)
4. entry_condition (object: operator/threshold)
5. stop_loss (decimal, e.g., 0.08)
6. take_profit (decimal, e.g., 0.15)
7. confidence (0.0-1.0)
8. risk_reason (Taleb/Thorp logic)
9. source ("CoT_analyzed")

【Example Output】
{
  "strategy_name": "RSI2_OVERSOLD",
  "indicator": "RSI2",
  "params": {"period": 2, "threshold": 20},
  "entry_condition": {"operator": "CROSS_BELOW", "threshold": 20},
  "stop_loss": 0.08,
  "take_profit": 0.15,
  "confidence": 0.82,
  "risk_reason": "RSI2<20 oversold + price>EMA20 = Taleb asymmetric",
  "source": "CoT_analyzed"
}

【Hard Filters】
• Sharpe < 0.8 → REJECT
• MDD > 20% → REJECT
• WinRate < 35% → REJECT

Output JSON only."""


ONE_SHOT_EXAMPLE = """Example for NVDA with RSI2=22:
{
  "strategy_name": "RSI2_OVERSOLD_MOMENTUM",
  "indicator": "RSI2",
  "params": {"period": 2, "threshold": 20},
  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 20},
  "stop_loss": 0.08,
  "take_profit": 0.15,
  "confidence": 0.85,
  "risk_reason": "RSI2<20 oversold + MACD bullish + price>EMA20 = asymmetric (Taleb)",
  "source": "CoT_analyzed"
}"""

# ============================================================
# 核心：get_enhanced_proposal
# ============================================================

def get_enhanced_proposal(symbol, raw_indicators):
    rsi2 = raw_indicators.get('rsi2', 50)
    rsi14 = raw_indicators.get('rsi14', 50)
    macd_hist = raw_indicators.get('macd_hist', 0)
    price = raw_indicators.get('price', 0)
    ema20 = raw_indicators.get('ema20', 0)
    indicator = raw_indicators.get('indicator', 'RSI2')
    sharpe = raw_indicators.get('sharpe_30d', 0)
    mdd = raw_indicators.get('mdd_30d', 0)

    # 正確性：RAG 檢索
    historical_wisdom = get_relevant_corrections(symbol, indicator, rsi2)
    if not historical_wisdom:
        historical_wisdom = get_relevant_corrections(symbol)

    # 完整性：數據摘要
    data_summary = (
        f"Symbol: {symbol} | Price: ${price}\n"
        f"EMA20: ${ema20} | RSI14: {rsi14} | RSI2: {rsi2}\n"
        f"MACD Hist: {macd_hist:.4f} | Sharpe: {sharpe:.2f} | MDD: {mdd:.2%}\n"
    )

    # 結構性：組合 Prompt + JSON Mode
    try:
        import requests
        resp = requests.post(BASE_URL, json={
            "model": "ray-v1",
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": f"{data_summary}\n{historical_wisdom}\n\n{ONE_SHOT_EXAMPLE}\n\nNow output JSON:"}
            ],
            "format": "json",
            "temperature": 0.1,
            "stream": False
        }, timeout=30)

        raw_response = resp.json().get("message", {}).get("content", "")

        # 提取 JSON
        extracted = extract_json(raw_response)
        if not extracted:
            return {"error": "no_valid_json", "raw": str(raw_response)[:200]}

        result = json.loads(extracted)

        # 結構性保障：stop_loss 格式修正（8.0 → 0.08）
        if isinstance(result.get('stop_loss'), (int, float)) and result['stop_loss'] > 1:
            result['stop_loss'] = round(result['stop_loss'] / 100, 4)

        # 完整性檢查
        required = ['strategy_name', 'indicator', 'params', 'entry_condition', 'stop_loss', 'confidence']
        missing = [f for f in required if f not in result]
        if missing:
            return {"error": f"missing_fields: {missing}", "raw": str(raw_response)[:200]}

        return result

    except Exception as e:
        return {"error": f"boost_failed: {str(e)[:100]}"}


def extract_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            json.loads(m.group(1).strip())
            return m.group(1).strip()
        except:
            pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            json.loads(text[start:end])
            return text[start:end]
        except:
            pass
    return None


# ============================================================
# CLI 測試
# ============================================================

if __name__ == "__main__":
    test = {
        'symbol': 'NVDA',
        'price': 950,
        'ema20': 940,
        'rsi14': 42,
        'rsi2': 22,
        'macd_hist': 0.5,
        'sharpe_30d': 1.2,
        'mdd_30d': 0.12,
        'indicator': 'RSI2',
    }

    print("=== Ray Integrity Booster Test ===")
    result = get_enhanced_proposal('NVDA', test)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        print(f"   Raw: {str(result.get('raw', ''))[:200]}")
    else:
        print(f"✅ Strategy: {result.get('strategy_name')}")
        print(f"   Indicator: {result.get('indicator')}")
        print(f"   stop_loss: {result.get('stop_loss')}")
        print(f"   take_profit: {result.get('take_profit')}")
        print(f"   confidence: {result.get('confidence')}")
        print(f"   risk_reason: {(result.get('risk_reason') or '')[:80]}")
        print(f"   source: {result.get('source')}")
        print()
        print("三維優化效果：")
        print("  ✅ 正確性：RAG 檢索 + 大師邏輯錨定")
        print("  ✅ 完整性：CoT 指令 + 強制檢查清單")
        print("  ✅ 結構性：One-Shot + JSON Mode + 自動修復")