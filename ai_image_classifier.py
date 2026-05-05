# -*- coding: utf-8 -*-
"""
TensorFlow Lite 本地 AI 圖片分類腳本
功能：使用 MobileNet V2 模型對圖片進行本地 AI 分類
用途：自動識別工程圖片、生活照片等（完全離線，保護隱私）
模型：MobileNet V2（預訓練，~4MB）
"""

import os
import sys
import json
from pathlib import Path

try:
    import numpy as np
    import PIL.Image as Image
except ImportError:
    print("numpy and Pillow required: pip install numpy pillow")
    sys.exit(1)

# Try to import TFLite interpreter
try:
    import tensorflow as tf
    # Check if TFLite interpreter is available
    # For full TF, we use tf.lite
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("TensorFlow not installed. Use --install to install it.")

SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "mobilenet_v2_1.0_224.tflite"
LABELS_PATH = SCRIPT_DIR / "imagenet_labels.txt"
TEMP_IMAGE = SCRIPT_DIR / "temp_input.jpg"

# ImageNet labels (MobileNet V2 output classes)
IMAGENET_LABELS = [
    "背景", "前景物體",
    # Top-level categories we'll use for our classification
]

def get_simple_labels():
    """Return a simplified mapping for photo categories."""
    return {
        "indoor": ["room", "interior", "home", "house", "office", "kitchen", "bedroom", "bathroom", "toilet", "corridor", "hallway"],
        "outdoor": ["outdoor", "street", "building", "house", "garden", "yard", "park", "road", "sidewalk", "highway"],
        "construction": ["construction", "building", "skyscraper", "house", "office building", "church", "castle"],
        "food": ["food", "dish", "meal", "plate", "bowl", "cup", "glass", "spoon", "fork", "knife", "pizza", "burger", "salad"],
        "people": ["person", "man", "woman", "child", "people", "face", "portrait", "group"],
        "nature": ["nature", "tree", "flower", "plant", "landscape", "mountain", "beach", "ocean", "forest", "grass"],
        "vehicle": ["car", "truck", "bus", "motorcycle", "bicycle", "vehicle", "ambulance", "taxi"],
        "electronics": ["screen", "monitor", "laptop", "computer", "keyboard", "mouse", "phone", "camera"],
        "furniture": ["furniture", "chair", "table", "desk", "couch", "sofa", "bed", "shelf", "cabinet"],
        "document": ["document", "paper", "book", "page", "text", "chart", "diagram", "blueprint"],
    }

