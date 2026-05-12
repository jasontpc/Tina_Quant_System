# -*- coding: utf-8 -*-
"""
ray_token_tracker.py — 每5小時追蹤 MiniMax Token 用量
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "sk-cp-d1DZZxzGpsijgC4bJaTl6_mrDJp376z9iwXyRnXRq8wYZOXBKRqFL2YVSE6nVwJ0yi14yjhh6fPCwvtLT5J53KNdfLMSJgLIjfcCqTHpja08L58oTe0wztg"

def get_token_report():
    try:
        import requests
        resp = requests.get(
            "https://www.minimax.io/v1/token_plan/remains",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=15
        )
        data = resp.json()

        items = data.get("model_remains", [])
        lines = ["📊 MiniMax Token 用量追蹤\n"]

        for item in items:
            name = item.get("model_name", "N/A")
            weekly_total = item.get("current_weekly_total_count", 0)
            weekly_used = item.get("current_weekly_usage_count", 0)
            weekly_remains = item.get("weekly_remains_time", 0)

            if weekly_total > 0:
                pct = (weekly_used / weekly_total) * 100
                lines.append(f"• {name}: {weekly_used}/{weekly_total} ({pct:.1f}%)")
            elif weekly_remains > 0:
                lines.append(f"• {name}: 無配額限制，庫存 {weekly_remains:,}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Token 追蹤失敗: {str(e)}"

if __name__ == "__main__":
    print(get_token_report())