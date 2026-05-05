# -*- coding: utf-8 -*-
"""
Tina Cron 智能調整腳本
======================
清理重複/錯誤的 cron，優化排程時段
"""
import subprocess, json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# 清理清單（需移除的爛攤子）
CLEANUP_IDS = [
    'd7c9c175',  # Tina 每小時心跳監控（舊版，超時）
]

# 修復清單（需更新腳本或 timeout 的）
FIX_JOBS = [
    ('1c5349f9', 'RSI 數值覆核'),  # RSI cron 需改用本地 DB
]

# 應該刪除的重複 cron（多個 16:00 更新）
DUPLICATE_16 = [
    '27597611',  # Nana 每日DB更新
    'c0befe86',  # Leo 每日DB更新
    'f57996ce',  # Maggy 每日DB更新
    'facc1550',  # Tina 每日DB更新（已合併到統一）
]

# 應該刪除的閒置 cron（delivery 有問題）
IDLE_BROKEN = [
    '67d65889',  # Tina 股票追蹤（explicit delivery）
    'c66a23cd',  # Tina 大腦-每日報告（explicit delivery）
    'd470e2f2',  # Tina 每週複習（explicit delivery）
    '82c6406f',  # Tina 大腦週報（explicit delivery）
]

# 保留的 cron（不動）
KEEP_JOBS = {
    'ff547cbe': 'Tina 心跳監控（Gateway快速檢查）',
    'd9850830': 'Tina Cron 優化器（每2小時）',
    'c93f50c4': 'Tina 每日趨勢掃描（09:00）',
    'e1f8513c': 'Tina 市場雷達（14:00）',
    'd4034ea4': 'Tina 成長股海巡（15:00）',
    'f165269e': 'Tina ETF 每日收盤更新（16:00）',
    '00221ac7': 'Yahoo ETF 每日增量更新（16:00）',
    '1306d237': 'Tina 自動學習擴充DB（17:00）',
}


def run_cmd(cmd_list):
    """在 Windows 上使用 cmd /c 執行命令"""
    cmd_str = ' '.join(cmd_list)
    result = subprocess.run(
        ['cmd', '/c', cmd_str],
        capture_output=True,
        encoding='utf-8',
        errors='replace'
    )
    return result.returncode == 0, result.stdout or '', result.stderr or ''


def list_crons():
    """取得目前所有 cron ID"""
    ok, stdout, stderr = run_cmd(['openclaw', 'cron', 'list'])
    if not ok:
        print('  [WARN] 無法取得 cron 清單:', stderr)
        return []
    crons = []
    for line in stdout.split('\n'):
        if len(line) >= 36 and line[0] != ' ':
            parts = line.split()
            if parts:
                crons.append(parts[0])
    return crons


def remove_cron(cron_id):
    """移除指定的 cron（Windows 版本）"""
    ok, stdout, stderr = run_cmd(['openclaw', 'cron', 'remove', cron_id])
    return ok


def main():
    print('='*60)
    print('  Tina Cron 智能調整')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)
    print()

    # 1. 清理舊心跳
    print('[1/5] 清理舊心跳...')
    for cid in CLEANUP_IDS:
        print('  remove', cid, '...', end=' ')
        ok = remove_cron(cid)
        print('OK' if ok else 'FAILED (可能已不存在)')

    # 2. 清理重複的 16:00 cron
    print()
    print('[2/5] 清理重複的 16:00 cron（已合併到統一更新）...')
    for cid in DUPLICATE_16:
        print('  remove', cid, '...', end=' ')
        ok = remove_cron(cid)
        print('OK' if ok else 'FAILED (可能已不存在)')

    # 3. 清理 delivery 有問題的 idle cron
    print()
    print('[3/5] 清理 delivery 有問題的 idle cron...')
    for cid in IDLE_BROKEN:
        print('  remove', cid, '...', end=' ')
        ok = remove_cron(cid)
        print('OK' if ok else 'FAILED (可能已不存在)')

    # 4. 顯示清理後的 cron 狀態
    print()
    print('[4/5] 顯示清理後的 cron 狀態...')
    crons = list_crons()
    print('  目前有', len(crons), '個 cron')

    # 5. 建議的排程時間表
    print()
    print('[5/5] 建議的排程時間表（清理後）...')
    schedule = [
        ('09:00', '趨勢掃描 + 大腦報告'),
        ('14:00', '市場雷達（主動狩）'),
        ('15:00', '成長股海巡'),
        ('16:00', 'DB更新 + ETF更新'),
        ('17:00', '自動學習'),
    ]
    for time, desc in schedule:
        print('  ' + time + ' → ' + desc)

    print()
    print('='*60)
    print('  智能調整完成')
    print('='*60)


if __name__ == '__main__':
    main()