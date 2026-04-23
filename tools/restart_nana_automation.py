#!/usr/bin/env python3
"""
Nana 自動化重啟腳本
每6小時執行，確保 Nana 波段系統持續運行
"""

import subprocess
import sys

def restart_nana_automation():
    """重啟 Nana 自動化子任務"""
    cmd = [
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, 'C:/Users/USER/.openclaw/workspace')
from openclaw import sessions_spawn

sessions_spawn(
    runtime='subagent',
    mode='run',
    label='nana-automation',
    task='''## 任務：Nana 波段系統 - 永續自動化

你是 Nana，Tina 系統的波段交易專家。執行持續自動化波段交易循環。

### 核心功能
1. 每 6 小時掃描股票池（51檔）
2. 評分系統：法人(40%) + 技術(35%) + 趨勢(25%)
3. 動態持有：1-7天靈活持有
4. 持續學習：分析失敗案例

### 每 6 小時執行
1. 執行 nana_v5.py
2. 生成 Top Picks 報告
3. 判斷市場狀態
4. 寫入 memory/nana_daily_YYYYMMDD.md
5. 更新 memory/nana_trades.md

### Veto 規則
- RSI > 70（多頭）或 RSI > 65（空頭）
- VIF < 1.0
- 法人連續賣超 ≥ 3天
- Bias > 8%

### 立即開始
執行 nana_v5.py，生成掃描報告。'''
)
"""
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f" Nana 自動化重啟: {'成功' if result.returncode == 0 else '失敗'}")
    return result.returncode == 0

if __name__ == "__main__":
    restart_nana_automation()