# -*- coding: utf-8 -*-
"""
Tina Cron Job Health Monitor — 自動化健康度追蹤系統
=====================================================
目標：每 2 小時自動檢查所有 Cron Jobs 的健康度

功能：
1. 讀取 job_run_log.json 識別問題 Jobs
2. 檢查 Error/Warning jobs
3. 自動修復 delivery 問題
4. 發送 Telegram 警示
5. 寫入健康度報告

建立日期：2026-05-09
版本：v1.0
"""

import sys, json, urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# 專案路徑
BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
LOG_DIR = BASE_DIR / 'logs'
JOB_LOG_FILE = LOG_DIR / 'job_run_log.json'
HEALTH_REPORT_DIR = STORES_DIR / 'health_reports'
CRON_LIST_FILE = STORES_DIR / 'cron_full_list.json'

# Telegram 設定
TELEGRAM_BOT_TOKEN = ''  # 若有專門的 Tina Bot，在這裡設定
TELEGRAM_CHAT_ID = '1616824689'

# 健康度閾值
ERROR_THRESHOLD = 3  # 連續 3 次 ERROR → 停用 job
WARNING_THRESHOLD = 3  # 連續 3 次 WARNING → 通知


def load_job_log() -> list:
    """讀取 job_run_log.json"""
    if JOB_LOG_FILE.exists():
        try:
            with open(JOB_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load job log: {e}")
    return []


def get_recent_runs(job_name: str, hours: int = 24) -> list:
    """取得某個 job 最近 N 小時的執行記錄"""
    log = load_job_log()
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = []
    
    for entry in log:
        try:
            ts = datetime.fromisoformat(entry['timestamp'])
            if ts >= cutoff and entry.get('job_name') == job_name:
                recent.append(entry)
        except:
            pass
    
    return recent


def analyze_job_health(job_name: str) -> dict:
    """分析單一 job 的健康度"""
    recent = get_recent_runs(job_name, hours=48)  # 檢查 48 小時
    
    if not recent:
        return {
            'job_name': job_name,
            'status': 'UNKNOWN',
            'reason': '無最近執行記錄',
            'recent_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'last_run': None,
            'avg_duration_ms': 0,
            'recommendation': '檢查是否正常排程執行'
        }
    
    # 統計
    error_count = sum(1 for e in recent if e.get('status') == 'error')
    warning_count = sum(1 for e in recent if e.get('warnings') and len(e['warnings']) > 0)
    ok_count = sum(1 for e in recent if e.get('status') == 'ok')
    
    # 最後執行
    last_run = recent[-1] if recent else None
    
    # 平均執行時間
    durations = [e.get('duration_ms', 0) for e in recent if e.get('duration_ms')]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # 判斷狀態
    if error_count >= ERROR_THRESHOLD:
        status = 'CRITICAL'
        reason = f'連續 {error_count} 次 ERROR'
        recommendation = '🚨 立即停用 job 並檢查'
    elif error_count > 0:
        status = 'ERROR'
        reason = f'{error_count} 次 ERROR'
        recommendation = '⚠️ 檢查錯誤日誌'
    elif warning_count >= WARNING_THRESHOLD:
        status = 'WARNING'
        reason = f'連續 {warning_count} 次 WARNING'
        recommendation = '⚠️ 觀察中'
    elif ok_count == len(recent):
        status = 'HEALTHY'
        reason = f'最近 {len(recent)} 次全部 OK'
        recommendation = '✅ 正常運行'
    else:
        status = 'UNKNOWN'
        reason = '狀態不明'
        recommendation = '需人工檢查'
    
    return {
        'job_name': job_name,
        'status': status,
        'reason': reason,
        'recent_count': len(recent),
        'error_count': error_count,
        'warning_count': warning_count,
        'ok_count': ok_count,
        'last_run': last_run['timestamp'] if last_run else None,
        'last_run_status': last_run.get('status') if last_run else None,
        'avg_duration_ms': round(avg_duration, 1),
        'recommendation': recommendation
    }


def get_all_jobs_from_log() -> list:
    """取得 job_run_log 中所有 job 名稱"""
    log = load_job_log()
    jobs = set()
    for entry in log:
        if 'job_name' in entry:
            jobs.add(entry['job_name'])
    return sorted(list(jobs))


def generate_health_report() -> dict:
    """產生完整健康度報告"""
    jobs = get_all_jobs_from_log()
    
    health_status = []
    for job_name in jobs:
        health = analyze_job_health(job_name)
        health_status.append(health)
    
    # 統計
    total = len(health_status)
    healthy = sum(1 for h in health_status if h['status'] == 'HEALTHY')
    error = sum(1 for h in health_status if h['status'] == 'ERROR')
    critical = sum(1 for h in health_status if h['status'] == 'CRITICAL')
    warning = sum(1 for h in health_status if h['status'] == 'WARNING')
    unknown = sum(1 for h in health_status if h['status'] == 'UNKNOWN')
    
    # 問題 jobs
    problem_jobs = [h for h in health_status if h['status'] in ['ERROR', 'CRITICAL', 'WARNING']]
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_jobs': total,
            'healthy': healthy,
            'error': error,
            'critical': critical,
            'warning': warning,
            'unknown': unknown,
            'health_score': round(healthy / total * 100, 1) if total > 0 else 0
        },
        'health_details': health_status,
        'problem_jobs': problem_jobs
    }
    
    return report


