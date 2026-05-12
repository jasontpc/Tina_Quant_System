# -*- coding: utf-8 -*-
"""
Ray NL2Code Validator — Tina Architecture Edition
JSON Schema 拦截 AI 幻觉，确保策略提案为合法结构化 JSON
新增：auto_correct 模式，自动修正格式问题
"""

import json
import re
from typing import Dict, List, Optional, Tuple

# ── 严格策略协议 Schema ────────────────────────────────────────────
AXIOM_SCHEMA = {
    "type": "object",
    "required": ["strategy_name", "indicator", "params", "entry_condition"],
    "properties": {
        "strategy_name": {
            "type": "string",
            "pattern": "^[A-Z][A-Z0-9_]{2,30}$"
        },
        "indicator": {
            "type": "string",
            "enum": ["EMA_CROSS", "VEGAS_TUNNEL", "FOREIGN_BUY", "MOMENTUM",
                     "KDJ_CROSS", "RSI_THRESHOLD", "MACD_CROSS", "MA_BREAKOUT"]
        },
        "params": {
            "type": "object",
            "properties": {
                "fast":   {"type": "integer", "minimum": 2, "maximum": 200},
                "slow":   {"type": "integer", "minimum": 5, "maximum": 500},
                "window": {"type": "integer", "minimum": 2, "maximum": 300},
                "rsi_period":  {"type": "integer", "minimum": 2, "maximum": 50},
                "rsi_buy":     {"type": "number",  "minimum": 10, "maximum": 60},
                "rsi_sell":    {"type": "number",  "minimum": 50, "maximum": 95},
                "atr_period":  {"type": "integer", "minimum": 5, "maximum": 50},
                "stop_loss_pct": {"type": "number", "minimum": 0.01, "maximum": 0.30},
                "target_pct":    {"type": "number", "minimum": 0.01, "maximum": 1.00},
            }
        },
        "entry_condition": {
            "type": "object",
            "required": ["operator", "threshold"],
            "properties": {
                "operator":  {"type": "string", "enum": [">", "<", ">=", "<=", "CROSS_ABOVE", "CROSS_BELOW"]},
                "threshold": {"type": "number"}
            }
        },
        "stop_loss": {"type": "number", "minimum": 0.01, "maximum": 0.50},
        "target":    {"type": "number", "minimum": 0.01, "maximum": 2.00},
        "max_hold_days": {"type": "integer", "minimum": 1, "maximum": 60}
    }
}

# ── Indicator 映射（接受多种自然语言表述）───────────────────────────
INDICATOR_ALIASES = {
    "EMA_CROSS":    ["EMA_CROSS", "EMA CROSS", "EMA", "Moving Average Cross", "MA CROSS"],
    "VEGAS_TUNNEL": ["VEGAS_TUNNEL", "VEGAS", "Vegas Tunnel"],
    "MOMENTUM":     ["MOMENTUM", "MOM", "Momentum"],
    "KDJ_CROSS":    ["KDJ_CROSS", "KDJ", "KDJ Cross"],
    "RSI_THRESHOLD":["RSI_THRESHOLD", "RSI", "RSI Threshold", "RSI Signal"],
    "MACD_CROSS":   ["MACD_CROSS", "MACD", "MACD Cross"],
    "MA_BREAKOUT":  ["MA_BREAKOUT", "MA BREAKOUT", "Breakout"],
    "FOREIGN_BUY":  ["FOREIGN_BUY", "FOREIGN", "Foreign Net Buy"],
}


def _to_upper_snake(name: str) -> str:
    """自动修正为 UPPER_SNAKE_CASE"""
    # 移除空格、特殊字符，转大写，用下划线连接
    name = re.sub(r'[^a-zA-Z0-9]', '_', name.strip())
    parts = name.split('_')
    result = '_'.join(p.upper() for p in parts if p)
    # 确保以字母开头
    if result and not result[0].isalpha():
        result = 'STRATEGY_' + result
    return result[:30]


def _normalize_indicator(ind: str) -> Optional[str]:
    """将任意 indicator 表述正规化"""
    if not ind:
        return None
    ind_upper = ind.strip().upper()
    for canonical, aliases in INDICATOR_ALIASES.items():
        if ind_upper in [a.upper() for a in aliases]:
            return canonical
    # 部分匹配
    for canonical, aliases in INDICATOR_ALIASES.items():
        if any(alias.upper() in ind_upper or ind_upper in alias.upper() for alias in aliases):
            return canonical
    return None


