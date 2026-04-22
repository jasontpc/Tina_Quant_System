# utils/ - 通用工具模組

## 模組說明

| 函數 | 說明 |
|:-----|:-----|
| `get_trade_logger()` | 取得交易紀錄日誌器 |
| `get_system_logger()` | 取得系統錯誤日誌器 |
| `get_api_logger()` | 取得 API 呼叫日誌器 |
| `get_twse_trading_days()` | 取得台股交易日 |
| `calc_rsi()` | 計算 RSI 指標 |
| `calc_atr()` | 計算 ATR 指標 |
| `calc_ma()` | 計算移動平均 |
| `calc_slope()` | 計算均線斜率 |
| `send_telegram_message()` | 發送 Telegram 訊息 |
| `send_line_notify()` | 發送 LINE Notify |
| `load_json()` / `save_json()` | JSON 檔案讀寫 |
| `ensure_dir()` | 確保目錄存在 |

## 使用範例

```python
from utils import get_trade_logger, calc_rsi, send_telegram_message

# 取得日誌器
logger = get_trade_logger()
logger.info("買入 3017 @ 2560")

# 計算技術指標
rsi = calc_rsi(prices, period=14)

# 發送通知
send_telegram_message("🎯 進場信號：3017")
```

## 日誌範例

```python
from utils import get_system_logger

logger = get_system_logger()
logger.error("API 逾時")
logger.critical("資料庫連線失敗")
```
