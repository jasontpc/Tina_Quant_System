# -*- coding: utf-8 -*-
"""
Tina Alert System — 主動預警系統
監控進場機會、風險、策略績效，主動通知
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
CONFIG_DIR = BASE_DIR / 'configs'
DB_PATH = DATA_DIR / 'tina_learning.db'
RULES_PATH = CONFIG_DIR / 'tina_alert_rules.json'


class TinaAlertSystem:
    """主動預警系統"""

    def __init__(self):
        self.config = self._load_config()
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.alerts = []

    def _load_config(self) -> dict:
        with open(RULES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _alert(self, alert_type: str, priority: str, title: str, message: str, details: dict = None):
        """發出警報"""
        emoji = "🚨" if priority == "high" else "⚠️"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        alert = {
            'timestamp': timestamp,
            'type': alert_type,
            'priority': priority,
            'title': title,
            'message': message,
            'details': details or {}
        }
        self.alerts.append(alert)

        # 終端輸出
        print(f"{emoji} Tina Alert [{priority.upper()}]")
        print(f"   時間：{timestamp}")
        print(f"   {title}")
        print(f"   {message}")
        if details:
            for k, v in details.items():
                print(f"   {k}：{v}")
        print()

    def check_all(self) -> list:
        """執行全面檢查"""
        self.alerts = []

        self._check_market_overbought()
        self._check_market_oversold()
        self._check_vix()
        self._check_strategy_win_rate()
        self._check_open_positions()
        self._check_patterns()

        return self.alerts

    def _check_market_overbought(self):
        """檢查大盤過熱"""
        cur = self.conn.cursor()
        cur.execute('SELECT twii_rsi FROM market_context ORDER BY timestamp DESC LIMIT 1')
        row = cur.fetchone()
        if not row or not row['twii_rsi']:
            return

        rsi = row['twii_rsi']
        if rsi >= 75:
            self._alert(
                'market',
                'medium',
                '【市場警訊】台股 RSI 過熱',
                f'TWII RSI {rsi:.0f}，建議獲利了結，降低倉位',
                {'rsi': rsi, 'threshold': 75}
            )

    def _check_market_oversold(self):
        """檢查大盤超賣"""
        cur = self.conn.cursor()
        cur.execute('SELECT twii_rsi FROM market_context ORDER BY timestamp DESC LIMIT 1')
        row = cur.fetchone()
        if not row or not row['twii_rsi']:
            return

        rsi = row['twii_rsi']
        if rsi <= 32:
            self._alert(
                'market',
                'medium',
                '【市場警訊】台股 RSI 超賣',
                f'TWII RSI {rsi:.0f}，關注價值股進場機會',
                {'rsi': rsi, 'threshold': 32}
            )

    def _check_vix(self):
        """檢查 VIX"""
        cur = self.conn.cursor()
        cur.execute('SELECT vix_rsi FROM market_context ORDER BY timestamp DESC LIMIT 1')
        row = cur.fetchone()
        if not row or not row['vix_rsi']:
            return

        vix = row['vix_rsi']
        if vix >= 25:
            self._alert(
                'market',
                'high',
                '【市場警訊】VIX 飆高',
                f'VIX {vix:.0f}，市場波動加劇，謹慎操作',
                {'vix': vix, 'threshold': 25}
            )
        elif vix <= 15:
            self._alert(
                'market',
                'medium',
                '【市場警訊】VIX 低檔',
                f'VIX {vix:.0f}，市場過於樂觀，注意風險',
                {'vix': vix, 'threshold': 15}
            )

    def _check_strategy_win_rate(self):
        """檢查策略勝率變化"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT strategy, win_rate, total_trades, updated_at
            FROM strategy_performance
            WHERE total_trades >= 5
            ORDER BY updated_at DESC
        ''')
        strategies = cur.fetchall()

        # 簡化：只檢查是否有策略勝率低於 40%
        for s in strategies:
            if s['win_rate'] < 0.40:
                self._alert(
                    'strategy',
                    'high',
                    f"【策略警訊】{s['strategy']} 勝率過低",
                    f"勝率 {s['win_rate']*100:.0f}%（共 {s['total_trades']} 筆交易），需檢討進場條件",
                    {'strategy': s['strategy'], 'win_rate': s['win_rate'], 'total_trades': s['total_trades']}
                )

    def _check_open_positions(self):
        """檢查持倉 RSI 過熱"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT id, stock, entry_price, entry_rsi, strategy_used, entry_date
            FROM trades
            WHERE exit_date IS NULL
        ''')
        positions = cur.fetchall()

        # 需要即時 RSI — 從 market_context 或其他來源獲取
        # 這裡簡化為檢查 entry_rsi 已過熱的情況
        for p in positions:
            if p['entry_rsi'] and p['entry_rsi'] > 75:
                self._alert(
                    'position',
                    'medium',
                    f"【持倉警訊】{p['stock']} 進場時 RSI 過高",
                    f"{p['stock']} 進場 RSI {p['entry_rsi']:.0f}，注意風險",
                    {'stock': p['stock'], 'entry_rsi': p['entry_rsi'], 'strategy': p['strategy_used']}
                )

    def _check_patterns(self):
        """檢查市場模式"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT pattern_name, description, success_rate, last_observed
            FROM market_patterns
            ORDER BY success_rate ASC
            LIMIT 3
        ''')
        patterns = cur.fetchall()

        for p in patterns:
            if p['success_rate'] < 0.35:
                self._alert(
                    'pattern',
                    'medium',
                    f"【模式警訊】{p['pattern_name']}",
                    f"成功率 {p['success_rate']*100:.0f}%({p['description']})",
                    {'pattern': p['pattern_name'], 'success_rate': p['success_rate']}
                )

    def generate_alert_report(self) -> str:
        """產出預警報告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        lines = [
            f"# 🚨 Tina 預警報告",
            f"**時間：{timestamp}**",
            "",
            f"## 警報數量：{len(self.alerts)}",
            ""
        ]

        if not self.alerts:
            lines.append("✅ 目前無需關注的警報")
        else:
            for i, alert in enumerate(self.alerts, 1):
                emoji = "🔴" if alert['priority'] == 'high' else "🟡"
                lines.append(f"### {emoji} {alert['title']}")
                lines.append(f"- 時間：{alert['timestamp']}")
                lines.append(f"- 訊息：{alert['message']}")
                if alert['details']:
                    for k, v in alert['details'].items():
                        lines.append(f"- {k}：{v}")
                lines.append("")

        report = "\n".join(lines)

        REPORT_DIR = BASE_DIR / 'reports'
        REPORT_DIR.mkdir(exist_ok=True)
        path = REPORT_DIR / f"tina_alerts_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    print("🚨 Tina Alert System 啟動...")
    print()

    system = TinaAlertSystem()
    alerts = system.check_all()

    print(f"共發現 {len(alerts)} 個警報")
    print()

    report = system.generate_alert_report()
    print(report)

    system.close()