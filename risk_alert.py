# -*- coding: utf-8 -*-
"""
Tina 風險警示系統
功能：
  1. 監控 TWII RSI（> 85 = 紅色警示）
  2. 監控各系統持倉狀態
  3. 自動記錄警示歷史
  4. 產出每日風險報告
"""

import sys
import os
import json
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 嘗試 import yfinance
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ========== 警示等級定義 ==========
def get_alert_level(rsi):
    if rsi is None:
        return "UNKNOW", "⚪", "無法取得 RSI 資料"
    if rsi > 93:
        return "BLACK", "⚫", f"TWII RSI {rsi} 極端過熱（>93），歷史上僅見於重大頭部"
    if rsi > 85:
        return "RED", "🔴", f"TWII RSI {rsi} 進入紅色警示區（>85）"
    if rsi >= 75:
        return "YELLOW", "🟡", f"TWII RSI {rsi} 進入黃色警示區（75-85）"
    return "GREEN", "🟢", f"TWII RSI {rsi} 正常區間（<75）"

# ========== 建議行動 ==========
def get_action(level, rsi):
    if level == "BLACK":
        return "立即減倉至 30% 以下，停損所有短線部位"
    if level == "RED":
        return "減倉至 50%，提高停損紀律，避免追高"
    if level == "YELLOW":
        return "謹慎偏多，設定停損，別重倉"
    return "正常操作，順勢而為"

# ========== 讀取持倉狀態 ==========
def get_positions():
    """讀取 positions_report.json 取得持倉狀態"""
    base_dir = Path(__file__).parent
    pos_file = base_dir / "teams" / "reports" / "positions_report.json"
    if pos_file.exists():
        try:
            with open(pos_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"positions": [], "total_value": 0, "cash_ratio": 0}

# ========== 抓 TWII RSI ==========
def get_twii_rsi():
    if not HAS_YF:
        return None
    try:
        twii = yf.Ticker("^TWII")
        hist = twii.history(period="2mo")
        if len(hist) < 15:
            return None
        close = hist['Close']
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2)
    except Exception:
        return None

# ========== 讀取歷史警示 ==========
def load_history():
    base_dir = Path(__file__).parent
    hist_file = base_dir / "teams" / "reports" / "risk_alert_history.json"
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

# ========== 主程式 ==========
def main():
    base_dir = Path(__file__).parent
    report_dir = base_dir / "teams" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "risk_alert_report.json"

    # 抓 RSI
    rsi = get_twii_rsi()

    # 警示等級
    level, icon, desc = get_alert_level(rsi)

    # 建議行動
    action = get_action(level, rsi)

    # 持倉狀態
    positions = get_positions()

    # 歷史記錄
    history = load_history()
    if rsi is not None and level in ("RED", "BLACK", "YELLOW"):
        history_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "icon": icon,
            "rsi": rsi,
            "action": action
        }
        history.append(history_entry)
        # 只留最近 100 筆
        history = history[-100:]

    # 寫入歷史
    hist_path = report_dir / "risk_alert_history.json"
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 產出報告
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "twii_rsi": rsi,
        "alert_level": level,
        "alert_icon": icon,
        "alert_desc": desc,
        "action": action,
        "positions_summary": {
            "total_positions": len(positions.get("positions", [])),
            "cash_ratio": positions.get("cash_ratio", 0)
        },
        "last_alerts": history[-5:]
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 風險警示報告已寫入: {report_path}")
    print(f"   等級: {icon} {level}")
    print(f"   TWII RSI: {rsi}")
    print(f"   描述: {desc}")
    print(f"   行動: {action}")

if __name__ == "__main__":
    main()