# -*- coding: utf-8 -*-
"""
Nana v1.0 Telegram 發送模組
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import pandas as pd
from datetime import datetime

def send_nana_telegram(token, chat_id, report_df, top_n=10):
    """
    發送 Nana v1.0 掃描報告至 Telegram
    """
    if report_df is None or len(report_df) == 0:
        message = "⚠️ *Nana v1.0 掃描報告*\n\n今日市場未達進場門檻。"
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 取 Top N
        top = report_df.head(top_n)
        
        message = f"📊 *Nana v1.0 今日波段掃描報告*\n"
        message += f"🗓 {today} | {len(report_df)} 檔已掃描\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Buy signals first
        buys = top[top['訊號'].str.contains('買進|⭐️', na=False)]
        watches = top[~top['訊號'].str.contains('買進|⭐️', na=False)]
        
        if len(buys) > 0:
            message += "🔥 *進場訊號*\n"
            for _, row in buys.iterrows():
                icon = "🔥" if "⭐️" in str(row['訊號']) else "✅"
                message += f"{icon} *{row['代號']}* | 總分: `{row['總分']}`\n"
                message += f"   💰 {row['價格']:.0f} | 法人 {row['法人分']} | 技術 {row['技術分']}\n"
                message += f"   RSI: {row['RSI']:.1f} | F天:{row['F天']} T天:{row['T天']}\n\n"
            message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if len(watches) > 0:
            message += "👀 *觀察名單*\n"
            for _, row in watches.head(5).iterrows():
                message += f"▫️ {row['代號']} | 總分 `{row['總分']}` | RSI {row['RSI']:.1f}\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━"
        message += "\n🤖 Nana v1.0 | Tina System"
    
    # 發送
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        else:
            print(f"❌ 發送失敗: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram 異常: {e}")
        return False

if __name__ == '__main__':
    # 測試
    import json
    with open('Tina_Quant_System/teams/nana/scan_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    # 讀取 token
    import os
    token = os.getenv('TG_TOKEN', '')
    chat_id = os.getenv('TG_CHAT_ID', '1616824689')
    
    if token:
        send_nana_telegram(token, chat_id, df)
    else:
        print('請設定 TG_TOKEN 環境變數')