# -*- coding: utf-8 -*-
"""
ray_expert_modules.py — 五大交易權威邏輯蒸餾
已整合至 Ray 大腦架構

專家模組：
1. Simons (HMM)     — 市場狀態切換
2. Connors (RSI2)   — 均值回歸超跌反彈
3. Taleb (Fat-tail) — 肥尾風險反脆弱
4. Thorp (Kelly)    — 凱利倉位管理
5. De Haeverpra (Meta-Labeling) — 二次校準
"""

import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# Expert 1: Simons 隱馬爾可夫模型 (HMM) 市場狀態切換
# ============================================================

SIMONS_HMM_PROMPT = """
【Simons HMM 市場狀態診斷】
當使用本模組時，必須先判斷當前市場狀態：

State 1: TRENDING (趨勢市場)
  特征：MA20 與 MA60 排列一致（多頭：上漲排列/空頭：下跌排列）
  策略：動能策略（MOMENTUM_60）優先，均值回歸次之
  風險：順勢但警惕反轉

State 2: RANGE (盤整市場)
  特征：MA20 穿越 MA60，價格在區間內震蕩
  策略：均值回歸策略（RSI2）優先，動能次之
  風險：區間突破失敗

State 3: VOLATILE (高波動市場)
  特征：ATR > 20日均值 1.5x，VIX > 25
  策略：縮減倉位，使用寬停損
  風險：假突破頻繁

【HMM 切換觸發】
  當 RSI 從 <30 快速反彈至 >50 → State 1 確認
  當 RSI 持續在 40-60 徘徊 → State 2 確認
  當 VIX 突然飆升 → State 3 警戒
"""

# ============================================================
# Expert 2: Connors RSI(2) 均值回歸
# ============================================================

CONNORS_RSI2_PROMPT = """
【Connors RSI2 均值回歸策略】

核心公式：
  RSI2 = 100 - 100 / (1 + RS)
  其中 RS = Avg(Gain) / Avg(Loss)，period = 2

【進場條件】（全部滿足）
  1. RSI2 < 20 → 超賣
  2. 價格 > EMA20 → 支撐確認
  3. MACD Hist > 0 → 動能向上
  4. 成交量 > 5日均量 → 確認

【出场條件】（任一滿足）
  1. RSI2 > 60 → 均值回歸完成
  2. 價格 < EMA20 → 支撐跌破
  3. 持有 > 5 交易日 → 時間衰減

【止損設定】
  • 積極：8%（RSI2 < 15 進場）
  • 標準：12%（RSI2 15-20 進場）
  • 寬鬆：15%（市場波動大）

【Connors 額外規則】
  • 連續下跌後的 RSI2 < 10 = 極度超賣 → 凱利倉位加倍
  • RSI2 在 20-30 之間震蕩 = 弱勢 → 觀望
  • 避免在重大新聞發布前進場
"""

# ============================================================
# Expert 3: Taleb 肥尾風險與反脆弱
# ============================================================

TALEB_FAT_TAIL_PROMPT = """
【Taleb 肥尾風險防禦】

核心原則：
  1. 不追求常態分布假設
  2. 不假設未來與過去相似
  3. 系統必須能從黑天鵝事件中獲益或存活

【峰度（Kurtosis）檢查】
  • Kurtosis > 3 → 警告：肥尾風險
  • Kurtosis > 5 → 拒絕：極度肥尾，放棄策略
  • Kurtosis < 0 → 警告：分布過度集中，小心假突破

【MDD 強化檢查】
  • MDD > 15% → Taleb 警告
  • MDD > 20% → 拒絕：超出反脆弱承受範圍
  • MDD > 30% → 系統性崩潰，不允許任何進場

【Sharpe 門檻（Taleb 版本）】
  • Sharpe < 0.5 → 尾部風險過高，拒絕
  • Sharpe 0.5-0.8 → 僅允許做多，不做空
  • Sharpe > 1.5 → 優秀：反脆弱正向不對稱

【反脆弱倉位計算】
  • 正向不對稱：潛在收益 >> 潛在損失
  • 當成功概率 > 60% 且收益/風險 > 2 → 凱利 * 0.5 進場
  • 當失敗歷史 > 3 次 → 降低倉位 50%
"""

# ============================================================
# Expert 4: Thorp 凱利公式與倉位管理
# ============================================================

THORP_KELLY_PROMPT = """
【Thorp 凱利公式倉位管理】

核心公式：
  Kelly % = WinRate / (1 - WinRate) * (AvgWin / AvgLoss)

簡化版：
  Kelly % = (2 * WinRate - 1) / AvgWinLossRatio

【Thorp 保守倉位表】
  | Kelly % | 實際倉位（半凱利）| 適用情境
  |--------|----------------|--------------
  | > 10%  | 5%            | 高信心趨勢
  | 5-10%  | 2.5-5%        | 標準動能
  | 1-5%   | 0.5-2.5%      | 均值回歸
  | < 1%   | 0%            | 拒絕進場

【最大倉位限制】
  • 單一標的：不得超過帳戶 20%
  • 單一方向：不得超過帳戶 30%
  • 所有倉位：不得超過帳戶 60%

【Thorp 止損規則】
  • ATR 止損：2 * ATR（標準）
  • ATR 止損：1.5 * ATR（緊縮）
  • ATR 止損：3 * ATR（寬鬆，僅波動市場）

【凱利調整觸發條件】
  • 連續 3 次失敗 → 降低倉位 25%
  • 連續 5 次失敗 → 降低倉位 50%
  • 連續 10 次失敗 → 系統性檢討，暫停交易
"""

