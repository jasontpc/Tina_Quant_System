# -*- coding: utf-8 -*-
"""
Tina Market Thinker — 市場思考引擎
深入分析市場動態、資金流向、情緒指標，產出綜合判斷
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'tina_learning.db'


class TinaMarketThinker:
    """市場思考引擎"""

    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row

    def think(self) -> dict:
        """執行完整市場思考"""
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'regime': self._judge_regime(),
            'twii': self._deep_twii_analysis(),
            'qqq': self._deep_qqq_analysis(),
            'sectors': self._analyze_sectors(),
            'sentiment': self._judge_sentiment(),
            'opportunities': [],
            'risks': [],
            'verdict': ""
        }

        result['opportunities'] = self._find_opportunities(result)
        result['risks'] = self._find_risks(result)
        result['verdict'] = self._make_verdict(result)

        return result

    def _judge_regime(self) -> str:
        """判斷市場體制"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM market_context ORDER BY timestamp DESC LIMIT 5')
        rows = cur.fetchall()
        if not rows:
            return "unknown"

        recent_rsi = [r['twii_rsi'] for r in rows if r['twii_rsi']]
        recent_vix = [r['vix_rsi'] for r in rows if r['vix_rsi']]
        risk_ons = [r['risk_on_score'] for r in rows if r['risk_on_score'] is not None]

        avg_rsi = sum(recent_rsi) / len(recent_rsi) if recent_rsi else 50
        avg_vix = sum(recent_vix) / len(recent_vix) if recent_vix else 20
        avg_risk_on = sum(risk_ons) / len(risk_ons) if risk_ons else 0.5

        if avg_rsi > 72 and avg_risk_on > 0.7:
            return "bull_hot"
        elif avg_rsi < 38 and avg_risk_on < 0.35:
            return "oversold_rebound"
        elif 45 <= avg_rsi <= 60:
            return "neutral"
        else:
            return "transition"

    def _deep_twii_analysis(self) -> dict:
        """深度台股分析"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM market_context ORDER BY timestamp DESC LIMIT 20')
        rows = cur.fetchall()

        result = {'rsi': None, 'rsi_trend': 'neutral', 'price_level': 'unknown'}

        if not rows or not rows[0]['twii_rsi']:
            return result

        rsi = rows[0]['twii_rsi']
        result['rsi'] = rsi

        # RSI 趨勢
        if len(rows) >= 5:
            older_rsi = rows[4]['twii_rsi'] if rows[4]['twii_rsi'] else rsi
            if rsi > older_rsi + 5:
                result['rsi_trend'] = 'rising'
            elif rsi < older_rsi - 5:
                result['rsi_trend'] = 'falling'

        # 價格水平
        if rsi > 70:
            result['price_level'] = 'overbought'
        elif rsi < 35:
            result['price_level'] = 'oversold'
        else:
            result['price_level'] = 'neutral'

        return result

    def _deep_qqq_analysis(self) -> dict:
        """深度納指分析"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM market_context ORDER BY timestamp DESC LIMIT 5')
        row = cur.fetchone()

        result = {'rsi': None, 'level': 'unknown'}
        if row and row['qqq_rsi']:
            rsi = row['qqq_rsi']
            result['rsi'] = rsi
            if rsi > 72:
                result['level'] = 'overbought'
            elif rsi < 35:
                result['level'] = 'oversold'
            else:
                result['level'] = 'neutral'

        return result

    def _analyze_sectors(self) -> list:
        """分析產業狀態"""
        cur = self.conn.cursor()
        # 從 trades 表的 strategy_used 欄位分析產業
        cur.execute('''
            SELECT strategy_used as sector, COUNT(*) as trades, AVG(pnl_pct) as avg_pnl
            FROM trades
            WHERE exit_date >= ? AND strategy_used IS NOT NULL
            GROUP BY strategy_used
            ORDER BY avg_pnl DESC
            LIMIT 5
        ''', ((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),))

        sectors = []
        for row in cur.fetchall():
            sectors.append({
                'name': row['sector'] or '未知',
                'trades': row['trades'],
                'avg_pnl': row['avg_pnl'] or 0
            })
        return sectors

    def _judge_sentiment(self) -> str:
        """判斷市場情緒"""
        cur = self.conn.cursor()
        cur.execute('SELECT risk_on_score, risk_off_score FROM market_context ORDER BY timestamp DESC LIMIT 1')
        row = cur.fetchone()

        if not row or row['risk_on_score'] is None:
            return "unknown"

        risk_on = row['risk_on_score']
        risk_off = row['risk_off_score'] or 0

        if risk_on > 0.7:
            return "risk_on_euphoria"
        elif risk_on < 0.3:
            return "risk_off_fear"
        else:
            return "neutral"

    def _find_opportunities(self, analysis: dict) -> list:
        """找機會"""
        opportunities = []
        regime = analysis['regime']
        twii = analysis['twii']

        if regime in ("oversold_rebound", "neutral"):
            opportunities.append({
                'type': '價值布局',
                'reason': f'TWII RSI {twii["rsi"]:.0f} {twii["price_level"]}，適合佈局價值股',
                'confidence': 0.70 if regime == "oversold_rebound" else 0.60
            })

        if analysis['qqq']['rsi'] and analysis['qqq']['rsi'] < 40:
            opportunities.append({
                'type': '科技反彈',
                'reason': f'QQQ RSI {analysis["qqq"]["rsi"]:.0f}，關注 AI 伺服器/半導體',
                'confidence': 0.65
            })

        return opportunities

    def _find_risks(self, analysis: dict) -> list:
        """找風險"""
        risks = []
        regime = analysis['regime']

        if regime == "bull_hot":
            risks.append({
                'type': '過熱回調',
                'reason': '市場情緒過度樂觀，隨時可能回調',
                'severity': 'high'
            })

        if analysis['twii']['rsi'] and analysis['twii']['rsi'] > 78:
            risks.append({
                'type': 'RSI 極端',
                'reason': f'TWII RSI {analysis["twii"]["rsi"]:.0f} 達到極端值',
                'severity': 'medium'
            })

        return risks

    def _make_verdict(self, analysis: dict) -> str:
        """做出判斷"""
        regime = analysis['regime']

        verdicts = {
            "bull_hot": "市場過熱，建議降低倉位，優先止盈，觀望為主",
            "oversold_rebound": "市場超賣，適合分批布局，等待反彈",
            "neutral": "市場中性，可謹慎參與，嚴守止損",
            "transition": "市場方向不明，建議觀望，等待趨勢明確",
            "unknown": "數據不足，無法判斷"
        }

        return verdicts.get(regime, "無法判斷")

    def generate_think_report(self) -> str:
        """產出思考報告"""
        result = self.think()

        lines = [
            f"# 🧠 Tina 市場思考報告",
            f"**時間：{result['timestamp']}**",
            "",
            "## 🌐 市場格局判斷",
            f"- 體制：{result['regime']}",
            f"- 情緒：{result['sentiment']}",
            "",
            "## 📊 台股深度分析",
            f"- RSI：{result['twii']['rsi'] or 'N/A'}（{result['twii']['rsi_trend']}）",
            f"- 價格位階：{result['twii']['price_level']}",
            "",
            "## 📈 納指分析",
            f"- RSI：{result['qqq']['rsi'] or 'N/A'}（{result['qqq']['level']}）",
            "",
        ]

        if result['sectors']:
            lines.append("## 🏭 產業表現")
            for s in result['sectors']:
                lines.append(f"- {s['name']}：{s['trades']} 筆交易，平均 {s['avg_pnl']*100:+.1f}%")
            lines.append("")

        if result['opportunities']:
            lines.append("## 🎯 機會")
            for o in result['opportunities']:
                lines.append(f"- **{o['type']}**：{o['reason']}（信心 {o['confidence']*100:.0f}%）")
            lines.append("")

        if result['risks']:
            lines.append("## ⚠️ 風險")
            for r in result['risks']:
                lines.append(f"- **{r['type']}**（{r['severity']}）：{r['reason']}")
            lines.append("")

        lines.append("## 💡 最終判斷")
        lines.append(f"**{result['verdict']}**")

        report = "\n".join(lines)

        REPORT_DIR = BASE_DIR / 'reports'
        REPORT_DIR.mkdir(exist_ok=True)
        path = REPORT_DIR / f"tina_market_think_{datetime.now().strftime('%Y%m%d')}.md"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    thinker = TinaMarketThinker()
    print("🧠 Tina Market Thinker 啟動...")
    print()

    report = thinker.generate_think_report()
    print(report)

    thinker.close()