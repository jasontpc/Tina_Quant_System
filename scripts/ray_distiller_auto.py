# -*- coding: utf-8 -*-
"""
ray_distiller_auto.py — 物理固化腳本（05:00 執行）
功能：
  - 讀取 axioms_v3.5.json（7B 蒸餾結果）
  - 生成 Ray-v3.5.Modelfile
  - 執行 ollama create 物理固化
  - 記錄固化日誌

執行時間：每日 05:00（Ray System v3.5 每日固化）
使用方式：python scripts/ray_distiller_auto.py
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path

# ── VRAM 守護 ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(UTILS_DIR))
try:
    from ray_guard import ray_singleton
except ImportError:
    def ray_singleton(func):
        return func

# ── 路徑設定 ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
SCRIPTS_DIR = BASE_DIR / "scripts"
UTILS_DIR = SCRIPTS_DIR / "utils"
MODELS_DIR = BASE_DIR / "models"

AXIOMS_FILE = BASE_DIR / "stores" / "long_term" / "axioms_v3.5.json"
RAY_MODELFILE = BASE_DIR / "Ray-v3.5.Modelfile"
DISTILL_LOG = BASE_DIR / "logs" / "ray_distiller.log"

# 備援天條（當 axioms_v3.5.json 不存在時）
FALLBACK_AXIOMS = (
    "1. RSI2 > 70 → SELL（Connors 均值回歸）\n"
    "2. RSI2 < 30 → BUY（Connors 均值回歸）\n"
    "3. 波動率 > 50% → 現金為王（Taleb）\n"
    "4. 單筆虧損 > 1% → 立即止損（Thorp）\n"
    "5. 持有 > 30 天 + RSI > 50 → 警惕（Taleb）"
)

# ── 日誌設定 ─────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(DISTILL_LOG, encoding="utf-8"),
        logging.StreamHandler()
    ],
    encoding="utf-8"
)
logger = logging.getLogger(__name__)


# ── 核心函式 ────────────────────────────────────────────────────────────────

def load_axioms():
    """讀取 axioms_v3.5.json，若失敗則使用備援"""
    if not AXIOMS_FILE.exists():
        logger.warning(f"⚠️ {AXIOMS_FILE} 不存在，使用備援天條")
        return FALLBACK_AXIOMS

    try:
        with open(AXIOMS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            # JSON 陣列格式
            lines = []
            for item in data:
                if isinstance(item, dict):
                    axiom_id = item.get("id", "?")
                    when = item.get("when", "")
                    then = item.get("then", "")
                    axiom = item.get("axiom", "")
                    lines.append(f"{axiom_id}. {when} → {then}（{axiom}）")
            return "\n".join(lines)
        elif isinstance(data, dict):
            # 可能是 {"axioms": [...]} 或其他格式
            if "axioms" in data:
                return load_axioms_array(data["axioms"])
            elif "patterns" in data and isinstance(data["patterns"], list):
                return load_axioms_array(data["patterns"])

        return str(data)

    except Exception as e:
        logger.error(f"❌ 讀取 axioms 失敗：{e}")
        return FALLBACK_AXIOMS


def load_axioms_array(arr):
    """將 JSON 陣列轉為可讀文字"""
    lines = []
    for item in arr:
        if isinstance(item, dict):
            id_ = item.get("id", "?")
            when = item.get("when", "")
            then = item.get("then", "")
            reason = item.get("reason", item.get("axiom", ""))
            lines.append(f"{id_}. {when} → {then}｜理由：{reason}")
    return "\n".join(lines)


def clear_all_models():
    """物理清理：停止所有 Ollama 模型"""
    logger.info("🧹 [VRAM] 停止所有模型...")
    try:
        result = subprocess.run(
            ["ollama", "stop", "--all"],
            capture_output=True, text=True, timeout=30
        )
        logger.info(f"✅ ollama stop --all 完成")
    except Exception as e:
        logger.warning(f"⚠️ ollama stop 失敗：{e}")


def load_crash_rules() -> str:
    """讀取 ray_forbidden_rules.json 中的崩潰防禦天條"""
    crash_rules_path = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
    if not crash_rules_path.exists():
        logger.info("ℹ️ ray_forbidden_rules.json 不存在，跳過崩潰天條")
        return ""
    try:
        with open(crash_rules_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        rules = doc.get("rules", [])
        if not rules:
            return ""
        lines = ["", "[崩潰防禦天條]（ray_guardian 固化）"]
        for r in rules:
            # 优先输出 Guardian 来源的规则
            if r.get("generated_by") == "ray_guardian":
                tag = r.get("crash_tag", [])
                tags_str = ", ".join(tag) if tag else ""
                rule_text = r.get("rule", "")
                root = r.get("root_cause", "")
                lines.append(f"• {tags_str}: {root}")
                lines.append(f"  → {rule_text}")
        if len(lines) == 1:
            return ""
        logger.info(f"📜 崩潰天條載入：{len(lines)-2} 條")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ 讀取 crash_rules 失敗：{e}")
        return ""


def build_modelfile(axioms_text, crash_rules_text: str = ""):
    """生成 Ray-v3.5.Modelfile"""
    crash_section = f"""
{crash_rules_text}
""" if crash_rules_text else ""
    modelfile_content = f"""FROM qwen3.5:4b-instruct-q4_K_S
