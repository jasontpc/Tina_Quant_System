"""
Tina 互動記憶大腦 v1.0
===========================
三層級記憶架構：
1. 短期記憶 (Context) - 當前對話上下文
2. 情境經驗 (Experience Ledger) - 個股勝敗紀錄  
3. 長期偏好 (User Profile) - 風險接受度與交易習慣

閉環系統：對話 → 執行 → 反思 → 記憶 → 下次提取
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'

# ========== 記憶儲存路徑 ==========
MEMORY_DIR = os.path.join(WORKSPACE, 'memory')
EXPERIENCE_FILE = os.path.join(WORKSPACE, 'reports', 'experience_ledger.md')
DECISION_FILE = os.path.join(WORKSPACE, 'reports', 'decision_history.md')
PROFILE_FILE = os.path.join(WORKSPACE, 'USER.md')
CONTEXT_FILE = os.path.join(MEMORY_DIR, 'current_context.json')
DB_PATH = os.path.join(WORKSPACE, 'data', 'tina_memory.db')

# ========== 記憶數據庫初始化 ==========
def init_memory_db():
    """初始化互動記憶資料庫"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 短期記憶表（對話上下文）
    c.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            user_input TEXT,
            tina_response TEXT,
            stock_mentioned TEXT,
            action_taken TEXT,
            result TEXT
        )
    ''')
    
    # 情境經驗表（個股分析）
    c.execute('''
        CREATE TABLE IF NOT EXISTS experience_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT,
            event_date TEXT,
            event_type TEXT,
            analysis_content TEXT,
            decision TEXT,
            outcome TEXT,
            lessons_learned TEXT,
            confidence_score INTEGER
        )
    ''')
    
    # 長期偏好表（用戶Profile）
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')
    
    # 反思標籤表（每次對話的自我修正）
    c.execute('''
        CREATE TABLE IF NOT EXISTS reflection_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            session_id TEXT,
            stock_id TEXT,
            reflection_text TEXT,
            new_rule TEXT,
            mood_score INTEGER
        )
    ''')
    
    # 主動行為記錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS proactive_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            trigger_type TEXT,
            content TEXT,
            delivered INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# ========== 短期記憶管理 ==========
def save_short_term_memory(session_id, user_input, tina_response, stock=None, action=None, result=None):
    """儲存短期對話記憶"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO short_term_memory 
        (session_id, timestamp, user_input, tina_response, stock_mentioned, action_taken, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, datetime.now().isoformat(), user_input, tina_response, stock, action, result))
    
    conn.commit()
    conn.close()

def get_recent_context(session_id=None, stock_id=None, hours=24):
    """取得最近上下文"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = '''
        SELECT timestamp, user_input, tina_response, stock_mentioned, action_taken, result
        FROM short_term_memory
        WHERE timestamp >= datetime('now', '-{} hours')
    '''.format(hours)
    
    if session_id:
        query += f" AND session_id = '{session_id}'"
    if stock_id:
        query += f" AND stock_mentioned = '{stock_id}'"
    
    query += ' ORDER BY timestamp DESC LIMIT 10'
    
    c.execute(query)
    results = c.fetchall()
    conn.close()
    
    return results

# ========== 情境經驗管理 ==========
def save_experience(stock_id, event_type, analysis_content, decision, outcome=None, lessons=None, confidence=5):
    """儲存情境經驗"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO experience_log 
        (stock_id, event_date, event_type, analysis_content, decision, outcome, lessons_learned, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (stock_id, datetime.now().date().isoformat(), event_type, analysis_content, decision, outcome, lessons, confidence))
    
    conn.commit()
    conn.close()

def get_stock_experience(stock_id, limit=3):
    """取得特定股票的最新經驗"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT event_date, event_type, analysis_content, decision, outcome, lessons_learned, confidence_score
        FROM experience_log
        WHERE stock_id = ?
        ORDER BY event_date DESC
        LIMIT ?
    ''', (stock_id, limit))
    
    results = c.fetchall()
    conn.close()
    
    return results

def get_relevant_experience(keyword, limit=5):
    """關鍵詞匹配取得相關經驗"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT stock_id, event_date, event_type, analysis_content, decision, outcome, lessons_learned
        FROM experience_log
        WHERE analysis_content LIKE ? OR decision LIKE ? OR lessons_learned LIKE ?
        ORDER BY event_date DESC
        LIMIT ?
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))
    
    results = c.fetchall()
    conn.close()
    
    return results

# ========== 長期偏好管理 ==========
def save_user_preference(key, value):
    """儲存用戶偏好"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO user_profile (key, value, updated_at)
        VALUES (?, ?, ?)
    ''', (key, value, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_user_preference(key, default=None):
    """取得用戶偏好"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT value FROM user_profile WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else default

def get_all_preferences():
    """取得所有用戶偏好"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT key, value, updated_at FROM user_profile')
    results = c.fetchall()
    conn.close()
    
    return {r[0]: {'value': r[1], 'updated': r[2]} for r in results}

# ========== 反思標籤管理 ==========
def save_reflection(session_id, stock_id, reflection_text, new_rule=None, mood_score=5):
    """儲存反思標籤"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO reflection_tags 
        (timestamp, session_id, stock_id, reflection_text, new_rule, mood_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), session_id, stock_id, reflection_text, new_rule, mood_score))
    
    conn.commit()
    conn.close()

def get_recent_reflections(hours=48):
    """取得最近的反思記錄"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT timestamp, stock_id, reflection_text, new_rule, mood_score
        FROM reflection_tags
        WHERE timestamp >= datetime('now', '-{} hours')
        ORDER BY timestamp DESC
    '''.format(hours))
    
    results = c.fetchall()
    conn.close()
    
    return results

