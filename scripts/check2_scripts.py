# Full health check step 2: critical scripts
import os, glob
from pathlib import Path

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
SCRIPTS = WORKSPACE / "scripts"

critical = {
    'tw_institutional.py': 'TW 法人',
    'macro_institutional_fetcher.py': 'DB寫入法人',
    'fetch_margin_data.py': 'Margin',
    'maggy_db_update.py': 'Maggy',
    'backfill_rsi.py': 'RSI Backfill',
    'ray_etf_dca.py': 'Ray DCA',
    'ray_dca_longterm.py': 'Ray DCA長線',
    'etf_value_screener.py': 'Ray篩選',
    'dca_backtest.py': 'DCA回測',
    'tina_brain_monitor.py': '健康檢查',
    'tina_cron_optimizer.py': 'Cron優化',
    'tina_system_sop_health.py': 'SOP',
    'fix_brain_alerts.py': '警報修復',
    'full_health_check.py': '全健檢',
    'fetch_margin_finmind.py': 'Margin FinMind',
    'institutional_flow_analyzer.py': '法人分析',
}
for script, label in critical.items():
    path = SCRIPTS / script
    tag = 'OK' if path.exists() else 'MISSING'
    print(f"  [{tag}] {script} ({label})")

# Check db size
DATA = WORKSPACE / "data"
print("\nDB size check: (first 15 DBs)")
for db in sorted(DATA.glob("*.db"))[:15]:
    size = db.stat().st_size
    tag = 'ZERO' if size == 0 else ('BIG' if size > 1024*1024 else ('MED' if size > 1024 else 'OK'))
    print(f"  [{tag}] {db.name}: {size:,} bytes")