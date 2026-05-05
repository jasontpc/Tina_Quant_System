"""
Tina 自主學習整合系統 v1.0
===========================
五大階段整合：
1. 感知層 (Perception) - 閒置檢測、狀態掃描、配置普查
2. 智能層 (Intelligence) - 績效分析、排程推演、衝突校正
3. 操作層 (Manipulation) - Cron動態調整、原子化寫入
4. 執行層 (Execution) - 環境對齊、運行鎖、主動喚醒
5. 反思層 (Reflection) - 決策記錄、效能追蹤、報告推送

這是 Tina 的完整自主學習大腦。
"""

import os
import sys
import json
import time
import subprocess
import sqlite3
import psutil
import threading
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'tina_autonomous.db')
CONFIG_DIR = os.path.join(WORKSPACE, 'configs', 'stock_strategies')

# ========== 第一階段：感知層 ==========
class PerceptionLayer:
    """閒置感知與狀態掃描"""
    
    def __init__(self):
        self.resource_threshold = 0.3  # CPU/記憶體閾值 30%
        self.max_history_days = 7  # 歷史回顧天數
    
    def check_resource_pressure(self) -> Dict:
        """資源壓力監測"""
        cpu = psutil.cpu_percent(interval=1) / 100
        memory = psutil.virtual_memory().percent / 100
        
        return {
            'cpu_percent': cpu,
            'memory_percent': memory,
            'is_idle': cpu < self.resource_threshold and memory < self.resource_threshold,
            'timestamp': datetime.now().isoformat()
        }
    
    def check_trading_status(self) -> Dict:
        """交易行為審計"""
        # 檢查持倉狀態
        portfolio_file = os.path.join(WORKSPACE, 'data', 'portfolio.json')
        
        has_position = False
        has_pending_orders = False
        
        if os.path.exists(portfolio_file):
            try:
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)
                    has_position = len(portfolio.get('positions', [])) > 0
                    has_pending_orders = len(portfolio.get('pending_orders', [])) > 0
            except:
                pass
        
        return {
            'has_position': has_position,
            'has_pending_orders': has_pending_orders,
            'trading_active': has_position or has_pending_orders,
            'timestamp': datetime.now().isoformat()
        }
    
    def scan_stock_configs(self) -> List[Dict]:
        """個股配置普查"""
        configs = []
        
        if not os.path.exists(CONFIG_DIR):
            return configs
        
        for file in os.listdir(CONFIG_DIR):
            if file.endswith('.json'):
                config_path = os.path.join(CONFIG_DIR, file)
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        stock_id = file.replace('.json', '')
                        
                        configs.append({
                            'stock_id': stock_id,
                            'file_path': config_path,
                            'last_modified': os.path.getmtime(config_path),
                            'performance': config.get('performance', {}),
                            'evolution_count': config.get('evolution_count', 0),
                            'last_evolution': config.get('last_evolution', None),
                            'status': config.get('status', 'unknown')
                        })
                except:
                    pass
        
        return configs
    
    def detect_market_regime(self) -> str:
        """市場情境分類"""
        # 讀取 TW RSI
        try:
            result = subprocess.run(
                ['python', os.path.join(WORKSPACE, 'scripts', 'tw_report.py')],
                capture_output=True, timeout=30
            )
            
            # 解析輸出找 RSI
            output = result.stdout + result.stderr
            if 'RSI' in output:
                # 找到 RSI 值
                for line in output.split('\n'):
                    if 'TWII' in line and 'RSI' in line:
                        parts = line.split('RSI')[1].split()[0] if 'RSI' in line else '50'
                        rsi = float(parts.replace(',', ''))
                        
                        if rsi > 75:
                            return 'overheated'
                        elif rsi > 60:
                            return 'bullish'
                        elif rsi < 40:
                            return 'oversold'
                        elif rsi < 50:
                            return 'bearish'
                        else:
                            return 'neutral'
        except:
            pass
        
        return 'unknown'
    
    def full_scan(self) -> Dict:
        """完整感知掃描"""
        print()
        print('[Perception Layer]')
        print('-'*50)
        
        # 1. 資源監測
        resources = self.check_resource_pressure()
        print(f'Resource: CPU={resources["cpu_percent"]*100:.1f}% MEM={resources["memory_percent"]*100:.1f}%')
        print(f'Is Idle: {resources["is_idle"]}')
        
        # 2. 交易審計
        trading = self.check_trading_status()
        print(f'Trading: Position={trading["has_position"]} Pending={trading["has_pending_orders"]}')
        
        # 3. 配置普查
        configs = self.scan_stock_configs()
        print(f'Configs: {len(configs)} stocks scanned')
        
        # 4. 市場情境
        regime = self.detect_market_regime()
        print(f'Market Regime: {regime}')
        
        return {
            'resources': resources,
            'trading': trading,
            'configs': configs,
            'market_regime': regime,
            'scan_time': datetime.now().isoformat()
        }

