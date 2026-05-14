# -*- coding: utf-8 -*-
"""
ray_retriever_v2.py — 增強版 RAG 檢索（根據 Jo 的設計優化）
功能：
1. 根據 meta_label 分類（均值回歸/趨勢追隨/波段操作/防守）
2. 根據 symbol 類型（科技股/ETF/期貨）檢索相似案例
3. 根據技術指標狀態（RSI超賣/MACD金叉）檢索對應大師建議
"""

import json, sqlite3, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = "ray_wisdom.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ============================================================
# 策略類型分類
# ============================================================

STRATEGY_TYPES = {
    "mean_reversion": ["RSI2", "RSI_CONNORS", "RSI_THRESHOLD", "BBANDS", "STOCH"],
    "momentum": ["MOMENTUM", "MOMENTUM_60", "EMA_CROSS", "MACD_CROSS"],
    "swing": ["VEGAS_TUNNEL", "VEGA_144", "SWING_20"],
    "defensive": ["BND", "BONDS", "PROTECT", "STOP_LOSS"],
}

INDICATOR_MAPPING = {
    "RSI2": "mean_reversion",
    "RSI_CONNORS": "mean_reversion",
    "RSI": "mean_reversion",
    "BBANDS": "mean_reversion",
    "MOMENTUM": "momentum",
    "MOMENTUM_60": "momentum",
    "EMA_CROSS": "momentum",
    "MACD_CROSS": "momentum",
    "VEGAS_TUNNEL": "swing",
    "VEGA_144": "swing",
}

# ============================================================
# 核心檢索函式
# ============================================================

def classify_strategy_type(indicator):
    """根據指標名稱分類策略類型"""
    ind_upper = indicator.upper()
    for stype, indicators in INDICATOR_MAPPING.items():
        if stype in ind_upper:
            return INDICATOR_MAPPING[stype]
    return None

def retrieve_by_strategy_type(strategy_type, limit=5):
    """根據策略類型檢索修正案例"""
    c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label
                  FROM wisdom_corrections
                  WHERE meta_label LIKE ? OR corrected_json LIKE ?
                  ORDER BY confidence DESC LIMIT ?''',
              [f'%{strategy_type}%', f'%{strategy_type}%', limit])
    return c.fetchall()

def retrieve_by_symbol_type(symbol, limit=5):
    """根據標的類型檢索（科技股/ETF/藍籌）"""
    symbol_upper = symbol.upper()
    if any(s in symbol_upper for s in ['NVDA', 'TSLA', 'META', 'AAPL', 'MSFT', 'AMZN']):
        type_filter = 'US_TECH'
    elif any(s in symbol_upper for s in ['VTI', 'VOO', 'QQQ', 'BND', 'VEA']):
        type_filter = 'US_ETF'
    elif any(s in symbol_upper for s in ['SPY', 'QQQ', 'DIA']):
        type_filter = 'INDEX_ETF'
    else:
        type_filter = 'OTHER'

    c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence
                  FROM wisdom_corrections
                  WHERE meta_label = ? OR symbol = ?
                  ORDER BY confidence DESC LIMIT ?''',
              [type_filter, symbol, limit])
    return c.fetchall()

def retrieve_by_indicator_state(indicator, value, limit=3):
    """根據指標狀態檢索（RSI < 30 超賣 / RSI > 70 超買）"""
    if 'RSI' in indicator.upper():
        if value < 30:
            state = 'oversold'
        elif value > 70:
            state = 'overbought'
        else:
            state = 'neutral'
        c.execute('''SELECT axiom_id, symbol, diagnosis, confidence
                      FROM wisdom_corrections
                      WHERE (diagnosis LIKE ? OR diagnosis LIKE ?)
                      AND confidence >= 0.7
                      ORDER BY confidence DESC LIMIT ?''',
                  [f'%{state}%', f'%RSI%', limit])
        return c.fetchall()
    return []

def build_enhanced_context(symbol, indicator=None, indicator_value=None):
    """
    增強版 RAG Context 建構
    根據 Jo 的設計：根據市場特徵動態注入相關修正案例
    """
    ctx = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
        "strategy_type": None,
        "retrieved_knowledge": [],
    }

    # 1. 根據策略類型檢索
    if indicator:
        strategy_type = classify_strategy_type(indicator)
        if strategy_type:
            ctx["strategy_type"] = strategy_type
            strat_corrs = retrieve_by_strategy_type(strategy_type, limit=5)
            ctx["retrieved_knowledge"].append({
                "type": "strategy_type",
                "category": strategy_type,
                "cases": [{"axiom_id": r["axiom_id"], "diagnosis": r["diagnosis"][:100], "confidence": r["confidence"]} for r in strat_corrs]
            })

    # 2. 根據標的類型檢索
    symbol_corrs = retrieve_by_symbol_type(symbol, limit=5)
    if symbol_corrs:
        ctx["retrieved_knowledge"].append({
            "type": "symbol_type",
            "cases": [{"symbol": r["symbol"], "diagnosis": r["diagnosis"][:100], "confidence": r["confidence"]} for r in symbol_corrs]
        })

    # 3. 根據指標狀態檢索
    if indicator and indicator_value is not None:
        indicator_state_corrs = retrieve_by_indicator_state(indicator, indicator_value, limit=3)
        if indicator_state_corrs:
            ctx["retrieved_knowledge"].append({
                "type": "indicator_state",
                "indicator": indicator,
                "value": indicator_value,
                "cases": [{"diagnosis": r["diagnosis"][:100], "confidence": r["confidence"]} for r in indicator_state_corrs]
            })

    return ctx

def format_enhanced_prompt(ctx):
    """格式化增強版提示詞"""
    lines = []
    lines.append("=== Retrieved Master Knowledge（檢索到的大師建議）===")

    for knowledge in ctx.get("retrieved_knowledge", []):
        ktype = knowledge["type"]
        cases = knowledge["cases"]

        if ktype == "strategy_type":
            category = knowledge["category"]
            lines.append(f"\n【{category.upper()} 策略修正】")
            for case in cases:
                lines.append(f"  • {case['diagnosis']} (conf={case['confidence']:.2f})")

        elif ktype == "symbol_type":
            lines.append(f"\n【同類型標的修正案例】")
            for case in cases:
                lines.append(f"  • [{case['symbol']}] {case['diagnosis']} (conf={case['confidence']:.2f})")

        elif ktype == "indicator_state":
            ind = knowledge["indicator"]
            val = knowledge["value"]
            lines.append(f"\n【指標狀態：{ind}={val}】")
            for case in cases:
                lines.append(f"  • {case['diagnosis']} (conf={case['confidence']:.2f})")

    if not ctx.get("retrieved_knowledge"):
        lines.append("\n(No prior knowledge found)")

    return "\n".join(lines)

# ============================================================
# CLI 測試
# ============================================================

if __name__ == "__main__":
    import sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    indicator = sys.argv[2] if len(sys.argv) > 2 else "RSI2"
    indicator_value = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0

    print(f"=== Enhanced RAG Test ===")
    print(f"Symbol: {symbol} | Indicator: {indicator} | Value: {indicator_value}")
    print()

    ctx = build_enhanced_context(symbol, indicator, indicator_value)
    print(f"Strategy type: {ctx['strategy_type']}")
    print(f"Retrieved knowledge items: {len(ctx['retrieved_knowledge'])}")
    print()

    prompt = format_enhanced_prompt(ctx)
    print(prompt)

conn.close()