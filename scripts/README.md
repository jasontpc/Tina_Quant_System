# Tina 即時分析工具

## 快速呼叫

### 美股分析
```
python tina_telegram.py --us
```

### 單一股票
```
python tina_telegram.py AAPL
python tina_telegram.py TSLA
python tina_telegram.py META
```

### 台股
```
python tina_telegram.py 2330.TW
```

## 快捷批次
- `run_us.bat` - 美股分析
- `run_tw.bat` - 台股分析

## Telegram 設定
在 OpenClaw 中設定命令別名：
- `/us` → `python tina_telegram.py --us`
- `/a [股票]` → `python tina_telegram.py [股票]`