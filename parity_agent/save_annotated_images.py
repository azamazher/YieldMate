"""
Save Before/After Annotated Detection Images

Renders bounding boxes on each test image for both:
  - BEFORE (config from baseline_snapshot.json) → results/snapshots/baseline_images/
  - AFTER  (current fixed config in config.yaml) → results/snapshots/final_images/

Portable: reads the broken config from the baseline snapshot, no hardcoded values.
If no baseline snapshot exists, uses the current config as both before and after.

Run with:
    python parity_agent/save_annotated_images.py
"""

import sys
import os
import json
import glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parity_agent.run_agent import load_config
from parity_agent.trace.online_tracer import OnlineTracer
from parity_agent.trace.offline_tracer import OfflineTracer
from parity_agent.trace.schema import GoldenTrace


# ── Colour palette ──
COL_ONLINE  = (37, 99, 235)     # Blue
COL_BROKEN  = (239, 68, 68)     # Red
COL_FIXED   = (16, 185, 129)    # Green


def draw_boxes(image, detections, box_color, title="", max_labels=30):
    """
    Draw bounding boxes on a copy of the image.

    Args:
        image: PIL Image
        detections: list of Detection objects
        box_color: (R, G, B) tuple
        title: banner text
        max_labels: only draw text labels for the first N; draw all boxes
    """
    img = image.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except (IOError, OSError):
            font = ImageFont.load_default()
            title_font = font

    # Title banner
    if title:
        banner_h = 36
        draw.rectangle([0, 0, w, banner_h], fill=(0, 0, 0))
        draw.text((10, 7), title, fill=(255, 255, 255), font=title_font)

    # Draw all boxes (thin lines for large counts, thick for small)
    line_w = 1 if len(detections) > 50 else 3

    for i, det in enumerate(detections):
        x1 = int(det.bbox[0] * w)
        y1 = int(det.bbox[1] * h)
        x2 = int(det.bbox[2] * w)
        y2 = int(det.bbox[3] * h)

        draw.rectangle([x1, y1, x2, y2], outline=box_color, width=line_w)

        # Only draw labels for the first N detections (readability)
        if i < max_labels:
            label = f"{det.class_name} {det.confidence:.0%}"
            bbox_text = draw.textbbox((0, 0), label, font=font)
            text_w = bbox_text[2] - bbox_text[0]
            text_h = bbox_text[3] - bbox_text[1]
            draw.rectangle(
                [x1, max(0, y1 - text_h - 4), x1 + text_w + 6, y1],
                fill=box_color,
            )
            draw.text((x1 + 3, max(0, y1 - text_h - 3)), label,
                       fill=(255, 255, 255), font=font)

    return img


def save_comparison_images(golden_traces, output_dir, tag, box_color, config_desc):
    """
    Save annotated images for a set of golden traces.
    Creates online + offline side-by-side per image.
    """
    os.makedirs(output_dir, exist_ok=True)

    for gt in golden_traces:
        image_path = gt.image_path or gt.online.metadata.get("image_path", "")
        if not image_path or not os.path.exists(image_path):
            print(f"    [SKIP] {gt.image_id} — image not found")
            continue

        original = Image.open(image_path).convert("RGB")
        w, h = original.size

        on_dets = gt.online.nms_boxes if gt.online and gt.online.nms_boxes else []
        off_dets = gt.offline.nms_boxes if gt.offline and gt.offline.nms_boxes else []

        # Draw online (blue) and offline (colored) on separate copies
        online_img = draw_boxes(
            original, on_dets, COL_ONLINE,
            title=f"Online/PyTorch: {len(on_dets)} detections"
        )
        offline_img = draw_boxes(
            original, off_dets, box_color,
            title=f"Offline/TFLite ({config_desc}): {len(off_dets)} detections"
        )

        # Stitch side by side
        combined = Image.new("RGB", (w * 2 + 4, h), (40, 40, 40))
        combined.paste(online_img, (0, 0))
        combined.paste(offline_img, (w + 4, 0))

        safe_name = gt.image_id.replace(" ", "_").replace("/", "_")
        save_path = os.path.join(output_dir, f"{safe_name}.jpg")
        combined.save(save_path, quality=92)
        print(f"    Saved: {save_path}  ({len(on_dets)} online, {len(off_dets)} offline)")


