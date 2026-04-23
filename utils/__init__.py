"""
utils/ - Tina Quant System 通用工具模組
"""

import os
import json
import logging
from datetime import datetime, timedelta

# === Position Sizing ===
from .position_sizing import PositionSizer, calc_kelly_fractional, kelly_to_shares

# === 日誌模組 ===

def setup_logger(name, log_file, level=logging.INFO):
    """設定單一日誌器"""
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger

def get_trade_logger():
    """交易紀錄日誌"""
    os.makedirs('logs', exist_ok=True)
    return setup_logger('trade', 'logs/trade.log')

def get_system_logger():
    """系統錯誤日誌"""
    os.makedirs('logs', exist_ok=True)
    return setup_logger('system', 'logs/system.log')

def get_api_logger():
    """API 呼叫日誌"""
    os.makedirs('logs', exist_ok=True)
    return setup_logger('api', 'logs/api.log')

# === 日期工具 ===

def get_twse_trading_days(start_date, end_date):
    """
    取得台股交易日（排除週末與國定假日）
    簡易版：僅排除週末
    """
    days = []
    current = start_date
    while current <= end_date:
        # 0=週一, 5=週六, 6=週日
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days

def date_to_str(date, fmt='%Y-%m-%d'):
    """日期轉字串"""
    return date.strftime(fmt)

def str_to_date(date_str, fmt='%Y-%m-%d'):
    """字串轉日期"""
    return datetime.strptime(date_str, fmt)

# === 技術指標 ===

def calc_rsi(prices, period=14):
    """計算 RSI"""
    import numpy as np
    d = np.diff(prices)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    if al == 0:
        return 50
    return 100 - (100 / (1 + ag / al))

def calc_atr(high, low, close, period=14):
    """計算 ATR"""
    import numpy as np
    tr = [max(high[i]-low[i], 
              abs(high[i]-close[i-1]),
              abs(low[i]-close[i-1])) 
          for i in range(1, len(high))]
    return np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)

def calc_ma(prices, period=20):
    """計算移動平均"""
    import numpy as np
    return np.mean(prices[-period:])

def calc_slope(ma_series):
    """計算均線斜率"""
    import numpy as np
    if len(ma_series) < 5:
        return 0
    recent = list(ma_series[-5:])
    return (recent[-1] - recent[0]) / recent[0]

# === 通知模組 ===

def send_telegram_message(message, token=None, chat_id=None):
    """發送 Telegram 訊息"""
    import requests
    
    # 從環境變數讀取
    token = token or os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        return False, "缺少 token 或 chat_id"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    
    try:
        r = requests.post(url, data=data, timeout=10)
        return True, r.json()
    except Exception as e:
        return False, str(e)

def send_line_notify(message, token=None):
    """發送 LINE Notify 訊息"""
    import requests
    
    token = token or os.getenv('LINE_NOTIFY_TOKEN')
    if not token:
        return False, "缺少 LINE_NOTIFY_TOKEN"
    
    headers = {'Authorization': f'Bearer {token}'}
    data = {'message': message}
    
    try:
        r = requests.post('https://notify-api.line.me/api/notify', 
                         headers=headers, data=data, timeout=10)
        return True, r.json()
    except Exception as e:
        return False, str(e)

# === 通用工具 ===

def ensure_dir(path):
    """確保目錄存在"""
    os.makedirs(path, exist_ok=True)
    return path

def load_json(path):
    """讀取 JSON"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    """寫入 JSON"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 版本
__version__ = '1.1.0'