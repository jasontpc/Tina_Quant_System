# -*- coding: utf-8 -*-
"""Ray Brain - Qwen 路由层 + 本地脚本协调器 (v3 - Router版)"""

import json, re, sqlite3, time
from typing import Dict, List, Optional

# ── Router 導入（統一 LLM 調度）────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

BASE_URL = "http://localhost:11434/api/chat"

# ── Ray 核心模組 ──────────────────────────────────────────────
try:
    from ray_data_center import RayDataCenter
    from ray_engine import RayEngine
    from ray_nl2code import NL2CodeValidator
    from ray_retriever_v2 import build_enhanced_context, format_enhanced_prompt, classify_strategy_type
    HAS_RAY = True
    HAS_RETRIEVER = True
except ImportError:
    HAS_RAY = False
    HAS_RETRIEVER = False


class RayBrain:
    def __init__(self):
        self.fast_model = "ray-v3.5"       # 固化後的4B指揮官（含大師天條）
        self.deep_model = "qwen2.5:7b"          # Jo 指定：7B 負責複雜反思蒸餾
        self.db = RayDataCenter() if HAS_RAY else None
        self.engine = RayEngine() if HAS_RAY else None
        self.validator = NL2CodeValidator(auto_correct=True) if HAS_RAY else None

    # ══════════════════════════════════════════════════════════
    # Layer 0: 本地 Python（不需要 LLM）
    # ══════════════════════════════════════════════════════════

    def local_indicators(self, symbol: str) -> Dict:
        """用本地 Python 计算技术指标（不需要 LLM）"""
        if not HAS_RAY:
            return {"error": "ray modules not available"}

        try:
            import yfinance as yf
            df = yf.Ticker(symbol).history(period="60d", interval="1d", auto_adjust=True)
            if df is None or len(df) < 20:
                return {"symbol": symbol, "error": "insufficient data"}

            close = df["Close"].values.astype(float)
            high  = df["High"].values.astype(float)
            low   = df["Low"].values.astype(float)

            def ema(c, n):
                e = [c[0]] * len(c)
                a = 2 / (n + 1)
                for i in range(1, len(c)):
                    e[i] = c[i] * a + e[i - 1] * (1 - a)
                return e

            m20 = ema(close, 20)
            m60 = ema(close, 60)
            ef  = ema(close, 12)
            es  = ema(close, 26)
            mac = [ef[i] - es[i] for i in range(len(ef))]
            sigv = ema(mac, 9)
            mh = [mac[i] - sigv[i] for i in range(len(mac))]

            # RSI
            d = [0] + [close[i] - close[i - 1] for i in range(1, len(close))]
            g = [max(d[i], 0) for i in range(len(d))]
            l = [max(-d[i], 0) for i in range(len(d))]
            ag = list(g)
            al = list(l)
            for i in range(14, len(g)):
                ag[i] = ag[i - 1] * 13 / 14 + g[i]
                al[i] = al[i - 1] * 13 / 14 + l[i]
            rs = [ag[i] / al[i] if al[i] > 0 else 50 for i in range(14, len(ag))]
            rsi14 = sum(rs[-15:]) / 15 if len(rs) >= 15 else 50

            # RSI2 (Connors)
            def rsi2_calc(close, period=2):
                delta = [0] + [close[i] - close[i - 1] for i in range(1, len(close))]
                up = [max(d, 0) for d in delta]
                dn = [max(-d, 0) for d in delta]
                rs_up = [0] * period + [sum(up[i - period:i]) / period for i in range(period, len(up))]
                rs_dn = [0] * period + [sum(dn[i - period:i]) / period for i in range(period, len(dn))]
                return [100 - 100 / (1 + rs_up[i] / rs_dn[i]) if rs_dn[i] > 0 else 50 for i in range(len(close))]

            rsi2_vals = rsi2_calc(close, 2)
            rsi2_val = rsi2_vals[-1] if len(rsi2_vals) > 0 else rsi14

            # KDJ
            n = 9
            k = [50] * n
            d_k = [50] * n
            for i in range(n, len(close)):
                rr = high[i - n:i + 1]
                ll = low[i - n:i + 1]
                r = max(rr) if max(rr) > 0 else close[i]
                r2 = min(rr) if min(rr) > 0 else close[i]
                k_val = 50 if r == r2 else (close[i] - r2) / (r - r2) * 100
                k.append(k_val)
                d_k.append(k[-1] * 0.5 + d_k[-1] * 0.5)
            kdj_j = k[-1] - 2 * d_k[-1] if len(k) > 2 else 0

            price = close[-1]
            above_ma20 = price > m20[-1]
            above_ma60 = price > m60[-1]
            macd_bull = mh[-1] > 0
            kdj_bull = kdj_j > 0

            mom_5d = (close[-1] - close[-6]) / close[-6] * 100 if len(close) >= 6 else 0

            # Sharpe / MDD / WinRate（30日滾動）
            ret = [0] + [(close[i] - close[i - 1]) / close[i - 1] * 100 for i in range(1, len(close))]
            window = min(30, len(ret))
            rets = ret[-window:]
            avg_r = sum(rets) / len(rets) if rets else 0
            std_r = (sum((x - avg_r) ** 2 for x in rets) / len(rets)) ** 0.5 if len(rets) > 1 else 0.01
            sharpe_30d = avg_r / std_r * (252 ** 0.5) if std_r > 0 else 0

            cummax = [max(close[:i + 1]) for i in range(len(close))]
            dd = [(cummax[i] - close[i]) / cummax[i] * 100 for i in range(len(close))]
            mdd_30d = min(dd[-window:]) / 100 if dd else 0

            wins = sum(1 for i in range(1, len(ret)) if ret[i] > 0)
            win_rate_30d = wins / len(ret) if len(ret) > 1 else 0

            math_passed = (sharpe_30d >= 1.0) and (mdd_30d <= 0.20) and (win_rate_30d >= 0.35)

            return {
                "symbol": symbol,
                "price": round(float(price), 2),
                "ema20": round(float(m20[-1]), 2),
                "ema60": round(float(m60[-1]), 2),
                "macd_hist": round(float(mh[-1]), 4),
                "rsi14": round(float(rsi14), 2),
                "rsi2": round(float(rsi2_val), 2),
                "kdj_j": round(float(kdj_j), 2),
                "mom_5d": round(float(mom_5d), 2),
                "above_ma20": above_ma20,
                "above_ma60": above_ma60,
                "macd_bull": macd_bull,
                "kdj_bull": kdj_bull,
                "sharpe_30d": round(float(sharpe_30d), 3),
                "mdd_30d": round(float(mdd_30d), 4),
                "win_rate_30d": round(float(win_rate_30d), 4),
                "math_passed": math_passed,
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    # ══════════════════════════════════════════════════════════
    # Memory Injection: 3-layer context for fast_model
    # Structure: [K-line] + [32GB RAM axioms] + [Today's warning] = JSON
    # ══════════════════════════════════════════════════════════
    def _load_memory_context(self) -> str:
        """Load axioms_v3.5.json (from 32GB RAM store) + web_auto warnings."""
        parts = []

        # Layer 1: Load axioms_v3.5.json (historical distilled lessons)
        axioms_path = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term\axioms_v3.5.json"
        try:
            with open(axioms_path, 'r', encoding='utf-8') as f:
                axioms = json.load(f)
            if axioms and isinstance(axioms, list):
                parts.append("【10條蒸餾交易準則】（歷史教訓，智力灌頂結果）")
                for a in axioms[:10]:
                    if isinstance(a, dict):
                        parts.append(f"  [{a.get('id','?')}] {a.get('axiom','')} ({a.get('type','')})")
                parts.append("")
        except Exception:
            pass

        # Layer 2: Load latest web_auto warnings from wisdom_corrections
        try:
            db_path = os.path.join(os.path.dirname(__file__), "ray_wisdom.db")
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('''SELECT web_auto, created_at FROM wisdom_corrections
                         WHERE web_auto IS NOT NULL
                         ORDER BY created_at DESC LIMIT 5''')
            rows = c.fetchall()
            conn.close()
            if rows:
                parts.append("【今日大師警示】（web_auto 實時注入）")
                for web_auto_json, created in rows:
                    try:
                        w = json.loads(web_auto_json)
                        parts.append(f"  [{w.get('master','?')}] {w.get('risk_level','?')}: {w.get('warning','')} | 門檻: {w.get('threshold','')}")
                    except:
                        pass
                parts.append("")
        except Exception:
            pass

        return "\n".join(parts) if parts else ""

    # ══════════════════════════════════════════════════════════
    # Layer 1: 快速策略提案（走 Router → qwen3.5-4b-iq4xs 本地）
    # ══════════════════════════════════════════════════════════

    def fast_propose(self, indicators: Dict) -> Dict:
        """用 1.5B 对已计算的指标快速输出策略 JSON（走 Router Layer 1）"""
        symbol = indicators.get('symbol', 'N/A')
        rsi2 = indicators.get('rsi2', 50)
        gate = "PASSED" if indicators.get("math_passed") else "FAILED"

        # ── RAG Context（可選）──────────────────────────────────
        rag_context = ""
        if HAS_RETRIEVER:
            try:
                ctx_obj = build_enhanced_context(
                    symbol=symbol,
                    indicator="RSI2",
                    indicator_value=rsi2
                )
                rag_context = format_enhanced_prompt(ctx_obj)
                if ctx_obj.get('retrieved_knowledge'):
                    rag_context = f"\n{rag_context}\n"
            except Exception:
                rag_context = ""

        # ── 3-Layer Memory Context（32GB RAM axioms + web_auto）──
        memory_ctx = self._load_memory_context()

        # ── 構建 prompt ─────────────────────────────────────────
        ctx = (
            f"【當前K線數據】\n"
            f"Symbol: {symbol}\n"
            f"Price: ${indicators.get('price', 'N/A')}\n"
            f"EMA20: {indicators.get('ema20')} | EMA60: {indicators.get('ema60')}\n"
            f"MACD Hist: {indicators.get('macd_hist')} | RSI14: {indicators.get('rsi14')} | RSI2: {rsi2}\n"
            f"KDJ J: {indicators.get('kdj_j')} | Mom 5D: {indicators.get('mom_5d')}%\n"
            f"Sharpe: {indicators.get('sharpe_30d')} | MDD: {indicators.get('mdd_30d')} | Win: {indicators.get('win_rate_30d')}\n"
            f"Math Gate: {gate}\n"
            f"{rag_context}"
            f"{memory_ctx}"
        )

        # ── 走 Router Layer 1（ray-v1 本地）────────────────────
        if ROUTER and HAS_ROUTER:
            try:
                result_text = ROUTER.fast(prompt=ctx)
                text = self._extract_json(result_text)
                result = json.loads(text)
            except Exception as e:
                return {"error": f"router.fast failed: {str(e)[:100]}"}
        else:
            # 降級：直接走 requests（舊相容）
            import requests
            payload = {
                "model": self.fast_model,
                "messages": [
                    {"role": "system", "content": "You are Ray Fast Logic Unit. Output ONLY JSON with strategy_name (UPPER_SNAKE), indicator, params, entry_condition, stop_loss. No text outside JSON."},
                    {"role": "user",   "content": f"Data:\n{ctx}\n\nOutput JSON: {{\"strategy_name\":\"...\",\"indicator\":\"...\",\"params\":{{}},\"?entry_condition\":{{}},\"stop_loss\":0.0}}\n"}
                ],
                "temperature": 0.1,
                "stream": False,
            }
            resp = requests.post(BASE_URL, json=payload, timeout=30)
            resp.raise_for_status()
            text = self._extract_json(resp.json()["message"]["content"])
            result = json.loads(text)

        # ── NL2Code 二次驗證 + 自動修正 ────────────────────────
        if self.validator:
            is_valid, corrected, errs = self.validator.validate(result)
            if is_valid:
                if self.validator.corrections:
                    result = corrected
            else:
                if corrected:
                    result = corrected
                else:
                    return {"error": f"NL2Code rejected: {errs[0]}", "raw": text[:200]}

        # ── 安全檢查：補全結構 ──────────────────────────────────
        if "entry_condition" not in result or not result["entry_condition"]:
            result["entry_condition"] = {"operator": ">", "threshold": 0}
        if "stop_loss" not in result or not result["stop_loss"]:
            result["stop_loss"] = 0.08
        if "params" not in result:
            result["params"] = {}

        return result

    # ══════════════════════════════════════════════════════════
    # Layer 1.5: 3B 實戰指揮官（ray-v3 大師對齊模式）
    # ══════════════════════════════════════════════════════════

    def v3_commander_propose(self, symbol: str, indicators: Dict) -> Dict:
        """
        使用 ray-v3 Quant Commander（大師對齊模式）
        動態注入 RAG 上下文（歷史修正 + 連網智慧）
        輸出嚴格 JSON Schema
        """
        task = f"分析 {symbol}，輸出交易信號 JSON Schema"

        if ROUTER and HAS_ROUTER:
            try:
                result_text = ROUTER.v3_commander(
                    symbol=symbol,
                    indicators=indicators,
                    task=task
                )
                text = self._extract_json(result_text)
                result = json.loads(text)

                # NL2Code 安全驗證
                if self.validator:
                    is_valid, corrected, errs = self.validator.validate(result)
                    if is_valid and self.validator.corrections:
                        result = corrected
                    elif not is_valid and corrected:
                        result = corrected

                return result
            except Exception as e:
                return {"error": f"v3_commander failed: {str(e)[:100]}"}

        # 降級到 fast_propose
        return self.fast_propose(indicators)

    # ══════════════════════════════════════════════════════════
    # Layer 2: 深度推理（走 Router → MiniMax）
    # ══════════════════════════════════════════════════════════

    def deep_analysis(self, symbol: str, context: str = "") -> Dict:
        """用 7B 做深度归因分析（走 Router Layer 2 → MiniMax）"""
        prompt = f"Symbol: {symbol}\n\nContext:\n{context}\n\nTask: Deep analysis"

        if ROUTER and HAS_ROUTER:
            try:
                result_text = ROUTER.deep(prompt=prompt)
                return json.loads(self._extract_json(result_text))
            except Exception as e:
                pass  # 降級到本地 7B

        # 降級：直接走 Ollama ray-deep-v1
        import requests
        payload = {
            "model": self.deep_model,
            "messages": [
                {"role": "system", "content": "Output JSON with rationale field."},
                {"role": "user",   "content": prompt}
            ],
            "temperature": 0.2,
            "stream": False,
        }
        try:
            resp = requests.post(BASE_URL, json=payload, timeout=300)
            resp.raise_for_status()
            text = self._extract_json(resp.json()["message"]["content"])
            return json.loads(text)
        except Exception as e:
            return {"error": f"deep_analysis: {str(e)[:100]}"}

    # ══════════════════════════════════════════════════════════
    # End-to-End: Scan + Propose
    # ══════════════════════════════════════════════════════════

    def scan_and_propose(self, symbols: List[str]) -> List[Dict]:
        """
        完整流程：
        1. 本地计算指标（Layer 0）
        2. 数学把关筛选
        3. Router Layer 1 → ray-v1 快速策略提案
        4. 對抗校準：confidence < 0.7 → Router Layer 2 → MiniMax 複審
        5. 结果写入 SQLite
        """
        results = []
        for sym in symbols:
            ind = self.local_indicators(sym)
            if "error" in ind:
                results.append({"symbol": sym, "error": ind["error"]})
                continue

            if not ind.get("math_passed"):
                results.append({
                    "symbol": sym,
                    "price":  ind.get("price"),
                    "score":  0,
                    "tag":   "NEUT",
                    "reason": "math_gate_failed",
                    "indicators": ind,
                })
                continue

            strategy = self.fast_propose(ind)

            # ── 對抗校準（Co-Inference Alignment）────────────
            conf = strategy.get('confidence', 1) if isinstance(strategy, dict) else 1
            if conf < 0.7 and self.deep_model:
                deep = self.deep_analysis(sym, json.dumps({k: v for k, v in ind.items() if k != 'error'}, ensure_ascii=False))
                if isinstance(deep, dict) and 'error' not in deep:
                    deep['co_inference'] = True
                    strategy = deep

            score = self._calc_score(ind)
            tag = "BUY" if score >= 3 else "WATCH"

            if self.db:
                try:
                    self.db.log_signal(
                        symbol     = sym,
                        source     = "brain_scan",
                        score      = float(score),
                        sharpe     = ind.get("sharpe_30d"),
                        mdd        = ind.get("mdd_30d"),
                        win_rate   = ind.get("win_rate_30d"),
                        signal_tag = tag,
                    )
                except Exception:
                    pass

            results.append({
                "symbol":     sym,
                "price":      ind.get("price"),
                "score":      score,
                "tag":        tag,
                "strategy":   strategy,
                "indicators": ind,
            })

        return results

    def _calc_score(self, ind: Dict) -> int:
        """计算多空评分（5分制）"""
        s = 0
        if ind.get("above_ma20"): s += 1
        if ind.get("above_ma60"): s += 1
        if ind.get("macd_bull"):  s += 1
        if ind.get("kdj_bull"):   s += 1
        if ind.get("math_passed"): s += 1
        return min(s, 5)

    def _extract_json(self, text: str) -> str:
        """从任意文字提取第一个 JSON 区块"""
        text = text.strip()
        m = re.search(r"```(?:\w+)?\s*([\s\S]*?)```", text)
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
        return text

    @property
    def stats(self) -> Dict:
        """Ray 系统状态"""
        if not self.db:
            return {"status": "db unavailable"}
        sig_stats = self.db.get_signal_stats()
        wids = self.db.get_wisdom_logs(limit=100)
        bts = self.db.get_recent_backtests(days=7)
        approved = [b for b in bts if b.get("passed")]
        return {
            "signals":        f"{sig_stats['approved_signals']}/{sig_stats['total_signals']} approved",
            "wisdom_logs":    len(wids),
            "failed_wisdoms": len([w for w in wids if not w.get("passed")]),
            "backtests_7d":   len(bts),
            "approved_bt":    len(approved),
        }


if __name__ == "__main__":
    import sys
    rb = RayBrain()
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["NVDA", "TSLA", "SPY"]
    for r in rb.scan_and_propose(symbols):
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print()