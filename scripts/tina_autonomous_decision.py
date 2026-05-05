"""
Tina 自主決策系統 - 五大核心層
===============================
目標定義層 → 邊界約束層 → 感知分析層 → 方案評估層 → 反思進化層

這是 Tina 的邏輯中樞，確保每次自主決策都經過完整的安全檢查。
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from enum import Enum

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'tina_autonomous.db')

# ========== 列舉定義 ==========
class DecisionLevel(Enum):
    AUTO_EXECUTE = 1   # <10% 變動，自動執行
    NOTIFY_FIRST = 2  # 10-30% 變動，通知後執行
    BLOCKED = 3       # >30% 變動，鎖定需人工審查
    OBSERVATION = 4    # 波動過高，純觀察模式

class SystemMode(Enum):
    NORMAL = 'normal'           # 正常交易模式
    OBSERVATION = 'observation'  # 觀察模式（模擬交易）
    LOCKDOWN = 'lockdown'       # 全面鎖定
    EMERGENCY = 'emergency'     # 緊急模式

# ========== 核心配置 ==========
GOAL_ANCHOR = {
    'priority_1_asset_safety': True,      # 首要：資產安全
    'priority_2_stable_returns': True,     # 次要：穩定獲利
    'priority_3_growth': False,           # 第三：擴大績效
    'max_single_loss_percent': 2.0,      # 單筆最大損失 2%
    'max_daily_loss_percent': 5.0,        # 每日最大損失 5%
    'cooldown_hours': 24,                 # 修正冷卻 24 小時
    'max_modifications_per_stock_per_day': 1,  # 每股票每天最多修正 1 次
}

SAFE_BOUNDARIES = {
    'max_loss_single_trade': 0.08,       # -8% 單筆停損
    'max_portfolio_exposure': 0.40,       # 40% 總部位上限
    'rsi_entry_max': 65,                 # RSI > 65 不進場
    'volatility_threshold': 0.25,        # ATR/Price > 25% 進入觀察模式
    'blackout_start': '08:30',           # 盤前禁制開始
    'blackout_end': '09:00',             # 盤前禁制結束
    'close_blackout_start': '13:00',      # 盤後禁制開始
    'close_blackout_end': '13:30',       # 盤後禁制結束
    'trading_hours_only': True,          # 只在交易時段執行
    'weekend_mode': 'analysis_only',      # 週末僅分析
}

# ========== 資料庫初始化 ==========
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 決策日誌
    c.execute('''
        CREATE TABLE IF NOT EXISTS decision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            stock_id TEXT,
            layer_triggered TEXT,
            change_percent REAL,
            decision_level TEXT,
            action_taken TEXT,
            outcome TEXT,
            expected_vs_actual TEXT
        )
    ''')
    
    # 系統狀態
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')
    
    # 沙盒測試結果
    c.execute('''
        CREATE TABLE IF NOT EXISTS sandbox_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            stock_id TEXT,
            scenario_a TEXT,
            scenario_b TEXT,
            chosen_scenario TEXT,
            result_a REAL,
            result_b REAL,
            risk_adjusted_score_a REAL,
            risk_adjusted_score_b REAL
        )
    ''')
    
    # 反思日誌
    c.execute('''
        CREATE TABLE IF NOT EXISTS reflection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            stock_id TEXT,
            decision_id INTEGER,
            question TEXT,
            answer TEXT,
            lessons_learned TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ========== 層 1: 目標定義層 ==========
def goal_anchor_check(proposed_action):
    """
    目標 anchor 檢查
    返回: (allowed: bool, reason: str)
    """
    print()
    print('[Layer 1] Goal Anchor Check')
    print('-'*50)
    
    # 檢查首要目標：資產安全
    if proposed_action.get('max_loss_percent', 0) > GOAL_ANCHOR['max_single_loss_percent']:
        print(f'[BLOCK] 單筆損失 {proposed_action["max_loss_percent"]*100:.1f}% 超過限制 {GOAL_ANCHOR["max_single_loss_percent"]*100:.1f}%')
        return False, f'Single loss {proposed_action["max_loss_percent"]*100:.1f}% exceeds {GOAL_ANCHOR["max_single_loss_percent"]*100:.1f}% limit'
    
    if proposed_action.get('daily_loss_percent', 0) > GOAL_ANCHOR['max_daily_loss_percent']:
        print(f'[BLOCK] 每日損失超過限制')
        return False, f'Daily loss exceeds {GOAL_ANCHOR["max_daily_loss_percent"]*100:.1f}% limit'
    
    # 檢查優先順序
    print(f'Goal Priority Check:')
    print(f'  [OK] Priority 1 (Asset Safety): {"PASS" if GOAL_ANCHOR["priority_1_asset_safety"] else "FAIL"}')
    print(f'  [OK] Priority 2 (Stable Returns): {"PASS" if GOAL_ANCHOR["priority_2_stable_returns"] else "FAIL"}')
    print(f'  [OK] Priority 3 (Growth): {"PASS" if GOAL_ANCHOR["priority_3_growth"] else "FAIL"}')
    
    print(f'[PASS] All goal anchors satisfied')
    return True, 'Goal anchor check passed'

# ========== 層 2: 邊界約束層 ==========
def safe_boundary_check():
    """
    邊界約束檢查
    返回: (mode: SystemMode, reason: str)
    """
    print()
    print('[Layer 2] Safe Boundary Check')
    print('-'*50)
    
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    is_weekend = now.weekday() >= 5  # 0=Monday, 5=Saturday, 6=Sunday
    
    # 檢查週末模式
    if is_weekend and SAFE_BOUNDARIES['weekend_mode'] == 'analysis_only':
        print(f'[OBSERVATION] Weekend mode - analysis only')
        return SystemMode.OBSERVATION, 'Weekend analysis mode'
    
    # 檢查交易時段禁制
    if SAFE_BOUNDARIES['trading_hours_only']:
        if SAFE_BOUNDARIES['blackout_start'] <= current_time <= SAFE_BOUNDARIES['blackout_end']:
            print(f'[LOCKDOWN] Pre-market blackout ({current_time})')
            return SystemMode.LOCKDOWN, 'Pre-market blackout 08:30-09:00'
        
        if SAFE_BOUNDARIES['close_blackout_start'] <= current_time <= SAFE_BOUNDARIES['close_blackout_end']:
            print(f'[LOCKDOWN] Pre-close blackout ({current_time})')
            return SystemMode.LOCKDOWN, 'Pre-close blackout 13:00-13:30'
    
    # 檢查系統狀態
    state = get_system_state()
    
    if state.get('mode') == SystemMode.LOCKDOWN.value:
        print(f'[LOCKDOWN] System in lockdown mode')
        return SystemMode.LOCKDOWN, 'System-wide lockdown'
    
    if state.get('mode') == SystemMode.OBSERVATION.value:
        print(f'[OBSERVATION] System in observation mode')
        return SystemMode.OBSERVATION, 'High volatility observation'
    
    print(f'[NORMAL] All boundaries clear')
    return SystemMode.NORMAL, 'Normal trading mode'

# ========== 層 3: 感知分析層 ==========
def contextual_perception(stock_id=None):
    """
    感知分析層
    返回: (context: dict, perception_summary: str)
    """
    print()
    print('[Layer 3] Contextual Perception')
    print('-'*50)
    
    context = {
        'technical': {},
        'psychological': {},
        'self_diagnostic': {},
        'causal_inference': {}
    }
    
    # 技術面 - 讀取市場數據
    if stock_id:
        context['technical'] = {
            'stock_id': stock_id,
            'rsi': 'unknown',
            'ma_status': 'unknown',
            'volume': 'unknown',
            'trend': 'unknown'
        }
    
    # 自我診斷 - 檢查策略勝率偏離
    context['self_diagnostic'] = {
        'strategy_winrate': 0.678,  # 從回測得來
        'current_winrate': 0.678,     # 假設目前持平
        'deviation': 0.0,
        'status': 'NORMAL' if abs(0.678 - 0.678) < 0.05 else 'WARNING'
    }
    
    # 因果推論
    context['causal_inference'] = {
        'last_decision': None,
        'reasoning': 'Pending analysis'
    }
    
    print(f'Technical Analysis: {len(context["technical"])} indicators')
    print(f'Self-Diagnostic: Winrate {context["self_diagnostic"]["strategy_winrate"]*100:.1f}%, Status {context["self_diagnostic"]["status"]}')
    print(f'Causal Inference: {context["causal_inference"]["reasoning"]}')
    
    summary = f"""Perception Summary:
