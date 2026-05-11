"""
yfinance.db 每週清理腳本
保留：每檔最近 2年（730天）的 OHLCV 數據
刪除：過舊的歷史數據
"""
import sqlite3, os, logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs\yfinance_cleanup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('yfinance_cleanup')

DB_PATH = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db'
CUTOFF_DAYS = 730  # 保留最近2年
DRY_RUN = False  # 改 True 預覽不刪除

def main():
    if not os.path.exists(DB_PATH):
        logger.error(f"DB not found: {DB_PATH}")
        return

    size_before = os.path.getsize(DB_PATH) / (1024 * 1024)
    logger.info(f"=== yfinance.db Cleanup | Cutoff: {CUTOFF_DAYS} days | {'DRY RUN' if DRY_RUN else 'LIVE'} ===")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=CUTOFF_DAYS)).strftime('%Y-%m-%d')
    logger.info(f"Cutoff date: {cutoff_date}")

    # 統計即將刪除的資料
    cur.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE date < ?", (cutoff_date,))
    old_rows = cur.fetchone()[0]
    logger.info(f"Rows to delete (date < {cutoff_date}): {old_rows:,}")

    # 預覽即將刪除的 symbols
    cur.execute("""
        SELECT symbol, COUNT(*) as cnt, MIN(date), MAX(date)
        FROM daily_ohlcv
        WHERE date < ?
        GROUP BY symbol
        ORDER BY cnt DESC
        LIMIT 20
    """, (cutoff_date,))
    old_symbols = cur.fetchall()
    logger.info(f"Symbols with old data (top 20):")
    for sym, cnt, mn, mx in old_symbols:
        logger.info(f"  {sym}: {cnt} rows ({mn} ~ {mx})")

    if DRY_RUN:
        logger.info("[DRY RUN] 預覽完成，不刪除任何資料")
        conn.close()
        return

    # 執行刪除
    logger.info("執行刪除...")
    cur.execute("DELETE FROM daily_ohlcv WHERE date < ?", (cutoff_date,))
    deleted = cur.rowcount
    logger.info(f"已刪除 {deleted:,} 行")
    conn.commit()

    # VACUUM 釋放空間
    logger.info("VACUUM 壓縮資料庫...")
    conn.execute("VACUUM")
    conn.commit()

    size_after = os.path.getsize(DB_PATH) / (1024 * 1024)
    logger.info(f"資料庫大小: {size_before:.1f}MB -> {size_after:.1f}MB (節省 {size_before - size_after:.1f}MB)")

    # 驗證
    cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
    remaining = cur.fetchone()[0]
    cur.execute("SELECT MIN(date), MAX(date) FROM daily_ohlcv")
    date_range = cur.fetchone()
    logger.info(f"保留 rows: {remaining:,} | date range: {date_range[0]} ~ {date_range[1]}")

    conn.close()
    logger.info("=== Cleanup Done ===")

if __name__ == '__main__':
    main()