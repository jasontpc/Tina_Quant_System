"""
Tina Param Evolution - 參數進化系統
基於複盤結果建立新參數版本，不覆蓋原始代碼
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime
from collections import defaultdict


class ParamEvolution:
    VERSION_PREFIX = 'v'

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.configs_dir = os.path.join(base_dir, 'configs')
        self.param_versions_dir = os.path.join(self.configs_dir, 'param_versions')
        os.makedirs(self.param_versions_dir, exist_ok=True)

        self.versions_db = os.path.join(self.data_dir, 'tina_param_versions.db')
        self.default_params_file = os.path.join(self.configs_dir, 'unified_strategy_config.json')
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS param_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                parent_version TEXT,
                created_at TEXT NOT NULL,
                description TEXT,
                params_json TEXT NOT NULL,
                performance_json TEXT,
                is_active INTEGER DEFAULT 0,
                is_deployed INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS param_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                param_key TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ──── 讀取預設參數 ────
    def load_base_params(self):
        if os.path.exists(self.default_params_file):
            with open(self.default_params_file, encoding='utf-8') as f:
                return json.load(f)
        # 回退預設值
        return {
            'entry_rsi_min': 32,
            'entry_rsi_max': 45,
            'stop_loss_atr': 2.0,
            'take_profit_atr': 3.0,
            'max_hold_days': 20,
            'ma_confirm': True,
            'ma_period': 20,
            'rsi_period': 14,
            'atr_period': 14,
        }

    # ──── 建立新版本 ────
    def create_new_version(self, base_version=None, changes=None, description=''):
        """
        建立新參數版本
        base_version: 基礎版本（如 'v1_base'），None 表示使用當前活躍版本
        changes: dict of {param_key: new_value}
        description: 版本說明
        """
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()

        # 取得基礎參數
        if base_version:
            cur.execute("SELECT params_json FROM param_versions WHERE version = ?", (base_version,))
            row = cur.fetchone()
            if row:
                base_params = json.loads(row[0])
            else:
                base_params = self.load_base_params()
        else:
            # 取得當前活躍版本
            cur.execute("SELECT params_json FROM param_versions WHERE is_active = 1 LIMIT 1")
            row = cur.fetchone()
            base_params = json.loads(row[0]) if row else self.load_base_params()

        # 計算新版本號
        cur.execute("SELECT version FROM param_versions ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            last_ver = row[0]
            # 解析版本號
            try:
                num = int(last_ver.replace('v', '').split('_')[0])
                new_num = num + 1
            except Exception:
                new_num = 1
        else:
            new_num = 1

        # 命名：v{num}_{tag} 或 v{num}_optimized / v{num}_adapted
        tag = 'optimized'
        if 'rsi' in str(changes).lower():
            tag = 'adapted_rsi'
        elif 'hold' in str(changes).lower():
            tag = 'adapted_hold'
        elif 'atr' in str(changes).lower():
            tag = 'adapted_atr'

        new_version = f"v{new_num}_{tag}"

        # 合併變更
        new_params = dict(base_params)
        change_records = []
        if changes:
            for key, new_val in changes.items():
                old_val = base_params.get(key)
                new_params[key] = new_val
                change_records.append({
                    'param_key': key,
                    'old_value': str(old_val) if old_val is not None else 'None',
                    'new_value': str(new_val),
                    'reason': description,
                })

        # 寫入資料庫
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""
            INSERT INTO param_versions (version, parent_version, created_at, description, params_json, is_active, is_deployed)
            VALUES (?, ?, ?, ?, ?, 0, 0)
        """, (new_version, base_version or 'base', now, description, json.dumps(new_params, ensure_ascii=False)))

        # 寫入變更記錄
        for c in change_records:
            cur.execute("""
                INSERT INTO param_changes (version, param_key, old_value, new_value, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_version, c['param_key'], c['old_value'], c['new_value'], c['reason'], now))

        conn.commit()
        conn.close()

        # 同時儲存 JSON 檔案
        version_file = os.path.join(self.param_versions_dir, f"{new_version}.json")
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump({
                'version': new_version,
                'parent_version': base_version,
                'created_at': now,
                'description': description,
                'params': new_params,
                'changes': change_records,
            }, f, ensure_ascii=False, indent=2)

        print(f"[ParamEvolution] New param version created: {new_version}")
        return new_version, new_params

    # ──── 比較兩個版本 ────
    def compare_versions(self, v1, v2):
        """比較兩個版本的參數差異"""
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()

        result = {}
        for ver in [v1, v2]:
            cur.execute("SELECT params_json, performance_json, description FROM param_versions WHERE version = ?", (ver,))
            row = cur.fetchone()
            if row:
                result[ver] = {
                    'params': json.loads(row[0]),
                    'performance': json.loads(row[1]) if row[1] else None,
                    'description': row[2],
                }
        conn.close()

        if not result or v1 not in result or v2 not in result:
            print(f"[ParamEvolution] 版本 {v1} 或 {v2} 找不到")
            return None

        p1 = result[v1]['params']
        p2 = result[v2]['params']

        all_keys = set(p1.keys()) | set(p2.keys())
        diffs = []
        for k in sorted(all_keys):
            if p1.get(k) != p2.get(k):
                diffs.append({
                    'param': k,
                    f'{v1}_value': p1.get(k),
                    f'{v2}_value': p2.get(k),
                })

        return {
            'version1': v1,
            'version2': v2,
            'diffs': diffs,
            'performance1': result[v1]['performance'],
            'performance2': result[v2]['performance'],
        }

    # ──── 更新版本績效 ────
    def update_version_performance(self, version, perf_data):
        """更新某版本的績效記錄（由 backtest 或 live 結果寫入）"""
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()
        cur.execute(
            "UPDATE param_versions SET performance_json = ? WHERE version = ?",
            (json.dumps(perf_data, ensure_ascii=False), version)
        )
        conn.commit()
        conn.close()
        print(f"[ParamEvolution] Updated {version} performance: {perf_data}")

    # ──── 部署新版本（勝出則部署） ────
    def deploy_if_better(self, new_version, threshold=0.05):
        """
        比對新版本與當前活躍版本
        若新版本勝出則設為活躍並部署
        """
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()

        # 取得新版本績效
        cur.execute("SELECT performance_json FROM param_versions WHERE version = ?", (new_version,))
        row = cur.fetchone()
        if not row or not row[0]:
            print(f"[ParamEvolution] {new_version} 尚無績效資料，無法部署")
            conn.close()
            return False

        new_perf = json.loads(row[0])

        # 取得當前活躍版本
        cur.execute("SELECT version, performance_json FROM param_versions WHERE is_active = 1 LIMIT 1")
        row_active = cur.fetchone()

        if row_active and row_active[1]:
            cur_perf = json.loads(row_active[1])
            # 比較 win_rate 或 avg_return
            new_win = new_perf.get('win_rate', 0)
            cur_win = cur_perf.get('win_rate', 0)
            new_ret = new_perf.get('avg_return', 0)
            cur_ret = cur_perf.get('avg_return', 0)

            # 新版本必須在兩個指標都進步才部署
            if new_win < cur_win - threshold and new_ret < cur_ret - threshold:
                print(f"[ParamEvolution] REJECTED: {new_version} performance worse than current, no deploy")
                conn.close()
                return False

        # 部署：新版本設為活躍
        cur.execute("UPDATE param_versions SET is_active = 0 WHERE is_active = 1")
        cur.execute("UPDATE param_versions SET is_active = 1, is_deployed = 1 WHERE version = ?", (new_version,))
        conn.commit()
        conn.close()

        # 更新 unified_strategy_config.json
        cur.execute = None  # reset
        version_file = os.path.join(self.param_versions_dir, f"{new_version}.json")
        if os.path.exists(version_file):
            with open(version_file, encoding='utf-8') as f:
                ver_data = json.load(f)
            with open(self.default_params_file, 'w', encoding='utf-8') as f:
                json.dump(ver_data['params'], f, ensure_ascii=False, indent=2)

        print(f"[ParamEvolution] DEPLOYED: {new_version} is now the active version")
        return True

    # ──── 列出所有版本 ────
    def list_versions(self):
        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()
        cur.execute("""
            SELECT version, parent_version, created_at, description, is_active, is_deployed, performance_json
            FROM param_versions ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()

        versions = []
        for r in rows:
            perf = json.loads(r[6]) if r[6] else None
            versions.append({
                'version': r[0],
                'parent': r[1],
                'created_at': r[2],
                'description': r[3],
                'is_active': bool(r[4]),
                'is_deployed': bool(r[5]),
                'performance': perf,
            })
        return versions

    # ──── 產出進化報告 ────
    def generate_evolution_report(self, version):
        report_path = os.path.join(
            os.path.dirname(self.param_versions_dir),
            'reports',
            f"tina_param_evolution_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        conn = sqlite3.connect(self.versions_db)
        cur = conn.cursor()
        cur.execute("SELECT params_json, performance_json, description, parent_version, created_at FROM param_versions WHERE version = ?", (version,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        params = json.loads(row[0])
        perf = json.loads(row[1]) if row[1] else None

        md = f"""# Tina 參數進化報告

**版本**: {version}  
**父版本**: {row[3]}  
**建立時間**: {row[4]}  
**說明**: {row[2]}

---

## 📊 參數內容

| 參數 | 數值 |
|------|------|
"""
        for k, v in sorted(params.items()):
            md += f"| {k} | {v} |\n"

        if perf:
            md += f"""
---

## 📈 績效表現

| 指標 | 數值 |
|------|------|
| 勝率 | {perf.get('win_rate', 'N/A')} |
| 平均損益 | {perf.get('avg_return', 'N/A')} |
| 總交易次數 | {perf.get('total_trades', 'N/A')} |
| 最大虧損 | {perf.get('max_loss', 'N/A')} |
| Sharpe | {perf.get('sharpe', 'N/A')} |

---

*由 Tina 量化系統 v3.12 自動產生 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        else:
            md += "\n\n_尚無績效資料_\n"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"[ParamEvolution] Evolution report saved: {report_path}")
        return report_path


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evo = ParamEvolution(base_dir=base)

    print("=== Existing versions ===")
    for v in evo.list_versions():
        print(f"  {v['version']} | {v['description']} | active={v['is_active']}")

    # Test: create new version
    new_ver, new_params = evo.create_new_version(
        base_version=None,
        changes={'entry_rsi_max': 40, 'max_hold_days': 15},
        description='Adjusted RSI entry max and max hold days per strategy review'
    )
    print(f"\nNew version: {new_ver}")
    print(f"New params: {new_params}")

    # Generate report
    evo.generate_evolution_report(new_ver)