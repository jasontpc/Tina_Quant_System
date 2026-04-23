# -*- coding: utf-8 -*-
"""
Tina + Nana 團隊共享資料層
===========================

目的: 讓 Tina 和 Nana 團隊共享公開資訊

共享資料:
1. 市場概況 (Market Overview)
2. 當日強弱股票 (Daily Strength)
3. 系統訊號 (System Signals)
4. 風險狀態 (Risk Status)

使用方法:
    from team_shared import TeamShared, MarketSnapshot
    
    shared = TeamShared()
    
    # Tina 寫入當日分析
    shared.write_tina_signal('2330', {'score': 85, 'signal': 'buy'})
    
    # Nana 讀取 Tina 訊號
    tina_signals = shared.get_tina_signals()
    
    # 產生聯合報告
    joint = shared.get_joint_report()
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

SHARED_DIR = 'Tina_Quant_System/teams/shared'
os.makedirs(SHARED_DIR, exist_ok=True)

MARKET_FILE = os.path.join(SHARED_DIR, 'market_snapshot.json')
TINA_SIGNALS_FILE = os.path.join(SHARED_DIR, 'tina_signals.json')
NANA_SIGNALS_FILE = os.path.join(SHARED_DIR, 'nana_signals.json')
WATCHLIST_FILE = os.path.join(SHARED_DIR, 'watchlist.json')
ALERTS_FILE = os.path.join(SHARED_DIR, 'alerts.json')


class TeamShared:
    """
    Tina + Nana 團隊共享資料管理
    
    所有團隊成員都能讀寫共享資料
    """
    
    def __init__(self):
        self.shared_dir = SHARED_DIR
        os.makedirs(self.shared_dir, exist_ok=True)
    
    # ==================== 市場快照 ====================
    
    def write_market_snapshot(self, data: Dict):
        """寫入市場快照 (Tina/Nana 都能寫)"""
        snapshot = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'twii': data.get('twii'),
            'sp500': data.get('sp500'),
            'vix': data.get('vix'),
            'usdtwd': data.get('usdtwd'),
            'market_status': data.get('market_status', 'normal'),
            'breadth': data.get('breadth', {}),
            'sector_rotation': data.get('sector_rotation', [])
        }
        
        with open(MARKET_FILE, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    
    def get_market_snapshot(self) -> Dict:
        """讀取市場快照"""
        try:
            with open(MARKET_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    # ==================== Tina 訊號 ====================
    
    def write_tina_signal(self, symbol: str, signal_data: Dict):
        """寫入 Tina 訊號"""
        signals = self.get_tina_signals()
        signals[symbol] = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            **signal_data
        }
        self._cleanup_old_signals(signals)
        
        with open(TINA_SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
    
    def get_tina_signals(self) -> Dict:
        """讀取所有 Tina 訊號"""
        try:
            with open(TINA_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def get_tina_signal(self, symbol: str) -> Optional[Dict]:
        """讀取特定股票 Tina 訊號"""
        signals = self.get_tina_signals()
        return signals.get(symbol)
    
    # ==================== Nana 訊號 ====================
    
    def write_nana_signal(self, symbol: str, signal_data: Dict):
        """寫入 Nana 訊號"""
        signals = self.get_nana_signals()
        signals[symbol] = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            **signal_data
        }
        self._cleanup_old_signals(signals)
        
        with open(NANA_SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
    
    def get_nana_signals(self) -> Dict:
        """讀取所有 Nana 訊號"""
        try:
            with open(NANA_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def get_nana_signal(self, symbol: str) -> Optional[Dict]:
        """讀取特定股票 Nana 訊號"""
        signals = self.get_nana_signals()
        return signals.get(symbol)
    
    # ==================== 共用觀察名單 ====================
    
    def write_watchlist(self, watchlist: List[Dict]):
        """寫入共用觀察名單"""
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'stocks': watchlist
        }
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_watchlist(self) -> List[Dict]:
        """讀取共用觀察名單"""
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get('stocks', [])
        except:
            return []
    
    # ==================== 警報 ====================
    
    def write_alert(self, alert_type: str, message: str, severity: str = 'info'):
        """寫入警報"""
        alerts = self.get_alerts()
        alerts.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'type': alert_type,
            'message': message,
            'severity': severity  # 'info', 'warning', 'critical'
        })
        
        # 只保留最近 20 筆
        alerts = alerts[-20:]
        
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    def get_alerts(self) -> List[Dict]:
        """讀取所有警報"""
        try:
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def get_active_alerts(self) -> List[Dict]:
        """讀取未清除的警報"""
        return [a for a in self.get_alerts() if not a.get('cleared', False)]
    
    # ==================== 聯合報告 ====================
    
    def get_joint_report(self) -> Dict:
        """
        取得 Tina + Nana 聯合報告
        
        這是雙方團隊共享資訊的核心
        """
        tina_signals = self.get_tina_signals()
        nana_signals = self.get_nana_signals()
        market = self.get_market_snapshot()
        watchlist = self.get_watchlist()
        alerts = self.get_active_alerts()
        
        # 找出共識股票 (雙方都買)
        consensus = []
        for symbol in set(tina_signals.keys()) & set(nana_signals.keys()):
            t = tina_signals[symbol]
            n = nana_signals[symbol]
            
            # 評估共識強度
            t_score = t.get('score', 0)
            n_score = n.get('score', 0)
            
            if t.get('signal') in ['buy', 'strong_buy'] and n.get('signal') in ['buy', 'strong_buy']:
                consensus.append({
                    'symbol': symbol,
                    'tina_score': t_score,
                    'nana_score': n_score,
                    'avg_score': (t_score + n_score) / 2,
                    'tina_signal': t.get('signal'),
                    'nana_signal': n.get('signal')
                })
        
        # 排序
        consensus.sort(key=lambda x: x['avg_score'], reverse=True)
        
        # 衝突股票 (一方買一方不買)
        conflicts = []
        for symbol in set(tina_signals.keys()) | set(nana_signals.keys()):
            t = tina_signals.get(symbol, {})
            n = nana_signals.get(symbol, {})
            
            t_sig = t.get('signal', 'no_signal')
            n_sig = n.get('signal', 'no_signal')
            
            if t_sig != n_sig and t_sig != 'no_signal' and n_sig != 'no_signal':
                conflicts.append({
                    'symbol': symbol,
                    'tina_signal': t_sig,
                    'nana_signal': n_sig
                })
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'market': market,
            'consensus': consensus,
            'conflicts': conflicts,
            'tina_count': len(tina_signals),
            'nana_count': len(nana_signals),
            'watchlist': watchlist,
            'alerts': alerts
        }
    
    def print_joint_report(self):
        """格式化輸出聯合報告"""
        report = self.get_joint_report()
        
        print()
        print('='*60)
        print(' Tina + Nana 聯合分析報告')
        print('='*60)
        print(f' 時間: {report["timestamp"]}')
        print()
        
        # 市場概況
        m = report.get('market', {})
        if m:
            print(f' 市場: TWII {m.get("twii", "N/A")} | SP500 {m.get("sp500", "N/A")}')
            print()
        
        # 共識股票
        if report['consensus']:
            print(' 🔥 共識買進 (Tina + Nana 同步)')
            print('-'*60)
            for c in report['consensus'][:5]:
                print(f'  {c["symbol"]} | Tina {c["tina_score"]} + Nana {c["nana_score"]} = AVG {c["avg_score"]:.0f}')
            print()
        
        # 衝突股票
        if report['conflicts']:
            print(' ⚠️ 訊號衝突')
            print('-'*60)
            for c in report['conflicts']:
                print(f'  {c["symbol"]} | Tina={c["tina_signal"]} vs Nana={c["nana_signal"]}')
            print()
        
        # 警報
        if report['alerts']:
            print(' 🔔 活動警報')
            for a in report['alerts'][-3:]:
                print(f'  [{a["severity"].upper()}] {a["message"]}')
        
        print('='*60)
    
    # ==================== 工具 ====================
    
    def _cleanup_old_signals(self, signals: Dict, max_age_hours: int = 48):
        """清理過舊的訊號"""
        now = datetime.now()
        cleaned = {}
        
        for symbol, data in signals.items():
            ts = data.get('timestamp', '')
            try:
                signal_time = datetime.strptime(ts, '%Y-%m-%d %H:%M')
                age_hours = (now - signal_time).total_seconds() / 3600
                
                if age_hours < max_age_hours:
                    cleaned[symbol] = data
            except:
                cleaned[symbol] = data
        
        return cleaned
    
    def clear_all(self):
        """清除所有共享資料 (新的一天開始時)"""
        for f in [MARKET_FILE, TINA_SIGNALS_FILE, NANA_SIGNALS_FILE, ALERTS_FILE]:
            try:
                os.remove(f)
            except:
                pass


# ==================== 快速測試 ====================

def quick_test():
    """測試共享資料層"""
    print('='*50)
    print(' Tina + Nana 共享資料層測試')
    print('='*50)
    print()
    
    shared = TeamShared()
    
    # 寫入市場快照
    shared.write_market_snapshot({
        'twii': 37212,
        'sp500': 5230,
        'vix': 18.5,
        'market_status': 'bull'
    })
    print('✅ 寫入市場快照')
    
    # Tina 寫入訊號
    shared.write_tina_signal('2330', {
        'score': 85,
        'signal': 'buy',
        'rsi': 65,
        'atr_pct': 0.8
    })
    shared.write_tina_signal('2317', {
        'score': 70,
        'signal': 'buy',
        'rsi': 80
    })
    print('✅ Tina 寫入訊號')
    
    # Nana 寫入訊號
    shared.write_nana_signal('2330', {
        'score': 80,
        'signal': 'buy',
        'f_consec': 3
    })
    shared.write_nana_signal('3034', {
        'score': 75,
        'signal': 'buy',
        'f_consec': 4
    })
    print('✅ Nana 寫入訊號')
    
    # 寫入警報
    shared.write_alert('RSI', '2330 RSI 超過 80', 'warning')
    print('✅ 寫入警報')
    
    # 產出聯合報告
    shared.print_joint_report()


if __name__ == '__main__':
    quick_test()