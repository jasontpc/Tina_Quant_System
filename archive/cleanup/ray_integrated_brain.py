# -*- coding: utf-8 -*-
"""
ray_integrated_brain.py — LLM 與核心腳本整合
整合：
- ray_brain.py (三層推理)
- ray_data_center.py (yfinance 數據)
- ray_tw_api.py (Shioaji 台股數據)
- ray_tw_fetcher.py (twstock 備用)
- backtest_reports (策略庫)
- wisdom_corrections (修正庫)
"""
import sys, os, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np

DB = 'ray_wisdom.db'

# ── Router 導入 ──────────────────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

OLLAMA_URL = "http://localhost:11434/api/chat"

# ============================================================
# 1. 數據整合層
# ============================================================

class DataHub:
    """統一台股/美股數據獲取"""

    def __init__(self):
        self._sj = None
        self._cache = {}

    def get_shioaji(self):
        if self._sj is None:
            import shioaji as sj
            self._sj = sj.Shioaji()
            self._sj.login(
                api_key="3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW",
                secret_key="FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF"
            )
        return self._sj

    def get_us_data(self, symbol, period="1y"):
        """yfinance 美股數據"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            return df
        except:
            return None

    def get_tw_data(self, symbol):
        """Shioaji 台股數據"""
        try:
            api = self.get_shioaji()
            code = symbol.replace(".TW", "")
            contract = api.Contracts.Stocks[code]
            kbars = api.kbars(contract, start="2024-01-01", end="2026-05-12")
            import pandas as pd
            df = pd.DataFrame({
                'Date': pd.to_datetime(kbars.ts, unit='ns').dt.strftime('%Y-%m-%d'),
                'Open': kbars.Open,
                'High': kbars.High,
                'Low': kbars.Low,
                'Close': kbars.Close,
                'Volume': kbars.Volume
            })
            return df
        except Exception as e:
            return None

    def get_indicators(self, df):
        """計算指標"""
        if df is None or df.empty:
            return {}
        close = df['Close'].values
        # RSI
        delta = np.diff(close)
        gain = np.clip(delta, 0, None).mean()
        loss = np.clip(-delta, 0, None).mean()
        rs = gain / loss if loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
        # MA
        ma5 = close[-5:].mean() if len(close) >= 5 else close.mean()
        ma20 = close[-20:].mean() if len(close) >= 20 else close.mean()
        # Sharpe
        returns = np.diff(close) / close[:-1]
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        return {
            "rsi": round(rsi, 1),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "sharpe": round(sharpe, 2),
            "price": round(close[-1], 2),
            "volume": int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
        }

# ============================================================
# 2. 策略查詢層
# ============================================================

class StrategyHub:
    """策略庫查詢"""

    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.c = self.conn.cursor()

    def get_top_strategies(self, symbol, limit=5):
        """取得標的最佳策略"""
        self.c.execute('''
            SELECT strategy_name, sharpe_ratio, max_drawdown, win_rate, num_trades
            FROM backtest_reports
            WHERE symbol=? AND sharpe_ratio > 0
            ORDER BY sharpe_ratio DESC
            LIMIT ?
        ''', (symbol, limit))
        return self.c.fetchall()

    def get_indicator_strategies(self, indicator, limit=5):
        """取得指標最佳策略"""
        self.c.execute('''
            SELECT symbol, strategy_name, sharpe_ratio, max_drawdown
            FROM backtest_reports
            WHERE indicator=? AND sharpe_ratio > 0
            ORDER BY sharpe_ratio DESC
            LIMIT ?
        ''', (indicator, limit))
        return self.c.fetchall()

    def close(self):
        self.conn.close()

# ============================================================
# 3. Wisdom 修正層
# ============================================================

class WisdomHub:
    """wisdom_corrections 查詢"""

    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.c = self.conn.cursor()

    def get_relevant_corrections(self, symbol, confidence=0.7):
        """取得相關修正"""
        self.c.execute('''
            SELECT diagnosis, corrected_json, confidence, meta_label
            FROM wisdom_corrections
            WHERE (symbol=? OR symbol='GLOBAL') AND confidence >= ?
            ORDER BY confidence DESC
            LIMIT 5
        ''', (symbol, confidence))
        return self.c.fetchall()

    def get_all_corrections(self, limit=10):
        """取得所有高信心修正"""
        self.c.execute('''
            SELECT symbol, diagnosis, confidence
            FROM wisdom_corrections
            WHERE confidence >= 0.8
            ORDER BY confidence DESC
            LIMIT ?
        ''', (limit,))
        return self.c.fetchall()

    def close(self):
        self.conn.close()

# ============================================================
# 4. LLM 整合層
# ============================================================

class LLMAdvisor:
    """整合 LLM 給出建議（走 Router 分層）"""

    def __init__(self):
        self.model_fast = "ray-deep-v1"  # Jo 指定全本地分析走 ray-deep-v1
        self.model_deep = "ray-deep-v1"  # Jo 指定統一走 ray-deep

    def ask(self, prompt, model="ray-deep-v1", layer=1):
        """
        詢問 LLM（走 Router）
        layer=1: 快速（ray-deep-v1 本地）
        layer=2: 深度（MiniMax）
        layer=3: 連網（MiniMax + web）
        """
        if ROUTER and HAS_ROUTER:
            try:
                if layer == 1:
                    return ROUTER.fast(prompt=prompt)
                elif layer == 2:
                    return ROUTER.deep(prompt=prompt)
                elif layer == 3:
                    return ROUTER.web(prompt=prompt)
            except Exception:
                pass  # 降級到直接 Ollama

        # 降級：直接走 Ollama
        try:
            import requests
            resp = requests.post(OLLAMA_URL, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }, timeout=60)
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def propose_signal(self, symbol, indicators, strategies, corrections, layer=2):
        """
        提出交易信號（預設走 Router Layer 2 → MiniMax）
        layer=1: 快速但淺（ray-v1）
        layer=2: 深度（MiniMax）
        layer=3: 連網（MiniMax + web）
        """
        """提出交易信號"""
        prompt = f"""你是 Ray 量化大腦。分析以下資料並給出交易建議。

