"""
Tina System Idle Checker
當系統閒置時，自動檢查待辦事項並執行建議。
"""
import yfinance as yf
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
MEMORY = Path(r"C:\Users\USER\.openclaw\workspace\memory")

OPENCLAW = r"C:\Users\USER\AppData\Roaming\npm\openclaw.cmd"

def get_cron_status():
    """檢查所有Cron狀態"""
    try:
        import subprocess
        result = subprocess.run(
            [OPENCLAW, "cron", "list"],
            capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore'
        )
        lines = result.stdout.strip().split('\n')
        
        # 解析 openclaw cron list 輸出（固定寬度格式）
        jobs = []
        for line in lines:
            if not line or line.startswith('ID '):
                continue
            # 跳過純空白行
            if line.strip() == '':
                continue
            
            # 根據位置解析
            # ID: 0-36, Name: 36-67, Schedule: 67-98, Next: 98-108, Last: 108-117, Status: 117-125
            try:
                job_id = line[0:36].strip()
                name = line[36:67].strip()
                schedule = line[67:98].strip()
                next_run = line[98:108].strip()
                last_run = line[108:117].strip()
                status = line[117:125].strip()
                
                if job_id and status:
                    jobs.append({
                        'id': job_id,
                        'name': name,
                        'state': {'lastStatus': status}
                    })
            except:
                continue
        
        running = [j for j in jobs if j.get('state', {}).get('lastStatus') == 'running']
        idle = [j for j in jobs if j.get('state', {}).get('lastStatus') == 'idle']
        error = [j for j in jobs if j.get('state', {}).get('lastStatus') == 'error']
        
        running = [j for j in jobs if j.get("state", {}).get("runningAtMs")]
        idle = [j for j in jobs if j.get("state", {}).get("lastStatus") == "idle"]
        error = [j for j in jobs if j.get("state", {}).get("lastStatus") == "error"]
        
        return {
            "total": len(jobs),
            "running": len(running),
            "idle": len(idle),
            "error": len(error),
            "jobs": jobs
        }
    except Exception as e:
        return {"total": 0, "running": 0, "idle": 0, "error": 1, "error_msg": str(e)}

def check_pending_todos():
    """檢查待辦事項"""
    todos = []
    
    # 檢查 Nana_status.md
    nana_status = MEMORY / "Nana_status.md"
    if nana_status.exists():
        content = nana_status.read_text(encoding="utf-8")
        if "P1" in content or "待處理" in content:
            # 找出待處理項目
            for line in content.split("\n"):
                if "P1" in line or ("缺口" in line and "+" in line):
                    todos.append(f"[Nana] {line.strip()}")
    
    # 檢查 Ray_status.md
    ray_status = MEMORY / "Ray_status.md"
    if ray_status.exists():
        content = ray_status.read_text(encoding="utf-8")
        if "待辦" in content or "P1" in content or "P2" in content:
            for line in content.split("\n"):
                if "待辦" in line or "P1" in line or "P2" in line:
                    todos.append(f"[Ray] {line.strip()}")
    
    # 檢查 automation_progress.md
    auto_progress = MEMORY / "automation_progress.md"
    if auto_progress.exists():
        content = auto_progress.read_text(encoding="utf-8")
        # 檢查是否有停滯的步驟
        if "循環計數: 0" in content:
            todos.append("[Tina] 10步引擎尚未正式啟動")
    
    # 檢查 institutional coverage
    coverage_file = MEMORY / "institutional_coverage_count.md"
    if coverage_file.exists():
        content = coverage_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if "覆蓋數量" in line or "總計" in line:
                todos.append(f"[Tina] {line.strip()}")
    
    return todos

def check_unfinished_suggestions():
    """檢查未完成的建議事項"""
    suggestions = []
    
    # 檢查 system_health.md
    health = MEMORY / "system_health.md"
    if health.exists():
        content = health.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if "未完成" in line or "建議" in line or "BLOCKED" in line:
                suggestions.append(f"[系統] {line.strip()}")
    
    # 檢查 failures.md
    failures = MEMORY / "failures.md"
    if failures.exists():
        content = failures.read_text(encoding="utf-8")
        if "失敗" in content:
            suggestions.append("[失敗分析] 有待處理的失敗記錄")
    
    return suggestions