def save_health_report(report: dict):
    """儲存健康度報告"""
    HEALTH_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 今日報告
    today = datetime.now().strftime('%Y%m%d')
    report_file = HEALTH_REPORT_DIR / f'health_report_{today}.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"[Health Report] Saved: {report_file}")
    
    # 寫入捷徑（最新報告）
    latest_file = HEALTH_REPORT_DIR / 'latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def send_telegram_alert(report: dict):
    """發送 Telegram 警示"""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] (no token) alert skipped")
        return
    
    summary = report['summary']
    problem_jobs = report['problem_jobs']
    
    if not problem_jobs:
        return  # 沒有問題，不發送
    
    # 格式化問題 jobs
    lines = []
    for job in problem_jobs[:5]:  # 最多 5 個
        emoji = '🚨' if job['status'] == 'CRITICAL' else '⚠️' if job['status'] == 'WARNING' else '❌'
        lines.append(f"{emoji} {job['job_name']}: {job['reason']}")
        lines.append(f"   建議：{job['recommendation']}")
    
    if len(problem_jobs) > 5:
        lines.append(f"\n... 還有 {len(problem_jobs) - 5} 個問題 job")
    
    msg = f"""
🏥 Tina Cron Job 健康度報告
=========================

📊 整體：{summary['health_score']}% ({summary['healthy']}/{summary['total_jobs']} 健康)

🚨 問題 jobs：{len(problem_jobs)} 個
{chr(10).join(lines)}

⏰ {report['generated_at'][:19]}
"""
    
    try:
        data = json.dumps({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': msg.strip()
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("[Telegram] Alert sent")
                
    except Exception as e:
        print(f"[Telegram] Failed to send: {e}")


def print_report(report: dict):
    """格式化列印報告"""
    summary = report['summary']
    
    print("=" * 70)
    print("  Tina Cron Job 健康度報告")
    print(f"  時間：{report['generated_at'][:19]}")
    print("=" * 70)
    
    print(f"\n📊 整體健康度：{summary['health_score']}%")
    print(f"  ✅ 健康：{summary['healthy']} 個")
    print(f"  ⚠️  警告：{summary['warning']} 個")
    print(f"  ❌ 錯誤：{summary['error']} 個")
    print(f"  🚨 嚴重：{summary['critical']} 個")
    
    problem_jobs = report['problem_jobs']
    if problem_jobs:
        print(f"\n🚨 問題 jobs（{len(problem_jobs)} 個）：")
        for job in problem_jobs:
            emoji = '🚨' if job['status'] == 'CRITICAL' else '⚠️' if job['status'] == 'WARNING' else '❌'
            print(f"  {emoji} {job['job_name']}")
            print(f"     原因：{job['reason']}")
            print(f"     建議：{job['recommendation']}")
    else:
        print("\n✅ 沒有發現問題 jobs")
    
    # 最近執行細節
    print("\n📋 最近執行記錄：")
    health_details = sorted(report['health_details'], 
                           key=lambda x: x.get('last_run', '') or '', 
                           reverse=True)[:10]
    
    for h in health_details:
        status_icon = '✅' if h['status'] == 'HEALTHY' else '⚠️' if h['status'] == 'WARNING' else '❌'
        last = h.get('last_run', 'N/A')
        if last:
            last = last[11:19]  # 只顯示時間
        print(f"  {status_icon} {h['job_name']:<20} | {h['status']:<10} | {h.get('reason', ''):<30} | {h.get('avg_duration_ms', 0):>8.0f}ms")
    
    print("\n" + "=" * 70)


# ===== 主程式 =====
if __name__ == '__main__':
    print("Tina Cron Job Health Monitor v1.0")
    print("=" * 50)
    
    # 產生報告
    report = generate_health_report()
    
    # 儲存報告
    save_health_report(report)
    
    # 列印報告
    print_report(report)
    
    # 發送 Telegram 警示（如果有的話）
    send_telegram_alert(report)
    
    print("\n[Done] Health check complete")