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
import numpy as np
from collections import defaultdict

app = Flask(__name__)
CORS(app)  # Allow Flutter app to call this

# Load your TFLite model using Ultralytics
# Primary: assets/model.tflite (used in Flutter app)
# Fallback: best_float32.tflite if available
import os

# Get project root directory
# In Docker: /app
# Local dev: two levels up from lib/backend/
if os.path.exists('/app/assets/model.tflite'):
    # Docker environment
    project_root = '/app'
    print("🐳 Running in Docker environment")
else:
    # Local development
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("💻 Running in local development environment")

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

# ============================================================================
# OBJECT TRACKING SYSTEM FOR LIVE DETECTION
# ============================================================================
class FruitTracker:
    """IoU-based tracker that assigns unique IDs to fruits and prevents duplicate counting"""
    
    def __init__(self, max_disappeared=5, iou_threshold=0.3):
        self.next_id = 0
        self.objects = {}  # {id: {'bbox': [...], 'class': '...', 'confidence': 0.0, 'frames_seen': 0}}
        self.max_disappeared = max_disappeared
        self.iou_threshold = iou_threshold
        self.disappeared = {}  # Track how many frames object hasn't been seen
    
    def calculate_iou(self, box1, box2):
        """Calculate Intersection over Union between two bounding boxes"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Calculate intersection area
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def update(self, detections):
        """
        Update tracker with new detections.
        Returns: (tracked_objects_dict, new_fruits_count)
        """
        if len(detections) == 0:
            # No detections, mark all existing objects as disappeared
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    # Remove object after being gone too long
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return self.objects.copy(), 0
        
        # If no existing objects, register all detections as new
        if len(self.objects) == 0:
            new_count = 0
            for det in detections:
                obj_id = self.next_id
                self.next_id += 1
                self.objects[obj_id] = {
                    'bbox': det['bbox'],
                    'class': det['class'],
                    'confidence': det['confidence'],
                    'frames_seen': 1
                }
                self.disappeared[obj_id] = 0
                new_count += 1
            return self.objects.copy(), new_count
        
        # Match detections to existing objects using IoU
        used_detection_indices = set()
        used_object_ids = set()
        
        # Build IoU matrix
        obj_ids_list = list(self.objects.keys())
        iou_matrix = []
        for obj_id in obj_ids_list:
            obj = self.objects[obj_id]
            iou_row = []
            for det in detections:
                iou = self.calculate_iou(obj['bbox'], det['bbox'])
                iou_row.append(iou)
            iou_matrix.append(iou_row)
        
        # Greedy matching: find best IoU matches
        matches = []
        for _ in range(min(len(self.objects), len(detections))):
            best_iou = 0
            best_obj_idx = -1
            best_det_idx = -1
            
            for obj_idx in range(len(iou_matrix)):
                if obj_idx in used_object_ids:
                    continue
                for det_idx in range(len(iou_matrix[obj_idx])):
                    if det_idx in used_detection_indices:
                        continue
                    if iou_matrix[obj_idx][det_idx] > best_iou:
                        best_iou = iou_matrix[obj_idx][det_idx]
                        best_obj_idx = obj_idx
                        best_det_idx = det_idx
            
            if best_iou >= self.iou_threshold:
                matches.append((best_obj_idx, best_det_idx))
                used_object_ids.add(best_obj_idx)
                used_detection_indices.add(best_det_idx)
        
        # Update matched objects with smoothed bounding boxes
        for obj_idx, det_idx in matches:
            obj_id = obj_ids_list[obj_idx]
            det = detections[det_idx]
            
            # Smooth bounding box update (moving average for stability)
            old_bbox = np.array(self.objects[obj_id]['bbox'], dtype=np.float32)
            new_bbox = np.array(det['bbox'], dtype=np.float32)
            smoothed_bbox = 0.7 * old_bbox + 0.3 * new_bbox  # Weighted average for stability
            
            self.objects[obj_id]['bbox'] = smoothed_bbox.tolist()
            self.objects[obj_id]['confidence'] = det['confidence']
            self.objects[obj_id]['frames_seen'] += 1
            self.disappeared[obj_id] = 0
        
        # Register new detections (not matched to existing objects)
        new_count = 0
        for det_idx, det in enumerate(detections):
            if det_idx not in used_detection_indices:
                obj_id = self.next_id
                self.next_id += 1
                self.objects[obj_id] = {
                    'bbox': det['bbox'],
                    'class': det['class'],
                    'confidence': det['confidence'],
                    'frames_seen': 1
                }
                self.disappeared[obj_id] = 0
                new_count += 1
        
        # Mark unmatched objects as disappeared
        for obj_idx, obj_id in enumerate(obj_ids_list):
            if obj_idx not in used_object_ids:
                self.disappeared[obj_id] = self.disappeared.get(obj_id, 0) + 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    # Remove after being gone too long
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
        
        return self.objects.copy(), new_count
    
    def get_total_count(self):
        """Get total number of unique fruits counted"""
        return self.next_id
    
    def reset(self):
        """Reset tracker for new counting session"""
        self.next_id = 0
        self.objects = {}
        self.disappeared = {}

# Global tracker instance (persists across requests)
tracker = FruitTracker(max_disappeared=5, iou_threshold=0.3)

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

@app.route('/detect_live', methods=['POST'])
def detect_live():
    """Live detection endpoint with object tracking for real-time counting"""
    try:
        # Get image from request
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Run detection with Ultralytics
        results = model.predict(image, conf=0.25, iou=0.45, verbose=False)
        
        # Format detections
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get bounding box coordinates (xyxy format)
                bbox = box.xyxy[0].cpu().numpy().tolist()
                
                # Get class index and map to fruit name
                class_idx = int(box.cls)
                if class_idx < len(class_names):
                    class_name = class_names[class_idx]
                else:
                    class_name = model.names.get(class_idx, f'class{class_idx}')
                
                detections.append({
                    'class': class_name,
                    'confidence': float(box.conf),
                    'bbox': bbox,  # [x1, y1, x2, y2]
                })
        
        # Update tracker with new detections
        tracked_objects, new_count = tracker.update(detections)
        
        # Format tracked objects for response
        tracked_list = []
        for obj_id, obj in tracked_objects.items():
            tracked_list.append({
                'id': obj_id,
                'class': obj['class'],
                'bbox': obj['bbox'],
                'confidence': obj['confidence'],
                'frames_seen': obj['frames_seen']
            })
        
        return jsonify({
            'success': True,
            'tracked_objects': tracked_list,
            'total_count': tracker.get_total_count(),
            'new_count_this_frame': new_count,
            'active_objects': len(tracked_objects)
        })
        
    except Exception as e:
        print(f"❌ Error in detect_live: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/reset_tracker', methods=['POST'])
def reset_tracker():
    """Reset tracker for new counting session"""
    try:
        global tracker
        old_count = tracker.get_total_count()
        tracker.reset()
        print(f"🔄 Tracker reset. Previous count: {old_count}")
        return jsonify({
            'success': True,
            'previous_count': old_count,
            'message': 'Tracker reset successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tracker_status', methods=['GET'])
def tracker_status():
    """Get current tracker status"""
    try:
        return jsonify({
            'success': True,
            'total_count': tracker.get_total_count(),
            'active_objects': len(tracker.objects),
            'tracker_info': {
                'max_disappeared': tracker.max_disappeared,
                'iou_threshold': tracker.iou_threshold
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model': 'loaded'})

if __name__ == '__main__':
    # Get port from environment variable (for cloud deployments) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') != 'production'
    
    print("Starting fruit detection server...")
    print(f"Server will run on http://0.0.0.0:{port}")
    print(f"Looking for model at: {os.path.join(project_root, 'assets', 'model.tflite')}")
    print(f"Debug mode: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
