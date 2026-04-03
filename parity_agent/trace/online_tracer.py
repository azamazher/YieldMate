"""
Online Tracer — Captures Golden Traces from the PyTorch/Ultralytics pipeline.

This instruments the Ultralytics YOLO inference to extract tensors at each
checkpoint: input_tensor → raw_output → decoded_boxes → nms_boxes.

The online pipeline is the "ground truth" reference.
"""

import os
import numpy as np
from pathlib import Path
from typing import List, Optional
from PIL import Image
from ultralytics import YOLO

from .schema import PipelineTrace, Detection, GoldenTrace


class OnlineTracer:
    """Captures traces from the online PyTorch/Ultralytics pipeline."""

    def __init__(self, model_path: str, labels: List[str],
                 conf_threshold: float = 0.25, iou_threshold: float = 0.45):
        """
        Initialize the online tracer.

        Args:
            model_path: Path to the TFLite model (loaded via Ultralytics).
            labels: List of class names.
            conf_threshold: Confidence threshold for detection.
            iou_threshold: IoU threshold for NMS.
        """
        self._model_path = model_path
        self.model = YOLO(model_path)
        self.labels = labels
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def trace_image(self, image_path: str) -> PipelineTrace:
        """
        Run inference on a single image and capture the full trace.

        Args:
            image_path: Path to the input image.

        Returns:
            PipelineTrace with all four checkpoints populated.
        """
        image_id = Path(image_path).stem
        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)

        # Run Ultralytics prediction (captures internal state)
        results = self.model.predict(
            image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        result = results[0]
        img_height, img_width = img_array.shape[:2]

        # --- Checkpoint 1: Input tensor ---
        # Ultralytics preprocesses internally; we capture what was fed to the model.
        # The preprocessed tensor is accessible from the result's orig_img vs the
        # internal letterboxed version. We reconstruct the preprocessing here.
        input_tensor = self._get_preprocessed_tensor(img_array)

        # --- Checkpoint 2: Raw output ---
        # Run a SEPARATE TFLite inference to get the actual raw model output
        # (pre-decode, same shape as the offline tracer captures).
        # Ultralytics' result.boxes.data is post-NMS [N, 6] which has a different
        # shape than the offline tracer's raw output [1, 12, 8400].
        raw_output = self._get_raw_tflite_output(input_tensor)

        # --- Checkpoint 3: Decoded boxes (before NMS, above conf threshold) ---
        # In Ultralytics, the returned boxes are already post-NMS.
        # We capture them as "decoded" since Ultralytics handles decode+NMS together.
        decoded_boxes = []
        if result.boxes is not None:
            for box in result.boxes:
                bbox = box.xyxy[0].cpu().numpy()
                class_idx = int(box.cls)
                class_name = self.labels[class_idx] if class_idx < len(self.labels) else f"class{class_idx}"
                confidence = float(box.conf)

                # Normalize bbox to [0, 1]
                norm_bbox = [
                    float(bbox[0]) / img_width,
                    float(bbox[1]) / img_height,
                    float(bbox[2]) / img_width,
                    float(bbox[3]) / img_height,
                ]

                decoded_boxes.append(Detection(
                    class_name=class_name,
                    class_index=class_idx,
                    confidence=confidence,
                    bbox=norm_bbox,
                ))

        # --- Checkpoint 4: NMS boxes ---
        # In Ultralytics, predict() already applies NMS, so decoded == nms
        nms_boxes = decoded_boxes.copy()

        trace = PipelineTrace(
            image_id=image_id,
            pipeline="online",
            input_tensor=input_tensor,
            raw_output=raw_output,
            decoded_boxes=decoded_boxes,
            nms_boxes=nms_boxes,
            metadata={
                "image_path": str(image_path),
                "image_width": img_width,
                "image_height": img_height,
                "conf_threshold": self.conf_threshold,
                "iou_threshold": self.iou_threshold,
                "model_path": str(self.model.model_name) if hasattr(self.model, 'model_name') else "unknown",
            },
        )
        return trace

    def _get_preprocessed_tensor(self, img_array: np.ndarray) -> np.ndarray:
        """
        Replicate Ultralytics letterbox preprocessing to capture the input tensor.

        Uses the same letterbox approach as YOLO: resize maintaining aspect ratio,
        pad with gray (114, 114, 114), normalize to [0, 1].
        """
        input_size = 640  # Standard YOLO input
        h, w = img_array.shape[:2]

        # Calculate scale and padding (same as Ultralytics/Dart)
        scale = min(input_size / w, input_size / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize
        from PIL import Image as PILImage
        resized = PILImage.fromarray(img_array).resize((new_w, new_h), PILImage.BILINEAR)
        resized_array = np.array(resized)

        # Create canvas with gray padding
        canvas = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
        dx = (input_size - new_w) // 2
        dy = (input_size - new_h) // 2
        canvas[dy:dy + new_h, dx:dx + new_w] = resized_array

        # Normalize to [0, 1] float32
        tensor = canvas.astype(np.float32) / 255.0

        # Add batch dimension: [1, H, W, 3]
        tensor = np.expand_dims(tensor, axis=0)

        return tensor

    def _get_raw_tflite_output(self, input_tensor: np.ndarray) -> Optional[np.ndarray]:
        """
        Run a separate TFLite inference to get the raw model output.

        This ensures the raw_output shape matches what the offline tracer captures
        (e.g., [1, 12, 8400]), instead of Ultralytics' post-NMS format [N, 6].
        """
        try:
            # Cache interpreter for reuse across images
            if not hasattr(self, '_tflite_interpreter'):
                try:
                    import tensorflow as tf
                    self._tflite_interpreter = tf.lite.Interpreter(model_path=self._model_path)
                except ImportError:
                    import tflite_runtime.interpreter as tflite
                    self._tflite_interpreter = tflite.Interpreter(model_path=self._model_path)
                self._tflite_interpreter.allocate_tensors()

            interpreter = self._tflite_interpreter
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            interpreter.set_tensor(input_details[0]['index'], input_tensor)
            interpreter.invoke()
            raw = interpreter.get_tensor(output_details[0]['index']).copy()
            return raw
        except Exception as e:
            print(f"[OnlineTracer] Could not get raw TFLite output: {e}")
            return None

    def trace_batch(self, image_paths: List[str]) -> List[PipelineTrace]:
        """Trace a batch of images."""
        traces = []
        for path in image_paths:
            try:
                trace = self.trace_image(path)
                traces.append(trace)
            except Exception as e:
                print(f"[OnlineTracer] Error tracing {path}: {e}")
        return traces
