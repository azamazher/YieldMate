"""
Visual Parity Report — Generates side-by-side detection comparison images.

Creates a publishable Markdown report with:
- Bounding box overlays (online vs offline) on test images
- Metrics table per image
- Alignment history summary
- Before/after parity loss comparison
"""

import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from ..trace.schema import PipelineTrace, GoldenTrace, Detection
from ..trace.storage import TraceStorage
from ..diff.parity_loss import ParityLoss
from ..diff.metrics import compute_all_metrics


# Color palette for classes
CLASS_COLORS = [
    (255, 87, 34),    # Deep Orange
    (76, 175, 80),    # Green
    (33, 150, 243),   # Blue
    (255, 193, 7),    # Amber
    (156, 39, 176),   # Purple
    (0, 188, 212),    # Cyan
    (244, 67, 54),    # Red
    (139, 195, 74),   # Light Green
]


def draw_detections(
    image: Image.Image,
    detections: List[Detection],
    title: str = "",
    color_offset: int = 0,
) -> Image.Image:
    """
    Draw bounding boxes and labels on an image.

    Args:
        image: PIL Image to draw on.
        detections: List of Detection objects.
        title: Optional title to draw at the top.
        color_offset: Offset for class colors (0=online colors, 4=offline colors).

    Returns:
        New image with detections drawn.
    """
    img = image.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (IOError, OSError):
        font = ImageFont.load_default()
        title_font = font

    # Draw title banner
    if title:
        banner_h = 32
        draw.rectangle([0, 0, w, banner_h], fill=(0, 0, 0, 180))
        draw.text((10, 6), title, fill=(255, 255, 255), font=title_font)

    # Draw each detection
    for det in detections:
        color = CLASS_COLORS[det.class_index % len(CLASS_COLORS)]

        # Convert normalized bbox to pixel coordinates
        x1 = int(det.bbox[0] * w)
        y1 = int(det.bbox[1] * h)
        x2 = int(det.bbox[2] * w)
        y2 = int(det.bbox[3] * h)

        # Draw box
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        # Draw label
        label = f"{det.class_name} {det.confidence:.0%}"
        bbox_text = draw.textbbox((0, 0), label, font=font)
        text_w = bbox_text[2] - bbox_text[0]
        text_h = bbox_text[3] - bbox_text[1]
        draw.rectangle([x1, y1 - text_h - 6, x1 + text_w + 8, y1], fill=color)
        draw.text((x1 + 4, y1 - text_h - 4), label, fill=(255, 255, 255), font=font)

    return img


def create_comparison_image(
    image_path: str,
    online_trace: PipelineTrace,
    offline_trace: PipelineTrace,
) -> Image.Image:
    """Create a side-by-side comparison image."""
    original = Image.open(image_path).convert("RGB")

    # Draw online and offline detections
    online_img = draw_detections(
        original, online_trace.nms_boxes,
        title=f"ONLINE ({len(online_trace.nms_boxes)} detections)"
    )
    offline_img = draw_detections(
        original, offline_trace.nms_boxes,
        title=f"OFFLINE ({len(offline_trace.nms_boxes)} detections)"
    )

    # Combine side by side
    combined_w = online_img.width + offline_img.width + 10
    combined_h = max(online_img.height, offline_img.height)
    combined = Image.new("RGB", (combined_w, combined_h), (40, 40, 40))
    combined.paste(online_img, (0, 0))
    combined.paste(offline_img, (online_img.width + 10, 0))

    return combined


