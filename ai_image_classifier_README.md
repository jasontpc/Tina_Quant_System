# TensorFlow Lite 本地 AI 圖片分類腳本使用說明

## 腳本位置
`Tina_Quant_System/ai_image_classifier.py`

## 功能
- 使用 MobileNet V2 AI 模型對圖片進行本機分類
- 完全離線運行，保護隱私
- 自動識別：室內/室外/建築/食物/人物/風景等場景

## 安裝依賴（首次使用）

```bash
pip install tensorflow pillow numpy
```

然後下載模型：
```bash
python ai_image_classifier.py --download-model
```

## 使用方式

### 單張圖片分類
```bash
python ai_image_classifier.py --classify "C:\path\to\photo.jpg"
```

### 批量分類資料夾
```bash
python ai_image_classifier.py --folder "C:\Users\USER\Pictures\Photos-iPhone" --output results.json
```

### 輸出格式
```json
{
  "IMG_1234.jpg": {
    "category": "outdoor",
    "confidence": 0.87,
    "method": "tflite model"
  }
}
```

## 分類類別（自訂簡化映射）

| 類別 | 說明 |
|:-----|:-----|
| indoor | 室內場景（房間/廚房/浴室）|
| outdoor | 室外場景（街道/建築/花園）|
| construction | 建築工程（工地/鋼筋/模板）|
| food | 美食 |
| people | 人物 |
| nature | 自然風景 |
| vehicle | 交通工具 |
| electronics | 電子產品 |
| furniture | 家具 |
| document | 文件圖表 |

## 注意事項

- 模型下載約 4MB（國外伺服器，可能需要時間）
- 第一次執行會下載模型，後續可離線使用
- 如不安裝 TensorFlow，腳本會自動降級為關鍵字分類（仍可使用）
- 大量圖片分類建議分批執行

## 技術規格

| 項目 | 內容 |
|:-----|:-----:|
| 模型 | MobileNet V2（Google 預訓練）|
| 模型大小 | ~4MB |
| 輸入尺寸 | 224x224 |
| 輸出類別 | 1000+ ImageNet classes |
| 運行環境 | Python 3.8+, TensorFlow 2.x |