def download_model():
    """Download MobileNet V2 TFLite model if not present."""
    if MODEL_PATH.exists():
        print(f"Model already exists: {MODEL_PATH}")
        return True
    
    print("Downloading MobileNet V2 TFLite model...")
    try:
        import urllib.request
        url = "https://storage.googleapis.com/tensorflow-1.4.1.tflite/mobilenet_v2_1.0_224.tflite"
        urllib.request.urlretrieve(url, str(MODEL_PATH))
        print(f"Model downloaded: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"Failed to download model: {e}")
        return False

def preprocess_image(image_path, target_size=(224, 224)):
    """Preprocess image for MobileNet V2."""
    try:
        img = Image.open(image_path).convert('RGB')
        img = img.resize(target_size, Image.BILINEAR)
        img_array = np.array(img, dtype=np.float32)
        img_array = (img_array / 127.5) - 1.0  # Normalize to [-1, 1]
        img_array = np.expand_dims(img_array, axis=0)
        return img_array
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        return None

def classify_image_simple(image_path):
    """
    Simple keyword-based classification without AI model.
    Uses filename and EXIF data for categorization.
    This works WITHOUT TensorFlow installed.
    """
    filename = Path(image_path).stem.lower()
    
    # Categories to detect from filename
    keywords = {
        "工程-室內裝修": ["室內", "裝修", "範圍", "差异", "竣工", "圖面", "平面", "立面", "配置", "水電", "機電", "消防", "弱電"],
        "工程-估價": ["估價", "計價", "報價", "發包", "材料", "報價", "預算"],
        "工程-結構": ["鋼筋", "混凝土", "模板", "結構", "基礎", "梁", "柱", "版"],
        "生活-美食": ["美食", "食物", "餐廳", "吃", "料理", " cooking"],
        "生活-風景": ["風景", "景", "山海", "沙灘", "日出", "日落"],
        "生活-人物": ["人像", "自拍", "團體", "合照"],
        "截圖": ["截圖", "screenshot", "snip", "capture"],
        "文件": ["文件", "pdf", "doc", "合約", "證書", "執照"],
    }
    
    for category, kws in keywords.items():
        if any(kw.lower() in filename for kw in kws):
            return category, 0.95, "filename match"
    
    return "未分類", 0.0, "no match"

def classify_with_tflite(image_path):
    """Classify image using TFLite model."""
    if not MODEL_PATH.exists():
        print("Model not found. Using simple classification.")
        return classify_image_simple(image_path)
    
    try:
        # Load model
        interpreter = tf.lite.Interpreter(model_path=str(MODEL_PATH))
        interpreter.allocate_tensors()
        
        input_index = interpreter.get_input_details()[0]['index']
        output_index = interpreter.get_output_details()[0]['index']
        
        # Preprocess
        input_data = preprocess_image(image_path)
        if input_data is None:
            return classify_image_simple(image_path)
        
        # Run inference
        interpreter.set_tensor(input_index, input_data)
        interpreter.invoke()
        output = interpreter.tensor(output_index)[0]
        
        # Get top result
        top_idx = np.argmax(output)
        confidence = float(output[top_idx])
        
        # Map to simple category
        simple_labels = get_simple_labels()
        # For now, just return the ImageNet class
        return f"ImageNet_{top_idx}", confidence, "tflite model"
        
    except Exception as e:
        print(f"TFLite inference failed: {e}")
        return classify_image_simple(image_path)

def batch_classify_folder(folder_path, extensions=None):
    """
    Batch classify all images in a folder.
    
    Args:
        folder_path: Path to folder
        extensions: List of extensions to process (default: jpg, jpeg, png, webp)
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return
    
    # Get all image files
    image_files = []
    for ext in extensions:
        image_files.extend(folder.glob(f"*{ext}"))
        image_files.extend(folder.glob(f"*{ext.upper()}"))
    
    if not image_files:
        print(f"No images found in {folder}")
        return
    
    print(f"Found {len(image_files)} images to classify")
    
    results = {}
    for img_path in image_files:
        category, confidence, method = classify_with_tflite(str(img_path))
        results[img_path.name] = {
            "category": category,
            "confidence": confidence,
            "method": method
        }
        
        if len(results) % 50 == 0:
            print(f"Processed {len(results)}/{len(image_files)}")
    
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description="TF Lite Image Classifier (Local AI)")
    parser.add_argument('--install', action='store_true', help='Install TensorFlow and dependencies')
    parser.add_argument('--download-model', action='store_true', help='Download TFLite model')
    parser.add_argument('--classify', type=str, help='Classify a single image')
    parser.add_argument('--folder', type=str, help='Batch classify a folder')
    parser.add_argument('--output', type=str, help='Output JSON file for batch results')
    
    args = parser.parse_args()
    
    if args.install:
        print("Installing TensorFlow...")
        os.system("pip install tensorflow pillow numpy")
        print("Done. Run --download-model to get the AI model.")
        return
    
    if args.download_model:
        download_model()
        return
    
    if args.classify:
        category, confidence, method = classify_with_tflite(args.classify)
        print(f"Image: {args.classify}")
        print(f"Category: {category}")
        print(f"Confidence: {confidence:.2%}")
        print(f"Method: {method}")
        return
    
    if args.folder:
        results = batch_classify_folder(args.folder)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return
    
    # Default: show help
    print("TFLite Image Classifier (Local AI, Privacy-Safe)")
    print()
    print("Usage:")
    print("  --install          Install TensorFlow")
    print("  --download-model   Download MobileNet V2 model")
    print("  --classify <path>  Classify single image")
    print("  --folder <path>    Batch classify folder")
    print("  --output <path>    Save batch results to JSON")
    print()
    print("Example:")
    print("  python ai_image_classifier.py --download-model")
    print("  python ai_image_classifier.py --classify photo.jpg")
    print("  python ai_image_classifier.py --folder ./Photos --output results.json")

if __name__ == '__main__':
    main()
