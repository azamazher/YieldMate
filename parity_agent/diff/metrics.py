"""
Divergence Metrics — Quantify the gap between online and offline pipeline traces.

Five core metrics that together form the Parity Loss Function:

1. tensor_l2      — L2 norm of input tensor difference (preprocessing mismatch)
2. logits_diff    — Mean absolute difference of raw model outputs (numerical drift)
3. iou_mismatch   — 1 - mean(matched IoU) between final detections (localization)
4. count_diff     — Absolute detection count difference (NMS behavior)
5. confidence_kl  — KL divergence of confidence distributions (calibration)
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from scipy.special import kl_div

from ..trace.schema import PipelineTrace, Detection


def tensor_l2(online: PipelineTrace, offline: PipelineTrace) -> float:
    """
    L2 norm of the preprocessed input tensor difference.
    
    Catches: normalization, resize, channel order, padding mismatches.
    
    Returns:
        Normalized L2 distance (per-element) or -1 if tensors unavailable.
    """
    if online.input_tensor is None or offline.input_tensor is None:
        return -1.0

    a = online.input_tensor.astype(np.float64).flatten()
    b = offline.input_tensor.astype(np.float64).flatten()

    if a.shape != b.shape:
        # If shapes differ, that's already a major preprocessing issue
        return float("inf")

    l2 = np.linalg.norm(a - b)
    # Normalize by number of elements for comparability across resolutions
    return float(l2 / max(len(a), 1))


def logits_diff(online: PipelineTrace, offline: PipelineTrace) -> float:
    """
    Mean absolute difference of raw model output tensors.
    
    Catches: numerical drift between runtimes (quantization, delegate effects).
    
    Returns:
        Mean absolute difference or -1 if outputs unavailable.
    """
    if online.raw_output is None or offline.raw_output is None:
        return -1.0

    a = online.raw_output.astype(np.float64).flatten()
    b = offline.raw_output.astype(np.float64).flatten()

    if a.shape != b.shape:
        # Different output shapes — this is itself a divergence signal
        return float("inf")

    return float(np.mean(np.abs(a - b)))


def iou_mismatch(online: PipelineTrace, offline: PipelineTrace) -> float:
    """
    1 - mean(matched IoU) between final NMS detections.
    
    Matches online and offline detections greedily by IoU, then computes
    the average IoU of matched pairs. Unmatched detections count as IoU=0.
    
    Catches: localization divergence from coordinate transformations.
    
    Returns:
        Mismatch score in [0, 1]. 0 = perfect match, 1 = no overlap.
    """
    online_boxes = online.nms_boxes
    offline_boxes = offline.nms_boxes

    if not online_boxes and not offline_boxes:
        return 0.0  # Both empty = perfect agreement

    if not online_boxes or not offline_boxes:
        return 1.0  # One has detections, other doesn't

    # Build IoU matrix
    n = len(online_boxes)
    m = len(offline_boxes)
    iou_matrix = np.zeros((n, m))

    for i, det_on in enumerate(online_boxes):
        for j, det_off in enumerate(offline_boxes):
            iou_matrix[i, j] = _calculate_iou(det_on.bbox, det_off.bbox)

    # Greedy matching (same approach as in the Dart tracker)
    matched_ious = []
    used_online = set()
    used_offline = set()

    for _ in range(min(n, m)):
        best_iou = 0.0
        best_i, best_j = -1, -1
        for i in range(n):
            if i in used_online:
                continue
            for j in range(m):
                if j in used_offline:
                    continue
                if iou_matrix[i, j] > best_iou:
                    best_iou = iou_matrix[i, j]
                    best_i, best_j = i, j

        if best_iou > 0 and best_i >= 0:
            matched_ious.append(best_iou)
            used_online.add(best_i)
            used_offline.add(best_j)
        else:
            break

    # Unmatched detections contribute IoU=0
    num_unmatched = max(n, m) - len(matched_ious)
    all_ious = matched_ious + [0.0] * num_unmatched

    mean_iou = np.mean(all_ious) if all_ious else 0.0
    return float(1.0 - mean_iou)


def count_diff(online: PipelineTrace, offline: PipelineTrace) -> float:
    """
    Absolute difference in detection count after NMS.
    
    Catches: NMS threshold divergence, missing/extra detections.
    
    Returns:
        Absolute count difference (0 = same count).
    """
    return float(abs(len(online.nms_boxes) - len(offline.nms_boxes)))


def confidence_kl(online: PipelineTrace, offline: PipelineTrace) -> float:
    """
    KL divergence of confidence score distributions.
    
    Discretizes confidence scores into histogram bins and computes
    the KL divergence D_KL(online || offline).
    
    Catches: calibration drift from quantization or sigmoid differences.
    
    Returns:
        KL divergence value (0 = identical distributions).
    """
    online_confs = [d.confidence for d in online.nms_boxes]
    offline_confs = [d.confidence for d in offline.nms_boxes]

    if not online_confs and not offline_confs:
        return 0.0

    # Create histograms with same bins
    bins = np.linspace(0, 1, 21)  # 20 bins from 0 to 1

    hist_on, _ = np.histogram(online_confs if online_confs else [0], bins=bins, density=True)
    hist_off, _ = np.histogram(offline_confs if offline_confs else [0], bins=bins, density=True)

    # Add small epsilon to avoid log(0)
    eps = 1e-10
    hist_on = hist_on.astype(np.float64) + eps
    hist_off = hist_off.astype(np.float64) + eps

    # Normalize to valid probability distributions
    hist_on = hist_on / hist_on.sum()
    hist_off = hist_off / hist_off.sum()

    # KL divergence: sum(p * log(p/q))
    kl = float(np.sum(hist_on * np.log(hist_on / hist_off)))
    return max(0.0, kl)


def _calculate_iou(box_a: List[float], box_b: List[float]) -> float:
    """IoU between two [x1, y1, x2, y2] boxes."""
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

    return inter_area / union_area if union_area > 0 else 0.0


def compute_all_metrics(
    online: PipelineTrace, offline: PipelineTrace
) -> Dict[str, float]:
    """
    Compute all five divergence metrics for a single image pair.
    
    Returns:
        Dict with keys: tensor_l2, logits_diff, iou_mismatch, count_diff, confidence_kl
    """
    return {
        "tensor_l2": tensor_l2(online, offline),
        "logits_diff": logits_diff(online, offline),
        "iou_mismatch": iou_mismatch(online, offline),
        "count_diff": count_diff(online, offline),
        "confidence_kl": confidence_kl(online, offline),
    }
