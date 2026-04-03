"""
Hypothesis Agent — Generates candidate causes for observed divergence.

Given the profiler's analysis, generates ranked hypotheses about
what configuration change will most likely reduce parity loss.
"""

from typing import Dict, List, Any


class HypothesisAgent:
    """
    Rule-based hypothesis generation for deployment parity issues.
    
    Encodes domain knowledge about common causes of cross-platform
    ML divergence (learned from the manual alignment phase).
    """

    # Domain knowledge: known cause-effect relationships
    HYPOTHESIS_RULES = [
        # --- Preprocessing stage hypotheses ---
        {
            "condition": lambda profile: profile["dominant_stage"] == "preprocessing"
                and profile["metric_averages"].get("tensor_l2", 0) > 0.01,
            "hypothesis": "normalization_mismatch",
            "description": "Input tensor normalization differs between pipelines",
            "params_to_test": ["normalization", "channel_order"],
            "priority": "high",
        },
        {
            "condition": lambda profile: profile["dominant_stage"] == "preprocessing"
                and profile["metric_averages"].get("tensor_l2", 0) > 0.001,
            "hypothesis": "resize_method_mismatch",
            "description": "Image resize interpolation method differs",
            "params_to_test": ["resize_method"],
            "priority": "medium",
        },
        {
            "condition": lambda profile: profile["dominant_stage"] == "preprocessing",
            "hypothesis": "channel_order_swap",
            "description": "RGB/BGR channel order mismatch",
            "params_to_test": ["channel_order"],
            "priority": "high",
        },
        # --- NMS / count divergence hypotheses ---
        # KEY FIX: When count_diff is very high, confidence_threshold is usually the
        # primary cause (not iou_threshold). The offline pipeline passes through too
        # many raw detections because its confidence bar is too low.
        {
            "condition": lambda profile: profile["metric_averages"].get("count_diff", 0) > 10,
            "hypothesis": "confidence_threshold_too_low",
            "description": "Offline confidence threshold too permissive — floods NMS with spurious detections",
            "params_to_test": ["confidence_threshold"],
            "priority": "critical",
        },
        {
            "condition": lambda profile: profile["dominant_stage"] in ("nms_behavior", "localization")
                and profile["metric_averages"].get("count_diff", 0) > 0,
            "hypothesis": "nms_threshold_mismatch",
            "description": "NMS IoU threshold causes different suppression behavior",
            "params_to_test": ["iou_threshold", "confidence_threshold"],
            "priority": "high",
        },
        # --- Calibration stage hypotheses ---
        {
            "condition": lambda profile: profile["dominant_stage"] in ("calibration", "localization")
                and profile["metric_averages"].get("confidence_kl", 0) > 0.01,
            "hypothesis": "confidence_threshold_mismatch",
            "description": "Confidence threshold gap causes detection count difference",
            "params_to_test": ["confidence_threshold"],
            "priority": "high",
        },
        {
            "condition": lambda profile: profile["dominant_stage"] == "calibration",
            "hypothesis": "sigmoid_missing_or_double",
            "description": "Sigmoid activation may be missing or applied differently",
            "params_to_test": ["apply_sigmoid"],
            "priority": "critical",
        },
        # --- Fallback hypotheses ---
        {
            "condition": lambda profile: profile["metric_averages"].get("tensor_l2", 0) > 0.05,
            "hypothesis": "padding_color_mismatch",
            "description": "Letterbox padding color differs between pipelines",
            "params_to_test": ["padding_color"],
            "priority": "low",
        },
        # --- Catch-all: sweep NMS params if any IoU divergence ---
        {
            "condition": lambda profile: profile["metric_averages"].get("iou_mismatch", 0) > 0,
            "hypothesis": "iou_threshold_sweep",
            "description": "IoU mismatch detected — sweep NMS threshold to find best match",
            "params_to_test": ["iou_threshold"],
            "priority": "medium",
        },
        # --- Ultimate fallback: sweep everything if loss still above threshold ---
        {
            "condition": lambda profile: True,  # Always true — will be last due to low priority
            "hypothesis": "exhaustive_parameter_sweep",
            "description": "Loss still above threshold — sweep all remaining parameters",
            "params_to_test": ["confidence_threshold", "iou_threshold", "apply_sigmoid",
                              "normalization", "channel_order"],
            "priority": "low",
        },
    ]

    def generate(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate hypotheses based on the profiler's analysis.

        Args:
            profile: Output from ProfilerAgent.analyze()

        Returns:
            List of hypotheses, sorted by priority (critical > high > medium > low).
        """
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        hypotheses = []
        for rule in self.HYPOTHESIS_RULES:
            try:
                if rule["condition"](profile):
                    hypotheses.append({
                        "hypothesis": rule["hypothesis"],
                        "description": rule["description"],
                        "params_to_test": rule["params_to_test"],
                        "priority": rule["priority"],
                    })
            except (KeyError, TypeError):
                continue

        # Deduplicate by hypothesis name
        seen = set()
        unique = []
        for h in hypotheses:
            if h["hypothesis"] not in seen:
                unique.append(h)
                seen.add(h["hypothesis"])

        # Sort by priority
        unique.sort(key=lambda h: priority_order.get(h["priority"], 99))

        return unique
