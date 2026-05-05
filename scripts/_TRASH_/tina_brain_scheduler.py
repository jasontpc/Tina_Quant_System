# -*- coding: utf-8 -*-
"""
Tina Brain - 團隊學習目標與排程管理器 v2
======================================
每個團隊都有明確的：
  1. 學習目標（每週 / 每月）
  2. 輸入來源（本地 DB）
  3. 輸出目標（訊號 / 報告）
  4. 自評機制（勝率 / 學習筆記）
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

# ===== 團隊學習目標定義 =====
TEAMS = {
    "NANA": {
        "role": "台股波段操作（個股）",
        "focus": "2382/2330/3665/2317/3034 波段交易",
        "input_db": "yfinance.db / limitup.db",
        "output": "nana_signal.json",
        "schedule": "*/20 9-23 * * 1-5",  # 每20分鐘
        "learning_cycle": "週一回測 → 週二應用 → 週五檢討",
        "goal": "RSI<35 + MA多头排列 + 動量確認 → 進場",
        "metric": "勝率 > 65%，平均報酬 > +2%",
        "priority": 1,
    },
    "RAY": {
        "role": "ETF 定額定期（長抱）",
        "focus": "0050/00646/00662/00713/0056 ETF DCA",
        "input_db": "yfinance.db / finmind.db",
        "output": "ray_dca_signal.json",
        "schedule": "0 16 * * 1-5",  # 每日 16:00
        "learning_cycle": "每季檢視 ETF 表現",
        "goal": "RSI < 40 進場，長抱 6-12 個月",
        "metric": "殖利率 > 3%，通膨 +2% 跑贏",
        "priority": 1,
    },
    "LEO": {
        "role": "台股 AI 科技股波段",
        "focus": "2330/2454/2317 等科技股",
        "input_db": "yfinance.db / finmind.db",
        "output": "leo_signal.json",
        "schedule": "0 8,11,14,17,21 * * 1-5",  # 盤中5次
        "learning_cycle": "每週一回測，每週日自主學習",
        "goal": "MA60>MA20 + RSI<35 + 法人買進",
        "metric": "勝率 > 60%，平均報酬 > +3%",
        "priority": 1,
    },
    "MAGGY": {
        "role": "美股 AI 科技選股",
        "focus": "INTC/MU/NVDA/AVGO/QCOM 等科技股",
        "input_db": "yfinance.db / stocktwits_sentiment.db",
        "output": "maggy_signal.json",
        "schedule": "0 8 * * 1-5",  # 每日 08:00
        "learning_cycle": "每週一回測",
        "goal": "MA 多頭排列 + RSI 40-50 + 社群情緒觀察",
        "metric": "勝率 > 55%",
        "priority": 2,
    },
    "SHERKY": {
        "role": "ETF DCA 市場分析",
        "focus": "XLV/VHT/GLD/TLT/LQD 等 ETF",
        "input_db": "sherry_etf.db",
        "output": "sherry_signal.json",
        "schedule": "0 8 * * 1-5",
        "learning_cycle": "每週日自主學習更新 ETF 觀察名單",
        "goal": "RSI<40 進場，殖利率參考",
        "metric": "進場準確率 > 70%",
        "priority": 2,
    },
    "VOGEL": {
        "role": "台指期策略開發",
        "focus": "^TWII 台指期",
        "input_db": "vogel_tx.db",
        "output": "vogel_signal.json",
        "schedule": "0 9 * * 0",  # 每周日
        "learning_cycle": "每週回測信號",
        "goal": "BB突破 + RSI+MACD 共振",
        "metric": "勝率 > 60%，Avg Win/Loss > 3",
        "priority": 3,
    },
}

def print_team_report():
    print("=" * 65)
    print("  Tina Brain - 團隊學習目標與排程")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    for name, info in sorted(TEAMS.items(), key=lambda x: x[1]["priority"]):
        print(f"[{name}] {info['role']}")
        print(f"  專注: {info['focus']}")
        print(f"  目標: {info['goal']}")
        print(f"  排程: {info['schedule']}")
        print(f"  輸入: {info['input_db']}")
        print(f"  指標: {info['metric']}")
        print(f"  學習循環: {info['learning_cycle']}")
        print()

    print("=" * 65)
    print("Tina 大腦協調原則:")
    print("  1. 每日 08:00 市場快報 → 所有團隊輸入統一")
    print("  2. 社群情緒（觀察用）→ 不影響 Nana/Leo 進場分數")
    print("  3. RSI bias 修復 → 優先處理 diff>5 的標的")
    print("  4. Sherry/Vogel 重新啟動 → 納入 Tina 每週檢視")
    print("  5. Cron timeout → 全數修正至 300s 以上")
    print("=" * 65)


if __name__ == "__main__":
    print_team_report()
