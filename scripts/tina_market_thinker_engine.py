# -*- coding: utf-8 -*-
"""
Tina Market Thinker Engine — 每日市場自主思考
"""

import sqlite3
import json
import os
import sys
import yfinance as yf
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
LEARNING_DB = DATA_DIR / 'tina_learning.db'


class TinaMarketThinker:
    """市場自主思考引擎"""

    def __init__(self):
        self.conn = sqlite3.connect(str(LEARNING_DB))
        self.conn.row_factory = sqlite3.Row
        self.today = datetime.now().strftime('%Y-%m-%d')

    # ─── Market Data Fetchers ──────────────────────────────

    def _get_twii_rsi(self) -> Optional[float]:
        try:
            twii = yf.Ticker("^TWII")
            hist = twii.history(period="3mo")
            if len(hist) < 15:
                return None
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, float('inf'))
            rsi = 100 - (100 / (1 + rs))
            return round(float(rsi.iloc[-1]), 1)
        except Exception:
            return self._get_cached_rsi('twii')

    def _get_qqq_rsi(self) -> Optional[float]:
        try:
            qqq = yf.Ticker("QQQ")
            hist = qqq.history(period="3mo")
            if len(hist) < 15:
                return None
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, float('inf'))
            rsi = 100 - (100 / (1 + rs))
            return round(float(rsi.iloc[-1]), 1)
        except Exception:
            return self._get_cached_rsi('qqq')

    def _get_cached_rsi(self, market: str) -> Optional[float]:
        cur = self.conn.cursor()
        col = f"{market}_rsi"
        cur.execute(f"SELECT {col} FROM market_context ORDER BY timestamp DESC LIMIT 1")
        r = cur.fetchone()
        return r[col] if r else None

    def _get_vix(self) -> Optional[float]:
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1mo")
            return round(float(hist['Close'].iloc[-1]), 2)
        except Exception:
            cur = self.conn.cursor()
            cur.execute("SELECT vix_rsi FROM market_context ORDER BY timestamp DESC LIMIT 1")
            r = cur.fetchone()
            return r['vix_rsi'] if r else None

    def _get_recent_prices(self, symbol: str, days: int = 30) -> Optional[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(days)
            if len(hist) < 5:
                return None
            return {
                'current': round(float(hist['Close'].iloc[-1]), 2),
                'high': round(float(hist['High'].iloc[-1]), 2),
                'low': round(float(hist['Low'].iloc[-1]), 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'ma20': round(float(hist['Close'].rolling(20).mean().iloc[-1]), 2) if len(hist) >= 20 else None,
                'ma60': round(float(hist['Close'].rolling(60).mean().iloc[-1]), 2) if len(hist) >= 60 else None,
            }
        except Exception:
            return None

    def _get_risk_on_score(self) -> float:
        vix = self._get_vix()
        if vix is None:
            return 0.5
        # VIX > 30 恐慌，risk_off；VIX < 15 貪婪，risk_on
        if vix <= 15:
            return 0.9
        elif vix <= 20:
            return 0.7
        elif vix <= 25:
            return 0.5
        elif vix <= 30:
            return 0.3
        else:
            return 0.1

    # ─── Core Thinking ────────────────────────────────────

    def think_market(self) -> str:
        """執行完整市場思考並產出報告"""
        print("🧠 Tina 市場思考引擎啟動...")
        print()

        # 1. 收集市場數據
        print("📡 收集市場數據...")
        twii_rsi = self._get_twii_rsi()
        qqq_rsi = self._get_qqq_rsi()
        vix = self._get_vix()
        risk_on = self._get_risk_on_score()
        twii_prices = self._get_recent_prices("^TWII")
        qqq_prices = self._get_recent_prices("QQQ")
        print(f"   TWII RSI: {twii_rsi}, QQQ RSI: {qqq_rsi}, VIX: {vix}")
        print()

        # 2. 分析市場大局
        print("🌐 分析市場大局...")
        market_regime = self._assess_regime(twii_rsi, risk_on)
        macro_view = self._analyze_macro(twii_rsi, qqq_rsi, vix, risk_on)
        print(f"   市場格局：{market_regime}")

        # 3. 技術面觀察
        print("📈 技術面觀察...")
        tech_obs = self._technical_observation(twii_rsi, qqq_rsi, twii_prices, qqq_prices)

        # 4. 情緒判斷
        print("💭 情緒判斷...")
        sentiment = self._judge_sentiment(vix, risk_on, twii_rsi)

        # 5. 機會識別
        print("🎯 識別進場機會...")
        opportunities = self._scan_opportunities(twii_rsi, qqq_rsi, market_regime)

        # 6. 風險警示
        print("⚠️ 風險警示...")
        risks = self._check_risks(twii_rsi, qqq_rsi, vix, market_regime)

        # 7. 策略調整建議
        print("⚖️ 策略調整...")
        strategy_adj = self._suggest_strategy_adjustments(twii_rsi, qqq_rsi, market_regime, opportunities, risks)

        # 8. 明日觀察重點
        print("🔮 明日觀察...")
        tomorrow = self._tomorrow_watch(vix, risk_on)

        # 9. 組裝報告
        report = self._assemble_report(
            twii_rsi, qqq_rsi, vix, risk_on, market_regime,
            macro_view, tech_obs, sentiment,
            opportunities, risks, strategy_adj, tomorrow
        )

        # 10. 儲存並記錄
        REPORT_DIR.mkdir(exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        report_path = REPORT_DIR / f'tina_thinking_diary_{date_str}.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"   已儲存：{report_path}")

        # 寫入思考日記資料庫
        self._save_thinking_diary(market_regime, opportunities, risks, strategy_adj)

        print()
        print(report)
        print()
        print("✅ 市場思考完成")
        return report

    # ─── Analysis Sub-Methods ──────────────────────────────

    def _assess_regime(self, twii_rsi: Optional[float], risk_on: float) -> str:
        if twii_rsi is None:
            return "數據不足"
        if twii_rsi > 75 or risk_on > 0.8:
            return "過熱謹慎"
        elif twii_rsi < 35 or risk_on < 0.2:
            return "超跌機會"
        elif 40 <= twii_rsi <= 65:
            return "中性整理"
        else:
            return "方向不明"

    def _analyze_macro(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                       vix: Optional[float], risk_on: float) -> Dict:
        view = {
            'summary': '',
            'twii': {},
            'qqq': {},
            'vix': vix,
            'risk_on': risk_on,
            'flow': 'neutral'
        }

        if twii_rsi is not None:
            view['twii']['rsi'] = twii_rsi
            view['twii']['status'] = '過熱' if twii_rsi > 75 else ('超賣' if twii_rsi < 35 else '正常')

        if qqq_rsi is not None:
            view['qqq']['rsi'] = qqq_rsi
            view['qqq']['status'] = '過熱' if qqq_rsi > 75 else ('超賣' if qqq_rsi < 35 else '正常')

        # 資金流向判斷
        if qqq_rsi and twii_rsi:
            if qqq_rsi > twii_rsi + 10:
                view['flow'] = '美股帶動台股'
            elif twii_rsi > qqq_rsi + 10:
                view['flow'] = '台股相對強勢'
            else:
                view['flow'] = '同步格局'

        # 總結
        if risk_on > 0.7:
            view['summary'] = "風險偏好高，資金追逐成長股"
        elif risk_on < 0.3:
            view['summary'] = "風險規避升溫，防禦類股相對抗跌"
        else:
            view['summary'] = "市場觀望，指數區間整理"

        return view

    def _technical_observation(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                               twii_prices: Optional[Dict], qqq_prices: Optional[Dict]) -> Dict:
        obs = []
        if twii_rsi:
            obs.append(f"TWII RSI {twii_rsi:.0f}（{'過熱' if twii_rsi > 75 else ('超賣' if twii_rsi < 35 else '正常')}）")
        if qqq_rsi:
            obs.append(f"QQQ RSI {qqq_rsi:.0f}（{'過熱' if qqq_rsi > 75 else ('超賣' if qqq_rsi < 35 else '正常')}）")
        if twii_prices and twii_prices.get('ma20'):
            price = twii_prices['current']
            ma20 = twii_prices['ma20']
            ma60 = twii_prices.get('ma60')
            obs.append(f"TWII {price} vs MA20 {ma20}（{'▲' if price > ma20 else '▼'}）")
            if ma60:
                obs.append(f"TWII MA60 {ma60}")
        if qqq_prices and qqq_prices.get('ma20'):
            price = qqq_prices['current']
            ma20 = qqq_prices['ma20']
            obs.append(f"QQQ {price} vs MA20 {ma20}（{'▲' if price > ma20 else '▼'}）")

        return {'observations': obs, 'summary': ' | '.join(obs) if obs else '數據不足'}

    def _judge_sentiment(self, vix: Optional[float], risk_on: float, twii_rsi: Optional[float]) -> Dict:
        if vix is None:
            vix_display = 'N/A'
            vix_level = 'unknown'
        else:
            vix_display = f"{vix:.1f}"
            vix_level = '恐慌' if vix > 25 else ('警戒' if vix > 20 else ('正常' if vix > 15 else '貪婪'))

        if risk_on > 0.75:
            emotion = "貪婪 💚"
        elif risk_on > 0.55:
            emotion = "偏多 🟢"
        elif risk_on > 0.45:
            emotion = "中立 🟡"
        elif risk_on > 0.25:
            emotion = "偏空 🟠"
        else:
            emotion = "恐慌 🔴"

        institutional = "偏多但已高檔" if twii_rsi and twii_rsi > 65 else ("偏多低檔" if twii_rsi and twii_rsi < 45 else "中性")

        return {
            'vix': vix_display,
            'vix_level': vix_level,
            'emotion': emotion,
            'institutional': institutional,
            'risk_on': risk_on
        }

    def _scan_opportunities(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                            regime: str) -> List[Dict]:
        opps = []
        if regime == "超跌機會" and twii_rsi:
            opps.append({
                'rank': 1,
                'type': '價值回歸',
                'target': '台股價值成長股',
                'signal': f'RSI {twii_rsi:.0f} 超賣，法人買超',
                'confidence': 0.75,
                'action': '分批進場，設定 -10% 止損'
            })
        if regime == "中性整理":
            opps.append({
                'rank': 1,
                'type': 'MA20 突破',
                'target': '突破 MA20 的成長股',
                'signal': '指數區間整理時，個股突破MA20',
                'confidence': 0.70,
                'action': '突破量 > 1000 張進場'
            })
        if qqq_rsi and qqq_rsi < 60 and qqq_rsi > 40:
            opps.append({
                'rank': 2,
                'type': '美股連動',
                'target': '科技硬體供應鏈',
                'signal': f'QQQ RSI {qqq_rsi:.0f} 中性，美股支撐台灣供應鏈',
                'confidence': 0.68,
                'action': '逢低布局'
            })
        if not opps:
            opps.append({
                'rank': 1,
                'type': '觀望',
                'target': '無明確進場機會',
                'signal': '等待趨勢明確',
                'confidence': 0.5,
                'action': '保持觀望'
            })
        return opps

    def _check_risks(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                    vix: Optional[float], regime: str) -> List[Dict]:
        risks = []
        if twii_rsi and twii_rsi > 75:
            risks.append({
                'rank': 1,
                'type': '過熱回調',
                'detail': f'TWII RSI {twii_rsi:.0f} 過熱',
                'severity': 'high',
                'action': '漲多減碼，避免追高'
            })
        if vix and vix > 25:
            risks.append({
                'rank': 2,
                'type': '高波動',
                'detail': f'VIX {vix:.0f} 市場波動加劇',
                'severity': 'high',
                'action': '降低倉位，等恐慌指數回落'
            })
        if regime == "過熱謹慎":
            risks.append({
                'rank': 1,
                'type': '市場過熱',
                'detail': '整體市場過熱，回調機率高',
                'severity': 'high',
                'action': '分批了結，現金為王'
            })
        if not risks:
            risks.append({
                'rank': 1,
                'type': '無重大風險',
                'detail': '目前市場無明顯風險',
                'severity': 'low',
                'action': '正常倉位操作'
            })
        return risks

    def _suggest_strategy_adjustments(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                                      regime: str, opps: List[Dict], risks: List[Dict]) -> List[str]:
        adj = []
        high_risk = any(r['severity'] == 'high' for r in risks)
        high_opp = any(o['confidence'] >= 0.75 for o in opps)

        if regime == "過熱謹慎":
            adj.append("⬇️ 下調：成長股追高（RSI 過熱）")
            adj.append("⬆️ 上調：金融股波段（估值修復）")
            adj.append("📊 倉位降至 5 成以下")
        elif regime == "超跌機會":
            adj.append("⬆️ 上調：價值成長股低接")
            adj.append("⬇️ 下調：短線操作，持有至 MA20")
            adj.append("📊 倉位可提升至 7 成")
        elif regime == "中性整理":
            adj.append("➡️ 維持：現有策略不變")
            adj.append("📊 倉位維持 5-7 成")
            adj.append("🔍 等待突破 MA20 確認進場")
        else:
            adj.append("➡️ 維持：觀望為主")
            adj.append("📊 倉位 3-5 成")

        if twii_rsi and twii_rsi > 70:
            adj.append("⚠️ TWII RSI > 70：禁用 RSI>65 進場策略")
        if qqq_rsi and qqq_rsi > 75:
            adj.append("⚠️ QQQ RSI > 75：科技股注意獲利了結")

        return adj

    def _tomorrow_watch(self, vix: Optional[float], risk_on: float) -> List[str]:
        watch = []
        if vix and vix > 20:
            watch.append(f"VIX {vix:.0f} 是否回落（目前{vix:.0f}）")
        watch.append("美國 CPI / PCE 數據（聯準會政策參考）")
        watch.append("台股法人動向（三大法人買賣超）")
        watch.append("明日 TWII 是否跌破 MA20")
        return watch

    # ─── Assembly ──────────────────────────────────────────

    def _assemble_report(self, twii_rsi: Optional[float], qqq_rsi: Optional[float],
                         vix: Optional[float], risk_on: float, regime: str,
                         macro: Dict, tech: Dict, sentiment: Dict,
                         opps: List[Dict], risks: List[Dict],
                         adj: List[str], tomorrow: List[str]) -> str:
        today = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M')

        lines = [
            f"# 🧠 Tina 市場思考",
            f"**{time_str}**",
            "",
            "---",
            "",
            "## 🌐 今日市場大局",
            "",
            f"- **TWII RSI:** {twii_rsi or 'N/A'}",
            f"- **QQQ RSI:** {qqq_rsi or 'N/A'}",
            f"- **VIX:** {vix or 'N/A'}（{sentiment.get('vix_level', 'N/A')}）",
            f"- **Risk-On 分數:** {risk_on:.2f}",
            f"- **市場格局:** {regime}",
            f"- **宏觀總結:** {macro.get('summary', 'N/A')}",
            f"- **資金流向:** {macro.get('flow', 'N/A')}",
            "",
            "## 📈 技術面觀察",
        ]

        for obs in tech.get('observations', []):
            lines.append(f"- {obs}")

        lines += [
            "",
            "## 💭 情緒判斷",
            f"- **市場情緒:** {sentiment.get('emotion', 'N/A')}",
            f"- **法人動向:** {sentiment.get('institutional', 'N/A')}",
            f"- **恐慌指數:** VIX {sentiment.get('vix', 'N/A')}（{sentiment.get('vix_level', 'N/A')}）",
            "",
            "## 🎯 機會識別",
        ]

        for o in opps:
            lines.append(f"{o['rank']}. **{o['type']}** — {o['target']}")
            lines.append(f"   - 信號：{o['signal']}")
            lines.append(f"   - 信心度：{o['confidence']*100:.0f}%")
            lines.append(f"   - 操作：{o['action']}")

        lines += ["", "## ⚠️ 風險警示", ""]
        for r in risks:
            sev_emoji = '🔴' if r['severity'] == 'high' else ('🟡' if r['severity'] == 'medium' else '🟢')
            lines.append(f"{sev_emoji} **{r['rank']}. {r['type']}**（{r['severity'].upper()}）")
            lines.append(f"   - {r['detail']}")
            lines.append(f"   - 對策：{r['action']}")

        lines += ["", "## ⚖️ 策略調整建議", ""]
        for a in adj:
            lines.append(f"- {a}")

        lines += ["", "## 🔮 明日觀察重點", ""]
        for w in tomorrow:
            lines.append(f"- {w}")

        lines += [
            "",
            "---",
            f"*Tina 市場思考 {today} — 持續學習，日拱一卒*",
        ]

        return "\n".join(lines)

    def _save_thinking_diary(self, regime: str, opps: List[Dict], risks: List[Dict], adj: List[str]):
        """將思考結果寫入資料庫"""
        cur = self.conn.cursor()
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS thinking_diary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    regime TEXT,
                    top_opportunity TEXT,
                    top_risk TEXT,
                    strategy_adjustments TEXT,
                    confidence REAL,
                    created_at TEXT
                )
            ''')
            top_opp = opps[0]['type'] + ':' + opps[0]['target'] if opps else ''
            top_risk = risks[0]['type'] if risks else ''
            adj_text = '; '.join(adj)

            cur.execute('''
                INSERT INTO thinking_diary (date, regime, top_opportunity, top_risk,
                    strategy_adjustments, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.today, regime, top_opp, top_risk, adj_text, 0.8,
                  datetime.now().strftime('%Y-%m-%d %H:%M')))
            self.conn.commit()
        except Exception as e:
            print(f"   ⚠️ 寫入思考日記失敗：{e}")

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    thinker = TinaMarketThinker()
    thinker.think_market()
    thinker.close()
