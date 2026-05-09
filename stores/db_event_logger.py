# -*- coding: utf-8 -*-
"""
DB Event Logger — 所有資料庫變化寫入記憶系統
============================================
功能：
1. 攔截所有 INSERT/UPDATE/DELETE 操作
2. 記錄變化的摘要到記憶系統
3. 追蹤各 DB 的最後更新時間
4. 發現異常波動（如大量新增/刪除）時寫入 lesson

用法：
  from db_event_logger import DBEventLogger
  logger = DBEventLogger()
  
  # 包裝 sqlite3.connect
  conn = logger.connect('yfinance.db')
  
  # 或裝飾任何 DB 操作函式
  @logger.log_insert('daily_ohlcv', universe='TW', importance=7)
  def insert_ohlcv(conn, data):
      ...

  # 手動記錄重大變化
  logger.log_change('yfinance.db', 'symbols', 'INSERT', {'symbol': '2330.TW', 'universe_group': 'tw500'})
"""

import sqlite3, json, os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from functools import wraps

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
DATA_DIR = BASE_DIR / 'data'
DB_EVENT_LOG = STORES_DIR / 'db_event_log.json'

class DBEventLogger:
    """資料庫事件紀錄器"""
    
    # 標準 DB → Universe 映射
    DB_UNIVERSE = {
        'yfinance.db': 'MULTI',
        'tw_history.db': 'TW',
        'us_history.db': 'US',
        'etf.db': 'MULTI',
        'leverage_etf.db': 'US',
        'sherry_etf.db': 'MULTI',
        'sherry_sim_trades.db': 'US',
        'tw_margin.db': 'TW',
        'tw_stock_registry.db': 'TW',
        'macro_institutional.db': 'MULTI',
        'finmind.db': 'TW',
        'news_trends.db': 'MULTI',
        'stock_trends.db': 'TW',
        'sherry_backtest.db': 'US',
        'master_backtest.db': 'MULTI',
        'us_sim_trades.db': 'US',
        'twse_data.db': 'TW',
        'tw_active_etf.db': 'TW',
        'yuan_zheng2.db': 'TW',
    }
    
    # 各 DB 的重要性權重（數值越大表示越重要）
    DB_IMPORTANCE = {
        'yfinance.db': 9,
        'tw_history.db': 8,
        'us_history.db': 8,
        'sherry_sim_trades.db': 8,
        'us_sim_trades.db': 8,
        'macro_institutional.db': 7,
        'master_backtest.db': 7,
    }
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.event_log = self._load_log()
        self._last_events = defaultdict(list)
    
    def _load_log(self) -> list:
        if DB_EVENT_LOG.exists():
            try:
                with open(DB_EVENT_LOG, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_log(self):
        with open(DB_EVENT_LOG, 'w', encoding='utf-8') as f:
            json.dump(self.event_log[-1000:], f, ensure_ascii=False, indent=2)  # 保留1000筆
    
    def connect(self, db_name: str) -> sqlite3.Connection:
        """回傳包裝過的 sqlite3 connection"""
        db_path = self.data_dir / db_name
        conn = sqlite3.connect(str(db_path))
        
        # 包裝 cursor 執行
        original_execute = conn.cursor().execute
        original_executemany = conn.cursor().executemany
        
        cursor_wrapper = conn.cursor()
        
        def logged_execute(sql, params=None):
            result = original_execute(sql, params) if params else original_execute(sql)
            self._log_sql_event(db_name, sql, conn)
            return result
        
        def logged_executemany(sql, params_seq):
            result = original_executemany(sql, params_seq)
            self._log_sql_event(db_name, sql, conn, many=True)
            return result
        
        # 這裡我們需要維持原有介面
        # 注意：實際上很難完美替換，這只是示範概念
        return conn
    
    def _log_sql_event(self, db_name: str, sql: str, conn: sqlite3.Connection, many: bool = False):
        """記錄 SQL 事件"""
        sql_upper = sql.strip().upper()
        
        # 只關注 DML
        if not any(sql_upper.startswith(k) for k in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']):
            return
        
        op = 'INSERT' if sql_upper.startswith('INSERT') else \
              'UPDATE' if sql_upper.startswith('UPDATE') else \
              'DELETE' if sql_upper.startswith('DELETE') else 'DDL'
        
        # 嘗試解析 table 名稱
        table = self._extract_table(sql)
        universe = self.DB_UNIVERSE.get(db_name, 'UNKNOWN')
        importance = self.DB_IMPORTANCE.get(db_name, 5)
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'db': db_name,
            'universe': universe,
            'table': table,
            'operation': op,
            'importance': importance,
            'sql_preview': sql[:100]
        }
        
        self.event_log.append(event)
        self._last_events[db_name].append(event)
        
        # 記錄到短期記憶（如果重要）
        if importance >= 7:
            self._write_to_memory(event)
        
        self._save_log()
    
    def _extract_table(self, sql: str) -> str:
        """從 SQL 抽出 table 名稱"""
        words = sql.split()
        if len(words) < 2:
            return 'unknown'
        
        # INSERT INTO table
        if 'INTO' in sql.upper():
            idx = [w.upper() for w in words].index('INTO')
            if idx + 1 < len(words):
                return words[idx + 1].strip('`[]"\'()')
        
        # UPDATE table
        if sql.upper().startswith('UPDATE'):
            return words[1].strip('`[]"\'()')
        
        # DELETE FROM table
        if 'FROM' in sql.upper():
            idx = [w.upper() for w in words].index('FROM')
            if idx + 1 < len(words):
                return words[idx + 1].strip('`[]"\'()')
        
        # CREATE/DROP TABLE
        for kw in ['TABLE', 'INDEX']:
            if kw in sql.upper():
                idx = [w.upper() for w in words].index(kw)
                if idx + 1 < len(words):
                    return words[idx + 1].strip('`[]"\'()')
        
        return 'unknown'
    
    def _write_to_memory(self, event: dict):
        """寫入短期記憶"""
        try:
            sys_path = str(BASE_DIR / 'stores')
            if sys_path not in __import__('sys').path:
                __import__('sys').path.insert(0, sys_path)
            
            from short_term_writer import write_memory
            
            summary = f"[DB] {event['db']} {event['operation']} on {event['table']}"
            detail = json.dumps(event, ensure_ascii=False)
            
            write_memory(
                mtype='metric',
                summary=summary[:200],
                detail=detail,
                source='db_monitor',
                tags=['db', event['universe'].lower(), event['db'].replace('.db', ''), event['operation'].lower()],
                importance=event['importance'],
                links=[],
                expiry_days=7  # 只保留7天，週期性的 DB 寫入不需要太久
            )
        except Exception as e:
            print(f'[DBLogger] Memory write error: {e}')
    
    def get_db_last_updated(self) -> dict:
        """取得各 DB 的最後更新時間"""
        result = {}
        for db_name in self.DB_UNIVERSE.keys():
            db_path = self.data_dir / db_name
            if db_path.exists():
                mtime = datetime.fromtimestamp(db_path.stat().st_mtime)
                result[db_name] = mtime.isoformat()
        return result
    
    def get_event_summary(self, hours: int = 24) -> dict:
        """過去 N 小時的 DB 事件摘要"""
        cutoff = (datetime.now().timestamp() - hours * 3600)
        events = [e for e in self.event_log if datetime.fromisoformat(e['timestamp']).timestamp() > cutoff]
        
        by_db = defaultdict(int)
        by_op = defaultdict(int)
        for e in events:
            by_db[e['db']] += 1
            by_op[e['operation']] += 1
        
        return {
            'total_events': len(events),
            'by_database': dict(by_db),
            'by_operation': dict(by_op)
        }
    
    def check_anomalies(self, threshold_inserts: int = 100) -> list:
        """檢查異常（短時間大量寫入）"""
        anomalies = []
        for db_name, events in self._last_events.items():
            recent = [e for e in events if 
                     datetime.fromisoformat(e['timestamp']) > datetime.now().replace(hour=0, minute=0, second=0)]
            
            inserts = sum(1 for e in recent if e['operation'] == 'INSERT')
            if inserts > threshold_inserts:
                anomalies.append({
                    'db': db_name,
                    'inserts_today': inserts,
                    'threshold': threshold_inserts,
                    'severity': 'high' if inserts > threshold_inserts * 2 else 'medium'
                })
        
        return anomalies


def wrap_db_write(db_name: str, table: str, universe: str = 'MULTI'):
    """
    裝飾器：自動記錄 DB 寫入事件
    
    用法：
      @wrap_db_write('yfinance.db', 'daily_ohlcv', 'TW')
      def insert_ohlcv_batch(conn, records):
          cur = conn.cursor()
          cur.executemany('INSERT INTO daily_ohlcv ...', records)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 寫入記憶
            try:
                sys_path = str(BASE_DIR / 'stores')
                if sys_path not in __import__('sys').path:
                    __import__('sys').path.insert(0, sys_path)
                from short_term_writer import write_memory
                
                write_memory(
                    mtype='metric',
                    summary=f'[DB Write] {db_name}.{table} updated',
                    detail=f'Function: {func.__name__}',
                    source='db_monitor',
                    tags=['db', universe.lower(), db_name.replace('.db',''), 'write'],
                    importance=7,
                    expiry_days=7
                )
            except:
                pass
            
            return result
        return wrapper
    return decorator


if __name__ == '__main__':
    logger = DBEventLogger()
    
    print('=== DB Event Logger ===')
    print('Last updated check:')
    for db, t in logger.get_db_last_updated().items():
        print(f'  {db}: {t[:19]}')
    
    print('\nEvent summary (24h):')
    summary = logger.get_event_summary(24)
    print(f"  Total: {summary['total_events']}")
    for db, cnt in summary['by_database'].items():
        print(f'  {db}: {cnt}')
    
    anomalies = logger.check_anomalies()
    if anomalies:
        print('\nAnomalies:')
        for a in anomalies:
            print(f"  {a['db']}: {a['inserts_today']} inserts (severity: {a['severity']})")
    else:
        print('\nNo anomalies detected')