class NL2CodeValidator:
    """
    职责：拦截 AI 自然语言输出中的「幻觉」，确保所有策略都是合法的结构化 JSON
    auto_correct=True 时自动修正格式问题（strategy_name、indicator）
    """

    def __init__(self, schema: Dict = None, auto_correct: bool = False):
        self.schema = schema or AXIOM_SCHEMA
        self.auto_correct = auto_correct
        self.errors: List[str] = []
        self.corrections: List[str] = []

    def validate(self, axiom_json: str) -> Tuple[bool, Optional[Dict], List[str]]:
        self.errors = []
        self.corrections = []

        # ── Step 1：解析 JSON ──────────────────────────────
        if isinstance(axiom_json, str):
            try:
                axiom = json.loads(axiom_json)
            except json.JSONDecodeError as e:
                self.errors.append(f"JSON parse failed: {e}")
                return False, None, self.errors
        elif isinstance(axiom_json, dict):
            axiom = dict(axiom_json)
        else:
            self.errors.append(f"Unknown type: {type(axiom_json)}")
            return False, None, self.errors

        # ── Step 2：必要字段 ─────────────────────────────
        for field in self.schema.get("required", []):
            if field not in axiom:
                self.errors.append(f"Missing required field: {field}")

        # ── Step 3：strategy_name 格式 ───────────────────
        name = axiom.get("strategy_name", "")
        if not re.match(r"^[A-Z][A-Z0-9_]{2,30}$", name):
            if self.auto_correct and name:
                corrected = _to_upper_snake(name)
                if len(corrected) >= 3:
                    self.corrections.append(f"strategy_name '{name}' -> '{corrected}'")
                    axiom["strategy_name"] = corrected
                    name = corrected
                else:
                    self.errors.append(f"Invalid strategy_name '{name}': must be UPPER_SNAKE_CASE 3-30 chars")
            else:
                self.errors.append(f"Invalid strategy_name '{name}': must be UPPER_SNAKE_CASE 3-30 chars")

        # ── Step 4：indicator 合法值 ─────────────────────
        ind = axiom.get("indicator")
        if ind:
            normalized = _normalize_indicator(ind)
            if normalized:
                if ind != normalized:
                    self.corrections.append(f"indicator '{ind}' -> '{normalized}'")
                axiom["indicator"] = normalized
            elif self.auto_correct:
                axiom["indicator"] = "MOMENTUM"  # fallback
                self.corrections.append(f"indicator '{ind}' -> 'MOMENTUM' (unrecognized)")
            else:
                valid_list = list(INDICATOR_ALIASES.keys())
                self.errors.append(f"Unknown indicator '{ind}': must be one of {valid_list}")

        # ── Step 5：params 范围 ──────────────────────────
        params = axiom.get("params", {})
        param_specs = self.schema["properties"]["params"]["properties"]
        for key, spec in param_specs.items():
            if key in params:
                val = params[key]
                if spec["type"] == "integer" and not isinstance(val, int):
                    try:
                        params[key] = int(val)
                        self.corrections.append(f"params.{key} '{val}' -> int")
                    except:
                        self.errors.append(f"params.{key} must be int")

        # ── Step 6：entry_condition ──────────────────────
        ec = axiom.get("entry_condition", {})
        for field in ["operator", "threshold"]:
            if field not in ec:
                self.corrections.append(f"entry_condition.{field} missing -> auto-fill")
                ec[field] = ">" if field == "operator" else 0
        axiom["entry_condition"] = ec

        # ── Step 7：stop_loss / target 范围 ───────────────
        if "stop_loss" in axiom:
            sl = axiom["stop_loss"]
            if isinstance(sl, (int, float)):
                if not (0.01 <= float(sl) <= 0.50):
                    self.corrections.append(f"stop_loss {sl} -> 0.08 (out of range)")
                    axiom["stop_loss"] = 0.08
            else:
                self.corrections.append(f"stop_loss {sl} -> 0.08 (invalid type)")
                axiom["stop_loss"] = 0.08
        else:
            self.corrections.append("stop_loss missing -> 0.08")
            axiom["stop_loss"] = 0.08

        if "target" in axiom:
            tgt = axiom["target"]
            if isinstance(tgt, (int, float)) and not (0.01 <= float(tgt) <= 2.00):
                self.errors.append(f"target={tgt} must be between 0.01-2.00")

        is_valid = len(self.errors) == 0
        # 自动修正 structural 问题时，即使有错误也返回修正后的 dict
        if not is_valid and self.corrections and axiom:
            return False, axiom, self.errors
        return is_valid, axiom if is_valid else None, self.errors

    def validate_batch(self, axiom_list: List) -> List[Tuple[bool, Optional[Dict], List[str]]]:
        return [self.validate(a) for a in axiom_list]


def sanitize_llm_output(raw_output: str) -> str:
    """在 JSON 解析前，清理 LLM 输出的格式问题"""
    text = raw_output.strip()
    # 移除 ```json ... ``` 或 ``` ... ```
    pattern = r"```(?:\w+)?\s*([\s\S]*?)```"
    matches = re.findall(pattern, text)
    for block in matches:
        try:
            json.loads(block.strip())
            return block.strip()
        except:
            pass

    # 找第一个 {...} 区块
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        candidate = text[start:end]
        try:
            json.loads(candidate)
            return candidate
        except:
            pass

    return raw_output


if __name__ == "__main__":
    v = NL2CodeValidator(auto_correct=True)

    # 测试自然语言 indicator 修正
    test_cases = [
        '{"strategy_name":"EMA Cross 12 26","indicator":"EMA CROSS","params":{"fast":12,"slow":26},"entry_condition":{"operator":">","threshold":0},"stop_loss":0.08}',
        '{"strategy_name":"RayFastLogicUnit","indicator":"RSI, KDJ J, Mom","params":{},"entry_condition":{},"stop_loss":0.0}',
        '{"strategy_name":"MOM_5","indicator":"Momentum","params":{"window":5},"entry_condition":{"operator":">","threshold":0.02},"stop_loss":0.10}',
    ]
    for tc in test_cases:
        ok, ax, errs = v.validate(tc)
        print(f"Valid={ok} | Corrections={v.corrections} | Errors={errs[:2]}")
        if ax:
            print(f"  -> name={ax.get('strategy_name')}, ind={ax.get('indicator')}")