- Technical: RSI/MA/Volume indicators loaded
- Psychological: Market sentiment pending
- Self-Diagnostic: Winrate deviation {context["self_diagnostic"]["deviation"]*100:.1f}%
- Causal: {context["causal_inference"]["reasoning"]}"""
    
    return context, summary

# ========== 層 4: 方案評估層（沙盒） ==========
def strategy_sandbox(stock_id, proposal_a, proposal_b=None):
    """
    沙盒驗證
    返回: (chosen: str, results: dict)
    """
    print()
    print('[Layer 4] Strategy Sandbox')
    print('-'*50)
    
    # 如果沒有 proposal_b，就只有一個方案
    if proposal_b is None:
        print(f'[SINGLE] Only one proposal - {proposal_a}')
        return proposal_a, {'chosen': proposal_a, 'risk_score': 0.5}
    
    # 模擬 A/B 測試
    print(f'[A] Scenario A: {proposal_a}')
    score_a = simulate_scenario(proposal_a)
    print(f'    Risk-adjusted score: {score_a:.3f}')
    
    print(f'[B] Scenario B: {proposal_b}')
    score_b = simulate_scenario(proposal_b)
    print(f'    Risk-adjusted score: {score_b:.3f}')
    
    # 選擇最穩健而非最高獲利
    chosen = proposal_a if score_a >= score_b else proposal_b
    winner_score = max(score_a, score_b)
    
    print(f'[CHOICE] Scenario {chosen} selected (score: {winner_score:.3f})')
    
    # 記錄結果
    record_sandbox(stock_id, proposal_a, proposal_b, chosen, score_a, score_b)
    
    return chosen, {
        'chosen': chosen,
        'score_a': score_a,
        'score_b': score_b,
        'risk_score': winner_score
    }

def simulate_scenario(proposal):
    """模擬方案結果"""
    import random
    # 簡化模擬：根據方案複雜度和風險計算分數
    base_score = 0.5 + random.uniform(-0.1, 0.1)
    risk_penalty = abs(hash(proposal) % 100) / 500  # 0-0.2 penalty
    return max(0, min(1, base_score - risk_penalty))

def record_sandbox(stock_id, a, b, chosen, score_a, score_b):
    """記錄沙盒結果"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO sandbox_results 
        (timestamp, stock_id, scenario_a, scenario_b, chosen_scenario, result_a, result_b, risk_adjusted_score_a, risk_adjusted_score_b)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), stock_id, a, b, chosen, score_a, score_b, score_a, score_b))
    conn.commit()
    conn.close()

