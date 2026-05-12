import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import shioaji as sj
import numpy as np

api = sj.Shioaji()
api.login(
    api_key='3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW',
    secret_key='FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF'
)
print('Login OK')

# 測試 2330
contract = api.Contracts.Stocks['2330']
print('Contract:', contract)
kbars = api.kbars(contract, start='2024-01-01', end='2024-12-31')

print('Type:', type(kbars))
print('Fields: ts, Close, Open, High, Low, Volume, Amount')

ts = kbars.ts
close = kbars.Close
open_ = kbars.Open
high = kbars.High
low = kbars.Low
volume = kbars.Volume

print('Count:', len(ts))
print('First: ts=' + str(ts[0]) + ', close=' + str(close[0]))
print('Last: ts=' + str(ts[-1]) + ', close=' + str(close[-1]))

# 計算 RSI
closes = np.array(close)
delta = np.diff(closes)
gain = np.clip(delta, 0, None).mean()
loss = np.clip(-delta, 0, None).mean()
rs = gain / loss if loss > 0 else 0
rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
print('RSI:', rsi)

print('Done')