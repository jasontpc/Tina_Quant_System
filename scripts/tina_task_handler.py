"""
Tina Auto Task Handler - 主動處理待辦事項並學習
Monitor pending tasks, process them, learn from outcomes for future automation
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'tina_task_handler.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 待辦事項表
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            task_key TEXT NOT NULL,
            description TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_attempt TEXT,
            attempts INTEGER DEFAULT 0,
            resolved_at TEXT,
            resolution TEXT,
            outcome TEXT
        )
    ''')
    
    # 任務模板（學習後的預設操作）
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            task_pattern TEXT,
            default_action TEXT,
            success_rate REAL DEFAULT 0.0,
            times_used INTEGER DEFAULT 0,
            last_used TEXT,
            auto_execute INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 操作歷史
    c.execute('''
        CREATE TABLE IF NOT EXISTS action_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            action_taken TEXT,
            result TEXT,
            success INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES pending_tasks(id)
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_task_type ON pending_tasks(task_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_status ON pending_tasks(status)')
    
    conn.commit()
    conn.close()

def add_task(task_type, task_key, description, priority=5):
    """添加待辦事項"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO pending_tasks (task_type, task_key, description, priority)
        VALUES (?, ?, ?, ?)
    ''', (task_type, task_key, description, priority))
    
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return task_id

def get_pending_tasks(limit=20):
    """獲取待處理任務"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM pending_tasks 
        WHERE status = 'pending' 
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
    ''', (limit,))
    
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return rows

def resolve_task(task_key, resolution, success, auto_executed=False):
    """解決任務並學習"""
    conn = get_db()
    c = conn.cursor()
    
    # 更新任務狀態
    c.execute('''
        UPDATE pending_tasks 
        SET status = 'resolved',
            resolution = ?,
            outcome = ?,
            resolved_at = ?
        WHERE task_key = ?
    ''', (resolution, 'success' if success else 'failed', datetime.now().isoformat(), task_key))
    
    # 記錄操作歷史
    c.execute('''
        INSERT INTO action_history (task_id, action_taken, result, success)
        SELECT id, ?, ?, ?
        FROM pending_tasks WHERE task_key = ?
    ''', (resolution, 'success' if success else 'failed', 1 if success else 0, task_key))
    conn.commit()
    conn.close()

def learn_template(task_type, action, auto_executed):
    """學習並更新模板"""
    conn = get_db()
    c = conn.cursor()
    
    # 檢查是否已有模板
    c.execute('SELECT * FROM task_templates WHERE task_type = ?', (task_type,))
    existing = c.fetchone()
    
    if existing:
        # 更新現有模板
        new_times_used = existing['times_used'] + 1
        success_rate = (existing['success_rate'] * existing['times_used'] + (1 if auto_executed else 0.5)) / new_times_used
        
        c.execute('''
            UPDATE task_templates 
            SET default_action = ?,
                times_used = ?,
                success_rate = ?,
                last_used = ?,
                updated_at = ?
            WHERE task_type = ?
        ''', (action, new_times_used, success_rate, datetime.now().isoformat(), datetime.now().isoformat(), task_type))
    else:
        # 新建模板
        c.execute('''
            INSERT INTO task_templates (task_type, default_action, times_used, success_rate, auto_execute)
            VALUES (?, ?, 1, ?, ?)
        ''', (task_type, action, 1.0 if auto_executed else 0.5, 1 if auto_executed else 0))
    
    conn.commit()
    conn.close()

def get_template(task_type):
    """獲取任務模板"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM task_templates 
        WHERE task_type = ? 
        ORDER BY success_rate DESC, times_used DESC
        LIMIT 1
    ''', (task_type,))
    
    row = c.fetchone()
    conn.close()
    
    return dict(row) if row else None

def apply_auto_resolution(task_key, task_type):
    """應用自動解決方案"""
    template = get_template(task_type)
    
    if template and template['auto_execute']:
        return {
            'action': template['default_action'],
            'auto': True,
            'confidence': template['success_rate']
        }
    
    return None

def get_task_stats():
    """獲取任務統計"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total FROM pending_tasks')
    total = c.fetchone()['total']
    
    c.execute('SELECT COUNT(*) as pending FROM pending_tasks WHERE status = ?', ('pending',))
    pending = c.fetchone()['pending']
    
    c.execute('SELECT COUNT(*) as resolved FROM pending_tasks WHERE status = ?', ('resolved',))
    resolved = c.fetchone()['resolved']
    
    c.execute('SELECT task_type, COUNT(*) as count FROM pending_tasks WHERE status = ? GROUP BY task_type', ('pending',))
    by_type = [dict(row) for row in c.fetchall()]
    
    c.execute('SELECT * FROM task_templates ORDER BY success_rate DESC LIMIT 10')
    templates = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'resolved': resolved,
        'by_type': by_type,
        'templates': templates
    }

# ============================================================================
# 預設任務模板
# ============================================================================

DEFAULT_TEMPLATES = {
    'cron_error': {
        'action': 'Remove error cron, recreate with 120s timeout and telegram announce',
        'auto_execute': 1
    },
    'script_missing': {
        'action': 'Recreate script from backup or rebuild from templates',
        'auto_execute': 0
    },
    'health_check': {
        'action': 'Run tina_lifecycle_monitor_v2.py, report status',
        'auto_execute': 1
    },
    'backup': {
        'action': 'Create backup_YYYYMMDD_HHMM folder, copy essential DBs and configs',
        'auto_execute': 1
    },
    'restore': {
        'action': 'Copy from backup folder to original locations',
        'auto_execute': 0
    }
}

# ============================================================================
# 主程式
# ============================================================================

if __name__ == '__main__':
    init_db()
    
    print('Tina Auto Task Handler')
    print('='*50)
    
    stats = get_task_stats()
    print(f'Total Tasks: {stats["total"]}')
    print(f'Pending: {stats["pending"]}')
    print(f'Resolved: {stats["resolved"]}')
    print()
    
    if stats['templates']:
        print('Learned Templates:')
        for t in stats['templates'][:5]:
            auto = '[AUTO]' if t['auto_execute'] else '[MANUAL]'
            print(f"  {auto} {t['task_type']}: {t['default_action'][:50]}... ({t['success_rate']:.0%} success)")
    
    print()
    print('Default Templates:')
    for k in DEFAULT_TEMPLATES:
        print(f"  - {k}")