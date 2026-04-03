"""
Profiler Agent — Identifies the biggest source of divergence.

Analyzes the diff report to rank which pipeline stage
contributes most to parity loss.
"""

from typing import Dict, List, Any, Tuple


class ProfilerAgent:
    """
    Analyzes parity metrics to find the dominant divergence source.
    
    Pipeline stages ranked by their metric proxies:
        - Preprocessing → tensor_l2
        - Model runtime  → logits_diff
        - Localization   → iou_mismatch
        - NMS behavior   → count_diff
        - Calibration    → confidence_kl
    """

    # Map metric names to pipeline stages
    METRIC_TO_STAGE = {
        "tensor_l2": "preprocessing",
        "logits_diff": "model_runtime",
        "iou_mismatch": "localization",
        "count_diff": "nms_behavior",
        "confidence_kl": "calibration",
    }

    # Map stages to actionable parameters
    STAGE_TO_PARAMS = {
        "preprocessing": ["normalization", "resize_method", "channel_order", "padding_color"],
        "model_runtime": [],  # Can't fix without changing model/runtime
        "localization": ["confidence_threshold", "apply_sigmoid"],
        "nms_behavior": ["iou_threshold", "confidence_threshold"],
        "calibration": ["confidence_threshold", "apply_sigmoid"],
    }

    def analyze(self, batch_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze parity metrics and identify the dominant divergence source.

        Args:
            batch_result: Output from ParityLoss.compute_batch()

        Returns:
            Profiling result with ranked stages, dominant stage, and
            suggested parameters to investigate.
        """
        if not batch_result.get("per_image"):
            return {
                "dominant_stage": "unknown",
                "ranking": [],
                "suggested_params": [],
                "details": "No images to analyze.",
            }

        # Average each metric across all images
        metric_avgs = {}
        for metric_name in self.METRIC_TO_STAGE:
            values = []
            for img_result in batch_result["per_image"]:
                v = img_result["metrics"].get(metric_name, -1)
                if v >= 0:
                    values.append(v)
            metric_avgs[metric_name] = sum(values) / len(values) if values else 0.0

        # Rank metrics by magnitude (normalized — percentage of total)
        total = sum(metric_avgs.values()) or 1.0
        ranked = sorted(
            [
                {
                    "metric": name,
                    "stage": self.METRIC_TO_STAGE[name],
                    "value": val,
                    "pct_of_total": (val / total) * 100,
                }
                for name, val in metric_avgs.items()
            ],
            key=lambda x: x["value"],
            reverse=True,
        )

        # Dominant stage
        dominant = ranked[0] if ranked else None
        dominant_stage = dominant["stage"] if dominant else "unknown"

        # Suggested parameters (from dominant + secondary stages)
        suggested_params = []
        seen = set()
        for r in ranked[:3]:
            for p in self.STAGE_TO_PARAMS.get(r["stage"], []):
                if p not in seen:
                    suggested_params.append(p)
                    seen.add(p)

        return {
            "dominant_stage": dominant_stage,
            "ranking": ranked,
            "suggested_params": suggested_params,
            "metric_averages": metric_avgs,
        }
