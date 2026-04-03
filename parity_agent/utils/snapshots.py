"""
Snapshot Utility — Captures per-image detection data from golden traces.

Saves structured JSON snapshots at key moments during the agent run:
  - baseline_snapshot.json  (iteration 0, before any fixes)
  - final_snapshot.json     (after convergence)

These snapshots drive the BMVC figures and Streamlit tables dynamically,
eliminating the need for hardcoded values.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


def _extract_image_summary(golden_trace) -> Dict[str, Any]:
    """
    Extract a structured summary from a single GoldenTrace.

    Returns a dict with online/offline detection counts, per-class
    confidence scores, and bounding box data.
    """
    summary = {
        "image_id": golden_trace.image_id,
        "image_path": golden_trace.image_path,
        "online": {"detection_count": 0, "classes": {}},
        "offline": {"detection_count": 0, "classes": {}},
    }

    # Online detections
    if golden_trace.online and golden_trace.online.nms_boxes:
        dets = golden_trace.online.nms_boxes
        summary["online"]["detection_count"] = len(dets)
        for det in dets:
            name = det.class_name
            conf = round(det.confidence * 100, 1)  # as percentage
            # If multiple detections of same class, keep the highest
            if name not in summary["online"]["classes"] or conf > summary["online"]["classes"][name]:
                summary["online"]["classes"][name] = conf

    # Offline detections
    if golden_trace.offline:
        if golden_trace.offline.nms_boxes:
            dets = golden_trace.offline.nms_boxes
            summary["offline"]["detection_count"] = len(dets)
            for det in dets:
                name = det.class_name
                conf = round(det.confidence * 100, 1)
                if name not in summary["offline"]["classes"] or conf > summary["offline"]["classes"][name]:
                    summary["offline"]["classes"][name] = conf

        # Also capture decoded box count (pre-NMS) for the baseline
        if golden_trace.offline.decoded_boxes:
            summary["offline"]["decoded_count"] = len(golden_trace.offline.decoded_boxes)

    return summary


def save_snapshot(
    golden_traces: List,
    parity_loss: float,
    config: Dict[str, Any],
    snapshot_type: str,
    output_dir: str,
) -> str:
    """
    Save a snapshot of the current detection state.

    Args:
        golden_traces: List of GoldenTrace objects
        parity_loss: Current parity loss value
        config: Current pipeline config (conf_threshold, apply_sigmoid, etc.)
        snapshot_type: "baseline" or "final"
        output_dir: Directory to save JSON (e.g., results/snapshots/)

    Returns:
        Path to the saved snapshot JSON.
    """
    snapshots_dir = Path(output_dir) / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for gt in golden_traces:
        images.append(_extract_image_summary(gt))

    # Aggregate summary across all images
    total_online = sum(img["online"]["detection_count"] for img in images)
    total_offline = sum(img["offline"]["detection_count"] for img in images)

    # Collect all unique classes and their average confidences
    online_classes = {}
    offline_classes = {}
    for img in images:
        for cls, conf in img["online"]["classes"].items():
            online_classes.setdefault(cls, []).append(conf)
        for cls, conf in img["offline"]["classes"].items():
            offline_classes.setdefault(cls, []).append(conf)

    snapshot = {
        "type": snapshot_type,
        "timestamp": datetime.now().isoformat(),
        "parity_loss": parity_loss,
        "config": {
            "confidence_threshold": config.get("confidence_threshold", None),
            "iou_threshold": config.get("iou_threshold", None),
            "apply_sigmoid": config.get("apply_sigmoid", None),
        },
        "summary": {
            "num_images": len(images),
            "total_online_detections": total_online,
            "total_offline_detections": total_offline,
            "online_classes_avg": {
                cls: round(sum(confs) / len(confs), 1)
                for cls, confs in online_classes.items()
            },
            "offline_classes_avg": {
                cls: round(sum(confs) / len(confs), 1)
                for cls, confs in offline_classes.items()
            },
        },
        "per_image": images,
    }

    # Compute IoU-based parity metrics
    try:
        from parity_agent.utils.parity_metrics import compute_parity_metrics
        metrics = compute_parity_metrics(golden_traces)
        snapshot["metrics"] = metrics
    except Exception as e:
        snapshot["metrics"] = {"error": str(e)}

    filename = f"{snapshot_type}_snapshot.json"
    path = snapshots_dir / filename
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)

    return str(path)


def load_snapshot(output_dir: str, snapshot_type: str) -> Optional[Dict[str, Any]]:
    """
    Load a previously saved snapshot.

    Args:
        output_dir: Results directory (e.g., results/)
        snapshot_type: "baseline" or "final"

    Returns:
        The snapshot dict, or None if the file doesn't exist.
    """
    path = Path(output_dir) / "snapshots" / f"{snapshot_type}_snapshot.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)