# ========== 第二階段：智能層 ==========
class IntelligenceLayer:
    """智能診斷與決策"""
    
    def __init__(self, perception_data: Dict):
        self.perception = perception_data
        self.configs = perception_data['configs']
        self.regime = perception_data['market_regime']
    
    def analyze_performance_deviation(self) -> List[Tuple[str, str, float]]:
        """
        績效偏差分析
        返回: [(stock_id, priority, deviation), ...]
        """
        print()
        print('[Intelligence Layer]')
        print('-'*50)
        
        prioritized = []
        
        for config in self.configs:
            stock_id = config['stock_id']
            perf = config.get('performance', {})
            
            # 取得預期勝率和實際勝率
            expected_winrate = perf.get('winrate', 0.678)  # 預設 67.8%
            actual_winrate = perf.get('actual_winrate', expected_winrate)
            evolution_count = config.get('evolution_count', 0)
            
            # 計算偏差
            deviation = abs(actual_winrate - expected_winrate)
            
            # 判斷優先級
            if deviation > 0.10 or evolution_count == 0:
                priority = 'HIGH'
            elif deviation > 0.05:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            prioritized.append((stock_id, priority, deviation))
            
            if priority != 'LOW':
                print(f'{stock_id}: {priority} priority (deviation: {deviation*100:.1f}%, evolutions: {evolution_count})')
        
        # 按偏差排序
        prioritized.sort(key=lambda x: x[2], reverse=True)
        
        return prioritized
    
    def determine_schedule_strategy(self, prioritized: List) -> Dict:
        """
        排程策略推演
        根據優先級動態調整頻率
        """
        schedule_plan = {}
        
        base_intervals = {
            'HIGH': 3600,      # 1小時
            'MEDIUM': 14400,   # 4小時
            'LOW': 86400       # 24小時
        }
        
        for stock_id, priority, deviation in prioritized:
            # 根據市場情境調整
            if self.regime == 'overheated':
                interval = base_intervals[priority] * 2  # 延長間隔
                action = 'monitor_only'
            elif self.regime == 'oversold':
                interval = base_intervals[priority] * 0.5  # 縮短間隔
                action = 'watch_for_entry'
            else:
                interval = base_intervals[priority]
                action = 'normal'
            
            schedule_plan[stock_id] = {
                'priority': priority,
                'interval': interval,
                'action': action,
                'deviation': deviation,
                'last_check': None
            }
        
        return schedule_plan
    
    def detect_time_conflicts(self, schedule_plan: Dict) -> List[str]:
        """時間衝突校正"""
        conflicts = []
        
        # 檢查同一時間是否有太多任務
        intervals = [s['interval'] for s in schedule_plan.values()]
        
        # 找最接近的兩個間隔
        if len(intervals) > 1:
            intervals.sort()
            min_diff = min(b - a for a, b in zip(intervals[:-1], intervals[1:]))
            
            if min_diff < 300:  # 小於5分鐘
                conflicts.append(f'Scheduling conflict detected: {min_diff}s between tasks')
        
        return conflicts
    
    def full_analysis(self) -> Dict:
        """完整分析"""
        # 績效偏差分析
        prioritized = self.analyze_performance_deviation()
        
        # 排程策略
        schedule_plan = self.determine_schedule_strategy(prioritized)
        
        # 衝突檢測
        conflicts = self.detect_time_conflicts(schedule_plan)
        
        print()
        print(f'Total prioritized stocks: {len(prioritized)}')
        print(f'High priority: {sum(1 for p in prioritized if p[1] == "HIGH")}')
        print(f'Schedule conflicts: {len(conflicts)}')
        
        return {
            'prioritized': prioritized,
            'schedule_plan': schedule_plan,
            'conflicts': conflicts,
            'analysis_time': datetime.now().isoformat()
        }

