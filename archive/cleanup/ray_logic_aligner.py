# -*- coding: utf-8 -*-
"""
Ray Logic Aligner — Tina Architecture Edition
讓 7B 扮演「導師」，對 1.5B 的輸出進行打分與修正
 Logic Alignment：錯誤 → 修正 → 再學習  閉環

流程：
  1. 測試：餵給 1.5B 一段市場數據，讓它產出 JSON
  2. 批改：將 1.5B 的輸出給 7B 看
  3. 反饋：若 7B 認為 1.5B 忽略關鍵，生成修正指令
  4. 再學習：將「錯誤-修正」對加入蒸餾集
"""

import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

BASE_URL = "http://localhost:11434/api/chat"

# ── Ollama 端點 ─────────────────────────────────────────────────
LLM_1_5B = "ray-v1"      # 已定制 1.5B
LLM_7B   = "qwen2.5:7b"  # 等下載完成


class RayLogicAligner:
    """
    對齊 7B（老師）和 1.5B（學生）的決策邏輯
    """

    def __init__(self):
        self.tutor_model  = LLM_7B    # 7B 導師（下載完成後）
        self.student_model = LLM_1_5B  # 1.5B 學生
        self.corrections  = []       # 收集修正對

    # ── Step 1：Student 推理 ────────────────────────────────
    def student_inference(self, market_data: str) -> Tuple[str, str]:
        """
        餵給 1.5B 市場數據，讓它輸出策略 JSON
        返回：(raw_output, parsed_json)
        """
        system = (
            "You are Ray-Fast (1.5B student). "
            "Output ONLY valid JSON. No text."
        )

        payload = {
            "model": self.student_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": f"Data:\n{market_data}\n\nOutput JSON strategy."}
            ],
            "temperature": 0.1,
            "stream": False
        }

        try:
            resp = requests.post(BASE_URL, json=payload, timeout=60)
            resp.raise_for_status()
            raw = resp.json()["message"]["content"]
            json_str = self._extract_json(raw)
            parsed = json.loads(json_str)
            return raw, parsed
        except Exception as e:
            return "", {"error": str(e)[:100]}

    # ── Step 2：Tutor 批改 ─────────────────────────────────
    def tutor_review(self, market_data: str,
                     student_output: str,
                     student_json: dict) -> dict:
        """
        讓 7B 批改 1.5B 的輸出
        返回：{score, feedback, correction, is_passed}
        """
        if self.tutor_model == "qwen2.5:7b":
            return {"error": "7B not ready yet", "is_passed": False}

        system = (
            "You are Ray Deep Tutor (7B). "
            "You are grading a 1.5B student's JSON strategy output. "
            "Grade strictly on: (1) did it output valid JSON, "
            "(2) did it capture the key market logic, "
            "(3) is the stop_loss reasonable. "
            "Output ONLY valid JSON: "
            '{"score":int,"feedback":str,"correction":str|null,"is_passed":bool}'
        )

        payload = {
            "model": self.tutor_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": (
                    f"Market Data:\n{market_data}\n\n"
                    f"1.5B Student Output:\n{student_output}\n\n"
                    f"Parse: {json.dumps(student_json)[:500]}\n\n"
                    f"Grade (1-5): strict."
                )}
            ],
            "temperature": 0.2,
            "stream": False
        }

        try:
            resp = requests.post(BASE_URL, json=payload, timeout=300)
            resp.raise_for_status()
            raw = resp.json()["message"]["content"]
            text = self._extract_json(raw)
            graded = json.loads(text)
            return graded
        except Exception as e:
            return {"error": str(e)[:100], "is_passed": False}

    # ── Step 3：收集修正對 ─────────────────────────────────
    def build_correction_pair(self, market_data: str,
                               student_raw: str,
                               graded: dict) -> Optional[dict]:
        """
        將「錯誤-修正」對格式化為蒸餾數據
        """
        if graded.get("is_passed", False):
            return None  # 通過，不需要修正

        correction = graded.get("correction", "")
        if not correction:
            return None

        # 蒸餾格式：錯誤示範 → 修正後
        pair = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Ray-Causal (1.5B distilled with logic chain). "
                        "Output ONLY valid JSON. Think step by step."
                    )
                },
                {
                    "role": "user",
                    "content": f"Data:\n{market_data}\n\nOutput JSON."
                },
                {
                    "role": "assistant",
                    "content": correction  # 修正後的正確輸出
                }
            ],
            "context": {
                "student_raw": student_raw[:300],
                "feedback": graded.get("feedback", ""),
                "score": graded.get("score", 0),
                "type": "logic_alignment"
            }
        }
        self.corrections.append(pair)
        return pair

    # ── Step 4：導出蒸餾集 ────────────────────────────────
    def export_corrections(self, path: str = None) -> dict:
        """將所有修正對導出為 JSONL"""
        if not self.corrections:
            return {"count": 0, "path": ""}

        path = path or os.path.join(
            os.path.dirname(__file__), "ray_logic_alignment.jsonl"
        )

        with open(path, "w", encoding="utf-8") as f:
            for item in self.corrections:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"[*] Logic Aligner: {len(self.corrections)} pairs → {path}")
        return {"count": len(self.corrections), "path": path}

    # ── Tool ──────────────────────────────────────────────
    def _extract_json(self, text: str) -> str:
        text = text.strip()
        m = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', text)
        if m:
            try:
                json.loads(m.group(1).strip())
                return m.group(1).strip()
            except: pass
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                json.loads(text[start:end])
                return text[start:end]
            except: pass
        return text


if __name__ == "__main__":
    aligner = RayLogicAligner()

    # 測試：讀取 DB 中的市場數據，讓 1.5B 推理
    from ray_data_center import RayDataCenter

    db = RayDataCenter()
    signals = db.get_unpushed_approved_signals(limit=5)

    if not signals:
        print("[!] No approved signals. Run scan first.")
    else:
        print(f"[*] Testing {len(signals)} signals with Logic Aligner...")

        for sig in signals:
            market_data = (
                f"Symbol: {sig['symbol']}\n"
                f"Score: {sig['score']}/5\n"
                f"Sharpe: {sig.get('sharpe_30d', 'N/A')}\n"
                f"MDD: {sig.get('mdd_30d', 'N/A')}\n"
                f"Note: {sig.get('note', '')}"
            )

            raw, parsed = aligner.student_inference(market_data)
            print(f"  [{sig['symbol']}] Student: {str(parsed)[:100]}")

            if aligner.tutor_model != "qwen2.5:7b":
                print(f"  [7B not ready] Skip tutor review")
                continue

            graded = aligner.tutor_review(market_data, raw, parsed)
            print(f"  [Tutor] Score={graded.get('score','?')}/5, "
                  f"Passed={graded.get('is_passed', '?')}")

            pair = aligner.build_correction_pair(market_data, raw, graded)
            if pair:
                print(f"  [Correction] captured")

        if aligner.corrections:
            r = aligner.export_corrections()
            print(f"\n[*] Done. {r['count']} corrections exported.")