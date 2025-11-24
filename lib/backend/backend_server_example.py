"""
Simple Flask backend server to use Ultralytics for fruit detection.
Run this server, then update Flutter app to send images to it.

Usage:
    pip install flask ultralytics pillow
    python backend_server_example.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import io
from PIL import Image

app = Flask(__name__)
CORS(app)  # Allow Flutter app to call this

# Load your TFLite model using Ultralytics
# Primary: assets/model.tflite (used in Flutter app)
# Fallback: best_float32.tflite if available
import os

# Get project root directory (two levels up from lib/backend/)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

model_path = os.path.join(project_root, 'assets', 'model.tflite')
if not os.path.exists(model_path):
    # Try fallback location
    fallback_path = os.path.join(project_root, 'runs', 'multi_fruit_model', 'weights', 'best_saved_model', 'best_float32.tflite')
    if os.path.exists(fallback_path):
        model_path = fallback_path
        print(f"⚠️ Using fallback model: {model_path}")
    else:
        print(f"❌ Model not found! Expected: {os.path.join(project_root, 'assets', 'model.tflite')}")
        raise FileNotFoundError("TFLite model not found. Please ensure assets/model.tflite exists.")
else:
    print(f"✅ Using model: {model_path}")

model = YOLO(model_path)

# Load class names from labels.txt (same as Flutter app uses)
def load_class_names():
    labels_path = os.path.join(project_root, 'assets', 'labels.txt')
    class_names = []
    try:
        with open(labels_path, 'r') as f:
            class_names = [line.strip() for line in f if line.strip()]
        print(f"✅ Loaded {len(class_names)} class names from {labels_path}")
        return class_names
    except FileNotFoundError:
        print(f"⚠️ labels.txt not found, using model.names")
        # Fallback to model names if labels.txt not found
        return [model.names.get(i, f'class{i}') for i in range(len(model.names))]

class_names = load_class_names()

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # Get image from request
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Run detection with Ultralytics (exact same as your working code)
        results = model.predict(image, conf=0.25, iou=0.45, verbose=False)
        
        # Format results for Flutter
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get bounding box coordinates (xyxy format)
                bbox = box.xyxy[0].cpu().numpy().tolist()
                
                # Get class index and map to fruit name
                class_idx = int(box.cls)
                # Use class_names from labels.txt, fallback to model.names
                if class_idx < len(class_names):
                    class_name = class_names[class_idx]
                else:
                    class_name = model.names.get(class_idx, f'class{class_idx}')
                
                detections.append({
                    'class': class_name,
                    'confidence': float(box.conf),
                    'bbox': bbox,  # [x1, y1, x2, y2]
                })
        
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model': 'loaded'})

if __name__ == '__main__':
    print("Starting fruit detection server...")
    print("Server will run on http://localhost:5000")
    print(f"Looking for model at: {os.path.join(project_root, 'assets', 'model.tflite')}")
    app.run(host='0.0.0.0', port=5000, debug=True)
