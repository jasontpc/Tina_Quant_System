"""
Tina Event Handler - 事件處理記錄資料庫
自動記錄、學習、復現過往問題的解決方案
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'tina_event_log.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            event_key TEXT NOT NULL,
            error_message TEXT,
            resolution TEXT,
            resolved_at TEXT,
            outcome TEXT,
            times_encountered INTEGER DEFAULT 1,
            auto_resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS resolution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT NOT NULL,
            action_taken TEXT,
            success INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_event_key ON event_log(event_key)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_event_type ON event_log(event_type)
    ''')
    
    conn.commit()
    conn.close()

def log_event(event_type, event_key, error_message, resolution=None, outcome=None, auto_resolved=0):
    """記錄新事件"""
    conn = get_db()
    c = conn.cursor()
    
    # 檢查是否已有相同事件
    c.execute('SELECT * FROM event_log WHERE event_key = ? ORDER BY created_at DESC LIMIT 1', (event_key,))
    existing = c.fetchone()
    
    if existing:
        # 更新計數
        c.execute('''
            UPDATE event_log 
            SET times_encountered = times_encountered + 1,
                error_message = ?,
                resolution = COALESCE(resolution, ?),
                outcome = COALESCE(outcome, ?),
                resolved_at = COALESCE(resolved_at, ?)
            WHERE id = ?
        ''', (error_message, resolution, outcome, datetime.now().isoformat() if resolution else None, existing['id']))
    else:
        # 新事件
        c.execute('''
            INSERT INTO event_log (event_type, event_key, error_message, resolution, outcome, auto_resolved, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_type, event_key, error_message, resolution, outcome, auto_resolved, 
              datetime.now().isoformat() if resolution else None))
    
    conn.commit()
    conn.close()

def add_resolution_history(event_key, action_taken, success, notes=''):
    """添加解決方案歷史"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO resolution_history (event_key, action_taken, success, notes)
        VALUES (?, ?, ?, ?)
    ''', (event_key, action_taken, 1 if success else 0, notes))
    
    conn.commit()
    conn.close()

def find_similar_event(event_key, error_message, threshold=0.7):
    """查找相似事件（用於自動復現解決方案）"""
    conn = get_db()
    c = conn.cursor()
    
    # 查找同類型事件
    c.execute('''
        SELECT * FROM event_log 
        WHERE event_key = ? 
        AND resolution IS NOT NULL 
        AND outcome = 'success'
        ORDER BY times_encountered DESC, created_at DESC
        LIMIT 5
    ''', (event_key,))
    
    rows = c.fetchall()
    conn.close()
    
    if rows:
        # 返回最常見的成功解決方案
        return dict(rows[0])
    
    return None

def get_event_stats():
    """獲取事件統計"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total FROM event_log')
    total = c.fetchone()['total']
    
    c.execute('SELECT COUNT(*) as auto_resolved FROM event_log WHERE auto_resolved = 1')
    auto = c.fetchone()['auto_resolved']
    
    c.execute('SELECT event_type, COUNT(*) as count FROM event_log GROUP BY event_type')
    by_type = [dict(row) for row in c.fetchall()]
    
    c.execute('SELECT event_key, times_encountered, resolution FROM event_log WHERE times_encountered > 1 ORDER BY times_encountered DESC LIMIT 10')
    recurring = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return {
        'total_events': total,
        'auto_resolved': auto,
        'by_type': by_type,
        'recurring': recurring
    }

def resolve_event(event_key, resolution, success, auto_resolved=0, notes=''):
    """解決事件並記錄"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        UPDATE event_log 
        SET resolution = ?,
            outcome = ?,
            resolved_at = ?,
            auto_resolved = ?
        WHERE event_key = ? AND resolution IS NULL
    ''', (resolution, 'success' if success else 'failed', datetime.now().isoformat(), auto_resolved, event_key))
    
    conn.commit()
    conn.close()

# ============================================================================
# 預設解決方案映射
# ============================================================================

DEFAULT_RESOLUTIONS = {
    'cron_timeout': {
        'action': 'Increase timeout from 30s to 120s, rebuild cron',
        'auto_resolve': True
    },
    'cron_error_delivery': {
        'action': 'Remove cron, recreate with telegram announcement',
        'auto_resolve': True
    },
    'script_not_found': {
        'action': 'Check script path, recreate if missing',
        'auto_resolve': True
    },
    'pid_lock_active': {
        'action': 'Wait for PID lock expiry, or manually clear lock file',
        'auto_resolve': False
    },
    'cooldown_active': {
        'action': 'Wait for 24h cooldown, no action needed',
        'auto_resolve': True
    },
    'permission_denied': {
        'action': 'Check file permissions, ensure write access',
        'auto_resolve': False
    }
}

def apply_default_resolution(event_type, event_key, error_msg):
    """嘗試應用預設解決方案"""
    for key, resolution in DEFAULT_RESOLUTIONS.items():
        if key in event_type.lower() or key in error_msg.lower():
            return resolution['action'], resolution['auto_resolve']
    
    return None, False

# ============================================================================
# 主程式
# ============================================================================

if __name__ == '__main__':
    init_db()
    
    print('Tina Event Handler Database')
    print('='*50)
    print(f'DB Path: {DB_PATH}')
    print()
    
    stats = get_event_stats()
    print(f'Total Events: {stats["total_events"]}')
    print(f'Auto Resolved: {stats["auto_resolved"]}')
    print()
    
    if stats['recurring']:
        print('Recurring Events (encountered >1 time):')
        for r in stats['recurring'][:5]:
            print(f"  {r['event_key']}: {r['times_encountered']}x")
            if r['resolution']:
                print(f"    Solution: {r['resolution'][:50]}...")
    
    print()
    print('Available Default Resolutions:')
    for k in DEFAULT_RESOLUTIONS:
        print(f"  - {k}")