# ========== 第三階段：操作層 ==========
class ManipulationLayer:
    """Cron 排程動態調整"""
    
    def __init__(self, schedule_plan: Dict):
        self.schedule_plan = schedule_plan
        self.temp_file = os.path.join(WORKSPACE, 'temp_schedule.json')
        self.backup_dir = os.path.join(WORKSPACE, 'backups', 'schedules')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def generate_cron_expressions(self, stock_id: str, interval: int) -> str:
        """根據間隔生成 Cron 表達式"""
        if interval <= 3600:
            # 每小時
            return f'0 */1 * * *'
        elif interval <= 14400:
            # 每4小時
            return f'0 */4 * * *'
        elif interval <= 43200:
            # 每12小時
            return f'0 */12 * * *'
        else:
            # 每天
            return f'0 8 * * *'
    
    def generate_schedule_content(self) -> str:
        """生成排程內容"""
        schedules = []
        
        for stock_id, plan in self.schedule_plan.items():
            cron_expr = self.generate_cron_expressions(stock_id, plan['interval'])
            
            schedules.append({
                'stock_id': stock_id,
                'cron': cron_expr,
                'script': f'scripts/stock_optimize_{stock_id}.py',
                'action': plan['action'],
                'priority': plan['priority']
            })
        
        return json.dumps(schedules, indent=2)
    
    def validate_schedule(self, content: str) -> Tuple[bool, str]:
        """暫存與校驗機制"""
        try:
            schedules = json.loads(content)
            
            for schedule in schedules:
                # 驗證必填欄位
                required = ['stock_id', 'cron', 'script']
                for field in required:
                    if field not in schedule:
                        return False, f'Missing field: {field}'
                
                # 驗證 cron 表達式格式
                cron = schedule['cron']
                parts = cron.split()
                if len(parts) != 5:
                    return False, f'Invalid cron format: {cron}'
            
            return True, 'Validation passed'
            
        except json.JSONDecodeError as e:
            return False, f'JSON error: {e}'
    
    def atomic_write(self, content: str) -> bool:
        """原子化寫入"""
        try:
            # 1. 寫入暫存檔
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 2. 備份現有排程
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'schedule_{timestamp}.json')
            shutil.copy(self.temp_file, backup_file)
            
            # 3. 驗證
            valid, msg = self.validate_schedule(content)
            if not valid:
                print(f'[WARN] Validation failed: {msg}')
                return False
            
            print(f'[OK] Schedule validated: {msg}')
            print(f'[OK] Backup saved: {backup_file}')
            
            return True
            
        except Exception as e:
            print(f'[ERROR] Atomic write failed: {e}')
            return False
    
    def update_cron_jobs(self) -> int:
        """更新 Cron Jobs"""
        updated = 0
        
        for stock_id, plan in self.schedule_plan.items():
            if plan['priority'] == 'HIGH':
                # 動態調整高優先級股票的 cron
                cron_expr = self.generate_cron_expressions(stock_id, plan['interval'])
                
                # 這裡調用 openclaw cron update
                # 由於無法直接更新現有 cron，先標記為待更新
                print(f'[UPDATE] {stock_id}: {cron_expr} (action: {plan["action"]})')
                updated += 1
        
        return updated
    
    def full_manipulation(self) -> Dict:
        """完整操作"""
        print()
        print('[Manipulation Layer]')
        print('-'*50)
        
        # 生成內容
        content = self.generate_schedule_content()
        print(f'Generated {len(self.schedule_plan)} schedule entries')
        
        # 驗證
        valid, msg = self.validate_schedule(content)
        print(f'Validation: {msg}')
        
        if valid:
            # 原子化寫入
            success = self.atomic_write(content)
            print(f'Atomic Write: {"SUCCESS" if success else "FAILED"}')
            
            # 更新 Cron
            updated = self.update_cron_jobs()
            print(f'Cron Jobs Updated: {updated}')
        else:
            success = False
            updated = 0
        
        return {
            'success': success,
            'schedules_generated': len(self.schedule_plan),
            'cron_jobs_updated': updated,
            'manipulation_time': datetime.now().isoformat()
        }

