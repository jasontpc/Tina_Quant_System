# -*- coding: utf-8 -*-
"""
LLM Router - 統一調度層
=======================
所有 LLM 調用必須經過這裡，禁止跨層直接 call Ollama。

分層原則：
  Layer 0: 純本地計算 → 不走 LLM（ray_engine.py, us_momentum.py 等）
  Layer 1: 快速策略  → ray-deep-v1（Qwen 7B，Jo 全指定）
  Layer 2: 深度推理  → MiniMax Remnant（雲端，3-15s）
  Layer 3: 連網學習  → MiniMax（帶 web_fetch 能力）

使用範例：
  router = LLMRouter()
  result = router.call("deep_analysis", {"data": ...})
"""

import os, json, time
from typing import Dict, Any, Optional

# ── MiniMax API ──────────────────────────────────────────────
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY") or os.getenv("api-key") or ""
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

# ── Ollama 本地模型映射 ─────────────────────────────────────────
# 優先順序（根據速度和品質平衡）
# Layer 1: 快速任務 (4B — 台股/美股實戰時段)
LOCAL_MODEL_FAST   = "ray-v3.5"        # Qwen 4B — 交易時段主力 (2.7GB VRAM)
LOCAL_MODEL_ALT_FAST = "ray-v3.5"        # 備用同樣是 4B

# Layer 2: 深度任務 (7B — 訓練/蒸餾時段)
LOCAL_MODEL_DEEP   = "ray-deep-v1"     # Qwen 7B — 14:00-20:00 邏輯進化時段
LOCAL_MODEL_ALT_DEEP = "ray-commander"   # ray-commander + 大師對齊 System Prompt
LOCAL_MODEL_COMMANDER = "ray-commander"   # ray-deep-v1 + 大師對齊 System Prompt


