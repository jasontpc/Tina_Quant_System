# Tina Strategy Review Report

**Date**: 2026-05-05  
**Analyst**: Tina

---

## Overall Statistics

| Item | Value |
|------|-------|
| Total Trades | 8720 |
| Wins | 5442 |
| Losses | 3278 |
| Win Rate | 62.4% |
| Avg PnL | +2.09% if valid else +0.00% |
| Total PnL | +18224.29% |

---

## Market Regime

| Item | Value |
|------|-------|
| Regime | UNKNOWN |
| MA Slope | 0.0000 |
| Avg Volatility | 0.0000 |

---

## RSI Zone Performance

| Zone | Count | Win Rate | Avg PnL | Avg Win | Avg Loss |
|------|-------|----------|---------|---------|----------|
| RSI<30 | 4176 | 62.7% | +2.48% | +8.31% | -7.31% |
| RSI30-40 | 3661 | 61.6% | +1.82% | +7.99% | -8.10% |
| RSI40-50 | 0 | N/A | N/A | N/A | N/A |
| RSI50-60 | 0 | N/A | N/A | N/A | N/A |
| RSI>60 | 0 | N/A | N/A | N/A | N/A |

## Strategy Performance

| Strategy | Count | Win Rate | Avg PnL | Avg Win | Avg Loss |
|----------|-------|----------|---------|---------|----------|
| max_hold=20 | 1017 | 29.6% | -4.09% | +4.01% | -7.49% |
| MAX_HOLD | 446 | 31.2% | -2.32% | +2.92% | -4.69% |
| RSI_Aggressive | 857 | 61.6% | +1.42% | +6.33% | -6.45% |
| RSI_Rev_Low | 1166 | 61.1% | +2.17% | +8.10% | -7.15% |
| RSI_Rev_High | 1759 | 59.9% | +2.32% | +9.81% | -8.86% |
| RSI_Rev_Mid | 1524 | 61.9% | +2.39% | +9.04% | -8.44% |
| DCA_Monthly | 273 | 68.9% | +3.05% | +7.41% | -6.59% |
| DCA_Weekly | 229 | 72.1% | +3.57% | +6.60% | -4.26% |
| RSI_OVERBought | 437 | 98.4% | +5.15% | +5.26% | -1.55% |
| RSI>65 | 1012 | 96.9% | +7.95% | +8.27% | -1.98% |

## Worst Scenarios (Top 3)

### 1. COIN -- -52.56%

- Entry: 2022-04-11 | Exit: 2022-05-10
- Entry RSI: 32.37771217596351 | Exit RSI: 18.19117206800675
- Hold: 20 days | Strategy: max_hold=20 | System: Maggy
- Lesson: No record

### 2. NFLX -- -48.95%

- Entry: 2022-04-11 | Exit: 2022-05-10
- Entry RSI: 34.03438040998226 | Exit RSI: 27.303345148035845
- Hold: 20 days | Strategy: max_hold=20 | System: Maggy
- Lesson: No record

### 3. LYFT -- -42.98%

- Entry: 2022-04-11 | Exit: 2022-05-10
- Entry RSI: 33.08167327235054 | Exit RSI: 13.020379567351284
- Hold: 20 days | Strategy: max_hold=20 | System: Maggy
- Lesson: No record


## Optimization Recommendations

### [MED] 1. Market Regime Adaptation

**Market regime unknown, use conservative RSI 35-50 with MA confirmation

### [HIGH] 2. Strategy Performance

**Strategy 'max_hold=20' avg PnL=-4.09%, review or disable


---

## Recommended Parameter Version

Based on this review:

```
Version: v3_adapted
Changes (per UNKNOWN regime):
  - RSI entry max: 45 -> 40 (tighter entry in range/trend market)
  - Max hold days: 20 -> 15 (reduce exposure)
  - ATR stop: 2.0 -> 1.5 (more responsive stop)
```

---

_Generated: 2026-05-05 16:06:34_  
_Tina Quant System v3.12 | Tina_
