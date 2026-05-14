# -*- coding: utf-8 -*-
"""
Ray Tina Bridge - Ollama Local Model Integration Layer
"""

import requests
import json
import re

DEFAULT_URL   = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:1.5b"


class TinaBridge:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_URL):
        self.url   = base_url
        self.model = model

    def ask_logic(self, prompt: str, context_data: str = "") -> str:
        system_prompt = (
            "You are Ray's quant logic unit. Tina Architecture Edition. "
            "Always output valid JSON. No natural language. "
            'Schema: {"strategy_name":"...","indicator":"...","params":{},'
            '"entry_condition":{},"stop_loss":0.0}'
        )

        payload = {
            "model":      self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"Context:\n{context_data}\n\nTask:\n{prompt}"}
            ],
            "temperature": 0.1,
            "stream":     False,
        }

        try:
            resp = requests.post(self.url, json=payload, timeout=120)
            resp.raise_for_status()
            raw = resp.json()["message"]["content"]

            # Extract first JSON block from markdown or raw text
            json_str = self._extract_json(raw)
            json.loads(json_str)  # validate
            return json_str

        except requests.exceptions.ConnectionError:
            return '{"error": "Ollama not running"}'
        except json.JSONDecodeError as e:
            return f'{{"error": "Invalid JSON", "details": "{str(e)[:100]}"}}'
        except Exception as e:
            return f'{{"error": "Bridge failure", "details": "{str(e)[:100]}"}}'

    def _extract_json(self, text: str) -> str:
        """Strip markdown code fences and extract first valid JSON block."""
        # Remove ```json ... ``` or ``` ... ```
        text = text.strip()
        m = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', text)
        if m:
            candidate = m.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except: pass

        # Find first {...} block
        start = text.find('{')
        end   = text.rfind('}') + 1
        if start >= 0 and end > start:
            candidate = text[start:end]
            try:
                json.loads(candidate)
                return candidate
            except: pass

        return text  # fallback: return raw


if __name__ == "__main__":
    bridge = TinaBridge(model="ray-deep-v1")
    data = "NVDA | RSI=28 | Sharpe=1.8 | MACD金叉 | 外資淨買"
    result = bridge.ask_logic("Output strict JSON strategy", data)
    print(result)
    try:
        parsed = json.loads(result)
        print(f"Strategy: {parsed.get('strategy_name')}")
    except:
        pass