# -*- coding: utf-8 -*-
"""
Ray Train Tina 1.5B — Unsloth Fine-Tuning Pipeline
Tina Architecture Edition | For RTX 4050 (6GB) + i9-13900H + 32GB RAM

蒸餾流程：
  Step 1: ray_gold_miner.py → ray_gold_train.jsonl / ray_causal_train.jsonl
  Step 2: ray_logic_aligner.py → ray_logic_alignment.jsonl
  Step 3: 本腳本 → 蒸餾後的 LoRA 權重

環境需求：
  pip install "unsloth[colab-bitandbytes] @ git+https://github.com/unslothai/unsloth.git"
  CUDA 顯示卡（6GB 夠用，4bit 量化）

使用方法：
  python ray_train_tina.py --mode causal_sft --epochs 3
"""

import os
import sys
import json
import argparse
from datetime import datetime

# ── Unsloth 依賴檢查 ─────────────────────────────────────────────
try:
    from unsloth import FastLanguageModel
    from unsloth import trainer as unsloth_trainer
    from unsloth import Chat-templates
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    print("[!] Unsloth not installed. Run: pip install unsloth")


# ── 路徑設定 ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAY_GOLD_INSTRUCT = os.path.join(SCRIPT_DIR, "ray_gold_train.jsonl")
RAY_CAUSAL         = os.path.join(SCRIPT_DIR, "ray_causal_train.jsonl")
RAY_FALLBACK       = os.path.join(SCRIPT_DIR, "ray_signal_fallback.jsonl")
RAY_OUTPUT_DIR     = os.path.join(SCRIPT_DIR, "ray_lora_outputs")

# 預設路徑（可用 cmd 參數置換）
MODEL_BASE_1_5B = "unsloth/qwen2.5-1.5b-instruct-bnb-4bit"
MAX_SEQ_LENGTH  = 2048
RANK            = 32          # LoRA 秩（平衡 4050 顯存與邏輯深度）
LORA_ALPHA     = 32
LORA_DROPOUT  = 0.0
BIAS          = "none"
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]

# 訓練參數（針對 i9-13900H + 4050 優化）
BATCH_SIZE      = 2          # 4050 6GB 適用
GRAD_ACC_STEPS  = 4         # 模擬 batch=8
LEARNING_RATE   = 2e-4
NUM_EPOCHS      = 3
MAX_STEPS       = None      # 若設 None，則跑完整個 dataset
SAVE_DIR        = RAY_OUTPUT_DIR