def generate_visual_report(
    config: dict,
    project_root: str,
    output_dir: str = None,
) -> str:
    """
    Generate a full visual parity report with comparison images.

    Returns:
        Path to the generated report.
    """
    project_root = Path(project_root)
    traces_dir = project_root / config["paths"]["traces_dir"]
    results_dir = project_root / config["paths"]["results_dir"]

    if output_dir is None:
        output_dir = results_dir / "report"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    storage = TraceStorage(str(traces_dir))
    weights = config["parity_loss"]["weights"]
    parity_loss = ParityLoss(weights=weights)

    # Load golden traces
    image_ids = storage.list_image_ids()
    golden_traces = []
    for image_id in image_ids:
        gt = storage.load_golden_trace(image_id)
        if gt and gt.is_complete:
            golden_traces.append(gt)

    if not golden_traces:
        print("No complete golden traces found.")
        return ""

    # Compute metrics
    batch_result = parity_loss.compute_batch(golden_traces)

    # Load alignment history
    history_path = results_dir / "alignment_history.json"
    alignment_history = []
    if history_path.exists():
        with open(history_path) as f:
            alignment_history = json.load(f)

    # Generate comparison images
    print(f"\n[Report] Generating comparison images for {len(golden_traces)} images...")
    comparison_paths = []
    for gt in golden_traces:
        image_path = gt.online.metadata.get("image_path", "")
        if image_path and os.path.exists(image_path):
            try:
                comparison = create_comparison_image(image_path, gt.online, gt.offline)
                save_path = images_dir / f"{gt.image_id}_comparison.jpg"
                comparison.save(str(save_path), quality=85)
                comparison_paths.append((gt.image_id, str(save_path)))
                print(f"  ✓ {gt.image_id}")
            except Exception as e:
                print(f"  ✗ {gt.image_id}: {e}")

    # Build Markdown report
    report_lines = []
    report_lines.append("# Parity Agent — Visual Report")
    report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Summary
    agg = batch_result["aggregate"]
    report_lines.append("## Summary\n")
    report_lines.append(f"| Metric | Value |")
    report_lines.append(f"|--------|-------|")
    report_lines.append(f"| Images Analyzed | {agg['num_images']} |")
    report_lines.append(f"| Mean Parity Loss | **{agg['mean_loss']:.6f}** |")
    report_lines.append(f"| Threshold | {config['parity_loss']['threshold']} |")
    report_lines.append(f"| Status | {'✅ PASS' if agg['mean_loss'] < config['parity_loss']['threshold'] else '❌ FAIL'} |")

    # Alignment History
    if alignment_history:
        report_lines.append("\n## Alignment History\n")
        report_lines.append("| # | Parameter | Old → New | Improvement |")
        report_lines.append("|:-:|-----------|-----------|:-----------:|")
        total_improvement = 0
        for i, change in enumerate(alignment_history, 1):
            param = change.get("parameter", "?")
            old_val = change.get("old_value", "?")
            new_val = change.get("new_value", "?")
            imp = change.get("improvement", 0)
            total_improvement += imp
            report_lines.append(f"| {i} | `{param}` | {old_val} → {new_val} | {imp:.4f} |")
        report_lines.append(f"| | **Total** | | **{total_improvement:.4f}** |")

    # Per-Image metrics
    report_lines.append("\n## Per-Image Metrics\n")
    report_lines.append("| Image | Tensor L2 | Logits | IoU-M | Count Δ | KL | **Loss** |")
    report_lines.append("|-------|:---------:|:------:|:-----:|:-------:|:--:|:--------:|")
    for img_result in batch_result["per_image"]:
        m = img_result["metrics"]
        report_lines.append(
            f"| {img_result['image_id'][:20]} | {m['tensor_l2']:.6f} | {m['logits_diff']:.6f} | "
            f"{m['iou_mismatch']:.4f} | {m['count_diff']:.0f} | {m['confidence_kl']:.4f} | "
            f"**{img_result['total_loss']:.4f}** |"
        )

    # Comparison Images
    if comparison_paths:
        report_lines.append("\n## Detection Comparisons\n")
        report_lines.append("Side-by-side: **Online** (left) vs **Offline** (right)\n")
        for image_id, img_path in comparison_paths:
            rel_path = os.path.relpath(img_path, str(output_dir))
            report_lines.append(f"### {image_id}\n")
            report_lines.append(f"![{image_id}]({rel_path})\n")

    # Write report
    report_path = output_dir / "parity_report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ Report generated: {report_path}")
    print(f"  {len(comparison_paths)} comparison images saved to {images_dir}/")

    return str(report_path)
