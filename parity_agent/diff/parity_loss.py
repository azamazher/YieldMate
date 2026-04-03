"""
Parity Loss Function — Composite metric quantifying total cross-platform divergence.

ParityLoss = w₁·tensor_l2 + w₂·logits_diff + w₃·iou_mismatch + w₄·count_diff + w₅·confidence_kl

This is the objective that the agent minimizes.
"""

import numpy as np
from typing import Dict, List, Any, Optional

from ..trace.schema import PipelineTrace, GoldenTrace
from .metrics import compute_all_metrics


class ParityLoss:
    """
    Weighted composite parity loss function.

    The agent's goal is to minimize this loss by adjusting
    offline pipeline parameters.
    """

    DEFAULT_WEIGHTS = {
        "tensor_l2": 1.0,
        "logits_diff": 1.0,
        "iou_mismatch": 1.0,
        "count_diff": 0.5,
        "confidence_kl": 0.5,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Dict mapping metric name → weight.
                     Falls back to DEFAULT_WEIGHTS for missing keys.
        """
        self.weights = dict(self.DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)

    def compute(
        self, online: PipelineTrace, offline: PipelineTrace
    ) -> Dict[str, Any]:
        """
        Compute the parity loss for a single image pair.

        Returns:
            Dict with:
                - individual metric values
                - weighted contributions
                - total composite loss
        """
        raw_metrics = compute_all_metrics(online, offline)

        # Compute weighted contributions (skip unavailable metrics)
        contributions = {}
        total = 0.0
        valid_weight_sum = 0.0

        for metric_name, value in raw_metrics.items():
            weight = self.weights.get(metric_name, 0.0)
            if value < 0:
                # Metric unavailable (e.g., no tensors)
                contributions[metric_name] = None
                continue

            weighted = value * weight
            contributions[metric_name] = weighted
            total += weighted
            valid_weight_sum += weight

        # Normalize by sum of active weights
        if valid_weight_sum > 0:
            normalized_total = total / valid_weight_sum
        else:
            normalized_total = total

        return {
            "metrics": raw_metrics,
            "contributions": contributions,
            "total_loss": normalized_total,
            "raw_total": total,
            "weights": dict(self.weights),
        }

    def compute_batch(
        self, golden_traces: List[GoldenTrace]
    ) -> Dict[str, Any]:
        """
        Compute aggregate parity loss across multiple images.

        Returns:
            Dict with per-image results + aggregate statistics.
        """
        per_image = []
        losses = []

        for gt in golden_traces:
            if not gt.is_complete:
                continue
            result = self.compute(gt.online, gt.offline)
            result["image_id"] = gt.image_id
            per_image.append(result)
            losses.append(result["total_loss"])

        if not losses:
            return {
                "per_image": [],
                "aggregate": {
                    "mean_loss": float("inf"),
                    "std_loss": 0.0,
                    "min_loss": float("inf"),
                    "max_loss": float("inf"),
                    "num_images": 0,
                },
            }

        return {
            "per_image": per_image,
            "aggregate": {
                "mean_loss": float(np.mean(losses)),
                "std_loss": float(np.std(losses)),
                "min_loss": float(np.min(losses)),
                "max_loss": float(np.max(losses)),
                "num_images": len(losses),
            },
        }