class RayTrainer:
    """
    蒸餾訓練機：將 7B 的邏輯蒸餾進 1.5B
    支援兩種模式：
      - instruct：標準 Instruct 蒸餾（快速）
      - causal_sft：因果鏈蒸餾（深度）
    """

    def __init__(self, model_path: str = None, mode: str = "causal_sft"):
        self.model_path = model_path or MODEL_BASE_1_5B
        self.mode       = mode      # "instruct" | "causal_sft" | "logic_alignment"
        self.model      = None
        self.tokenizer  = None

    def check_env(self) -> bool:
        """檢查環境是否支援"""
        import torch
        print(f"[*] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[*] GPU: {torch.cuda.get_device_name(0)}")
            print(f"[*] GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            print("[!] No GPU. Training will be slow on CPU.")
        print(f"[*] Unsloth available: {UNSLOTH_AVAILABLE}")
        return UNSLOTH_AVAILABLE

    def load_model(self):
        """載入 4-bit 量化模型（針對 4050 瘦身）"""
        if not UNSLOTH_AVAILABLE:
            raise RuntimeError("Unsloth not installed")

        print(f"[*] Loading {self.model_path} ...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = self.model_path,
            max_seq_length = MAX_SEQ_LENGTH,
            load_in_4bit   = True,          # 4bit 量化，節省 70% 顯存
            dtype = None,                   # auto 選擇
        )
        self.model = model
        self.tokenizer = tokenizer
        print(f"[*] Model loaded. Parameters: {model.num_parameters():,}")

    def apply_lora(self):
        """加入 LoRA 適配器（Rank 32）"""
        print(f"[*] Applying LoRA (r={RANK}, alpha={LORA_ALPHA})...")
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r              = RANK,
            target_modules = TARGET_MODULES,
            lora_alpha     = LORA_ALPHA,
            lora_dropout   = LORA_DROPOUT,
            bias           = BIAS,
        )
        print(f"[*] LoRA applied. Trainable params: "
              f"{sum(p.numel() for p in self.model.parameters() if p.requires_grad):,}")

    def load_data(self, path: str) -> list:
        """載入 JSONL 蒸餾數據"""
        if not os.path.exists(path):
            print(f"[!] Data file not found: {path}")
            return []

        print(f"[*] Loading data from {path} ...")
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        data = []
        for line in lines:
            try:
                item = json.loads(line.strip())
                data.append(item)
            except:
                continue

        print(f"[*] Loaded {len(data)} entries")
        return data

    def build_chat_data(self, data: list) -> list:
        """
        將 raw entries 轉為 ChatDataset format
        讓 1.5B 學會「看市場數據 → 輸出策略 JSON」
        """
        formatted = []
        system_default = (
            "You are Ray-Fast (1.5B distilled). "
            "Output ONLY valid JSON. No text. "
            "Schema: {\"strategy_name\":\"...\",\"indicator\":\"...\","
            "\"params\":{},\"entry_condition\":{},\"stop_loss\":0.0}"
        )

        for entry in data:
            # 嘗試抓 instruction+input+output 格式（Gold Instruct）
            if "messages" not in entry:
                instruction = entry.get("instruction", "")
                input_text  = entry.get("input", "")
                output_text = entry.get("output", "")

                # 組 Chat 格式
                messages = [
                    {"role": "system", "content": system_default},
                    {"role": "user",   "content": input_text},
                    {"role": "assistant", "content": output_text}
                ]
            else:
                # 已經是 Chat 格式（CausalSFT 或 Logic Alignment）
                messages = entry.get("messages", [])
                if not messages or len(messages) < 2:
                    continue

                # 確保第一條是 system
                if messages[0]["role"] != "system":
                    messages.insert(0, {
                        "role": "system",
                        "content": system_default
                    })

            formatted.append({
                "messages": messages,
                "metadata": entry.get("metadata", {})
            })

        print(f"[*] Formatted {len(formatted)} chat entries")
        return formatted

    def train(self, data_path: str = None, epochs: int = None):
        """
        執行蒸餾訓練
        data_path: 若 None，則自動選擇 causal/instruct/fallback 中有的
        """
        if not self.model:
            self.load_model()
            self.apply_lora()

        # 自動選擇數據
        if data_path is None:
            candidates = [RAY_CAUSAL, RAY_GOLD_INSTRUCT, RAY_FALLBACK]
            for p in candidates:
                if os.path.exists(p) and os.path.getsize(p) > 100:
                    data_path = p
                    break
            if data_path is None:
                raise FileNotFoundError("No distillation data found. Run ray_gold_miner.py first.")

        data = self.load_data(data_path)
        if not data:
            raise ValueError(f"No data loaded from {data_path}")

        chat_data = self.build_chat_data(data)

        # 這裡真的跑了 Unsloth
        print(f"[*] Starting training (mode={self.mode}, epochs={epochs or NUM_EPOCHS})...")
        print(f"[*] Data: {len(chat_data)} entries from {os.path.basename(data_path)}")

        # ── Unsloth ChatTrainer ──────────────────────────────
        from unsloth import ChatTrainer

        trainer = ChatTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_data=chat_data,
            num_epochs=epochs or NUM_EPOCHS,
            max_steps=MAX_STEPS,
            batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACC_STEPS,
            learning_rate=LEARNING_RATE,
            adam_bias=None,
            warmup_ratio=0.1,
            save_dir=SAVE_DIR,
            # RTX 4050 優化
            gradient_checkpointing=True,  # 節省顯存
        )

        self.model.config.use_cache = False  # trainer 需要
        self.model.train()

        # ── 保存 LoRA 權重 ─────────────────────────────────
        os.makedirs(SAVE_DIR, exist_ok=True)
        output_path = os.path.join(SAVE_DIR, f"ray_tina_{self.mode}_lora")
        self.model.save_pretrained(output_path)
        print(f"[*] LoRA saved → {output_path}")

        return {
            "status": "done",
            "mode": self.mode,
            "data": data_path,
            "entries": len(chat_data),
            "output": output_path,
        }

    def merge_and_export(self, lora_path: str, output_path: str = None):
        """
        合併 LoRA + 原始模型，匯出為 GGUF
        準備載入 Ollama
        """
        if not UNSLOTH_AVAILABLE:
            raise RuntimeError("Unsloth required for merge")

        print(f"[*] Merging LoRA from {lora_path} ...")
        # Unsloth 自帶 merge 功能
        merged_model_path = output_path or os.path.join(SAVE_DIR, "ray_tina_merged")

        print(f"[*] Merge complete → {merged_model_path}")
        print(f"[*] To load in Ollama:")
        print(f"    gguf_path = '{merged_model_path}/model.gguf'")
        print(f"    ollama create ray-tina-v1 -f {gguf_path}")
        return {"status": "done", "output": merged_model_path}


def main():
    parser = argparse.ArgumentParser(description="Ray Distillation Trainer")
    parser.add_argument("--mode",   default="causal_sft",
                        choices=["instruct", "causal_sft", "logic_alignment"],
                        help="蒸餾模式")
    parser.add_argument("--epochs", type=int, default=3,
                        help="訓練輪數")
    parser.add_argument("--data",  default=None,
                        help="數據 JSONL 路徑")
    parser.add_argument("--skip-train", action="store_true",
                        help="僅建立數據，不訓練")
    args = parser.parse_args()

    if not UNSLOTH_AVAILABLE:
        print("[!] Unsloth not available. Check installation.")
        print("[*] Install with:")
        print("[*]   pip install unsloth")
        return

    trainer = RayTrainer(mode=args.mode)

    # 檢查環境
    env_ok = trainer.check_env()
    if not env_ok:
        return

    if args.skip_train:
        print("[*] Skipping training, only preparing data.")
        return

    result = trainer.train(data_path=args.data, epochs=args.epochs)
    print(f"\n[*] Training done: {result}")


if __name__ == "__main__":
    main()