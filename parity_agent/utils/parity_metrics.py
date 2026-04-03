"""
Parity Metrics — IoU-based detection metrics for cross-platform evaluation.

Treats Online (PyTorch/Ultralytics) detections as ground truth and measures
how well Offline (TFLite) detections reproduce them.

Computes: Precision, Recall, F1, mAP@0.5, mAP@0.5:0.95

Usage:
    from parity_agent.utils.parity_metrics import compute_parity_metrics
    metrics = compute_parity_metrics(golden_traces)
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional


def _compute_iou(box_a: List[float], box_b: List[float]) -> float:
    """Compute IoU between two [x1, y1, x2, y2] boxes."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, box_a[2] - box_a[0]) * max(0, box_a[3] - box_a[1])
    area_b = max(0, box_b[2] - box_b[0]) * max(0, box_b[3] - box_b[1])
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


def _match_detections(
    gt_dets: List,  # List[Detection] — online (ground truth)
    pred_dets: List,  # List[Detection] — offline (predictions)
    iou_threshold: float = 0.5,
) -> Tuple[int, int, int]:
    """
    Match predictions to ground truth using IoU and class label.

    Returns (TP, FP, FN).
    """
    if not gt_dets and not pred_dets:
        return 0, 0, 0
    if not gt_dets:
        return 0, len(pred_dets), 0
    if not pred_dets:
        return 0, 0, len(gt_dets)

    matched_gt = set()
    tp = 0
    fp = 0

    # Sort predictions by confidence (highest first)
    sorted_preds = sorted(pred_dets, key=lambda d: d.confidence, reverse=True)

    for pred in sorted_preds:
        best_iou = 0.0
        best_gt_idx = -1

        for idx, gt in enumerate(gt_dets):
            if idx in matched_gt:
                continue
            if pred.class_name != gt.class_name:
                continue

            iou = _compute_iou(pred.bbox, gt.bbox)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = idx

        if best_iou >= iou_threshold and best_gt_idx >= 0:
            tp += 1
            matched_gt.add(best_gt_idx)
        else:
            fp += 1

    fn = len(gt_dets) - len(matched_gt)
    return tp, fp, fn


def _compute_ap_at_iou(
    gt_dets_per_image: List[List],
    pred_dets_per_image: List[List],
    class_name: str,
    iou_threshold: float,
) -> float:
    """
    Compute Average Precision for a single class at a single IoU threshold.
    Uses the 11-point interpolation method (PASCAL VOC style).
    """
    # Collect all predictions and GT for this class across all images
    all_preds = []  # (confidence, image_idx, pred_idx)
    all_gt_count = 0
    gt_matched = {}  # (image_idx, gt_idx) -> bool

    for img_idx, (gts, preds) in enumerate(zip(gt_dets_per_image, pred_dets_per_image)):
        class_gts = [g for g in gts if g.class_name == class_name]
        class_preds = [p for p in preds if p.class_name == class_name]

        all_gt_count += len(class_gts)
        for gt_idx in range(len(class_gts)):
            gt_matched[(img_idx, gt_idx)] = False

        for pred_idx, pred in enumerate(class_preds):
            all_preds.append((pred.confidence, img_idx, pred_idx, pred))

    if all_gt_count == 0:
        return 0.0 if all_preds else 1.0

    # Sort all predictions by confidence (descending)
    all_preds.sort(key=lambda x: x[0], reverse=True)

    tp_list = []
    fp_list = []
    cumulative_tp = 0
    cumulative_fp = 0

    for conf, img_idx, pred_idx, pred in all_preds:
        gts = [g for g in gt_dets_per_image[img_idx] if g.class_name == class_name]

        best_iou = 0.0
        best_gt_idx = -1
        for gt_idx, gt in enumerate(gts):
            if gt_matched.get((img_idx, gt_idx), False):
                continue
            iou = _compute_iou(pred.bbox, gt.bbox)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx

        if best_iou >= iou_threshold and best_gt_idx >= 0:
            gt_matched[(img_idx, best_gt_idx)] = True
            cumulative_tp += 1
        else:
            cumulative_fp += 1

        tp_list.append(cumulative_tp)
        fp_list.append(cumulative_fp)

    # Compute precision-recall curve
    precisions = []
    recalls = []
    for tp, fp in zip(tp_list, fp_list):
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / all_gt_count if all_gt_count > 0 else 0
        precisions.append(prec)
        recalls.append(rec)

    # 11-point interpolation
    ap = 0.0
    for t in np.arange(0, 1.1, 0.1):
        prec_at_recall = [p for p, r in zip(precisions, recalls) if r >= t]
        if prec_at_recall:
            ap += max(prec_at_recall)
    ap /= 11.0

    return ap


