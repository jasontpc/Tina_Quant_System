# -*- coding: utf-8 -*-
"""
ray_retriever.py — 動態 RAG 檢索系統
讓 1.5B 在推論時能即時參考 wisdom_corrections

功能：
1. 根據輸入標的/指標，從 wisdom_corrections 檢索相似案例
2. 根據輸入標的，從 backtest_reports 檢索最優策略
3. 將檢索結果注入 Prompt，供 1.5B 使用
4. 實現「對抗校準」：confidence < 0.5 時自動觸發 7B 複審
"""

import json, sqlite3, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = "ray_wisdom.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ============================================================
# 核心檢索函式
# ============================================================

def retrieve_corrections(symbol=None, indicator=None, confidence_min=0.7, limit=5):
    """
    根據標的或指標檢索高信心 wisdom_corrections
    """
    query = '''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label
                FROM wisdom_corrections 
                WHERE confidence >= ?
                ORDER BY confidence DESC'''
    params = [confidence_min]
    
    if symbol:
        query += ' AND (symbol = ? OR symbol = ? OR symbol = "UNKNOWN")'
        # 嘗試匹配（移除 .TW 後綴）
        symbol_plain = symbol.replace('.TW', '')
        params.extend([symbol, symbol_plain])
    
    if indicator:
        query += ' AND corrected_json LIKE ?'
        params.append(f'%"{indicator}"%')
    
    query += ' ORDER BY confidence DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    return c.fetchall()

def retrieve_strategies(symbol=None, indicator=None, sharpe_min=0.8, limit=5):
    """
    根據標的或指標檢索最優 backtest_reports
    """
    query = '''SELECT strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, win_rate
                FROM backtest_reports 
                WHERE sharpe_ratio >= ?'''
    params = [sharpe_min]
    
    if symbol:
        symbol_plain = symbol.replace('.TW', '')
        query += ' AND (symbol = ? OR symbol = ?)'
        params.extend([symbol, symbol_plain])
    
    if indicator:
        query += ' AND indicator = ?'
        params.append(indicator)
    
    query += ' ORDER BY sharpe_ratio DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    return c.fetchall()

def retrieve_failed_patterns(symbol=None, indicator=None, limit=5):
    """
    檢索失敗模式（用於風險提示）
    """
    query = '''SELECT wl.id, wl.axiom_json, wl.reflection, wc.diagnosis
                FROM wisdom_logs wl
                LEFT JOIN wisdom_corrections wc ON wl.id = wc.axiom_id
                WHERE wl.passed = 0'''
    params = []
    
    if symbol:
        # 透過 backtest_reports 找相關標的
        query += ''' AND EXISTS (
            SELECT 1 FROM backtest_reports br 
            WHERE br.symbol = ? AND br.id = wl.backtest_id
        )'''
        symbol_plain = symbol.replace('.TW', '')
        params.append(symbol_plain)
    
    if indicator:
        query += ' AND wl.axiom_json LIKE ?'
        params.append(f'%"{indicator}"%')
    
    query += ' ORDER BY wl.id DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    return c.fetchall()