標的：{symbol}
指標：{indicators}
歷史策略：{strategies}
修正記錄：{corrections}

輸出 JSON：
{{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "reason": "原因", "action": "具體行動"}}
"""
        # 嘗試解析 JSON（保持現有邏輯）
        import re
        m = re.search(r'\{[\s\S]*\}', result)
        if m:
            return json.loads(m.group())
        return {"signal": "ERROR", "reason": result}

# ============================================================
# 5. 整合分析
# ============================================================

def analyze_symbol(symbol):
    """完整分析單一標的"""
    print(f"=== 分析 {symbol} ===")

    dh = DataHub()
    sh = StrategyHub()
    wh = WisdomHub()
    llm = LLMAdvisor()

    # 1. 取得數據
    if ".TW" in symbol:
        df = dh.get_tw_data(symbol)
    else:
        df = dh.get_us_data(symbol)

    indicators = dh.get_indicators(df)
    print(f"指標: {indicators}")

    # 2. 查詢策略
    strategies = sh.get_top_strategies(symbol)
    print(f"策略: {strategies[:3]}")

    # 3. 查詢修正
    corrections = wh.get_relevant_corrections(symbol)
    print(f"修正: {corrections[:3]}")

    # 4. LLM 建議
    signal = llm.propose_signal(symbol, indicators, strategies, corrections)
    print(f"信號: {signal}")

    # 5. 寫入 signals_log
    if signal.get("signal") != "ERROR":
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT INTO signals_log
            (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, symbol, "INTEGRATED_BRAIN", signal.get("confidence", 0),
             indicators.get("sharpe", 0), 0, 0,
             signal.get("signal", "WATCH"), 0,
             json.dumps({"indicators": indicators, "signal": signal})))
        conn.commit()
        conn.close()
        print(f"已寫入 signals_log")

    sh.close()
    wh.close()

    return {
        "symbol": symbol,
        "indicators": indicators,
        "strategies": strategies,
        "corrections": corrections,
        "signal": signal
    }

# ============================================================
# 6. 批量分析
# ============================================================

def batch_analyze():
    """批量分析所有關注標的"""
    symbols = [
        "VTI", "VOO", "QQQ", "BND", "VEA",  # 美股 ETF
        "2330.TW", "2454.TW", "2317.TW"       # 台股
    ]

    print(f"=== 批量分析 {len(symbols)} 檔 ===")
    results = []
    for sym in symbols:
        try:
            result = analyze_symbol(sym)
            results.append(result)
        except Exception as e:
            print(f"分析失敗 {sym}: {e}")
        time.sleep(2)

    return results

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    print("=== Ray 整合大腦 ===")
    print()

    # 分析單一標的
    result = analyze_symbol("VOO")
    print()
    print("=== 完成 ===")