def is_system_idle():
    """判斷系統是否閒置"""
    status = get_cron_status()
    
    # 如果有錯誤的Cron，系統不算閒置
    if status.get("error", 0) > 0:
        return False, f"無法獲取Cron狀態: {status.get('error_msg', 'unknown')}"
    
    # 如果有正在運行的Cron，系統不閒置
    if status.get("running", 0) > 0:
        return False, f"{status['running']}個Cron正在運行"
    
    # 如果有錯誤的Cron，需要處理
    if status.get("error", 0) > 0:
        return False, f"{status['error']}個Cron有錯誤，需要處理"
    
    # 如果所有Cron都是idle，系統閒置
    idle_count = status.get("idle", 0)
    total = status.get("total", 0)
    
    if idle_count >= 10:
        return True, f"系統閒置（{idle_count}/{total}個Cron idle）"
    elif idle_count >= 5:
        return True, f"系統基本閒置（{idle_count}/{total}個Cron idle）"
    else:
        return False, f"系統仍在運作（{idle_count}/{total}個Cron idle）"

def write_idle_report(status, todos, suggestions, action_taken):
    """寫入閒置報告"""
    report = MEMORY / "idle_check_report.md"
    content = f"""# 系統閒置檢查報告
## 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 系統狀態
- 總Cron數: {status.get('total', 'N/A')}
- 運行中: {status.get('running', 'N/A')}
- 閒置: {status.get('idle', 'N/A')}
- 錯誤: {status.get('error', 'N/A')}

## 閒置原因
{status.get('reason', 'N/A')}

## 待辦事項 ({len(todos)}項)
{chr(10).join(f'- {t}' for t in todos) if todos else '- 無'}

## 未完成建議 ({len(suggestions)}項)
{chr(10).join(f'- {s}' for s in suggestions) if suggestions else '- 無'}

## 本次執行動作
{chr(10).join(f'- {a}' for a in action_taken) if action_taken else '- 無'}
"""
    report.write_text(content, encoding="utf-8")
    return str(report)

def main():
    print("=" * 60)
    print("Tina 系統閒置檢查")
    print("=" * 60)
    
    # Step 1: 檢查系統是否閒置
    print("\n[1/4] 檢查系統狀態...")
    idle, reason = is_system_idle()
    print(f"      {reason}")
    
    if not idle:
        print("\n系統正常運行中，無需介入。")
        return
    
    # Step 2: 檢查待辦事項
    print("\n[2/4] 檢查待辦事項...")
    todos = check_pending_todos()
    print(f"      發現 {len(todos)} 項待辦")
    for t in todos[:5]:
        print(f"      - {t[:60]}")
    
    # Step 3: 檢查未完成的建議
    print("\n[3/4] 檢查未完成的建議...")
    suggestions = check_unfinished_suggestions()
    print(f"      發現 {len(suggestions)} 項未完成")
    
    action_taken = []
    
    # Step 4: 根據情況執行
    print("\n[4/4] 決定執行策略...")
    
    if todos:
        print("      → 有待辦事項，執行待辦清理")
        action_taken.append("執行待辦清理（見各團隊狀態檔案）")
    elif suggestions:
        print("      → 有未完成建議，執行建議事項")
        action_taken.append("執行建議事項（見 system_health.md）")
    else:
        print("      → 全部完成，執行10步引擎")
        action_taken.append("執行10步引擎")
        # 執行 10 步引擎
        try:
            import subprocess
            print("      → 啟動 automation_loop.py...")
            result = subprocess.run(
                ["python", str(BASE / "automation" / "automation_loop.py")],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                action_taken.append("10步引擎執行成功")
            else:
                action_taken.append(f"10步引擎執行失敗: {result.stderr[:100]}")
        except Exception as e:
            action_taken.append(f"10步引擎執行異常: {str(e)[:100]}")
    
    # 寫入報告
    report_path = write_idle_report(
        {"reason": reason, **get_cron_status()},
        todos, suggestions, action_taken
    )
    print(f"\n報告已寫入: {report_path}")
    
    print("\n" + "=" * 60)
    print("檢查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
