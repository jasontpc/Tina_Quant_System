"""
Tina v1 原始策略（保留版）
==========================
這是 Tina 量化系統的原始基礎策略，不應被修改。
所有自動修正版本應另存為 tina_v{N}_auto_patch.py

Author: Tina AI
Date: 2026-05-02
"""

class TinaV1Base:
    """Tina v1 原始策略"""

    VERSION = 1
    CREATED = "2026-05-02"

    # ===== 原始策略參數 =====
    ENTRY_RSI_MIN = 30
    ENTRY_RSI_MAX = 65
    EXIT_RSI_MIN  = 60
    EXIT_RSI_MAX  = 80

    # 停損停利
    STOP_LOSS_PCT   = -10.0
    TAKE_PROFIT_PCT = 20.0

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
        """進場判斷：RSI 在 30-65 之間"""
        if cls.ENTRY_RSI_MIN <= rsi <= cls.ENTRY_RSI_MAX:
            return True
        return False

    @classmethod
    def should_exit(cls, rsi, price, unrealized_pnl):
        """出场判斷"""
        if rsi >= cls.EXIT_RSI_MAX:
            return True
        if unrealized_pnl <= cls.STOP_LOSS_PCT:
            return True
        if unrealized_pnl >= cls.TAKE_PROFIT_PCT:
            return True
        return False

    @classmethod
    def get_strategy_name(cls):
        return "tina_v1_base"


def get_strategy():
    return TinaV1Base


if __name__ == "__main__":
    s = TinaV1Base
    print("Tina v1 Base Strategy")
    print(f"Entry RSI: {s.ENTRY_RSI_MIN}-{s.ENTRY_RSI_MAX}")
    print(f"Exit RSI:  {s.EXIT_RSI_MIN}-{s.EXIT_RSI_MAX}")
    print(f"Stop Loss: {s.STOP_LOSS_PCT}%")
    print(f"Take Profit: {s.TAKE_PROFIT_PCT}%")