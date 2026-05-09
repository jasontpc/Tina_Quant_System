# -*- coding: utf-8 -*-
"""Patch streamlit_tw_stock.py to update Score Breakdown display"""
from pathlib import Path

file = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py')
content = file.read_text(encoding='utf-8')

old_tw_block = """            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (color-coded inline) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',  bd.get('rsi',0),  (35<=rsi_v<=60)),
                ('MACD', bd.get('macd',0), (macd_v>0)),
                ('K',    bd.get('k',0),    kd_ok),
                ('D',    bd.get('d',0),    not kd_ok),
                ('BB',   bd.get('bb',0),   (20<=bb_v<=80)),
                ('MA',   bd.get('ma',0),   ma_bull),
                ('Vol',  bd.get('vol',0),  (0.8<=vol_v<=1.5)),
            ]"""

new_tw_block = """            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (v3.0 TW) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',    bd.get('rsi',0),     (40<=rsi_v<=70)),
                ('MACD',   bd.get('macd',0),    (macd_v>0)),
                ('Trend',  bd.get('trend',0),    ma_bull),
                ('KD',     bd.get('kd',0),      kd_ok),
                ('BB',     bd.get('bb',0),      (20<=bb_v<=80)),
                ('Rel.Str',bd.get('rel_str',0), (bd.get('rel_str',0)>=60)),
                ('Vol',    bd.get('vol',0),     (vol_v>=1.2)),
                ('Funda',  bd.get('funda',0),   (bd.get('funda',0)>=35)),
            ]"""

# Replace only the FIRST occurrence (TW section)
content = content.replace(old_tw_block, new_tw_block, 1)

# Now replace the second occurrence (US section)
# The US section doesn't have "Institutional (TW only)"
# It has different content, so find by context
old_us_block = """            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (color-coded inline) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',  bd.get('rsi',0),  (35<=rsi_v<=60)),
                ('MACD', bd.get('macd',0), (macd_v>0)),
                ('K',    bd.get('k',0),    kd_ok),
                ('D',    bd.get('d',0),    not kd_ok),
                ('BB',   bd.get('bb',0),   (20<=bb_v<=80)),
                ('MA',   bd.get('ma',0),   ma_bull),
                ('Vol',  bd.get('vol',0),  (0.8<=vol_v<=1.5)),
            ]"""

new_us_block = """            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (v3.0 US) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',    bd.get('rsi',0),     (40<=rsi_v<=70)),
                ('MACD',   bd.get('macd',0),    (macd_v>0)),
                ('Trend',  bd.get('trend',0),    ma_bull),
                ('KD',     bd.get('kd',0),      kd_ok),
                ('BB',     bd.get('bb',0),      (20<=bb_v<=80)),
                ('Rel.Str',bd.get('rel_str',0), (bd.get('rel_str',0)>=60)),
                ('Vol',    bd.get('vol',0),     (vol_v>=1.2)),
                ('Funda',  bd.get('funda',0),   (bd.get('funda',0)>=35)),
            ]"""

# Replace the second occurrence
content = content.replace(old_us_block, new_us_block, 1)

file.write_text(content, encoding='utf-8')
print("Patched score breakdown display (2 occurrences)")
print("Done!")