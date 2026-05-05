"""
Tina Proactive Housekeeper - 主動式管家系統
監控市場 ATR 變化、淨值表現、連續虧損，主動通知 Jo
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Alert rules
ALERT_RULES = {
    'atr_spike': {
        'condition': 'ATR > 2x 20日均值',
        'action': 'Telegram: 市場波動過高，系統暫停交易',
        'priority': 'HIGH',
        'cooldown_hours': 6,
    },
    'net_value_outperform': {
        'condition': '單日淨值 +2% 以上',
        'action': 'Telegram: 淨值表現優異，整理前五大持股',
        'priority': 'MEDIUM',
        'cooldown_hours': 24,
    },
    'three_losses_streak': {
        'condition': '連續3筆虧損',
        'action': 'Telegram: 要求策略面談',
        'priority': 'HIGH',
        'cooldown_hours': 0,
    },
    'high_vix': {
        'condition': 'VIX > 25',
        'action': 'Telegram: VIX 過高，市場恐慌，建議減碼',
        'priority': 'HIGH',
        'cooldown_hours': 6,
    },
    'consecutive_losses_5': {
        'condition': '連續5筆虧損',
        'action': 'Telegram: 策略嚴重失效，應全面檢討',
        'priority': 'CRITICAL',
        'cooldown_hours': 0,
    },
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'alert_rules.json')


def load_rules():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding='utf-8') as f:
                cfg = json.load(f)
            return cfg.get('rules', ALERT_RULES)
        except Exception:
            pass
    return ALERT_RULES


class ProactiveHousekeeper:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.logs_dir = os.path.join(base_dir, 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)

        self.stock_tracking_db = os.path.join(self.data_dir, 'stock_tracking.db')
        self.tina_learning_db = os.path.join(self.data_dir, 'tina_learning.db')
        self.positions_db = os.path.join(self.data_dir, 'portfolio.db')
        self.alert_db = os.path.join(self.data_dir, 'tina_alert_log.db')

        self.rules = load_rules()
        self.alerts_triggered = []
        self.check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self._init_alert_db()

    def _init_alert_db(self):
        conn = sqlite3.connect(self.alert_db)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_name TEXT NOT NULL,
                priority TEXT,
                condition TEXT,
                action_taken TEXT,
                details TEXT,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cooldown_tracker (
                alert_name TEXT PRIMARY KEY,
                last_triggered TEXT,
                cooldown_hours INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def _is_cooldown(self, alert_name, cooldown_hours):
        if cooldown_hours == 0:
            return False
        conn = sqlite3.connect(self.alert_db)
        cur = conn.cursor()
        cur.execute(
            "SELECT last_triggered FROM cooldown_tracker WHERE alert_name = ?",
            (alert_name,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        try:
            last = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            elapsed = (datetime.now() - last).total_seconds() / 3600
            return elapsed < cooldown_hours
        except Exception:
            return False

    def _record_alert(self, alert_name, priority, condition, details):
        conn = sqlite3.connect(self.alert_db)
        cur = conn.cursor()
        cooldown = self.rules.get(alert_name, {}).get('cooldown_hours', 0)
        cur.execute(
            "INSERT INTO alert_log (timestamp, alert_name, priority, condition, action_taken, details) VALUES (?, ?, ?, ?, ?, ?)",
            (self.check_time, alert_name, priority, condition, self.rules.get(alert_name, {}).get('action', ''), json.dumps(details, ensure_ascii=False))
        )
        cur.execute(
            "INSERT OR REPLACE INTO cooldown_tracker (alert_name, last_triggered, cooldown_hours) VALUES (?, ?, ?)",
            (alert_name, self.check_time, cooldown)
        )
        conn.commit()
        conn.close()

        self.alerts_triggered.append({
            'name': alert_name,
            'priority': priority,
            'condition': condition,
            'details': details,
            'action': self.rules.get(alert_name, {}).get('action', ''),
        })

    # ATR Spike check
    def check_atr_spike(self):
        alert_name = 'atr_spike'
        if self._is_cooldown(alert_name, self.rules[alert_name]['cooldown_hours']):
            return None

        master_db = os.path.join(self.data_dir, 'tina_master.db')
        if not os.path.exists(master_db):
            return None

        conn = sqlite3.connect(master_db)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT date, high, low, close
                FROM MarketData
                WHERE symbol = 'TWII' OR symbol = '0050'
                ORDER BY date DESC LIMIT 30
            """)
            rows = cur.fetchall()
        except Exception:
            conn.close()
            return None
        conn.close()

        if len(rows) < 21:
            return None

        highs = [r[1] for r in rows[::-1]]
        lows = [r[2] for r in rows[::-1]]
        closes = [r[3] for r in rows[::-1]]

        trs = []
        for i in range(1, len(highs)):
            h, l, pc = highs[i], lows[i], closes[i-1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)

        if len(trs) < 20:
            return None

        current_atr = sum(trs[-1:]) / 1
        avg_atr20 = sum(trs[-20:]) / 20

        if current_atr > 2 * avg_atr20:
            self._record_alert(alert_name, 'HIGH', f'ATR={current_atr:.2f}, 20日均值={avg_atr20:.2f}', {
                'current_atr': current_atr,
                'avg_atr20': avg_atr20,
                'ratio': current_atr / avg_atr20 if avg_atr20 else 0,
            })
            return True
        return False

    # Net value outperform check
    def check_net_value_outperform(self):
        alert_name = 'net_value_outperform'
        if self._is_cooldown(alert_name, self.rules[alert_name]['cooldown_hours']):
            return None

        positions_file = os.path.join(self.data_dir, 'positions', 'daily_nav.json')
        if not os.path.exists(positions_file):
            return None

        try:
            with open(positions_file, encoding='utf-8') as f:
                nav_data = json.load(f)
            if isinstance(nav_data, list) and len(nav_data) >= 2:
                latest = nav_data[-1]
                prev = nav_data[-2]
                change = (latest.get('nav', 0) - prev.get('nav', 0)) / prev.get('nav', 1) * 100
                if change >= 2.0:
                    self._record_alert(alert_name, 'MEDIUM', f'Single-day NAV {change:+.2f}%', {
                        'nav_change': change,
                        'latest_nav': latest.get('nav'),
                        'prev_nav': prev.get('nav'),
                        'date': latest.get('date'),
                    })
                    return True
        except Exception:
            pass
        return False

    # Consecutive losses check
    def check_consecutive_losses(self):
        learning_db = self.tina_learning_db
        if not os.path.exists(learning_db):
            return None

        conn = sqlite3.connect(learning_db)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT pnl_pct FROM trades
                ORDER BY exit_date DESC LIMIT 10
            """)
            rows = cur.fetchall()
        except Exception:
            conn.close()
            return None
        conn.close()

        if len(rows) < 3:
            return None

        pnls = [float(r[0]) for r in rows if r[0] is not None]
        consecutive = 0
        for p in pnls:
            if p < 0:
                consecutive += 1
            else:
                break

        if consecutive >= 5 and not self._is_cooldown('consecutive_losses_5', self.rules['consecutive_losses_5']['cooldown_hours']):
            self._record_alert('consecutive_losses_5', 'CRITICAL',
                f'Consecutive {consecutive} losses', {'consecutive_losses': consecutive, 'recent_pnls': pnls[:5]})
            return 'consecutive_losses_5'
        elif consecutive >= 3 and not self._is_cooldown('three_losses_streak', self.rules['three_losses_streak']['cooldown_hours']):
            self._record_alert('three_losses_streak', 'HIGH',
                f'Consecutive {consecutive} losses', {'consecutive_losses': consecutive, 'recent_pnls': pnls[:3]})
            return 'three_losses_streak'

        return False

    # High VIX check
    def check_high_vix(self):
        alert_name = 'high_vix'
        if self._is_cooldown(alert_name, self.rules[alert_name]['cooldown_hours']):
            return None

        vix_file = os.path.join(self.data_dir, 'market_regime.json')
        vix = None
        if os.path.exists(vix_file):
            try:
                with open(vix_file, encoding='utf-8') as f:
                    data = json.load(f)
                vix = data.get('vix') or data.get('VIX')
            except Exception:
                pass

        if vix and vix > 25:
            self._record_alert(alert_name, 'HIGH', f'VIX={vix:.2f}', {'vix': vix})
            return True
        return False

    # Main heartbeat check
    def run_heartbeat(self):
        print(f"[Housekeeper] Heartbeat check {self.check_time}")
        checks = [
            ('atr_spike', self.check_atr_spike),
            ('net_value_outperform', self.check_net_value_outperform),
            ('consecutive_losses', self.check_consecutive_losses),
            ('high_vix', self.check_high_vix),
        ]

        results = {}
        for name, fn in checks:
            try:
                results[name] = fn()
            except Exception as e:
                print(f"[Housekeeper] {name} check error: {e}")
                results[name] = None

        if self.alerts_triggered:
            print(f"[Housekeeper] TRIGGERED {len(self.alerts_triggered)} Alerts:")
            for a in self.alerts_triggered:
                print(f"  - [{a['priority']}] {a['name']}: {a['condition']}")
        else:
            print(f"[Housekeeper] All checks OK, no alerts")

        return {
            'timestamp': self.check_time,
            'alerts': self.alerts_triggered,
            'checks': results,
        }

    # Format Telegram message
    def format_telegram_message(self):
        if not self.alerts_triggered:
            return None

        lines = [
            "*Tina Proactive Housekeeper Alert*",
            f"Time: {self.check_time}",
            ""
        ]

        priority_icons = {'CRITICAL': '[CRIT]', 'HIGH': '[HIGH]', 'MEDIUM': '[MED]'}
        for a in self.alerts_triggered:
            icon = priority_icons.get(a['priority'], '[LOW]')
            lines.append(f"{icon} *{a['name'].replace('_', ' ').title()}*")
            lines.append(f"   Condition: {a['condition']}")
            lines.append(f"   Action: {a['action']}")
            if a['details']:
                if isinstance(a['details'], dict):
                    for k, v in a['details'].items():
                        lines.append(f"   - {k}: {v}")
            lines.append("")

        return "\n".join(lines)

    # Save alert log
    def save_alert_log(self):
        log_path = os.path.join(self.logs_dir, f"tina_alert_log_{datetime.now().strftime('%Y%m%d')}.json")
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': self.check_time,
                'alerts': self.alerts_triggered,
            }, f, ensure_ascii=False, indent=2)
        print(f"[Housekeeper] Alert log: {log_path}")
        return log_path


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    keeper = ProactiveHousekeeper(base_dir=base)
    result = keeper.run_heartbeat()
    keeper.save_alert_log()
    msg = keeper.format_telegram_message()
    if msg:
        print("\n" + msg)
    else:
        print("\n[OK] Heartbeat check complete, no alerts")