# -*- coding: utf-8 -*-
"""
Telegram 通知模組
當 Nana v5.0 發出進場信號時，立即推播到 Telegram

使用方法:
    from telegram_notifier import send_entry_signal

    send_entry_signal(
        code="2330",
        name="台積電",
        score=85,
        rsi=42.5,
        reason="均線黃金交叉 + RSI 突破 50"
    )

或非同步模式:
    import asyncio
    from telegram_notifier import send_entry_signal_async
    asyncio.run(send_entry_signal_async(...))
"""

import os
import sys
import logging
import asyncio
from datetime import datetime

# === 載入環境變數 ===
def _load_env():
    """載入 .env 環境變數"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

_load_env()

# === 日誌設定 ===
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger('telegram')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, 'telegram.log'),
        encoding='utf-8'
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# === 讀取設定 ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Jo 的 Telegram ID
DEFAULT_CHAT_ID = '1616824689'

# === 嘗試載入 python-telegram-bot v22+ (async) ===
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
    IS_ASYNC = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None
    TelegramError = Exception
    IS_ASYNC = False


def _build_message(code, name, score, rsi, reason):
    """建立格式化訊息"""
    emoji = "🔥" if score >= 80 else "✅" if score >= 70 else "⚠️"
    tag = "強烈進場" if score >= 80 else "進場" if score >= 70 else "觀察"

    return (
        f"🎯 *Nana v5.0 進場信號*\n\n"
        f"{emoji} *{tag}* | Score: *{score}*\n\n"
        f"📈 {code} {name}\n"
        f"📊 RSI: {rsi:.1f}\n"
        f"💡 原因: {reason}\n\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


async def _send_async(bot, chat_id, text):
    """非同步發送"""
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')


def send_entry_signal(code, name, score, rsi, reason, chat_id=None):
    """
    發送進場信號到 Telegram（同步包裝）

    參數:
        code: 股票代碼
        name: 股票名稱
        score: 評分 (0-100)
        rsi: RSI 數值
        reason: 進場原因
        chat_id: 目標 Chat ID (預設 Jo 的 ID)
    """
    target_chat_id = chat_id or TELEGRAM_CHAT_ID or DEFAULT_CHAT_ID

    if not TELEGRAM_AVAILABLE:
        logger.warning("python-telegram-bot 未安裝")
        return False

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
        logger.warning("TELEGRAM_BOT_TOKEN 未設定，跳過通知")
        return False

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
    except Exception as e:
        logger.error(f"建立 Bot 失敗: {e}")
        return False

    message = _build_message(code, name, score, rsi, reason)

    try:
        if IS_ASYNC:
            asyncio.run(_send_async(bot, target_chat_id, message))
        else:
            bot.send_message(chat_id=target_chat_id, text=message, parse_mode='Markdown')

        logger.info(f"Telegram 進場信號發送成功: {code} {name} (score={score})")
        return True

    except TelegramError as e:
        logger.error(f"Telegram 發送失敗: {e}")
        return False
    except Exception as e:
        logger.error(f"發送失敗: {e}")
        return False


def send_test_message(chat_id=None):
    """發送測試訊息，驗證 Bot 連線"""
    return send_entry_signal(
        code="TEST",
        name="測試訊息",
        score=75,
        rsi=50.0,
        reason="Nana Telegram 模組測試",
        chat_id=chat_id
    )


def send_daily_summary(stocks, chat_id=None):
    """
    發送每日監控摘要

    參數:
        stocks: [{code, name, score, rsi, reason}, ...]
        chat_id: 目標 Chat ID
    """
    target_chat_id = chat_id or TELEGRAM_CHAT_ID or DEFAULT_CHAT_ID

    if not TELEGRAM_AVAILABLE or not TELEGRAM_BOT_TOKEN:
        return False

    if not stocks:
        return False

    lines = ["📊 *每日監控摘要*\n\n"]

    for s in stocks:
        emoji = "🔥" if s['score'] >= 80 else "✅" if s['score'] >= 70 else "⚠️"
        lines.append(
            f"{emoji} {s['code']} {s['name']} | "
            f"Score: {s['score']} | RSI: {s.get('rsi', 'N/A')}\n"
            f"   💡 {s.get('reason', '')}\n\n"
        )

    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        message = ''.join(lines)

        if IS_ASYNC:
            asyncio.run(_send_async(bot, target_chat_id, message))
        else:
            bot.send_message(chat_id=target_chat_id, text=message, parse_mode='Markdown')

        logger.info(f"每日摘要發送成功 ({len(stocks)} 檔)")
        return True
    except TelegramError as e:
        logger.error(f"每日摘要發送失敗: {e}")
        return False
    except Exception as e:
        logger.error(f"每日摘要發送失敗: {e}")
        return False


if __name__ == '__main__':
    print("Telegram Notifier 測試")
    print(f"Bot Token: {'已設定' if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != 'your_telegram_bot_token_here' else '未設定'}")
    print(f"Chat ID: {TELEGRAM_CHAT_ID or DEFAULT_CHAT_ID}")

    result = send_test_message()
    if result:
        print("測試結果: 成功")
    else:
        print("測試結果: 失敗 (請確認 Bot Token 已設定)")
