# Tina 參數進化報告

**版本**: v2_adapted_rsi  
**父版本**: base  
**建立時間**: 2026-05-02 11:52:41  
**說明**: Adjusted RSI entry max and max hold days per strategy review

---

## 📊 參數內容

| 參數 | 數值 |
|------|------|
| blacklist | {'description': '黑名單股票（全系統禁止進場）', 'source': 'Nana loss_rules.json v4.21', 'codes': ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669', '2597', '2379'], 'reason': 'Q1 勝率 0-33%，迭代優化確認排除', 'per_stock_notes': {'2408': '友達：5次>20%極端虧損，貢獻40%極端虧損', '2379': '瑞昱：0% WR, -4.94% avg', '2382': '廣達：黑名單確認'}} |
| description | Tina 量化系統 全團隊統一策略配置 v1.0 |
| entry_rsi | {'description': 'RSI 進場標準（全系統共用語義）', 'strict': {'rsi_max': 45, 'rsi_min': 30, 'use_for': '積極市場、高信心進場'}, 'normal': {'rsi_max': 55, 'rsi_min': 30, 'use_for': '一般市場、多數情況'}, 'relaxed': {'rsi_max': 60, 'rsi_min': 25, 'use_for': 'OVERBOUGHT 緩解後市場恢復'}, 'emergency': {'rsi_max': 65, 'rsi_min': 20, 'use_for': '僅用於黑名單股票強勢修復後，不建議常規使用'}, 'system_default': 'normal'} |
| entry_rsi_max | 40 |
| failure_log_format | {'description': '統一失敗交易記錄格式', 'required_fields': ['team', 'symbol', 'name', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'rsi_entry', 'atr_entry', 'failure_type', 'failure_reason', 'market_status', 'system_version'], 'failure_types': ['RSI_OVERBOUGHT', 'HIGH_BIAS', 'LOW_VOLUME', 'INST_REVERSAL', 'MA_BREAK', 'STOP_LOSS', 'HOLD_DAYS_MAX', 'MARKET_CRASG']} |
| generated | 2026-05-02T08:00:00+08:00 |
| institutional_filter | {'description': '法人籌碼過濾（Nana 獨有，已驗證有效）', 'enabled': True, 'lookback_days': 3, 'requirement': '任一法人（外資或投信）3天內至少1天買超', 'applies_to': ['Nana', 'Leo'], 'note': 'Leo 應整合此條件'} |
| learning_config | {'tw': {'db_path': 'data/tw_value_growth.db', 'buy_log': 'data/tw_buy_log.csv', 'market_regime_key': 'normal', 'rsi_adjust_by_regime': {'bull': {'rsi_enter_adj': 5}, 'normal': {'rsi_enter_adj': 0}, 'bear': {'rsi_enter_adj': -10}}}, 'us': {'db_path': 'data/us_value_growth.db', 'buy_log': 'data/us_buy_log.csv', 'filter_weights_file': 'data/us_learning_weights.json'}} |
| market_regime | {'description': '大盤體制判定 — 所有團隊共用同一 TWII RSI 體制', 'OVERBOUGHT': {'twii_rsi_min': 75, 'action': '禁止新進場（全系統 watch mode）', 'rsi_entry_max_override': 45, 'note': '市場過熱，等待 RSI 回落'}, 'NEUTRAL': {'twii_rsi_range': [35, 75], 'action': '正常進場', 'rsi_entry_max_override': 55, 'note': '常規操作'}, 'OVERSOLD': {'twii_rsi_max': 35, 'action': '鼓勵進場（超賣撿便宜）', 'rsi_entry_max_override': 60, 'note': '市場超賣，積極尋找進場機會'}} |
| max_hold_days | 15 |
| momentum_filter | {'description': '動量過濾（全系統共用）', 'adx_threshold': 20, 'mom5_min_pct': 0, 'note': 'ADX > 20 確認趨勢，mom5 > 0 確認短期動量'} |
| next_actions | [{'priority': 1, 'action': '建立 configs/blacklist.json 供全系統引用', 'owner': 'Tina'}, {'priority': 2, 'action': 'Leo 整合 Nana 法人 3天篩選條件', 'owner': 'Leo'}, {'priority': 3, 'action': 'Ray 採用 unified RSI < 55 進場標準', 'owner': 'Ray'}, {'priority': 4, 'action': 'Maggy 擴展美股回測至 20+ 檔股票', 'owner': 'Maggy'}, {'priority': 5, 'action': 'TW Learning Engine 激活 market_regime 動態調整', 'owner': 'Tina'}] |
| per_team_overrides | {'Nana': {'rsi_entry_max': 55, 'atr_sl': 2.0, 'atr_tp': 4.0, 'hold_days': 10, 'trailing_atr': 2.0, 'score_min': 35, 'adx_threshold': 20, 'institutional_filter': True, 'note': 'v4.21 最佳實測參數'}, 'Leo': {'rsi_entry_max': 55, 'institutional_filter': False, 'note': '需整合法人篩選條件（from Nana）'}, 'Ray': {'rsi_entry_min': 40, 'rsi_entry_max': 50, 'atr_sl': 2.0, 'atr_tp': 3.5, 'hold_days': 7, 'trailing_atr': 2.0, 'score_min': 40, 'adx_threshold': 25, 'note': 'ETF 波段，37筆回測勝率62.2%'}, 'Maggy': {'entry_rsi': 35, 'exit_rsi': 65, 'max_hold_days': 20, 'note': '美股 RSI 均值回歸策略，樣本小需實盤驗證'}} |
| scope | 全系統共用（ Nana / Leo / Ray / Maggy / Core） |
| score_thresholds | {'description': '進場分數門檻（全系統）', 'Nana': {'min': 35, 'note': '已有 72 分嚴格版並存'}, 'Ray': {'min': 40}, 'Maggy': {'min': 35}, 'system_default': 35} |
| stop_loss | {'description': '停損 ATR 倍數（全系統基準）', 'atr_multiplier': 2.0, 'fixed_pct': 0.05, 'hard_stop_pct': 0.1, 'note': 'Nana/Ray 已驗證 2.0x 最佳'} |
| take_profit | {'description': '停利 ATR 倍數（全系統基準）', 'atr_multiplier_tp': 3.5, 'fixed_pct': 0.1, 'partial_exit': [{'return_pct': 3, 'action': '減碼 1/3'}, {'return_pct': 5, 'action': '再減碼 1/3'}, {'return_pct': 8, 'action': '持有觀望'}, {'return_pct': 10, 'action': '全數出清'}], 'note': 'Nana 偏 4.0x, Ray 偏 3.5x，建議區間 3.5-4.0x'} |
| trailing_stop | {'description': '移動停損 ATR（全系統基準）', 'atr_multiplier': 2.0, 'use_high_price': True, 'note': '僅往上移動，不往下'} |
| trend_confirmation | {'description': '趨勢確認條件（全系統共用）', 'ma_required': True, 'ma_condition': 'MA20 > MA60', 'ma_note': '確認多頭趨勢，防止逆勢進場', 'price_above_ma20': True, 'ma20_bias_max_pct': 8.0} |
| version | 1.0 |
| volatility_filter | {'description': '波動性過濾（全系統共用）', 'atr_min_pct': 0.005, 'atr_absolute_min': 30, 'note': 'ATR < 0.5% 或 ATR < 30 點，禁止進場'} |


_尚無績效資料_
