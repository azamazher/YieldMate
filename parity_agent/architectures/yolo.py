"""
YOLOv8 Architecture Plugin — Decoder for YOLO family output format.

Output format: [1, num_classes + 4, num_anchors]
  - Indices 0-3: cx, cy, w, h (normalized bounding box)
  - Indices 4+: class probabilities (already sigmoid-activated)
"""

import numpy as np
from typing import Dict, List, Any

from .base import ModelArchitecture


class YOLOv8Architecture(ModelArchitecture):
    """Decoder for YOLOv8 TFLite models."""

    @property
    def name(self) -> str:
        return "YOLOv8"

    @property
    def output_format(self) -> str:
        return "[1, num_classes+4, num_anchors] — e.g. [1, 12, 8400]"

    def decode_raw_output(
        self,
        raw_output: np.ndarray,
        num_classes: int,
        confidence_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """Decode YOLOv8 output tensor."""
        # raw_output shape: [1, num_classes+4, num_anchors]
        output = raw_output[0]  # Remove batch dim → [12, 8400]

        # Transpose to [num_anchors, num_classes+4]
        if output.shape[0] == num_classes + 4:
            output = output.T  # [8400, 12]

        detections = []
        for i in range(output.shape[0]):
            cx, cy, w, h = output[i, :4]
            class_probs = output[i, 4:4 + num_classes]

            max_class = int(np.argmax(class_probs))
            max_conf = float(class_probs[max_class])

            if max_conf >= confidence_threshold:
                # Convert center to corner format
                x1 = cx - w / 2
                y1 = cy - h / 2
                x2 = cx + w / 2
                y2 = cy + h / 2

                detections.append({
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": max_conf,
                    "class_index": max_class,
                })

        return detections

    def get_search_space(self) -> Dict[str, Dict[str, Any]]:
        """YOLO-specific parameter search space."""
        return {
            "confidence_threshold": {
                "type": "continuous", "min": 0.1, "max": 0.9,
                "step": 0.1, "default": 0.5,
                "description": "Detection confidence threshold",
            },
            "iou_threshold": {
                "type": "continuous", "min": 0.2, "max": 0.8,
                "step": 0.05, "default": 0.45,
                "description": "NMS IoU threshold",
            },
            "apply_sigmoid": {
                "type": "categorical", "values": [True, False],
                "default": True,
                "description": "Apply sigmoid to class logits",
            },
            "normalization": {
                "type": "categorical",
                "values": ["divide_255", "neg1_pos1", "none"],
                "default": "divide_255",
                "description": "Input normalization method",
            },
            "letterbox_padding": {
                "type": "categorical", "values": [True, False],
                "default": True,
                "description": "Use letterbox padding",
            },
        }

    def get_hypothesis_rules(self) -> List[Dict[str, Any]]:
        """YOLO-specific hypothesis generation rules."""
        return [
            {
                "condition": lambda p: p["metric_averages"].get("count_diff", 0) > 10,
                "hypothesis": "confidence_threshold_too_low",
                "description": "Too many weak detections passing threshold",
                "params_to_test": ["confidence_threshold"],
                "priority": "critical",
            },
            {
                "condition": lambda p: p["dominant_stage"] in ("nms_behavior", "localization"),
                "hypothesis": "nms_threshold_mismatch",
                "description": "NMS suppression differs between pipelines",
                "params_to_test": ["iou_threshold", "confidence_threshold"],
                "priority": "high",
            },
            {
                "condition": lambda p: p["dominant_stage"] == "calibration",
                "hypothesis": "sigmoid_double_apply",
                "description": "Sigmoid may be applied twice",
                "params_to_test": ["apply_sigmoid"],
                "priority": "critical",
            },
        ]