# ========== 主動行為管理 ==========
def save_proactive_action(trigger_type, content):
    """記錄主動行為"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO proactive_actions (timestamp, trigger_type, content)
        VALUES (?, ?, ?)
    ''', (datetime.now().isoformat(), trigger_type, content))
    
    conn.commit()
    conn.close()
    
    return c.lastrowid

def mark_proactive_delivered(action_id):
    """標記主動行為已發送"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('UPDATE proactive_actions SET delivered = 1 WHERE id = ?', (action_id,))
    conn.commit()
    conn.close()

def get_pending_proactive():
    """取得待發送的主動行為"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id, timestamp, trigger_type, content FROM proactive_actions WHERE delivered = 0')
    results = c.fetchall()
    conn.close()
    
    return results

# ========== 記憶壓縮（24小時） ==========
def compress_daily_memories(date_str=None):
    """壓縮當日記憶為核心經驗"""
    if date_str is None:
        date_str = datetime.now().date().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 取得當日所有短期記憶
    c.execute('''
        SELECT user_input, tina_response, stock_mentioned, action_taken, result
        FROM short_term_memory
        WHERE timestamp LIKE ?
        ORDER BY timestamp
    ''', (f'{date_str}%',))
    
    daily_memories = c.fetchall()
    
    if not daily_memories:
        conn.close()
        return None
    
    # 壓縮為核心經驗
    compression = {
        'date': date_str,
        'total_interactions': len(daily_memories),
        'stocks_discussed': list(set([m[2] for m in daily_memories if m[2]])),
        'actions_taken': list(set([m[3] for m in daily_memories if m[3]])),
        'key_outcomes': [m[4] for m in daily_memories if m[4]],
        'compressed_at': datetime.now().isoformat()
    }
    
    # 寫入經驗文件
    compression_file = os.path.join(MEMORY_DIR, f'compression_{date_str}.json')
    with open(compression_file, 'w', encoding='utf-8') as f:
        json.dump(compression, f, ensure_ascii=False, indent=2)
    
    conn.close()
    return compression

# ========== 記憶構建器（送給 MiniMax） ==========
def build_memory_prompt(stock_id=None, session_id=None):
    """構建包含記憶的Prompt"""
    
    memory_prompt = []
    
    # 1. 用戶長期偏好
    prefs = get_all_preferences()
    if prefs:
        risk_tolerance = prefs.get('risk_tolerance', {}).get('value', 'medium')
        trading_style = prefs.get('trading_style', {}).get('value', 'swing')
        memory_prompt.append(f"[用戶偏好] 風險承受度: {risk_tolerance}, 交易風格: {trading_style}")
    
    # 2. 個股相關經驗
    if stock_id:
        experiences = get_stock_experience(stock_id, limit=3)
        if experiences:
            memory_prompt.append(f"\n[關於 {stock_id} 的過往經驗]")
            for exp in experiences:
                date, etype, analysis, decision, outcome, lessons, conf = exp
                memory_prompt.append(f"  - {date}: {etype} → {decision}")
                if lessons:
                    memory_prompt.append(f"    學到: {lessons}")
    
    # 3. 最近的反思
    reflections = get_recent_reflections(hours=48)
    if reflections:
        memory_prompt.append(f"\n[最近48小時的反思]")
        for ref in reflections[:3]:
            ts, sid, rtext, new_rule, mood = ref
            memory_prompt.append(f"  - {sid or '系統'}: {rtext}")
            if new_rule:
                memory_prompt.append(f"    新規則: {new_rule}")
    
    # 4. 當日對話上下文
    recent = get_recent_context(hours=24, stock_id=stock_id)
    if recent:
        memory_prompt.append(f"\n[今日對話摘要]")
        for ctx in recent[:3]:
            ts, user, response, stock, action, result = ctx
            memory_prompt.append(f"  - [{stock or 'general'}] {user[:50]}...")
    
    return "\n".join(memory_prompt) if memory_prompt else ""

# ========== 健康度語氣對齊 ==========
def get_tina_mood(health_score):
    """根據健康度調整語氣"""
    if health_score >= 4:
        return {
            'tone': 'confident',
            'prefix': '[自信] ',
            'suffix': ' 保持這個節奏！'
        }
    elif health_score >= 2:
        return {
            'tone': 'cautious',
            'prefix': '[謹慎] ',
            'suffix': ' 我會密切關注變化。'
        }
    else:
        return {
            'tone': 'humble',
            'prefix': '[警覺] ',
            'suffix': ' 建議先觀望。'
        }

# ========== 初始化 ==========
init_memory_db()

print('[OK] Tina 互動記憶大腦初始化完成')
print(f'    DB: {DB_PATH}')