class LLMRouter:
    """統一 LLM 調度器"""

    def __init__(self):
        self.local_fast    = LOCAL_MODEL_FAST
        self.local_alt_fast = LOCAL_MODEL_FAST   # Jo 指定：全本地分析走 ray-deep
        self.local_v3      = LOCAL_MODEL_FAST   # Jo 指定：V3 備用同樣是 ray-deep
        self.local_deep    = LOCAL_MODEL_DEEP   # Jo 指定：統一走 ray-deep
        self.local_alt_deep = LOCAL_MODEL_ALT_DEEP
        self.local_commander = "ray-deep-v1"
        self.minimax_model = "minimax/MiniMax-M2.7"  # MiniMax Remnant
        self._mm_client = None
        self._ollama_fallback_chain = [
            # Layer 1 fallback chain
            (LOCAL_MODEL_FAST,     30, 0.1),
            (LOCAL_MODEL_ALT_FAST, 30, 0.1),
            (LOCAL_MODEL_DEEP,     300, 0.2),
        ]

    # ═══════════════════════════════════════════════════════════
    # 公開 API
    # ═══════════════════════════════════════════════════════════

    def call(self, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        統一路由入口
        task: scan | quick_signal | position_summary | backtest_summary |
              deep_analysis | macro_outlook | web_learn | news_summary
        data: {"prompt": ..., "context": ...}
        """
        layer = self._classify(task)

        if layer == 0:
            return {"error": "Layer 0 任務不需要 LLM，請用本地 Python"}
        elif layer == 1:
            return self._local_call(data)
        elif layer == 2:
            return self._minimax_call(data)
        elif layer == 3:
            return self._minimax_web_call(data)
        else:
            return {"error": f"未知 task: {task}"}

    def fast(self, prompt: str, context: str = "") -> str:
        """Layer 1: 快速策略提案（走 ray-v1）"""
        return self._ollama_raw(
            model=self.local_fast,
            prompt=self._build_prompt(prompt, context, mode="fast")
        )

    def deep(self, prompt: str, context: str = "") -> str:
        """Layer 2: 深度推理（走 MiniMax）"""
        return self._minimax_raw(
            prompt=self._build_prompt(prompt, context, mode="deep")
        )

    def web(self, prompt: str, context: str = "") -> str:
        """Layer 3: 連網學習（走 MiniMax + web）"""
        return self._minimax_raw(
            prompt=self._build_prompt(prompt, context, mode="web"),
            enable_web=True
        )

    def v3_commander(self, symbol: str, indicators: Dict[str, Any], task: str = "分析以下標的，輸出交易信號") -> str:
        """
        Layer 3B: ray-v3 Quant Commander（大師對齊模式）
        使用 qwen2.5:7b（ray-deep-v1）實作，避免 qwen3.5:4b Thinking Mode 問題
        動態注入 RAG 上下文
        """
        try:
            from ray_memory_bridge import RayMemoryBridge
            bridge = RayMemoryBridge()
            prompt = bridge.build_3b_prompt(symbol, indicators, task)
            bridge.close()

            # 走 Ollama ray-commander（大師對齊 System Prompt）
            return self._ollama_raw(
                model=self.local_commander,   # ray-commander
                prompt=prompt,
                timeout=120
            )
        except ImportError:
            # 降級到 ray-v1
            return self.fast(f"[{symbol}] {task}")

    # ═══════════════════════════════════════════════════════════
    # 私有方法
    # ═══════════════════════════════════════════════════════════

    def _classify(self, task: str) -> int:
        """任務分類：0=純本地, 1=快速, 2=深度, 3=連網"""
        fast_tasks    = {"scan", "quick_signal", "position_check", "position_summary", "signal_parse"}
        deep_tasks    = {"backtest_summary", "deep_analysis", "attribution", "macro_outlook", "json_validate"}
        web_tasks     = {"web_learn", "news_summary", "sentiment", "macro_news", "earnings_summary"}
        if task in fast_tasks:  return 1
        if task in deep_tasks:  return 2
        if task in web_tasks:   return 3
        # default: 嘗試本地快速
        return 1

    def _build_prompt(self, prompt: str, context: str, mode: str) -> str:
        """封裝 system prompt"""
        system_map = {
            "fast": "你是一個高效的美股交易策略助手。直接給出結論，不需要廢話。",
            "deep": "你是 Ray-Deep，深度量化分析專家。請完整推理，必要時寫出計算過程。",
            "web":  "你是 Ray，帶網路搜索能力的交易分析師。先抓取最新數據，再分析。"
        }
        system = system_map.get(mode, system_map["fast"])
        if context:
            return f"<system>{system}</system>\n<context>{context}</context>\n<user>{prompt}</user>"
        return f"<system>{system}</system>\n<user>{prompt}</user>"

    # ── Layer 1: 本地 Ollama ──────────────────────────────────

    def _local_call(self, data: Dict) -> Dict:
        try:
            result = self._ollama_raw(
                model=self.local_fast,
                prompt=data.get("prompt", "")
            )
            return {"ok": True, "layer": 1, "model": self.local_fast, "result": result}
        except Exception as e:
            return {"ok": False, "layer": 1, "error": str(e)}

    def _ollama_raw(self, model: str, prompt: str,
                    num_ctx: int = 4096,
                    temperature: float = 0.1,
                    timeout: int = 60,
                    num_predict: int = 512) -> str:
        """直接 call Ollama 本地模型（含 fallback 鏈）"""
        import urllib.request, urllib.error

        # 判斷是否為 qwen3.5 系列（使用 messages + 處理 thinking 欄位）
        is_qwen35 = "3.5" in model or "qwen3" in model.lower()

        if True:
            # 全部使用 messages 格式（更穩定）
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": num_ctx,
                    "temperature": temperature,
                    "num_predict": num_predict,
                    "top_p": 0.85 if is_qwen35 else 0.9,
                    "top_k": 20
                }
            }

        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        msg = raw.get("message", {})
        content = msg.get("content", "").strip()
        thinking = msg.get("thinking", "").strip() if is_qwen35 else ""

        # qwen3.5: 如果 content 為空但有 thinking，解析 thinking 作為輸出
        if is_qwen35 and not content and thinking:
            return thinking[-200:] if len(thinking) > 200 else thinking

        return content

    # ── Layer 2: MiniMax ──────────────────────────────────────

    def _minimax_call(self, data: Dict) -> Dict:
        try:
            result = self._minimax_raw(prompt=data.get("prompt", ""))
            return {"ok": True, "layer": 2, "model": self.minimax_model, "result": result}
        except Exception as e:
            return {"ok": False, "layer": 2, "error": str(e)}

    def _minimax_raw(self, prompt: str, enable_web: bool = False) -> str:
        """直接 call MiniMax API"""
        if not MINIMAX_API_KEY:
            return "[ERROR] MINIMAX_API_KEY 未設定"

        # 選擇模型：web 任務用較強的模型
        model = "minimax/MiniMax-M2.7"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3 if enable_web else 0.1,
            "max_tokens": 4000
        }
        if enable_web:
            payload["extra"] = {"web_search": True}

        req = urllib.request.Request(
            f"{MINIMAX_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        return raw["choices"][0]["message"]["content"]

    # ── Layer 3: MiniMax + Web ────────────────────────────────

    def _minimax_web_call(self, data: Dict) -> Dict:
        try:
            result = self._minimax_raw(
                prompt=data.get("prompt", ""),
                enable_web=True
            )
            return {"ok": True, "layer": 3, "model": self.minimax_model, "result": result}
        except Exception as e:
            return {"ok": False, "layer": 3, "error": str(e)}

    # ═══════════════════════════════════════════════════════════
    # 工具方法（供外部腳本查詢狀態）
    # ═══════════════════════════════════════════════════════════

    def status(self) -> Dict:
        """回報當前 Router 狀態"""
        return {
            "local_fast":     self.local_fast,
            "local_alt_fast": self.local_alt_fast,
            "local_v3":       self.local_v3,
            "local_deep":     self.local_deep,
            "local_alt_deep": self.local_alt_deep,
            "minimax_model":  self.minimax_model,
            "minimax_key_set": bool(MINIMAX_API_KEY),
            "ollama_fallback_chain": [m for m, _, _ in self._ollama_fallback_chain],
        }


# ═══════════════════════════════════════════════════════════════
# 便捷函式（可直接 import 使用）
# ═══════════════════════════════════════════════════════════════

_router: Optional[LLMRouter] = None

def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router

def fast(prompt: str, context: str = "") -> str:
    """快速策略（Layer 1）"""
    return get_router().fast(prompt, context)

def deep(prompt: str, context: str = "") -> str:
    """深度推理（Layer 2）"""
    return get_router().deep(prompt, context)

def web(prompt: str, context: str = "") -> str:
    """連網學習（Layer 3）"""
    return get_router().web(prompt, context)