def build_rag_context(symbol, indicator=None):
    """
    為 symbol 建構完整的 RAG context（用於注入 Prompt）
    """
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    c2 = conn2.cursor()

    ctx = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
    }

    # 檢索高信心修正
    c2.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label
                  FROM wisdom_corrections
                  WHERE confidence >= 0.7
                  ORDER BY confidence DESC LIMIT 5''')
    corrs_raw = c2.fetchall()
    ctx["corrections"] = [
        {
            "axiom_id": r["axiom_id"],
            "symbol": r["symbol"],
            "diagnosis": r["diagnosis"][:150] if r["diagnosis"] else "",
            "confidence": r["confidence"],
        }
        for r in corrs_raw
    ]

    # 檢索最優策略
    c2.execute('''SELECT strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, win_rate
                  FROM backtest_reports
                  WHERE sharpe_ratio >= 0.8
                  ORDER BY sharpe_ratio DESC LIMIT 5''')
    strat_raw = c2.fetchall()
    ctx["strategies"] = [
        {
            "strategy_name": r["strategy_name"],
            "indicator": r["indicator"],
            "sharpe": r["sharpe_ratio"],
            "mdd": r["max_drawdown"],
            "win_rate": r["win_rate"],
        }
        for r in strat_raw
    ]

    # 檢索失敗模式（使用 diagnosis 作為反思）
    c2.execute('''SELECT diagnosis, meta_label FROM wisdom_corrections
                  WHERE diagnosis IS NOT NULL AND LENGTH(diagnosis) > 10
                  ORDER BY confidence DESC LIMIT 3''')
    failed_raw = c2.fetchall()
    ctx["failed_patterns"] = [
        {
            "diagnosis": r["diagnosis"][:100] if r["diagnosis"] else "",
            "meta_label": r["meta_label"] or "",
        }
        for r in failed_raw
    ]

    conn2.close()
    return ctx

def format_rag_prompt(ctx):
    """
    將 RAG context 格式化為字串，用於注入 Prompt
    """
    lines = []
    lines.append("=== RAG Context ( Retrieved Knowledge ) ===")
    
    if ctx.get("corrections"):
        lines.append("\n【Recent Corrections (High Confidence)】")
        for corr in ctx["corrections"]:
            lines.append(f"• [{corr['symbol']}] {corr['diagnosis']} (conf={corr['confidence']:.2f})")
    
    if ctx.get("strategies"):
        lines.append("\n【Top-Performing Strategies】")
        for s in ctx["strategies"]:
            lines.append(f"• {s['strategy_name']} ({s['indicator']}): Sharpe={s['sharpe']:.2f}, MDD={s['mdd']:.2%}")
    
    if ctx.get("failed_patterns"):
        lines.append("\n【Warning: Failed Patterns to Avoid】")
        for f in ctx["failed_patterns"]:
            if f["diagnosis"]:
                lines.append(f"• {f['diagnosis']}")
            elif f["reflection"]:
                lines.append(f"• {f['reflection']}")
    
    if not any([ctx.get("corrections"), ctx.get("strategies"), ctx.get("failed_patterns")]):
        lines.append("\n(No prior knowledge found for this symbol)")
    
    return "\n".join(lines)

# ============================================================
# 對抗校準（Co-Inference Alignment）
# ============================================================

def check_confidence_threshold(strategy, threshold=0.5):
    """
    檢查策略 confidence 是否需要 7B 複審
    """
    if isinstance(strategy, dict):
        conf = strategy.get("confidence", 1)
        return conf < threshold
    return False

def should_trigger_7b_review(indicators, threshold_mdd=0.20):
    """
    根據指標判斷是否需要 7B 深度分析
    """
    # MDD 過高
    if indicators.get("mdd_30d", 0) > threshold_mdd:
        return True
    # RSI 極端值
    rsi = indicators.get("rsi14", 50)
    if rsi < 20 or rsi > 80:
        return True
    # 價格低於均線
    if not indicators.get("above_ma20", True):
        return True
    return False

# ============================================================
# 主函数：ray_retriever inference
# ============================================================

def retrieve_and_enrich(symbol, indicator=None, indicators=None):
    """
    完整流程：檢索 + 建構 context + 決定是否觸發 7B
    返回：{'rag_context', 'needs_7b', 'strategy'}
    """
    # 建構 RAG context
    ctx = build_rag_context(symbol, indicator)
    rag_prompt = format_rag_prompt(ctx)
    
    # 檢查是否需要 7B 複審
    needs_7b = False
    if indicators:
        needs_7b = should_trigger_7b_review(indicators)
    
    return {
        "rag_context": rag_prompt,
        "needs_7b": needs_7b,
        "symbol": symbol,
        "corrections_count": len(ctx.get("corrections", [])),
        "strategies_count": len(ctx.get("strategies", [])),
    }

# ============================================================
# CLI 測試
# ============================================================

if __name__ == "__main__":
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    indicator = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"=== Ray Retriever Test ===")
    print(f"Symbol: {symbol} | Indicator: {indicator}")
    print()
    
    # 建構 context
    ctx = build_rag_context(symbol, indicator)
    print(f"Corrections found: {len(ctx['corrections'])}")
    print(f"Strategies found: {len(ctx['strategies'])}")
    print(f"Failed patterns: {len(ctx['failed_patterns'])}")
    print()
    
    # 格式化
    rag_prompt = format_rag_prompt(ctx)
    print("=== RAG Context ===")
    print(rag_prompt)
    print()
    
    # 測試 confidence 檢查
    test_strategy = {"strategy_name": "TEST", "confidence": 0.3}
    needs_7b = check_confidence_threshold(test_strategy, threshold=0.5)
    print(f"Strategy confidence=0.3 → needs_7b_review: {needs_7b}")

conn.close()