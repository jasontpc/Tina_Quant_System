"""
Tina 個股策略熱啟動監控器
當策略文件變動時，自動重新載入該股票的策略配置
"""

import os
import time
import json
import threading
from datetime import datetime

class StrategyHotReload:
    """策略熱啟動監控器"""
    
    def __init__(self, strategies_dir, callback=None):
        self.strategies_dir = strategies_dir
        self.callback = callback  # 策略變動時的回調函數
        self.file_mtimes = {}  # 追蹤檔案修改時間
        self.modification_counts = {}  # 短時間內修改次數
        self.alert_threshold = 3  # 1小時內超過3次觸發警示
        self.alert_window = 3600  # 1小時（秒）
        self.suspended_stocks = {}  # 被停權的股票
        
        # 初始化：掃描所有策略檔案
        self._scan_all_files()
        
    def _scan_all_files(self):
        """掃描所有策略檔案並記錄修改時間"""
        if not os.path.exists(self.strategies_dir):
            return
            
        for f in os.listdir(self.strategies_dir):
            if f.endswith('.json') and f != 'template.json':
                path = os.path.join(self.strategies_dir, f)
                stock_code = f.replace('.json', '')
                self.file_mtimes[stock_code] = os.path.getmtime(path)
    
    def check_changes(self):
        """檢查策略檔案是否有變動"""
        changed_stocks = []
        
        for f in os.listdir(self.strategies_dir):
            if f.endswith('.json') and f != 'template.json':
                path = os.path.join(self.strategies_dir, f)
                stock_code = f.replace('.json', '')
                
                current_mtime = os.path.getmtime(path)
                if stock_code in self.file_mtimes:
                    if current_mtime != self.file_mtimes[stock_code]:
                        # 偵測到變動
                        changed_stocks.append({
                            'stock_code': stock_code,
                            'old_mtime': self.file_mtimes[stock_code],
                            'new_mtime': current_mtime,
                            'path': path
                        })
                        
                        # 更新記錄
                        self.file_mtimes[stock_code] = current_mtime
                        
                        # 記錄修改次數
                        self._record_modification(stock_code)
                else:
                    # 新檔案
                    changed_stocks.append({
                        'stock_code': stock_code,
                        'old_mtime': None,
                        'new_mtime': current_mtime,
                        'path': path
                    })
                    self.file_mtimes[stock_code] = current_mtime
        
        # 處理變動的檔案
        for change in changed_stocks:
            stock_code = change['stock_code']
            
            # 檢查是否被停權
            if stock_code in self.suspended_stocks:
                print(f"⚠️ {stock_code} 已被停權，跳過熱啟動")
                continue
            
            # 檢查修改頻率
            if self._check_modification_frequency(stock_code):
                print(f"🚫 {stock_code} 修改過於頻繁，已暫停自主修正權限")
                self._suspend_stock(stock_code)
                continue
            
            # 執行熱啟動
            self._hot_reload(change)
        
        return changed_stocks
    
    def _record_modification(self, stock_code):
        """記錄修改事件"""
        now = time.time()
        
        if stock_code not in self.modification_counts:
            self.modification_counts[stock_code] = []
        
        # 只保留最近 1 小時內的記錄
        self.modification_counts[stock_code] = [
            t for t in self.modification_counts[stock_code]
            if now - t < self.alert_window
        ]
        
        self.modification_counts[stock_code].append(now)
    
    def _check_modification_frequency(self, stock_code):
        """檢查修改頻率是否超標"""
        if stock_code not in self.modification_counts:
            return False
        
        now = time.time()
        recent = [
            t for t in self.modification_counts[stock_code]
            if now - t < self.alert_window
        ]
        
        return len(recent) >= self.alert_threshold
    
    def _suspend_stock(self, stock_code):
        """暫停該股票的自主修正權限"""
        self.suspended_stocks[stock_code] = time.time()
        
        # 可擴展：發送 Telegram 警示
        self._send_alert(stock_code, reason='修改過於頻繁')
    
    def _send_alert(self, stock_code, reason):
        """發送警示"""
        # TODO: 整合 Telegram 發送
        print(f"🚨 ALERT: {stock_code} 已暫停自主修正權限 - {reason}")
        
        # 寫入警示日誌
        alert_log = os.path.join(
            os.path.dirname(self.strategies_dir),
            'reports',
            'strategy_alerts.md'
        )
        os.makedirs(os.path.dirname(alert_log), exist_ok=True)
        
        with open(alert_log, 'a', encoding='utf-8') as f:
            f.write(f"\n## 警示 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**股票**: {stock_code}\n")
            f.write(f"**原因**: {reason}\n")
            f.write(f"**狀態**: 已暫停自主修正權限\n")
    
    def _hot_reload(self, change):
        """執行熱啟動"""
        stock_code = change['stock_code']
        print(f"🔄 熱啟動 {stock_code} 策略...")
        
        # 載入新策略
        with open(change['path'], 'r', encoding='utf-8') as f:
            new_strategy = json.load(f)
        
        # 清除快取（如果有的話）
        # TODO: 整合到 StockStrategyLoader 的清除方法
        
        # 呼叫回調函數
        if self.callback:
            self.callback(stock_code, new_strategy)
        
        print(f"✅ {stock_code} 策略已熱啟動")
    
    def get_modification_history(self, stock_code, hours=24):
        """取得股票修改歷史"""
        if stock_code not in self.modification_counts:
            return []
        
        now = time.time()
        return [
            datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
            for t in self.modification_counts[stock_code]
            if now - t < hours * 3600
        ]
    
    def is_suspended(self, stock_code):
        """檢查股票是否被停權"""
        if stock_code not in self.suspended_stocks:
            return False
        
        # 停權 24 小時後自動解除
        if time.time() - self.suspended_stocks[stock_code] > 86400:
            del self.suspended_stocks[stock_code]
            return False
        
        return True


# 測試
if __name__ == '__main__':
    strategies_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\configs\stock_strategies'
    
    monitor = StrategyHotReload(strategies_dir)
    
    print("=== 策略熱啟動監控器 ===")
    print(f"監控目錄: {strategies_dir}")
    print(f"已追蹤檔案數: {len(monitor.file_mtimes)}")
    
    # 測試檢查
    changes = monitor.check_changes()
    print(f"\n本次偵測到變動: {len(changes)} 檔")
    
    # 列出修改歷史
    print("\n修改歷史:")
    for stock_code in list(monitor.file_mtimes.keys())[:5]:
        history = monitor.get_modification_history(stock_code)
        if history:
            print(f"  {stock_code}: {len(history)} 次修改")