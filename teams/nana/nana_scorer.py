# -*- coding: utf-8 -*-
"""
Nana v1.0 評分系統整合
====================

類別: NanaScorer
功能:
1. 法人評分 (70分) - 連續買超天數階梯 + 合力加成
2. 技術評分 (30分) - RSI + Bias
3. 總分彙整
4. v4.21 進場訊號判定

設計精神:
- 評分用於排序,不是絕對門檻
- 過熱保護機制 (>10天 分數重挫)
- 向量化運算,支援大規模回測
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

class NanaScorer:
    """
    Nana v1.0 評分系統

    使用方式:
        scorer = NanaScorer(aligned_df)
        result = scorer.calculate_scores()
    """

    def __init__(self, df):
        """
        初始化 NanaScorer

        參數:
            df: 對齊後的 DataFrame
                 必要欄位: Close, RSI, Bias, MA20, MA60, ATR_Percent
                 法人欄位: Foreign_Inst_Days, Investment_Trust_Days
        """
        self.df = df.copy()

    def _get_inst_score(self, days):
        """
        法人評分 (根據連續買超天數)

        評分表:
        - >= 11天: 20分 (過熱)
        - 6-10天:  60分
        - 4-5天:   50分
        - 3天:     40分
        - 2天:     15分
        - 1天:     10分
        - 0天:      0分
        """
        if days is None or pd.isna(days):
            return 0
        days = int(days)

        if days >= 11:
            return 20  # 過熱保護
        elif days >= 6:
            return 60
        elif days >= 4:
            return 50
        elif days == 3:
            return 40
        elif days == 2:
            return 15
        elif days == 1:
            return 10
        else:
            return 0

    def _get_rsi_score(self, rsi):
        """
        RSI 評分 (最高15分)

        - 50-70: 15分 (黃金區間)
        - 30-50: 10分
        - 其他:   5分
        """
        if rsi is None or pd.isna(rsi):
            return 5

        if 50 <= rsi <= 70:
            return 15
        elif 30 <= rsi < 50:
            return 10
        else:
            return 5

    def _get_bias_score(self, bias):
        """
        Bias 乖離評分 (最高15分)

        - -2% ~ +3%: 15分 (最佳區間)
        - +3% ~ +6%:  10分
        - > +10%:      0分 (過熱)
        - < -5%:       5分
        - 其他:         5分
        """
        if bias is None or pd.isna(bias):
            return 5

        if -2 <= bias <= 3:
            return 15
        elif 3 < bias <= 6:
            return 10
        elif bias > 10:
            return 0  # 過熱
        elif bias < -5:
            return 5
        else:
            return 5

    def calculate_scores(self):
        """
        執行完整評分流程

        返回:
            DataFrame with columns:
            - Final_Inst_Score: 法人評分 (0-70)
            - RSI_Score: RSI評分 (0-15)
            - Bias_Score: Bias評分 (0-15)
            - Total_Score: 總分 (0-100)
            - Signal: 訊號 ('不進場'/'觀望'/'買進'/'⭐️ 強力買進')
        """
        df = self.df.copy()

        # 確保欄位名稱一致 (對齊 NanaDataAligner 的命名)
        col_map = {
            'foreign_consec': 'F_Consec',
            'trust_consec': 'T_Consec'
        }
        for old, new in col_map.items():
            if old in df.columns and new not in df.columns:
                df = df.rename(columns={old: new})

        # 確保必要的法人欄位存在
        if 'F_Consec' not in df.columns:
            df['F_Consec'] = 0
        if 'T_Consec' not in df.columns:
            df['T_Consec'] = 0

        # 計算 MA20 / MA60 / Bias / RSI
        close = df['Close'].values

        if 'MA20' not in df.columns:
            df['MA20'] = df['Close'].rolling(window=20, min_periods=1).mean()
        if 'MA60' not in df.columns:
            df['MA60'] = df['Close'].rolling(window=60, min_periods=1).mean()
        if 'Bias' not in df.columns:
            df['Bias'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
        if 'RSI' not in df.columns:
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(window=14, min_periods=1).mean()
            avg_loss = pd.Series(loss).rolling(window=14, min_periods=1).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            df['RSI'] = (100 - (100 / (1 + rs))).fillna(50)
        if 'ATR_Percent' not in df.columns:
            # 簡化 ATR%
            df['ATR_Percent'] = 0.005

        # === 1. 法人評分 (最高70分) ===

        # 外資評分
        df['Foreign_Score'] = df['F_Consec'].apply(self._get_inst_score)

        # 投信評分
        df['Trust_Score'] = df['T_Consec'].apply(self._get_inst_score)

        # 取兩者較高分作為基礎法人分
        df['Base_Inst_Score'] = df[['Foreign_Score', 'Trust_Score']].max(axis=1)

        # 合力加成: 外資+投信同時 >= 3天 → +10分 (上限70分)
        mask_both_3d = (df['F_Consec'] >= 3) & (df['T_Consec'] >= 3)

        df['Final_Inst_Score'] = df['Base_Inst_Score'].copy()
        df.loc[mask_both_3d, 'Final_Inst_Score'] += 10

        # 限制上限為70分
        df['Final_Inst_Score'] = df['Final_Inst_Score'].clip(upper=70)

        # === 2. 技術評分 (最高30分) ===

        # RSI 評分 (15分)
        df['RSI_Score'] = df['RSI'].apply(self._get_rsi_score)

        # Bias 評分 (15分)
        df['Bias_Score'] = df['Bias'].apply(self._get_bias_score)

        # === 3. 總分彙整 ===

        df['Total_Score'] = df['Final_Inst_Score'] + df['RSI_Score'] + df['Bias_Score']

        # === 4. v4.21 進場訊號判定 ===

        # 確保 ATR 欄位存在 (預設 0.5%)
        if 'ATR_Percent' not in df.columns:
            df['ATR_Percent'] = 0.005

        if 'MA20' not in df.columns or 'MA60' not in df.columns:
            df['MA20'] = df.get('MA20', df['Close'])
            df['MA60'] = df.get('MA60', df['Close'])

        # === VETO 檢查 (過熱保護) ===
        df['Veto'] = False
        df['Veto_Reason'] = ''

        # VETO 條件：RSI > 70（過熱）
        mask_rsi_hot = df['RSI'] > 70
        df.loc[mask_rsi_hot, 'Veto'] = True
        df.loc[mask_rsi_hot, 'Veto_Reason'] = 'RSI>70'

        # VETO 條件：Bias > 10（乖離過大）
        mask_bias_hot = df['Bias'] > 10
        df.loc[mask_bias_hot, 'Veto'] = True
        df.loc[mask_bias_hot & ~df['Veto'], 'Veto_Reason'] = 'Bias>10'
        df.loc[mask_bias_hot & df['Veto'], 'Veto_Reason'] = df['Veto_Reason'] + '+Bias>10'

        # v4.21 進場門檻
        entry_condition = (
            (df['RSI'] < 70) &
            (df['MA20'] > df['MA60']) &
            (df['ATR_Percent'] >= 0.005) &
            ((df['F_Consec'] > 0) | (df['T_Consec'] > 0))
        )

        # Signal 判定（套用 Veto 降級）
        df['Signal'] = '觀望'
        df.loc[entry_condition & (df['Total_Score'] >= 80), 'Signal'] = '⭐️ 強力買進'
        df.loc[entry_condition & (df['Total_Score'] >= 60), 'Signal'] = '買進'
        df.loc[df['Total_Score'] < 40, 'Signal'] = '不進場'

        # Veto 降級：過熱股票信號降一級
        # strong_buy→watch, buy→neutral, watch→no_position
        veto_mask = df['Veto']
        df.loc[veto_mask & (df['Signal'] == '⭐️ 強力買進'), 'Signal'] = '觀望'
        df.loc[veto_mask & (df['Signal'] == '買進'), 'Signal'] = '不進場'
        df.loc[veto_mask & (df['Signal'] == '觀望'), 'Signal'] = '不進場'

        self.df = df
        return df

    def get_latest_score(self):
        """取得最新一筆評分結果"""
        if self.df is None or len(self.df) == 0:
            return None

        latest = self.df.iloc[-1]

        return {
            'Date': latest.get('Date', latest.get('date', 'N/A')),
            'Close': latest.get('Close', latest.get('close', 'N/A')),
            'Total_Score': latest['Total_Score'],
            'Final_Inst_Score': latest['Final_Inst_Score'],
            'RSI_Score': latest['RSI_Score'],
            'Bias_Score': latest['Bias_Score'],
            'RSI': latest.get('RSI', 'N/A'),
            'Bias': latest.get('Bias', 'N/A'),
            'F_Consec': latest.get('F_Consec', 0),
            'T_Consec': latest.get('T_Consec', 0),
            'Signal': latest['Signal']
        }

    def get_signals(self, min_score=60):
        """取得所有進場訊號"""
        if self.df is None:
            return []

        signals = self.df[
            (self.df['Signal'].isin(['買進', '⭐️ 強力買進'])) &
            (self.df['Total_Score'] >= min_score)
        ]

        return signals

    def get_summary(self):
        """取得評分摘要統計"""
        if self.df is None or len(self.df) == 0:
            return None

        signals = self.get_signals()

        return {
            'Total_Records': len(self.df),
            'Signals_Count': len(signals),
            'Avg_Score': self.df['Total_Score'].mean(),
            'Max_Score': self.df['Total_Score'].max(),
            'Min_Score': self.df['Total_Score'].min(),
            'Latest_Score': self.df['Total_Score'].iloc[-1],
            'Signal_Distribution': self.df['Signal'].value_counts().to_dict()
        }

def create_nana_scorer_from_aligned(df):
    """
    工廠函數: 從對齊後的資料建立 NanaScorer 並計算評分

    範例:
        from nana_data_aligner import align_stock_data

        df = align_stock_data('2330', '2026-01-01', '2026-04-23')
        scorer = create_nana_scorer_from_aligned(df)

        print(scorer.get_latest_score())
    """
    scorer = NanaScorer(df)
    scorer.calculate_scores()
    return scorer

# ==================== 主程式測試 ====================

if __name__ == '__main__':
    # 讀取對齊後的資料
    try:
        df = pd.read_csv('Tina_Quant_System/teams/nana/aligned_data_sample.csv')
        print('讀取對齊資料:', len(df), '筆')

        # 建立 NanaScorer
        scorer = NanaScorer(df)
        result = scorer.calculate_scores()

        print()
        print('='*60)
        print(' NanaScorer 評分結果')
        print('='*60)
        print()

        # 最新評分
        latest = scorer.get_latest_score()
        if latest:
            print(f" 日期: {latest['Date']}")
            print(f" 收盤: {latest['Close']}")
            print(f" 總分: {latest['Total_Score']}/100")
            print(f"   法人: {latest['Final_Inst_Score']}/70")
            print(f"   RSI: {latest['RSI_Score']}/15")
            print(f"   Bias: {latest['Bias_Score']}/15")
            print(f" RSI: {latest['RSI']}")
            print(f" Bias: {latest['Bias']}")
            print(f" F_Consec: {latest['F_Consec']} | T_Consec: {latest['T_Consec']}")
            print(f" 訊號: {latest['Signal']}")

        print()
        print(' 摘要:')
        summary = scorer.get_summary()
        for k, v in summary.items():
            print(f"   {k}: {v}")

        print()
        print(' 訊號記錄:')
        signals = scorer.get_signals()
        if len(signals) > 0:
            print(signals[['Date', 'Close', 'Total_Score', 'Signal']].to_string())
        else:
            print(' 無進場訊號')

        # 儲存結果
        result.to_csv('Tina_Quant_System/teams/nana/scored_data.csv', index=False)
        print()
        print(' 已儲存: scored_data.csv')

    except FileNotFoundError:
        print('找不到 aligned_data_sample.csv,請先執行 nana_data_aligner.py')
    except Exception as e:
        print(f'錯誤: {e}')