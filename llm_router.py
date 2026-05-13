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
LOCAL_MODEL_ALT_FAST = "ray-v3.5"        # Jo 指定：全指向 ray-v3.5

# Layer 2: 深度任務 (7B — 訓練/蒸餾時段)
# Jo 指定：所有路由（fast/deep/v3/alt_fast）全部統一使用 ray-v3.5
LOCAL_MODEL_DEEP     = "ray-v3.5"
LOCAL_MODEL_ALT_DEEP = "ray-v3.5"
LOCAL_MODEL_COMMANDER = "ray-v3.5"


class LLMRouter:
    """統一 LLM 調度器"""

    def __init__(self):
        self.local_fast     = LOCAL_MODEL_FAST
        self.local_alt_fast = LOCAL_MODEL_FAST   # Jo 指定：全指向 ray-v3.5
        self.local_v3       = LOCAL_MODEL_FAST   # Jo 指定：V3 統一 ray-v3.5
        self.local_deep     = LOCAL_MODEL_FAST   # Jo 指定：deep 統一 ray-v3.5
        self.local_alt_deep = LOCAL_MODEL_FAST   # Jo 指定：alt_deep 統一 ray-v3.5
        self.local_commander = LOCAL_MODEL_FAST   # Jo 指定：commander 統一 ray-v3.5
        self.minimax_model = "minimax/MiniMax-M2.7"  # MiniMax Remnant
        self._mm_client = None
        self._ollama_fallback_chain = [
            # Jo 指定：全部統一 ray-v3.5，備用也是同一個
            (LOCAL_MODEL_FAST,     30, 0.1),
        ]

# ─── 單模型 VRAM 鎖定 ──────────────────────────────────────
def get_vram_gb():
    """讀取 NVIDIA GPU VRAM 使用量（GB）"""
    try:
        import subprocess
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                           "--format=csv,noheader,nounits"],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return int(r.stdout.strip().split('\n')[0]) / 1024
    except:
        pass
    return None

def clear_all_vram():
    """強制清理所有模型 VRAM（物理清理）"""
    try:
        import subprocess
        subprocess.run(["ollama", "stop", "--all"],
                       capture_output=True, timeout=60, check=False)
        import time; time.sleep(60)
    except:
        pass

def safe_route_call(target_model: str, required_gb: float = 0):
    """
    在路由轉發前，確保 VRAM 乾淨（單模型協議）
    1. 檢查 VRAM 殘留
    2. 若被佔用且 needed>available，執行 clear_all_vram()
    3. 返回是否安全執行
    """
    vram = get_vram_gb()
    if vram is None:
        return True  # 無法檢測，放行

    # 如果當前 VRAM > 5.5GB，說明有殘留模型未釋放
    if vram > 5.5:
        print(f"[VRAM LOCK] {vram:.1f}GB > 5.5GB（可能7B殘留）→ 執行清理")
        clear_all_vram()
        return True

    return True

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
            safe_route_call(LOCAL_MODEL_FAST)
            return self._local_call(data)
        elif layer == 2:
            safe_route_call(LOCAL_MODEL_FAST)
            return self._minimax_call(data)
        elif layer == 3:
            safe_route_call(LOCAL_MODEL_FAST)
            return self._minimax_web_call(data)
        else:
            return {"error": f"未知 task: {task}"}

    def fast(self, prompt: str, context: str = "") -> str:
        """Layer 1: 快速策略提案（走 ray-v3.5）"""
        safe_route_call(self.local_fast)
        return self._ollama_raw(
            model=self.local_fast,
            prompt=self._build_prompt(prompt, context, mode="fast")
        )

    def deep(self, prompt: str, context: str = "") -> str:
        """Layer 2: 深度推理（走 MiniMax）"""
        safe_route_call(self.local_fast)
        return self._minimax_raw(
            prompt=self._build_prompt(prompt, context, mode="deep")
        )

    def macro(self, prompt: str, context: str = "") -> str:
        """Layer 3: 宏觀任務（接管 MiniMax Layer 3，走本地 qwen2.5:7b）"""
        safe_route_call("qwen2.5:7b", required_gb=4.7)
        return self._local_7b_raw(
            prompt=self._build_prompt(prompt, context, mode="macro")
        )

    def deep_7b(self, prompt: str, context: str = "") -> str:
        """深度任務（走 ray-deep-v1，蒸餾/歸因時段專用）"""
        safe_route_call("ray-deep-v1", required_gb=4.7)
        return self._ollama_raw(
            model="ray-deep-v1",
            prompt=self._build_prompt(prompt, context, mode="deep")
        )
        """
        宏觀分析（Layer 3 MiniMax 替代者）
        使用本地 qwen2.5:7b 接管原本昂貴的雲端任務，節省 30%+ 配額。
        21:00 盤前宏觀自動觸發。
        """
        return self._local_7b_raw(
            model="qwen2.5:7b",
            prompt=self._build_prompt(prompt, context, mode="macro")
        )

    def _local_7b_raw(self, model: str, prompt: str, temperature: float = 0.15,
                      num_predict: int = 350, timeout: int = 90) -> str:
        """直接呼叫本地 7B（不走 MiniMax）"""
        return self._ollama_raw(
            model=model,
            prompt=prompt,
            temperature=temperature,
            num_predict=num_predict,
            timeout=timeout
        )

    def _local_7b_call(self, data: Dict) -> Dict:
        """本地 7B 調用（macro_outlook / sentiment 等）"""
        try:
            result = self._ollama_raw(
                model="qwen2.5:7b",
                prompt=data.get("prompt", ""),
                temperature=0.15,
                timeout=90
            )
            return {"ok": True, "layer": 3, "model": "qwen2.5:7b", "result": result}
        except Exception as e:
            return {"ok": False, "layer": 3, "model": "qwen2.5:7b", "error": str(e)}
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
            "web":  "你是 Ray，帶網路搜索能力的交易分析師。先抓取最新數據，再分析。",
            "macro": "你是 Master Macro Analyst。參考 Dalio 的多樣化與 Simons 的模式識別。將宏觀數據轉化為 4B 指揮官可理解的權重修正因子，輸出簡潔果斷。"
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