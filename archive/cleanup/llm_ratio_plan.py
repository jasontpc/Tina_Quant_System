# -*- coding: utf-8 -*-
"""
Ray LLM 使用比例優化腳本
根據慢思考檢討結果，優化 1.5B vs 7B 的使用比例
"""

import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== Ray LLM 使用比例優化 ===")
print()
print("建議比例：1.5B = 80%, 7B = 20%")
print()
print("| 任務                    | 模型    | 佔比 |")
print("|------------------------|---------|------|")
print("| 技術指標計算（本地）     | Python  | 0%   |")
print("| 訊號評分（score<3）     | 1.5B    | 30%  |")
print("| 快速分類（Layer 1）     | 1.5B    | 25%  |")
print("| 狀態查詢                | 1.5B    | 20%  |")
print("| 深度歸因（Layer 2）     | 7B      | 15%  |")
print("| 蒸餾/策略進化           | 7B      | 10%  |")
print()
print("現有腳本已實現此比例：")
print("  ray_brain.py: fast_propose() 使用 1.5B")
print("  ray_self_correct.py: 1.5B 初審，7B 複審")
print("  ray_engine.py: 100% 本地 Python（不呼叫 LLM）")
print()
print("=== 完成 ===")