# ============================================================
# Expert 5: De Haeverpra Meta-Labeling 二次校準
# ============================================================

META_LABELING_PROMPT = """
【Meta-Labeling 二次校準】

原理：
  對 1.5B 產出的訊號進行第二層過濾，提升勝率

【Meta-Labeling 二維矩陣】

         1.5B 訊號: BUY    |    1.5B 訊號: SELL
         -----------------|----------------------
RSI2<20  → META: STRONG_BUY  | META: WATCH
RSI2>70  → META: WATCH       | META: STRONG_SELL
RSI2中性 → META: HOLD        | META: HOLD

【Meta-Labeling 額外過濾器】
  1. VIX > 25 → 所有 BUY 信號降級
  2. TWII RSI > 75 → 美股 BUY 信號降級（避免系統風險）
  3. 法人賣超 > 連續 3 天 → 延長觀察期
  4. 成交量驟降 > 50% → 謹慎進場

【Meta-Labeling 信心調整】
  原始 confidence 乘以 meta_factor：
  • STRONG_BUY: meta_factor = 1.2
  • BUY: meta_factor = 1.0
  • HOLD: meta_factor = 0.7
  • WATCH: meta_factor = 0.5
  • STRONG_SELL: meta_factor = 0.3

【最終信心度計算】
  Final_Conf = Base_Conf * Meta_Factor
  • Final_Conf >= 0.7 → 執行
  • 0.5 <= Final_Conf < 0.7 → 觀望，記錄
  • Final_Conf < 0.5 → 拒絕，不記錄
"""

# ============================================================
# 專家系統工廠
# ============================================================

EXPERT_MODULES = {
    "SIMONS_HMM": {
        "name": "Simons HMM 市場狀態",
        "prompt": SIMONS_HMM_PROMPT,
        "layer": "Layer 3 (7B)",
        "trigger": "市場狀態診斷 / 趨勢vs盤整判斷",
    },
    "CONNORS_RSI2": {
        "name": "Connors RSI2 均值回歸",
        "prompt": CONNORS_RSI2_PROMPT,
        "layer": "Layer 1 & 2 (1.5B)",
        "trigger": "RSI2 < 30 或 RSI2 > 70",
    },
    "TALEB_FAT_TAIL": {
        "name": "Taleb 肥尾風險",
        "prompt": TALEB_FAT_TAIL_PROMPT,
        "layer": "Math Gate (Layer 1)",
        "trigger": "Kurtosis > 3 / MDD > 15% / Sharpe < 0.8",
    },
    "THORP_KELLY": {
        "name": "Thorp 凱利倉位",
        "prompt": THORP_KELLY_PROMPT,
        "layer": "Layer 3 (7B)",
        "trigger": "倉位計算 / 止損設定",
    },
    "META_LABELING": {
        "name": "Meta-Labeling 二次校準",
        "prompt": META_LABELING_PROMPT,
        "layer": "Layer 3 (7B)",
        "trigger": "所有訊號產出後二次過濾",
    },
}

def get_expert_prompt(expert_name):
    """根據專家名稱獲取對應的 System Instruction"""
    if expert_name in EXPERT_MODULES:
        return EXPERT_MODULES[expert_name]["prompt"]
    return ""

def get_all_experts_prompt():
    """獲取所有專家模組的合併 prompt"""
    parts = ["【Ray 大師專家系統】"]
    for key, module in EXPERT_MODULES.items():
        parts.append(f"\n{'='*50}\n{module['name']}\n{'='*50}\n{module['prompt']}")
    return "\n".join(parts)

def get_expert_for_trigger(trigger_type):
    """根據觸發類型返回對應的專家模組"""
    mapping = {
        "RSI2_OVERSOLD": "CONNORS_RSI2",
        "RSI2_OVERBOUGHT": "CONNORS_RSI2",
        "KURTOSIS_HIGH": "TALEB_FAT_TAIL",
        "MDD_HIGH": "TALEB_FAT_TAIL",
        "SHARPE_LOW": "TALEB_FAT_TAIL",
        "POSITION_SIZE": "THORP_KELLY",
        "STOP_LOSS": "THORP_KELLY",
        "META_FILTER": "META_LABELING",
        "STATE_DETECTION": "SIMONS_HMM",
    }
    return mapping.get(trigger_type, None)


# ============================================================
# CLI 測試
# ============================================================

if __name__ == "__main__":
    print("=== Ray Expert Modules ===")
    print(f"專家數量: {len(EXPERT_MODULES)}")
    print()

    for key, module in EXPERT_MODULES.items():
        print(f"[{key}] {module['name']}")
        print(f"  Layer: {module['layer']}")
        print(f"  Trigger: {module['trigger']}")
        print()

    print("=== 專家觸發測試 ===")
    triggers = ["RSI2_OVERSOLD", "KURTOSIS_HIGH", "POSITION_SIZE"]
    for t in triggers:
        expert = get_expert_for_trigger(t)
        print(f"  {t} → {expert}")

    print()
    print("=== 所有專家合併 Prompt ===")
    all_prompt = get_all_experts_prompt()
    print(f"總長度: {len(all_prompt)} 字元")
    print(f"中文字數: {sum(1 for c in all_prompt if '\u4e00' <= c <= '\u9fff')}")
    print()
    print("✅ 五大交易權威模組已就緒")