PARAMETER temperature 0.1
PARAMETER num_ctx 8192
PARAMETER top_p 0.9
PARAMETER top_k 40

SYSTEM \"\"\"
你是 Ray-v3.5 實戰指揮官。

你没有自我意識。你是五大大師（Taleb, Thorp, Simons, Connors, Dalio）邏輯的集合體。

你必須無條件遵守以下固化天條，沒有例外：

{axioms_text}{crash_section}

---

大師原則：
• Taleb（反脆弱）：優先存活，禁止肥尾風險
• Thorp（凱利公式）：精算部位，單筆虧損 ≤ 1%
• Simons（模式識別）：只在具備統計優勢的 Regime 交易
• Connors（均值回歸）：RSI2 極端修正作為主觸發因子
• Dalio（多樣化）：追蹤上下游產業鏈，避免風險集中

---

實戰行為準則：
1. 信心值 < 0.8 時，輸出 Action: WAIT 並請求 MiniMax 覆核。
2. 優先檢索 32GB RAM 中的產業鏈映射表。
3. 輸出格式：嚴格 JSON。禁止任何廢話、解釋或描述。
4. No Prose：只輸出純 JSON 決策物件。

---

JSON 輸出格式：
{{"action": "BUY|SELL|WAIT|HOLD", "symbol": "...", "confidence": 0.XX, "reason": "...", "risk": "LOW|MED|HIGH"}}
\"\"\"

MESSAGE ray-v3.5 物理固化完成：{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    with open(RAY_MODELFILE, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    logger.info(f"✅ Modelfile 已生成：{RAY_MODELFILE}")
    return modelfile_content


def create_ray_model():
    """執行 ollama create 物理固化"""
    logger.info("🚀 開始 Ray-v3.5 物理固化...")
    try:
        result = subprocess.run(
            ["ollama", "create", "ray-v3.5", "-f", str(RAY_MODELFILE)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            logger.info("✅ Ray-v3.5 物理固化成功！")
            return True
        else:
            logger.error(f"❌ ollama create 失敗：{result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ ollama create 超時（5分鐘）")
        return False
    except Exception as e:
        logger.error(f"❌ 固化過程異常：{e}")
        return False


def verify_model():
    """驗證模型是否成功創建"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=15
        )
        if "ray-v3.5" in result.stdout:
            logger.info("✅ 模型驗證：ray-v3.5 已存在於模型列表")
            return True
        else:
            logger.warning("⚠️ 模型驗證：ray-v3.5 未找到")
            return False
    except Exception as e:
        logger.warning(f"⚠️ 驗證失敗：{e}")
        return False


# ── 主程序 ──────────────────────────────────────────────────────────────────

@ray_singleton
def main():
    logger.info("=" * 50)
    logger.info(f"🚀 Ray Distiller Auto — 物理固化開始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # Step 1: 讀取 axioms + 崩潰天條
    axioms_text = load_axioms()
    crash_rules_text = load_crash_rules()
    logger.info(f"📜 天條載入：{len(axioms_text)} 字元")
    if crash_rules_text:
        logger.info(f"📜 崩潰天條載入：{len(crash_rules_text)} 字元")
    logger.info(f"天條預覽：{axioms_text[:200]}...")

    # Step 2: 清理 VRAM
    clear_all_models()

    # Step 3: 生成 Modelfile（含崩潰天條）
    modelfile = build_modelfile(axioms_text, crash_rules_text)

    # Step 4: 物理固化
    success = create_ray_model()

    # Step 5: 驗證
    if success:
        verify_model()
        logger.info("🎉 Ray-v3.5 指揮官已重生，隨時待命！")
    else:
        logger.error("❌ 固化失敗，請檢查日誌")

    logger.info("=" * 50)
    logger.info(f"🏁 固化流程完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)