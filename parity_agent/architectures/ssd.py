"""
SSD Architecture Plugin — Decoder for SSD family output format.

Output format: [1, num_anchors, num_classes + 4]
  - Last 4 values per anchor: y_min, x_min, y_max, x_max (normalized)
  - First num_classes values: class scores (softmax-activated)
"""

import numpy as np
from typing import Dict, List, Any

from .base import ModelArchitecture


class SSDArchitecture(ModelArchitecture):
    """Decoder for SSD/MobileNet-SSD TFLite models."""

    @property
    def name(self) -> str:
        return "SSD"

    @property
    def output_format(self) -> str:
        return "[1, num_anchors, num_classes+4] — e.g. [1, 1917, 91+4]"

    def decode_raw_output(
        self,
        raw_output: np.ndarray,
        num_classes: int,
        confidence_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Decode SSD output tensor.

        Note: SSD models from TF Model Zoo typically have
        multiple output tensors. This handles the most common
        single-tensor format.
        """
        output = raw_output[0]  # Remove batch dim

        # Handle different SSD output formats
        if output.shape[-1] == num_classes + 4:
            # Standard: [num_anchors, classes + 4]
            boxes = output[:, -4:]
            scores = output[:, :num_classes]
        elif output.shape[-1] == 4 and len(raw_output) > 1:
            # Multi-tensor: boxes and scores separate
            # This would need the other tensors too
            return []
        else:
            return []

        detections = []
        for i in range(output.shape[0]):
            max_class = int(np.argmax(scores[i]))
            max_conf = float(scores[i, max_class])

            # Skip background class (index 0 in SSD)
            if max_class == 0:
                continue

            if max_conf >= confidence_threshold:
                y1, x1, y2, x2 = boxes[i]
                detections.append({
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": max_conf,
                    "class_index": max_class - 1,  # Adjust for background
                })

        return detections

    def get_search_space(self) -> Dict[str, Dict[str, Any]]:
        """SSD-specific parameter search space."""
        return {
            "confidence_threshold": {
                "type": "continuous", "min": 0.1, "max": 0.9,
                "step": 0.1, "default": 0.5,
                "description": "Detection confidence threshold",
            },
            "iou_threshold": {
                "type": "continuous", "min": 0.2, "max": 0.8,
                "step": 0.05, "default": 0.5,
                "description": "NMS IoU threshold",
            },
            "normalization": {
                "type": "categorical",
                "values": ["divide_255", "neg1_pos1", "none"],
                "default": "divide_255",
                "description": "Input normalization",
            },
        }

    def get_hypothesis_rules(self) -> List[Dict[str, Any]]:
        """SSD-specific hypothesis rules."""
        return [
            {
                "condition": lambda p: p["metric_averages"].get("count_diff", 0) > 5,
                "hypothesis": "ssd_confidence_mismatch",
                "description": "SSD confidence threshold differs",
                "params_to_test": ["confidence_threshold"],
                "priority": "high",
            },
            {
                "condition": lambda p: p["dominant_stage"] == "preprocessing",
                "hypothesis": "ssd_normalization",
                "description": "SSD input normalization differs",
                "params_to_test": ["normalization"],
                "priority": "high",
            },
        ]
