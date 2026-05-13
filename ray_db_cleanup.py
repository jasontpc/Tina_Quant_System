# -*- coding: utf-8 -*-
"""
ray_db_cleanup.py — 清理髒數據 + 腳本健康度檢查 + DB 更新時間
"""

import sys, os, sqlite3, time, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = "ray_wisdom.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) or "."

print("=" * 60)
print("Ray 系統清理與健康度檢查")
print(f"時間：{time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

# ============================================================
# 1. 資料庫清理
# ============================================================

print("【1. 資料庫清理】")
print()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 檢查各表格數據
tables = ['wisdom_logs', 'wisdom_corrections', 'backtest_reports', 'signals_log', 'daily_performance']

print("  表格狀態：")
for table in tables:
    c.execute(f"SELECT COUNT(*) FROM {table}")
    count = c.fetchone()[0]
    c.execute(f"SELECT MAX(created_at) FROM {table}" if 'created_at' in [col[1] for col in c.execute(f"PRAGMA table_info({table})").fetchall()] else f"SELECT MAX(id) FROM {table}")
    last = c.fetchone()[0]
    print(f"    {table}: {count} 筆 | 最新: {last}")

# 清理無效資料
print()
print("  清理項目：")

# wisdom_logs: 清理 passed=1 但 Sharpe < 0 的異常
c.execute("SELECT COUNT(*) FROM wisdom_logs WHERE passed=1 AND (SELECT sharpe_ratio FROM backtest_reports WHERE id=wisdom_logs.backtest_id) < 0")
anomaly = c.fetchone()[0]
if anomaly > 0:
    print(f"    ⚠️  異常記錄: {anomaly} 筆（已標記但保留）")
else:
    print(f"    ✅ 無異常記錄")

# wisdom_corrections: 清理 symbol='UNKNOWN' 且 confidence=0
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE symbol='UNKNOWN' AND confidence=0")
bad_corr = c.fetchone()[0]
if bad_corr > 0:
    c.execute("DELETE FROM wisdom_corrections WHERE symbol='UNKNOWN' AND confidence=0")
    conn.commit()
    print(f"    🗑️  已刪除 {bad_corr} 筆無效修正（symbol=UNKNOWN, conf=0）")
else:
    print(f"    ✅ 無效修正已清理")

# backtest_reports: 清理 Sharpe < 0 且 passed=1 的矛盾記錄
c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio < 0 AND passed=1")
矛盾 = c.fetchone()[0]
if 矛盾 > 0:
    c.execute("UPDATE backtest_reports SET passed=0 WHERE sharpe_ratio < 0 AND passed=1")
    conn.commit()
    print(f"    ⚠️  已修正 {矛盾} 筆矛盾記錄（Sharpe<0 但 passed=1）")
else:
    print(f"    ✅ 無矛盾記錄")

# signals_log: 清理 score=0 且 tag='NEUT' 的空訊號
c.execute("SELECT COUNT(*) FROM signals_log WHERE score=0 AND signal_tag='NEUT'")
empty_sig = c.fetchone()[0]
if empty_sig > 0:
    c.execute("DELETE FROM signals_log WHERE score=0 AND signal_tag='NEUT'")
    conn.commit()
    print(f"    🗑️  已刪除 {empty_sig} 筆空訊號")
else:
    print(f"    ✅ 無空訊號")

# 檢查最後更新時間
print()
print("  【最後更新時間】")
for table in tables:
    try:
        c.execute(f"SELECT MAX(created_at) FROM {table}")
        last_time = c.fetchone()[0]
        if last_time:
            # 嘗試解析時間
            try:
                dt = time.strptime(str(last_time), '%Y-%m-%d %H:%M:%S')
                diff = time.time() - time.mktime(dt)
                mins = int(diff / 60)
                hours = int(mins / 60)
                days = int(hours / 24)
                if days > 0:
                    age = f"{days} 天前"
                elif hours > 0:
                    age = f"{hours} 小時前"
                elif mins > 0:
                    age = f"{mins} 分鐘前"
                else:
                    age = "剛更新"
                print(f"    {table}: {last_time} ({age})")
            except:
                print(f"    {table}: {last_time}")
        else:
            print(f"    {table}: 無數據")
    except Exception as e:
        print(f"    {table}: 無法讀取 ({e})")

conn.close()

# ============================================================
# 2. 腳本健康度檢查
# ============================================================

print()
print("【2. 腳本健康度檢查】")
print()

scripts = {
    # 核心腳本
    "ray_brain.py": "大腦協調",
    "ray_engine.py": "回測引擎",
    "ray_data_center.py": "資料中心",
    "ray_evolution.py": "自主學習",
    "ray_retriever_v2.py": "RAG 檢索",
    "ray_nl2code.py": "JSON 驗證",
    # 自動化腳本
    "tina_daily_self_correct.py": "每日修正",
    "dynamic_modelfile_generator.py": "Modelfile 更新",
    "ray_distiller_auto.py": "自動蒸餾",
    "ray_integrity_booster.py": "三維優化",
    "ray_expert_modules.py": "專家模組",
    # 健康檢查
    "tina_health_check.py": "健康檢查",
    "qwen_defect_review.py": "缺陷檢討",
}

all_healthy = True
for fname, desc in scripts.items():
    fpath = os.path.join(SCRIPT_DIR, fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        mtime = os.path.getmtime(fpath)
        age_days = (time.time() - mtime) / 86400
        status = "✅" if size > 100 else "⚠️"
        if size < 100:
            all_healthy = False
        print(f"  {status} {fname}（{desc}）: {size:,} bytes | {age_days:.1f} 天前")
    else:
        print(f"  ❌ {fname}（{desc}）: 缺失")
        all_healthy = False

print()
print(f"  腳本健康度：{'✅ 健康' if all_healthy else '⚠️ 有問題'}")

# ============================================================
# 3. Cron Jobs 狀態
# ============================================================

print()
print("【3. Cron Jobs 狀態】")

try:
    from openclaw_settings import cron_jobs
    active = [j for j in cron_jobs if j.get('enabled', True)]
    print(f"  總 Jobs: {len(cron_jobs)} | 啟用: {len(active)}")
except:
    print("  Cron Jobs: 無法讀取（可能需從外部查詢）")

# ============================================================
# 4. 系統摘要
# ============================================================

print()
print("【4. 系統摘要】")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=0')
failed = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0')
decayed = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
high_conf = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0.8')
good_strat = c.fetchone()[0]

print(f"  wisdom_logs: {failed} 失敗 / {decayed} 衰減")
print(f"  wisdom_corrections: {high_conf} 高信心")
print(f"  backtest_reports: {good_strat} 策略 Sharpe>0.8")

conn.close()

print()
print("=" * 60)
print("清理完成 ✅")
print("=" * 60)