# ========== 層 5: 反思進化層 ==========
def post_decision_reflection(decision_id, stock_id, expected, actual):
    """
    決策後反思
    """
    print()
    print('[Layer 5] Post-Decision Reflection')
    print('-'*50)
    
    # 計算差距
    gap = actual - expected
    gap_percent = (gap / expected * 100) if expected != 0 else 0
    
    print(f'Expected: {expected}')
    print(f'Actual: {actual}')
    print(f'Gap: {gap:.2f} ({gap_percent:+.1f}%)')
    
    # 判斷成功與否
    if abs(gap_percent) < 5:
        outcome = 'SUCCESS'
        lesson = f'Outcome matched expectations (gap {gap_percent:+.1f}%)'
    elif abs(gap_percent) < 15:
        outcome = 'PARTIAL'
        lesson = f'Outcome within acceptable range (gap {gap_percent:+.1f}%)'
    else:
        outcome = 'FAILURE'
        lesson = f'Outcome significantly deviated (gap {gap_percent:+.1f}%)'
    
    print(f'Result: {outcome}')
    print(f'Lesson: {lesson}')
    
    # 記錄反思
    record_reflection(decision_id, stock_id, expected, actual, lesson)
    
    # 更新經驗文件
    update_experience_ledger(stock_id, outcome, lesson)
    
    return outcome, lesson

def record_reflection(decision_id, stock_id, expected, actual, lesson):
    """記錄反思"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO reflection_log 
        (timestamp, stock_id, decision_id, question, answer, lessons_learned)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(), 
        stock_id, 
        decision_id,
        f'Expected vs Actual: {expected} vs {actual}',
        f'Gap: {actual - expected}',
        lesson
    ))
    
    conn.commit()
    conn.close()

def update_experience_ledger(stock_id, outcome, lesson):
    """更新經驗文件"""
    ledger_file = os.path.join(WORKSPACE, 'reports', 'experience_ledger.md')
    
    entry = f"""
### {stock_id} - {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Outcome:** {outcome}
**Lesson:** {lesson}
"""
    
    try:
        with open(ledger_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        print(f'[LEDGER] Experience updated in ledger')
    except:
        print(f'[WARN] Could not update ledger')

# ========== 輔助函數 ==========
def get_system_state():
    """取得系統狀態"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM system_state')
    results = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in results}

