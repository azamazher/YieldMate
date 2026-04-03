"""
Offline Tracer — Captures Golden Traces from the TFLite pipeline.

This replicates the Dart/Flutter preprocessing and postprocessing logic
in Python so traces are directly comparable to the online pipeline.

Key Dart logic replicated here (from model_service.dart + detection_service.dart):
  - Letterbox resize with gray (114,114,114) padding
  - Bilinear interpolation
  - RGB channel order
  - Pixel values / 255.0 normalization
  - Output shape: [1, 12, 8400] → transposed to [8400, 12]
  - Sigmoid activation on class logits (indices 4-11)
  - xywh → xyxy conversion
  - NMS with configurable thresholds
"""

import math
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image

from .schema import PipelineTrace, Detection


class OfflineTracer:
    """
    Captures traces from the offline TFLite pipeline.
    
    Replicates the exact Dart preprocessing and postprocessing to ensure
    the offline trace is what the Flutter app would actually produce.
    """

    def __init__(self, model_path: str, labels: List[str], config: Dict[str, Any]):
        """
        Initialize the offline tracer.

        Args:
            model_path: Path to the TFLite model file.
            labels: List of class names.
            config: Offline pipeline config dict from config.yaml.
        """
        self.model_path = model_path
        self.labels = labels
        self.config = config
        self.input_size = 640  # Standard YOLO input

        # Load TFLite model
        self.interpreter = self._load_model(model_path)

        # Get input/output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def _load_model(self, model_path: str):
        """Load TFLite model via tensorflow.lite."""
        try:
            import tensorflow as tf
            interpreter = tf.lite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            return interpreter
        except ImportError:
            try:
                import tflite_runtime.interpreter as tflite
                interpreter = tflite.Interpreter(model_path=model_path)
                interpreter.allocate_tensors()
                return interpreter
            except ImportError:
                raise ImportError(
                    "Neither tensorflow nor tflite_runtime is installed. "
                    "Install one: pip install tensorflow or pip install tflite-runtime"
                )

    def trace_image(self, image_path: str) -> PipelineTrace:
        """
        Run inference on a single image and capture the full trace.

        Replicates the exact Dart pipeline:
        1. Load image
        2. Letterbox resize with gray padding
        3. Normalize to [0, 1]
        4. Run TFLite inference
        5. Transpose + decode + sigmoid
        6. NMS

        Args:
            image_path: Path to the input image.

        Returns:
            PipelineTrace with all four checkpoints populated.
        """
        image_id = Path(image_path).stem
        image = Image.open(image_path).convert("RGB")
        img_width, img_height = image.size

        # --- Checkpoint 1: Preprocess (replicating Dart letterbox) ---
        input_tensor, preprocess_meta = self._preprocess(image)

        # --- Run TFLite inference ---
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        self.interpreter.invoke()

        # --- Checkpoint 2: Raw output ---
        raw_output = self.interpreter.get_tensor(self.output_details[0]['index']).copy()

        # --- Checkpoint 3: Decode (replicating Dart detection_service.dart) ---
        decoded_boxes = self._decode_output(
            raw_output, img_width, img_height, preprocess_meta
        )

        # --- Checkpoint 4: NMS ---
        nms_boxes = self._apply_nms(decoded_boxes)

        trace = PipelineTrace(
            image_id=image_id,
            pipeline="offline",
            input_tensor=input_tensor,
            raw_output=raw_output,
            decoded_boxes=decoded_boxes,
            nms_boxes=nms_boxes,
            metadata={
                "image_path": str(image_path),
                "image_width": img_width,
                "image_height": img_height,
                "config": self.config,
                "preprocess": preprocess_meta,
            },
        )
        return trace

    def _preprocess(self, image: Image.Image) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Letterbox preprocessing — exact replica of Dart model_service.dart.

        Steps (from Dart lines 156-196):
        1. Calculate scale to fit within input_size maintaining aspect ratio
        2. Resize with bilinear interpolation
        3. Create canvas filled with gray (114, 114, 114)
        4. Center the resized image on canvas
        5. Normalize pixel values to [0, 1]
        """
        img_width, img_height = image.size
        img_array = np.array(image)

        # Calculate scale factor (same as Dart)
        scale = min(self.input_size / img_width, self.input_size / img_height)
        new_w = round(img_width * scale)
        new_h = round(img_height * scale)

        # Resize method from config
        resize_method = self.config.get("resize_method", "bilinear")
        pil_methods = {
            "bilinear": Image.BILINEAR,
            "nearest": Image.NEAREST,
            "area": Image.BOX,
            "lanczos": Image.LANCZOS,
        }
        resample = pil_methods.get(resize_method, Image.BILINEAR)
        resized = image.resize((new_w, new_h), resample)
        resized_array = np.array(resized)

        # Create canvas with padding color
        padding_color = self.config.get("padding_color", [114, 114, 114])
        canvas = np.full(
            (self.input_size, self.input_size, 3),
            padding_color, dtype=np.uint8,
        )

        # Center the resized image
        dx = (self.input_size - new_w) // 2
        dy = (self.input_size - new_h) // 2
        canvas[dy:dy + new_h, dx:dx + new_w] = resized_array

        # Handle channel order
        channel_order = self.config.get("channel_order", "rgb")
        if channel_order == "bgr":
            canvas = canvas[:, :, ::-1]

        # Normalize
        normalization = self.config.get("normalization", "divide_255")
        if normalization == "divide_255":
            tensor = canvas.astype(np.float32) / 255.0
        elif normalization == "neg1_pos1":
            tensor = (canvas.astype(np.float32) / 127.5) - 1.0
        elif normalization == "none":
            tensor = canvas.astype(np.float32)
        else:
            tensor = canvas.astype(np.float32) / 255.0

        # Add batch dimension: [1, H, W, 3]
        tensor = np.expand_dims(tensor, axis=0)

        meta = {
            "scale": scale,
            "dx": dx,
            "dy": dy,
            "new_w": new_w,
            "new_h": new_h,
            "resize_method": resize_method,
            "normalization": normalization,
            "channel_order": channel_order,
        }

        return tensor, meta

    def _decode_output(
        self, raw_output: np.ndarray,
        img_width: int, img_height: int,
        preprocess_meta: Dict[str, Any],
    ) -> List[Detection]:
        """
        Decode raw TFLite output — exact replica of Dart detection_service.dart.

        Steps (from Dart lines 26-177):
        1. Determine output format and transpose if needed
        2. For each detection: extract cx, cy, w, h + class logits
        3. Apply sigmoid to class logits
        4. Find max class probability
        5. Filter by confidence threshold
        6. Convert xywh → xyxy (normalized 0-1)
        """
        conf_threshold = self.config.get("confidence_threshold", 0.5)
        apply_sigmoid = self.config.get("apply_sigmoid", True)

        # Handle output shape — replicate Dart logic
        output = raw_output.squeeze()  # Remove batch dim if present

        if output.ndim == 2:
            first_dim, second_dim = output.shape
        else:
            raise ValueError(f"Unexpected output shape: {output.shape}")

        # Transpose logic from Dart (lines 36-53)
        if first_dim >= 7 and second_dim >= 100:
            # Format: [classes+4, num_detections] → transpose
            detections_array = output.T  # [num_detections, classes+4]
        elif second_dim >= 7 and first_dim >= 100:
            # Format: [num_detections, classes+4] — already correct
            detections_array = output
        else:
            raise ValueError(
                f"Unexpected output dimensions: {first_dim}x{second_dim}. "
                "Expected YOLO format [12, N] or [N, 12]."
            )

        decoded = []
        num_classes = len(self.labels)
        class_start_idx = 4  # Dart: classProbStartIndex = 4

        for det in detections_array:
            if len(det) < 4 + num_classes:
                continue

            cx, cy, w, h = det[0], det[1], det[2], det[3]

            # Extract class logits and find max
            class_logits = det[class_start_idx:class_start_idx + num_classes]

            if apply_sigmoid:
                # Dart lines 96-111: sigmoid activation
                clamped = np.clip(class_logits, -20.0, 20.0)
                probs = 1.0 / (1.0 + np.exp(-clamped))
            else:
                probs = class_logits

            max_prob = float(np.max(probs))
            class_idx = int(np.argmax(probs))

            # Filter by confidence (Dart line 123)
            if max_prob < conf_threshold:
                continue

            # Validate bbox
            if w <= 0 or h <= 0 or np.isnan(cx) or np.isnan(cy):
                continue

            # Convert xywh → xyxy (Dart lines 154-158)
            left = cx - w / 2
            top = cy - h / 2
            right = cx + w / 2
            bottom = cy + h / 2

            if right <= left or bottom <= top:
                continue

            # Clamp to [0, 1] (Dart lines 164-168)
            left = max(0.0, min(1.0, left))
            top = max(0.0, min(1.0, top))
            right = max(0.0, min(1.0, right))
            bottom = max(0.0, min(1.0, bottom))

            if right <= left or bottom <= top:
                continue

            class_name = self.labels[class_idx] if class_idx < len(self.labels) else f"class{class_idx}"

            decoded.append(Detection(
                class_name=class_name,
                class_index=class_idx,
                confidence=max_prob,
                bbox=[left, top, right, bottom],
            ))

        return decoded

    def _apply_nms(self, detections: List[Detection]) -> List[Detection]:
        """
        Non-Maximum Suppression — replica of Dart detection_service.dart lines 200-219.
        
        Greedy NMS: sort by confidence desc, suppress overlapping boxes.
        """
        if not detections:
            return []

        iou_threshold = self.config.get("iou_threshold", 0.45)

        # Sort by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)

        keep = []
        remaining = list(range(len(sorted_dets)))

        while remaining:
            i = remaining.pop(0)
            keep.append(sorted_dets[i])

            suppressed = []
            for j_idx, j in enumerate(remaining):
                iou = self._calculate_iou(sorted_dets[i].bbox, sorted_dets[j].bbox)
                if iou > iou_threshold:
                    suppressed.append(j)

            remaining = [j for j in remaining if j not in suppressed]

        return keep

    @staticmethod
    def _calculate_iou(box_a: List[float], box_b: List[float]) -> float:
        """
        IoU calculation — replica of Dart detection_service.dart lines 222-249.
        
        Args:
            box_a, box_b: [x1, y1, x2, y2] normalized coordinates.
        """
        inter_left = max(box_a[0], box_b[0])
        inter_top = max(box_a[1], box_b[1])
        inter_right = min(box_a[2], box_b[2])
        inter_bottom = min(box_a[3], box_b[3])

        if inter_right <= inter_left or inter_bottom <= inter_top:
            return 0.0

        inter_area = (inter_right - inter_left) * (inter_bottom - inter_top)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union_area = area_a + area_b - inter_area

        if union_area <= 0:
            return 0.0

        return inter_area / union_area

    def trace_batch(self, image_paths: List[str]) -> List[PipelineTrace]:
        """Trace a batch of images."""
        traces = []
        for path in image_paths:
            try:
                trace = self.trace_image(path)
                traces.append(trace)
            except Exception as e:
                print(f"[OfflineTracer] Error tracing {path}: {e}")
        return traces