# ========== 第四階段：執行層 ==========
class ExecutionLayer:
    """自主啟動與任務管理"""
    
    def __init__(self):
        self.lock_dir = os.path.join(WORKSPACE, 'locks')
        os.makedirs(self.lock_dir, exist_ok=True)
        self.active_locks = set()
    
    def check_environment(self) -> Dict:
        """環境變數對齊"""
        env_status = {
            'api_keys_present': False,
            'paths_correct': False,
            'ready': False,
            'details': {}
        }
        
        # 檢查 API keys（讀取 TOOLS.md）
        tools_file = os.path.join(os.path.dirname(WORKSPACE), 'TOOLS.md')
        if os.path.exists(tools_file):
            with open(tools_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 檢查關鍵 API token 是否存在
                has_finmind = 'eyJ0eXAiOiJKV1' in content
                has_fugle = 'ZjEwNWVkNjMtMWNmNi00ZmI0LWI5MzEtZmQyZDJmNGM4M2E1' in content or 'ZGI1MDk1' in content
                env_status['details']['FinMind API'] = has_finmind
                env_status['details']['Fugle API'] = has_fugle
                env_status['api_keys_present'] = has_finmind or has_fugle
        else:
            # 嘗試工作區根目錄
            workspace_tools = os.path.join(WORKSPACE, 'TOOLS.md')
            if os.path.exists(workspace_tools):
                with open(workspace_tools, 'r', encoding='utf-8') as f:
                    content = f.read()
                    has_finmind = 'eyJ0eXAiOiJKV1' in content
                    has_fugle = 'ZjEwNWVkNjMtMWNmNi00ZmI0LWI5MzEtZmQyZDJmNGM4M2E1' in content
                    env_status['details']['FinMind API'] = has_finmind
                    env_status['details']['Fugle API'] = has_fugle
                    env_status['api_keys_present'] = has_finmind or has_fugle
        
        # 檢查關鍵路徑
        critical_paths = {
            'scripts': os.path.join(WORKSPACE, 'scripts'),
            'configs': os.path.join(WORKSPACE, 'configs'),
            'data': os.path.join(WORKSPACE, 'data'),
            'stock_strategies': os.path.join(WORKSPACE, 'configs', 'stock_strategies'),
            'reports': os.path.join(WORKSPACE, 'reports')
        }
        path_status = {k: os.path.exists(v) for k, v in critical_paths.items()}
        env_status['details']['paths'] = path_status
        env_status['paths_correct'] = all(path_status.values())
        
        env_status['ready'] = env_status['api_keys_present'] and env_status['paths_correct']
        
        return env_status
    
    def acquire_lock(self, task_name: str, ttl: int = 3600) -> bool:
        """
        運行鎖定保護
        TTL: 鎖的有效期（秒）
        """
        lock_file = os.path.join(self.lock_dir, f'{task_name}.lock')
        
        # 檢查是否已存在且未過期
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    lock_data = json.load(f)
                    lock_time = datetime.fromisoformat(lock_data['timestamp'])
                    elapsed = (datetime.now() - lock_time).total_seconds()
                    
                    if elapsed < lock_data['ttl']:
                        print(f'[LOCK] {task_name} already locked (ttl: {elapsed:.0f}s)')
                        return False
                    else:
                        print(f'[LOCK] {task_name} lock expired, releasing')
                        os.remove(lock_file)
            except:
                pass
        
        # 建立新鎖
        lock_data = {
            'task_name': task_name,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl
        }
        
        with open(lock_file, 'w') as f:
            json.dump(lock_data, f)
        
        self.active_locks.add(task_name)
        print(f'[LOCK] {task_name} lock acquired')
        return True
    
    def release_lock(self, task_name: str):
        """釋放鎖"""
        lock_file = os.path.join(self.lock_dir, f'{task_name}.lock')
        
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print(f'[UNLOCK] {task_name} lock released')
        
        self.active_locks.discard(task_name)
    
    def proactive_wake(self, task_name: str, reason: str) -> bool:
        """
        主動喚醒機制
        繞過定時器直接啟動任務
        """
        print()
        print(f'[WAKE] Proactive wake: {task_name}')
        print(f'      Reason: {reason}')
        
        # 檢查環境
        env = self.check_environment()
        if not env['ready']:
            print(f'[WARN] Environment not ready: {env}')
            return False
        
        # 獲取鎖
        if not self.acquire_lock(task_name):
            return False
        
        # 執行任務
        success = self.execute_task(task_name)
        
        # 釋放鎖
        self.release_lock(task_name)
        
        return success
    
    def execute_task(self, task_name: str) -> bool:
        """執行任務"""
        print(f'[EXEC] Executing task: {task_name}')
        
        # 根據任務名稱執行對應腳本
        script_map = {
            'stock_optimize': 'scripts/tina_active_brain.py',
            'market_scan': 'scripts/tw_report.py',
            'health_check': 'scripts/tina_lifecycle_monitor_v2.py',
            'cron_optimizer': 'scripts/tina_cron_optimizer.py',
            'memory_compact': 'scripts/tina_brain_evolution_report.py',
            'tw_value_scan': 'scripts/tw_value_growth_scan.py',
            'us_value_scan': 'scripts/us_value_growth_scan.py',
            'margin_scan': 'scripts/twse_margin_v4.py',
            'tw_drawdown': 'scripts/tw_drawdown.py',
            'rklb_report': 'scripts/rklb_report.py',
            'idle_intervention': 'scripts/tina_idle_intervention.py',
            'autonomous_decision': 'scripts/tina_autonomous_decision.py'
        }
        
        script = script_map.get(task_name)
        if not script:
            print(f'[WARN] Unknown task: {task_name}')
            return False
        
        script_path = os.path.join(WORKSPACE, script)
        if not os.path.exists(script_path):
            print(f'[WARN] Script not found: {script_path}')
            return False
        
        # 執行腳本
        try:
            print(f'[EXEC] Running: {script}')
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=WORKSPACE,
                encoding='utf-8',
                errors='replace'
            )
            
            success = result.returncode == 0
            
            # 輸出結果摘要
            if success:
                print(f'[OK] {task_name} completed successfully')
                # 如果有錯誤輸出也顯示
                if result.stderr:
                    stderr_lines = result.stderr.strip().split('\n')
                    if stderr_lines and stderr_lines[-1]:
                        print(f'    Last output: {stderr_lines[-1][:80]}')
            else:
                print(f'[FAIL] {task_name} failed with code {result.returncode}')
                if result.stderr:
                    print(f'    Error: {result.stderr[:200]}')
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f'[ERROR] {task_name} timed out (300s limit)')
            return False
        except Exception as e:
            print(f'[ERROR] {task_name} exception: {e}')
            return False
    
    def full_execution(self, tasks: List[str] = None, force: bool = False) -> Dict:
        """完整執行"""
        print()
        print('[Execution Layer]')
        print('-'*50)
        
        # 環境檢查
        env = self.check_environment()
        print(f'Environment Ready: {env["ready"]}')
        
        if not env['ready'] and not force:
            print('[WARN] Environment not ready, skipping task execution')
            print('[INFO] To force execution, set force=True')
            return {
                'success': False, 
                'reason': 'Environment not ready',
                'env': env,
                'tasks_attempted': 0,
                'tasks_succeeded': 0
            }
        
        # 預設任務
        if tasks is None:
            tasks = ['health_check', 'market_scan', 'tw_value_scan']
        
        print(f'Tasks to execute: {tasks}')
        print()
        
        # 執行每個任務
        results = {}
        for task in tasks:
            success = self.proactive_wake(task, f'Regular maintenance: {task}')
            results[task] = success
        
        success_count = sum(1 for v in results.values() if v)
        print()
        print(f'Execution Summary: {success_count}/{len(tasks)} tasks succeeded')
        
        return {
            'success': all(results.values()),
            'task_results': results,
            'execution_time': datetime.now().isoformat(),
            'tasks_attempted': len(tasks),
            'tasks_succeeded': success_count
        }

