#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tina 自動化系統 - Cron Manifest 套用工具
"""

import json
import subprocess
import sys

MANIFEST_PATH = "cron_manifest.json"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def get_current_ids():
    """取得目前所有 Cron 任務 ID"""
    code, stdout, _ = run_cmd("openclaw cron list")
    if code != 0:
        return []
    lines = stdout.split('\n')
    ids = []
    for line in lines:
        parts = line.split()
        if parts and parts[0].count('-') >= 2:
            ids.append(parts[0])
    return ids

def remove_all_crons():
    """移除所有 Cron 任務"""
    print("移除所有 Cron 任務...")
    ids = get_current_ids()
    for cron_id in ids:
        print(f"  移除: {cron_id}")
        run_cmd(f"openclaw cron rm {cron_id}")
    print(f"已移除 {len(ids)} 個 Cron 任務")
    return True

def apply_manifest(dry_run=False):
    """套用 Cron Manifest"""
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"無法讀取 {MANIFEST_PATH}: {e}")
        return False
    
    print(f"讀取 Manifest: {manifest.get('description', '')}")
    print(f"架構: {manifest.get('architecture', {}).get('說明', '')}")
    print()
    
    jobs = manifest.get('cron_jobs', [])
    print(f"共 {len(jobs)} 個 Cron 任務")
    print()
    
    for job in jobs:
        name = job.get('name', 'Unknown')
        schedule = job.get('schedule', '')
        message = job.get('message', '')
        desc = job.get('description', '')
        enabled = job.get('enabled', True)
        target = job.get('target', '')
        
        if not enabled:
            print(f"跳過 (已停用): {name}")
            continue
        
        print(f"設定: {name}")
        print(f"  排程: {schedule}")
        print(f"  說明: {desc}")
        
        if dry_run:
            print(f"  [DRY RUN] 不實際執行")
            print()
            continue
        
        cmd = f'openclaw cron add --name "{name}" --cron "{schedule}" --message "{message}"'
        
        if target:
            cmd += f' --to "{target}"'
        
        print(f"  執行中...")
        code, stdout, stderr = run_cmd(cmd)
        
        if code != 0:
            print(f"  錯誤: {stderr[:100] if stderr else 'unknown'}")
        else:
            print(f"  成功!")
        print()
    
    print("完成!")
    return True

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    remove = "--remove" in sys.argv
    
    if remove:
        remove_all_crons()
    else:
        if dry_run:
            print("[DRY RUN MODE]")
        apply_manifest(dry_run=dry_run)