def compute_parity_metrics(golden_traces: List) -> Dict[str, Any]:
    """
    Compute full detection parity metrics from golden traces.

    Treats online detections as ground truth, offline as predictions.

    Returns dict with:
        - precision, recall, f1 (at IoU 0.5)
        - mAP_50 (mAP@0.5)
        - mAP_50_95 (mAP@0.5:0.95)
        - per_class: {class_name: {precision, recall, f1, ap_50}}
    """
    total_tp = 0
    total_fp = 0
    total_fn = 0

    gt_per_image = []
    pred_per_image = []
    all_classes = set()

    for gt in golden_traces:
        online_dets = gt.online.nms_boxes if gt.online and gt.online.nms_boxes else []
        offline_dets = gt.offline.nms_boxes if gt.offline and gt.offline.nms_boxes else []

        gt_per_image.append(online_dets)
        pred_per_image.append(offline_dets)

        for d in online_dets:
            all_classes.add(d.class_name)
        for d in offline_dets:
            all_classes.add(d.class_name)

        tp, fp, fn = _match_detections(online_dets, offline_dets, iou_threshold=0.5)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    # Global precision, recall, F1 at IoU=0.5
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Per-class AP at IoU=0.5
    per_class = {}
    ap_50_list = []
    for cls in sorted(all_classes):
        ap = _compute_ap_at_iou(gt_per_image, pred_per_image, cls, 0.5)
        ap_50_list.append(ap)

        # Per-class precision/recall/F1
        cls_tp, cls_fp, cls_fn = 0, 0, 0
        for gts, preds in zip(gt_per_image, pred_per_image):
            cls_gts = [g for g in gts if g.class_name == cls]
            cls_preds = [p for p in preds if p.class_name == cls]
            t, f, n = _match_detections(cls_gts, cls_preds, 0.5)
            cls_tp += t
            cls_fp += f
            cls_fn += n

        cls_prec = cls_tp / (cls_tp + cls_fp) if (cls_tp + cls_fp) > 0 else 0.0
        cls_rec = cls_tp / (cls_tp + cls_fn) if (cls_tp + cls_fn) > 0 else 0.0
        cls_f1 = 2 * cls_prec * cls_rec / (cls_prec + cls_rec) if (cls_prec + cls_rec) > 0 else 0.0

        per_class[cls] = {
            "precision": round(cls_prec, 4),
            "recall": round(cls_rec, 4),
            "f1": round(cls_f1, 4),
            "ap_50": round(ap, 4),
        }

    mAP_50 = np.mean(ap_50_list) if ap_50_list else 0.0

    # mAP@0.5:0.95 — average AP across IoU thresholds [0.5, 0.55, ..., 0.95]
    iou_thresholds = np.arange(0.5, 1.0, 0.05)
    ap_per_threshold = []
    for iou_t in iou_thresholds:
        aps = []
        for cls in sorted(all_classes):
            ap = _compute_ap_at_iou(gt_per_image, pred_per_image, cls, iou_t)
            aps.append(ap)
        ap_per_threshold.append(np.mean(aps) if aps else 0.0)

    mAP_50_95 = np.mean(ap_per_threshold) if ap_per_threshold else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP_50": round(float(mAP_50), 4),
        "mAP_50_95": round(float(mAP_50_95), 4),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "num_classes": len(all_classes),
        "num_images": len(golden_traces),
        "per_class": per_class,
    }
