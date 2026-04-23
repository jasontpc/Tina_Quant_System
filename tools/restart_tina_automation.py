#!/usr/bin/env python3
"""
Tina 自動化重啟腳本
每小時執行，確保 Tina 10步驟循環持續運行
"""

import subprocess
import sys

def restart_tina_automation():
    """重啟 Tina 自動化子任務"""
    cmd = [
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, 'C:/Users/USER/.openclaw/workspace')
from openclaw import sessions_spawn

sessions_spawn(
    runtime='subagent',
    mode='run',
    label='tina-automation',
    task='''## 任務：Tina 主系統 - 永續自動化改善循環

你是 Tina 主系統的永續自動化引擎。執行 10 步驟循環，持續優化系統。

### 10 步驟循環
1. 分析失敗原因
2. 安裝缺少技能
3. 擴充資料
4. 優化評分
5. 回測股票池
6. 分級策略
7. 動態調整
8. 權重優化
9. 系統檢討
10. 執行改善

完成第10步後回到步驟1，循環計數+1，永不停止。

### 進度追蹤
寫入 memory/automation_progress.md

### 立即開始
讀取進度檔案，開始執行第一步。'''
)
"""
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f" Tina 自動化重啟: {'成功' if result.returncode == 0 else '失敗'}")
    return result.returncode == 0

if __name__ == "__main__":
    restart_tina_automation()