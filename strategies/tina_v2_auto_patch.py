"""
Tina v2 Auto Patch 策略
=========================
自動修正版策略，基於 2026-05-02 的市場分析

修改內容：
  - entry_rsi_min: 25（原30）
  - entry_rsi_max: 55（原65）
  - exit_rsi_min:  60（維持）
  - exit_rsi_max:  80（維持）

觸發原因：市場環境分析後自動修正
驗證狀態：待回測驗證

Author: Tina AI
Date: 2026-05-02 12:00
"""

class TinaV2AutoPatch:
    """Tina v2 自動修正策略"""

    VERSION = 2
    CREATED = "2026-05-02T12:00:00"

    # ===== 策略參數（自動修正後的新值）=====
    ENTRY_RSI_MIN = 25
    ENTRY_RSI_MAX = 55
    EXIT_RSI_MIN  = 60
    EXIT_RSI_MAX  = 80

    # 停損停利
    STOP_LOSS_PCT   = -8.0
    TAKE_PROFIT_PCT = 15.0

    @classmethod
    def get_params(cls):
        return {
            "version": cls.VERSION,
            "entry_rsi_min": cls.ENTRY_RSI_MIN,
            "entry_rsi_max": cls.ENTRY_RSI_MAX,
            "exit_rsi_min": cls.EXIT_RSI_MIN,
            "exit_rsi_max": cls.EXIT_RSI_MAX,
            "stop_loss_pct": cls.STOP_LOSS_PCT,
            "take_profit_pct": cls.TAKE_PROFIT_PCT,
        }

    @classmethod
    def should_entry(cls, rsi, price, volume):
        """進場判斷：RSI 在 25-55 之間（原：30-65）"""
        if cls.ENTRY_RSI_MIN <= rsi <= cls.ENTRY_RSI_MAX:
            return True
        return False

    @classmethod
    def should_exit(cls, rsi, price, unrealized_pnl):
        """出场判斷"""
        if rsi >= cls.EXIT_RSI_MAX:
            return True
        if rsi <= cls.EXIT_RSI_MIN:
            return True
        if unrealized_pnl >= cls.TAKE_PROFIT_PCT:
            return True
        if unrealized_pnl <= cls.STOP_LOSS_PCT:
            return True
        return False

    @classmethod
    def get_strategy_name(cls):
        return "tina_v2_auto_patch"


def get_strategy():
    return TinaV2AutoPatch


if __name__ == "__main__":
    s = TinaV2AutoPatch
    print("Tina v2 Auto Patch Strategy")
    print(f"Entry RSI: {s.ENTRY_RSI_MIN}-{s.ENTRY_RSI_MAX}")
    print(f"Exit RSI:  {s.EXIT_RSI_MIN}-{s.EXIT_RSI_MAX}")
    print(f"Stop Loss: {s.STOP_LOSS_PCT}%")
    print(f"Take Profit: {s.TAKE_PROFIT_PCT}%")