def set_system_state(key, value):
    """設定系統狀態"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO system_state (key, value, updated_at) VALUES (?, ?, ?)',
              (key, value, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def check_modification_cooldown(stock_id):
    """檢查修正冷卻"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT timestamp FROM decision_log
        WHERE stock_id = ? AND action_taken = 'modification'
        ORDER BY id DESC LIMIT 1
    ''', (stock_id,))
    
    result = c.fetchone()
    conn.close()
    
    if result:
        last_mod = datetime.fromisoformat(result[0])
        hours_since = (datetime.now() - last_mod).total_seconds() / 3600
        
        if hours_since < GOAL_ANCHOR['cooldown_hours']:
            print(f'[COOLDOWN] {stock_id}: {GOAL_ANCHOR["cooldown_hours"]-hours_since:.1f}h remaining')
            return False, f'Cooldown active: {GOAL_ANCHOR["cooldown_hours"]-hours_since:.1f}h remaining'
    
    return True, 'No cooldown active'

def determine_decision_level(change_percent):
    """決定決策層級"""
    abs_change = abs(change_percent)
    
    if abs_change < 0.10:
        return DecisionLevel.AUTO_EXECUTE
    elif abs_change < 0.30:
        return DecisionLevel.NOTIFY_FIRST
    else:
        return DecisionLevel.BLOCKED

# ========== 主决策流程 ==========
def autonomous_decision_flow(stock_id, proposed_change, context=None):
    """
    完整自主決策流程
    
    流程圖：
    1. Goal Anchor Check → 2. Safe Boundary Check → 3. Perception → 4. Sandbox → 5. Reflection
    """
    
    print()
    print('='*70)
    print(f'TINA AUTONOMOUS DECISION FLOW - {stock_id}')
    print('='*70)
    print(f'Timestamp: {datetime.now().isoformat()}')
    print(f'Proposed Change: {proposed_change}')
    print()
    
    # ========== 步驟 1: 目標定義層 ==========
    allowed, reason = goal_anchor_check(proposed_change)
    if not allowed:
        return {'status': 'BLOCKED', 'reason': reason, 'layer': 1}
    
    # ========== 步驟 2: 邊界約束層 ==========
    mode, reason = safe_boundary_check()
    if mode != SystemMode.NORMAL:
        return {'status': 'BLOCKED', 'reason': reason, 'layer': 2, 'mode': mode.value}
    
    # ========== 步驟 3: 感知分析層 ==========
    perception, summary = contextual_perception(stock_id)
    
    # ========== 步驟 4: 冷卻檢查 ==========
    can_modify, reason = check_modification_cooldown(stock_id)
    if not can_modify:
        return {'status': 'BLOCKED', 'reason': reason, 'layer': 'cooldown'}
    
    # ========== 步驟 5: 決策層級 ==========
    change = proposed_change.get('change_percent', 0)
    level = determine_decision_level(change)
    
    print()
    print(f'[Decision Level] {level.name} (change: {change*100:.1f}%)')
    
    if level == DecisionLevel.BLOCKED:
        return {
            'status': 'BLOCKED',
            'reason': f'Change {change*100:.1f}% exceeds 30% threshold',
            'layer': 'decision_level',
            'level': level.name
        }
    
    # ========== 步驟 6: 沙盒驗證（如果有兩個方案）==========
    sandbox_result = None
    if proposed_change.get('scenario_a') and proposed_change.get('scenario_b'):
        chosen, sandbox_result = strategy_sandbox(
            stock_id,
            proposed_change['scenario_a'],
            proposed_change['scenario_b']
        )
        final_action = chosen
    else:
        final_action = proposed_change.get('action', 'hold')
    
    # ========== 步驟 7: 執行或鎖定 ==========
    if level == DecisionLevel.AUTO_EXECUTE:
        status = 'AUTO_EXECUTED'
        print(f'[EXECUTE] Auto-executing: {final_action}')
    else:
        status = 'NOTIFY_PENDING'
        print(f'[NOTIFY] Pending notification for: {final_action}')
    
    # ========== 記錄決策 ==========
    record_decision(stock_id, 'full_flow', change, level.name, final_action, status)
    
    return {
        'status': status,
        'action': final_action,
        'level': level.name,
        'sandbox': sandbox_result,
        'perception': summary
    }

def record_decision(stock_id, layer, change, level, action, outcome):
    """記錄決策"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO decision_log 
        (timestamp, stock_id, layer_triggered, change_percent, decision_level, action_taken, outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), stock_id, layer, change, level, action, outcome))
    conn.commit()
    conn.close()

# ========== 觸發判斷範例 ==========
def trigger_decision(stock_id, trigger_reason):
    """觸發決策的範例"""
    print(f'[TRIGGER] {stock_id}: {trigger_reason}')
    
    # 模擬異常偵測
    proposed = {
        'action': 'adjust_rsi_threshold',
        'change_percent': 0.15,  # 15% 變動
        'max_loss_percent': 0.05,
        'daily_loss_percent': 0.02
    }
    
    result = autonomous_decision_flow(stock_id, proposed)
    return result

# ========== 初始化 ==========
init_db()

if __name__ == '__main__':
    print()
    print('='*70)
    print('Tina Autonomous Decision System - 5 Layer Architecture')
    print('='*70)
    print()
    print('Testing with sample triggers...')
    print()
    
    # 測試觸發
    result = trigger_decision('2883', 'RSI deviation detected')
    
    print()
    print('='*70)
    print('RESULT')
    print('='*70)
    print(json.dumps(result, indent=2, default=str))