def _load_baseline_config(results_dir, current_offline_config):
    """
    Load the baseline config from the baseline snapshot (portable).
    Falls back to the current config if no snapshot exists.
    """
    snapshot_path = Path(results_dir) / "snapshots" / "baseline_snapshot.json"
    if snapshot_path.exists():
        with open(snapshot_path) as f:
            snap = json.load(f)
        saved_cfg = snap.get("config", {})
        # Merge saved config keys into a copy of current config
        baseline = dict(current_offline_config)
        for key in ["confidence_threshold", "iou_threshold", "apply_sigmoid"]:
            if key in saved_cfg and saved_cfg[key] is not None:
                baseline[key] = saved_cfg[key]
        return baseline, True
    else:
        return dict(current_offline_config), False


def main():
    print("=" * 60)
    print("  Saving Before/After Annotated Detection Images")
    print("=" * 60)

    config = load_config()
    model_path = str(PROJECT_ROOT / config["paths"]["model_tflite"])
    labels = config["model"]["class_names"]
    test_images_dir = str(PROJECT_ROOT / config["paths"]["test_images"])
    results_dir = str(PROJECT_ROOT / config["paths"]["results_dir"])

    # Discover test images
    image_paths = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_paths.extend(glob.glob(os.path.join(test_images_dir, ext)))
    image_paths = sorted(image_paths)
    print(f"\n  Found {len(image_paths)} test images")

    # ── Online traces (shared ground truth) ──
    print("\n  Running online tracer...")
    online_tracer = OnlineTracer(
        model_path, labels,
        conf_threshold=config["online"]["confidence_threshold"],
        iou_threshold=config["online"]["iou_threshold"],
    )
    online_traces = online_tracer.trace_batch(image_paths)
    online_by_id = {t.image_id: t for t in online_traces}

    # ── BASELINE (read config from baseline snapshot, portable) ──
    broken_config, from_snapshot = _load_baseline_config(results_dir, config["offline"])
    if from_snapshot:
        print(f"\n  Loaded baseline config from snapshot:")
    else:
        print(f"\n  No baseline snapshot found. Using current config as baseline:")
    sig = broken_config.get("apply_sigmoid", "?")
    conf = broken_config.get("confidence_threshold", "?")
    print(f"    apply_sigmoid={sig}, confidence_threshold={conf}")

    print(f"\n  Running BASELINE offline tracer...")
    offline_broken = OfflineTracer(model_path, labels, broken_config)
    broken_traces = offline_broken.trace_batch(image_paths)

    broken_golden = []
    for off in broken_traces:
        on = online_by_id.get(off.image_id)
        if on:
            broken_golden.append(GoldenTrace(
                image_id=off.image_id,
                image_path=off.metadata.get("image_path", ""),
                online=on, offline=off
            ))

    config_desc = f"sigmoid={'ON' if sig else 'OFF'}, conf={conf}"
    baseline_dir = os.path.join(results_dir, "snapshots", "baseline_images")
    print(f"\n  Saving baseline images to {baseline_dir}")
    save_comparison_images(
        broken_golden, baseline_dir, "baseline", COL_BROKEN, config_desc
    )

    # ── FINAL (current fixed config) ──
    print("\n  Running FINAL offline tracer (current config)...")
    fixed_config = dict(config["offline"])

    offline_fixed = OfflineTracer(model_path, labels, fixed_config)
    fixed_traces = offline_fixed.trace_batch(image_paths)

    fixed_golden = []
    for off in fixed_traces:
        on = online_by_id.get(off.image_id)
        if on:
            fixed_golden.append(GoldenTrace(
                image_id=off.image_id,
                image_path=off.metadata.get("image_path", ""),
                online=on, offline=off
            ))

    final_dir = os.path.join(results_dir, "snapshots", "final_images")
    print(f"\n  Saving final images to {final_dir}")
    save_comparison_images(
        fixed_golden, final_dir, "final", COL_FIXED,
        f"sigmoid={'ON' if fixed_config.get('apply_sigmoid') else 'OFF'}, "
        f"conf={fixed_config.get('confidence_threshold', '?')}"
    )

    print(f"\n  Done!")
    print(f"  Baseline images: {baseline_dir}")
    print(f"  Final images:    {final_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

