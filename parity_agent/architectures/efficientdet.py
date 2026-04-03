"""
EfficientDet Architecture Plugin — Decoder for EfficientDet family.

Output format: typically multiple tensors:
  - Boxes: [1, num_anchors, 4]
  - Scores: [1, num_anchors, num_classes]
  
Or combined: [1, max_detections, 7] where each row is
[image_id, ymin, xmin, ymax, xmax, score, class_id]
"""

import numpy as np
from typing import Dict, List, Any

from .base import ModelArchitecture


class EfficientDetArchitecture(ModelArchitecture):
    """Decoder for EfficientDet TFLite models."""

    @property
    def name(self) -> str:
        return "EfficientDet"

    @property
    def output_format(self) -> str:
        return "[1, max_detections, 7] — post-processed EfficientDet format"

    def decode_raw_output(
        self,
        raw_output: np.ndarray,
        num_classes: int,
        confidence_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Decode EfficientDet output tensor.

        Handles the common TFLite post-processed format where
        NMS is already built into the model.
        """
        output = raw_output[0]  # Remove batch dim

        detections = []

        # Format: [max_detections, 7]
        # [image_id, ymin, xmin, ymax, xmax, score, class_id]
        if output.shape[-1] == 7:
            for i in range(output.shape[0]):
                _, y1, x1, y2, x2, score, class_id = output[i]

                if score >= confidence_threshold:
                    detections.append({
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": float(score),
                        "class_index": int(class_id),
                    })
        # Format: [max_detections, 6] — without image_id
        elif output.shape[-1] == 6:
            for i in range(output.shape[0]):
                y1, x1, y2, x2, score, class_id = output[i]
                if score >= confidence_threshold:
                    detections.append({
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": float(score),
                        "class_index": int(class_id),
                    })

        return detections

    def get_search_space(self) -> Dict[str, Dict[str, Any]]:
        """EfficientDet parameter search space (limited — NMS is in-model)."""
        return {
            "confidence_threshold": {
                "type": "continuous", "min": 0.1, "max": 0.9,
                "step": 0.1, "default": 0.4,
                "description": "Post-NMS confidence threshold",
            },
            "normalization": {
                "type": "categorical",
                "values": ["divide_255", "neg1_pos1", "none"],
                "default": "none",
                "description": "EfficientDet typically uses raw pixel values",
            },
        }

    def get_hypothesis_rules(self) -> List[Dict[str, Any]]:
        """EfficientDet-specific hypothesis rules."""
        return [
            {
                "condition": lambda p: p["metric_averages"].get("count_diff", 0) > 3,
                "hypothesis": "efficientdet_confidence",
                "description": "EfficientDet post-NMS confidence differs",
                "params_to_test": ["confidence_threshold"],
                "priority": "high",
            },
            {
                "condition": lambda p: p["dominant_stage"] == "preprocessing"
                    and p["metric_averages"].get("tensor_l2", 0) > 0.01,
                "hypothesis": "efficientdet_normalization",
                "description": "EfficientDet expects raw pixels, not normalized",
                "params_to_test": ["normalization"],
                "priority": "critical",
            },
        ]