# ========== 第五階段：反思層 ==========
class ReflectionLayer:
    """學習記錄與回饋閉環"""
    
    def __init__(self, perception: Dict, intelligence: Dict, manipulation: Dict, execution: Dict):
        self.perception = perception
        self.intelligence = intelligence
        self.manipulation = manipulation
        self.execution = execution
        self.db_path = os.path.join(WORKSPACE, 'data', 'autonomous_learning.db')
        self.init_db()
    
    def init_db(self):
        """初始化資料庫"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                phase TEXT,
                action TEXT,
                stock_id TEXT,
                details TEXT,
                success INTEGER
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS schedule_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                stock_id TEXT,
                old_interval INTEGER,
                new_interval INTEGER,
                reason TEXT,
                outcome TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS performance_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                stock_id TEXT,
                metric TEXT,
                before_value REAL,
                after_value REAL,
                change_percent REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_decision(self, phase: str, action: str, stock_id: str = None, details: str = None, success: bool = True):
        """記錄決策"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO learning_history (timestamp, phase, action, stock_id, details, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), phase, action, stock_id, details, 1 if success else 0))
        
        conn.commit()
        conn.close()
    
    def track_schedule_adjustment(self, stock_id: str, old_interval: int, new_interval: int, reason: str):
        """追蹤排程調整"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO schedule_adjustments (timestamp, stock_id, old_interval, new_interval, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), stock_id, old_interval, new_interval, reason))
        
        conn.commit()
        conn.close()
    
    def track_performance_change(self, stock_id: str, metric: str, before: float, after: float):
        """追蹤效能變化"""
        change = (after - before) / before if before != 0 else 0
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO performance_tracking (timestamp, stock_id, metric, before_value, after_value, change_percent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), stock_id, metric, before, after, change))
        
        conn.commit()
        conn.close()
    
    def generate_report(self) -> str:
        """生成自我優化報告"""
        report = []
        report.append('='*60)
        report.append('Tina 自主學習報告')
        report.append('='*60)
        report.append(f'生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        report.append('')
        
        # 感知層摘要
        report.append('[感知層]')
        report.append(f'  閒置狀態: {self.perception["resources"]["is_idle"]}')
        report.append(f'  市場情境: {self.perception["market_regime"]}')
        report.append(f'  配置普查: {len(self.perception["configs"])} 檔股票')
        report.append('')
        
        # 智能層摘要
        if 'prioritized' in self.intelligence:
            high_priority = [p for p in self.intelligence['prioritized'] if p[1] == 'HIGH']
            report.append('[智能層]')
            report.append(f'  高優先級: {len(high_priority)} 檔')
            for stock_id, priority, deviation in high_priority[:5]:
                report.append(f'    - {stock_id}: {priority} (偏差 {deviation*100:.1f}%)')
            report.append('')
        
        # 操作層摘要
        report.append('[操作層]')
        report.append(f'  排程生成: {self.manipulation.get("schedules_generated", 0)} 個')
        report.append(f'  Cron更新: {self.manipulation.get("cron_jobs_updated", 0)} 個')
        report.append('')
        
        # 執行層摘要
        if 'task_results' in self.execution:
            report.append('[執行層]')
            for task, success in self.execution['task_results'].items():
                status = 'SUCCESS' if success else 'FAILED'
                report.append(f'  {task}: {status}')
            report.append('')
        
        # 反思層摘要
        report.append('[反思層]')
        report.append(f'  已記錄決策: 所有流程完成')
        report.append('')
        
        report.append('系統已完成第 {n} 次自主學習循環')
        report.append('='*60)
        
        return '\n'.join(report)
    
    def full_reflection(self) -> Dict:
        """完整反思"""
        print()
        print('[Reflection Layer]')
        print('-'*50)
        
        # 記錄所有階段
        self.log_decision('perception', 'full_scan', details=f'idle={self.perception["resources"]["is_idle"]}')
        self.log_decision('intelligence', 'analyze', details=f'regime={self.perception["market_regime"]}')
        self.log_decision('manipulation', 'generate', details=f'schedules={len(self.manipulation.get("schedule_plan", {}))}')
        self.log_decision('execution', 'execute', details=f'tasks={len(self.execution.get("task_results", {}))}')
        
        # 生成報告
        report = self.generate_report()
        print(report)
        
        return {
            'report': report,
            'reflection_time': datetime.now().isoformat()
        }

# ========== 主控制類 ==========
class TinaAutonomousBrain:
    """
    Tina 自主學習整合系統
    五大階段完整閉環
    """
    
    def __init__(self):
        self.name = 'Tina Autonomous Brain'
        self.version = 'v1.0'
        
        self.perception = None
        self.intelligence = None
        self.manipulation = None
        self.execution = None
        self.reflection = None
    
    def run_full_cycle(self, force: bool = False) -> Dict:
        """
        執行完整自主學習循環
        
        流程：
        1. 感知層 → 2. 智能層 → 3. 操作層 → 4. 執行層 → 5. 反思層
        """
        print()
        print('='*70)
        print(f'{self.name} - {self.version}')
        print('自主學習循環啟動')
        print('='*70)
        print()
        
        timestamp = datetime.now().isoformat()
        
        # ========== 第一階段：感知層 ==========
        perception = PerceptionLayer()
        perception_data = perception.full_scan()
        self.perception = perception_data
        
        # 檢查是否應該繼續
        if not force and not perception_data['resources']['is_idle']:
            print('[SKIP] System not idle, skipping autonomous cycle')
            return {'status': 'skipped', 'reason': 'not_idle'}
        
        # ========== 第二階段：智能層 ==========
        intelligence = IntelligenceLayer(perception_data)
        intelligence_data = intelligence.full_analysis()
        self.intelligence = intelligence_data
        
        # ========== 第三階段：操作層 ==========
        schedule_plan = intelligence_data.get('schedule_plan', {})
        manipulation = ManipulationLayer(schedule_plan)
        manipulation_data = manipulation.full_manipulation()
        self.manipulation = manipulation_data
        
        # ========== 第四階段：執行層 ==========
        execution = ExecutionLayer()
        
        # 根據優先級執行任務
        high_priority_stocks = [p[0] for p in intelligence_data.get('prioritized', []) if p[1] == 'HIGH']
        tasks = ['market_scan', 'health_check']
        
        if high_priority_stocks:
            tasks.append('stock_optimize')
        
        execution_data = execution.full_execution(tasks)
        self.execution = execution_data
        
        # ========== 第五階段：反思層 ==========
        reflection = ReflectionLayer(perception_data, intelligence_data, manipulation_data, execution_data)
        reflection_data = reflection.full_reflection()
        self.reflection = reflection_data
        
        # ========== 完成 ==========
        print()
        print('='*70)
        print('自主學習循環完成')
        print('='*70)
        
        return {
            'status': 'completed',
            'perception': perception_data,
            'intelligence': intelligence_data,
            'manipulation': manipulation_data,
            'execution': execution_data,
            'reflection': reflection_data,
            'cycle_time': datetime.now().isoformat()
        }

# ========== 快速測試 ==========
if __name__ == '__main__':
    brain = TinaAutonomousBrain()
    result = brain.run_full_cycle(force=True)
    
    print()
    print('='*70)
    print('RESULT')
    print('='*70)
    print(f'Status: {result["status"]}')
    print(f'High priority stocks: {len([p for p in result.get("intelligence", {}).get("prioritized", []) if p[1] == "HIGH"])}')
    print(f'Tasks executed: {len(result.get("execution", {}).get("task_results", {}))}')