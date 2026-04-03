"""
Setup Wizard — Interactive project configuration for the Parity Agent.

Scans a project directory to auto-detect:
- TFLite models
- Label files
- Test images
- Dart source files with detection thresholds
- Online framework (Ultralytics, PyTorch, ONNX)

Generates a ready-to-use config.yaml so new users can get started immediately.

Usage:
    python parity_agent/run_agent.py --mode setup
"""

import os
import re
import sys
import glob
import struct
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import yaml

from parity_agent.utils.colors import banner, success, warning, info, highlight, bold

PROJECT_ROOT = Path(__file__).parent.parent


# ──────────────────────────────────────────────────────────
# AUTO-DETECTION FUNCTIONS
# ──────────────────────────────────────────────────────────

def find_tflite_models(project_root: Path) -> List[Path]:
    """Recursively find all .tflite files in the project."""
    models = []
    for p in project_root.rglob("*.tflite"):
        # Skip build artifacts and hidden dirs
        parts = p.parts
        if any(part.startswith(".") or part in ("build", "node_modules", ".dart_tool") for part in parts):
            continue
        models.append(p)
    return sorted(models, key=lambda p: len(p.parts))  # Shortest path first


def find_label_files(project_root: Path) -> List[Path]:
    """Find label/class name files."""
    patterns = ["labels.txt", "classes.txt", "classnames.txt", "class_names.txt", "labelmap.txt"]
    found = []
    for p in project_root.rglob("*.txt"):
        if p.name.lower() in patterns:
            parts = p.parts
            if not any(part.startswith(".") or part in ("build", "node_modules") for part in parts):
                found.append(p)
    return found


def read_labels_from_file(label_path: Path) -> List[str]:
    """Read class names from a label file (one per line)."""
    labels = []
    with open(label_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                labels.append(line)
    return labels


def infer_model_info(model_path: Path) -> Dict:
    """
    Load TFLite model and infer metadata:
    - Input size
    - Number of classes
    - Output tensor shape
    """
    info = {
        "input_size": 640,
        "num_classes": None,
        "output_shape": None,
        "architecture": "unknown",
    }

    try:
        import numpy as np

        # Try TFLite interpreter
        try:
            import tensorflow as tf
            interpreter = tf.lite.Interpreter(model_path=str(model_path))
        except ImportError:
            try:
                import tflite_runtime.interpreter as tflite
                interpreter = tflite.Interpreter(model_path=str(model_path))
            except ImportError:
                print(warning("  ⚠ Could not load TFLite runtime — using defaults."))
                return info

        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        # Input size
        input_shape = input_details[0]["shape"]  # e.g., [1, 640, 640, 3]
        if len(input_shape) == 4:
            info["input_size"] = int(input_shape[1])

        # Output shape
        output_shape = output_details[0]["shape"]
        info["output_shape"] = [int(x) for x in output_shape]

        # Infer architecture and num_classes from output shape
        if len(output_shape) == 3:
            # YOLOv8: [1, num_classes+4, num_boxes] or [1, num_boxes, num_classes+4]
            dim1, dim2 = output_shape[1], output_shape[2]
            if dim1 < dim2:
                # [1, num_classes+4, num_boxes]
                info["num_classes"] = int(dim1) - 4
                info["architecture"] = "yolov8"
            else:
                # [1, num_boxes, num_classes+4]
                info["num_classes"] = int(dim2) - 4
                info["architecture"] = "yolov8_transposed"
        elif len(output_shape) == 4:
            # SSD-like: [1, num_boxes, num_classes, 4]
            info["num_classes"] = int(output_shape[2])
            info["architecture"] = "ssd"

        print(success(f"  ✓ Model loaded: input={info['input_size']}x{info['input_size']}, "
                      f"output={info['output_shape']}, arch={info['architecture']}"))

        if info["num_classes"] is not None and info["num_classes"] > 0:
            print(success(f"  ✓ Detected {info['num_classes']} classes from output shape"))

    except Exception as e:
        print(warning(f"  ⚠ Could not analyze model: {e}"))

    return info


def find_test_images(project_root: Path) -> Tuple[Optional[Path], int]:
    """Find directories containing test images."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    candidates = []

    # Check common directory names
    for name in ["test_images", "test_imgs", "images", "test", "samples", "sample_images"]:
        d = project_root / name
        if d.is_dir():
            count = sum(1 for f in d.iterdir() if f.suffix.lower() in image_extensions)
            if count > 0:
                candidates.append((d, count))

    # Also check the project root itself
    root_count = sum(1 for f in project_root.iterdir() if f.suffix.lower() in image_extensions)
    if root_count > 0:
        candidates.append((project_root, root_count))

    if candidates:
        # Return the one with most images
        best = max(candidates, key=lambda x: x[1])
        return best[0], best[1]
    return None, 0


def detect_online_framework() -> str:
    """Detect which ML framework is installed for the online pipeline."""
    frameworks = []
    if importlib.util.find_spec("ultralytics"):
        frameworks.append("ultralytics")
    if importlib.util.find_spec("torch"):
        frameworks.append("pytorch")
    if importlib.util.find_spec("onnxruntime"):
        frameworks.append("onnx")

    if "ultralytics" in frameworks:
        return "ultralytics"
    elif "pytorch" in frameworks:
        return "pytorch"
    elif "onnx" in frameworks:
        return "onnx"
    return "ultralytics"  # default


def scan_dart_thresholds(project_root: Path) -> Dict[str, any]:
    """Scan Dart source files for detection-related thresholds."""
    dart_info = {
        "dart_files": [],
        "confidence_threshold": None,
        "iou_threshold": None,
        "patterns_found": [],
    }

    lib_dir = project_root / "lib"
    if not lib_dir.exists():
        return dart_info

    # Common patterns for thresholds in Dart
    conf_patterns = [
        r'confThreshold\s*[:=]\s*([\d.]+)',
        r'confidenceThreshold\s*[:=]\s*([\d.]+)',
        r'confidence_threshold\s*[:=]\s*([\d.]+)',
        r'minConfidence\s*[:=]\s*([\d.]+)',
        r'threshold\s*[:=]\s*([\d.]+)',
    ]
    iou_patterns = [
        r'iouThreshold\s*[:=]\s*([\d.]+)',
        r'iou_threshold\s*[:=]\s*([\d.]+)',
        r'nmsThreshold\s*[:=]\s*([\d.]+)',
        r'overlapThreshold\s*[:=]\s*([\d.]+)',
    ]

    for dart_file in lib_dir.rglob("*.dart"):
        try:
            content = dart_file.read_text()
        except Exception:
            continue

        for pattern in conf_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                dart_info["confidence_threshold"] = float(match.group(1))
                dart_info["dart_files"].append(str(dart_file.relative_to(project_root)))
                dart_info["patterns_found"].append(f"confidence: {match.group(0)}")
                break

        for pattern in iou_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                dart_info["iou_threshold"] = float(match.group(1))
                if str(dart_file.relative_to(project_root)) not in dart_info["dart_files"]:
                    dart_info["dart_files"].append(str(dart_file.relative_to(project_root)))
                dart_info["patterns_found"].append(f"iou: {match.group(0)}")
                break

    return dart_info


# ──────────────────────────────────────────────────────────
# INTERACTIVE WIZARD
# ──────────────────────────────────────────────────────────

def prompt_choice(message: str, options: list, default: int = 0) -> int:
    """Prompt user to pick from a list of options."""
    print(f"\n{bold(message)}")
    for i, opt in enumerate(options):
        marker = dim(" ← default") if i == default else ""
        print(f"  [{i + 1}] {opt}{marker}")
    while True:
        raw = input(f"\nChoice [1-{len(options)}] (default: {default + 1}): ").strip()
        if not raw:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print("  Invalid choice, try again.")


def prompt_value(message: str, default: str = "") -> str:
    """Prompt user for a value with a default."""
    from parity_agent.utils.colors import dim, bold
    suffix = dim(f" [{default}]") if default else ""
    raw = input(f"{bold(message)}{suffix}: ").strip()
    return raw if raw else default


def run_setup_wizard(project_root: Path = None):
    """
    Run the interactive setup wizard.

    Scans the project, auto-detects settings, confirms with user,
    and generates config.yaml.
    """
    if project_root is None:
        project_root = PROJECT_ROOT

    print("\n" + banner("=" * 70))
    print(banner("  🧙 PARITY AGENT — SETUP WIZARD"))
    print(banner("  Auto-configure the agent for your project"))
    print(banner("=" * 70))

    config_path = Path(__file__).parent / "config.yaml"
    existing_config = None
    if config_path.exists():
        with open(config_path) as f:
            existing_config = yaml.safe_load(f)
        print(success(f"\n  ℹ  Existing config found: {config_path}"))
        print(info("  The wizard will use existing values as defaults.\n"))

    # ── Step 1: Find TFLite model ──
    print(info("─" * 50))
    print(info("  Step 1: TFLite Model"))
    print(info("─" * 50))

    models = find_tflite_models(project_root)
    if models:
        print(f"\n  Found {len(models)} TFLite model(s):")
        model_options = [str(m.relative_to(project_root)) for m in models]
        default_idx = 0
        if existing_config:
            existing_model = existing_config.get("paths", {}).get("model_tflite", "")
            if existing_model in model_options:
                default_idx = model_options.index(existing_model)
        choice = prompt_choice("Select model:", model_options, default_idx)
        model_rel = model_options[choice]
        model_path = project_root / model_rel
    else:
        print(warning("\n  ⚠ No .tflite files found."))
        model_rel = prompt_value("  Enter path to .tflite model (relative to project root)")
        model_path = project_root / model_rel

    model_info = infer_model_info(model_path)

    # ── Step 2: Class labels ──
    print("\n" + info("─" * 50))
    print(info("  Step 2: Class Labels"))
    print(info("─" * 50))

    label_files = find_label_files(project_root)
    labels = []

    if label_files:
        print(f"\n  Found {len(label_files)} label file(s):")
        label_options = [str(f.relative_to(project_root)) for f in label_files]
        label_options.append("Enter manually")
        choice = prompt_choice("Select labels file:", label_options, 0)

        if choice < len(label_files):
            labels = read_labels_from_file(label_files[choice])
            labels_rel = label_options[choice]
            print(success(f"  ✓ Read {len(labels)} classes: {', '.join(labels[:5])}{'...' if len(labels) > 5 else ''}"))
        else:
            raw = prompt_value("  Enter class names (comma-separated)")
            labels = [l.strip() for l in raw.split(",") if l.strip()]
            labels_rel = ""
    elif existing_config:
        labels = existing_config.get("model", {}).get("class_names", [])
        labels_rel = existing_config.get("paths", {}).get("labels", "")
        if labels:
            print(success(f"  ✓ Using existing classes: {', '.join(labels[:5])}{'...' if len(labels) > 5 else ''}"))
    else:
        raw = prompt_value("  Enter class names (comma-separated)")
        labels = [l.strip() for l in raw.split(",") if l.strip()]
        labels_rel = ""

    # Validate num_classes
    num_classes = len(labels) if labels else model_info.get("num_classes", 8)
    if model_info["num_classes"] and labels and model_info["num_classes"] != len(labels):
        print(warning(f"\n  ⚠ Warning: Model expects {model_info['num_classes']} classes "
              f"but label file has {len(labels)}."))
        keep = prompt_choice("Use labels from:", [
            f"Label file ({len(labels)} classes)",
            f"Model shape ({model_info['num_classes']} classes)",
        ], 0)
        if keep == 1:
            num_classes = model_info["num_classes"]
            labels = [f"class_{i}" for i in range(num_classes)]
            print(warning(f"  ⚠ Using placeholder class names: {labels[:5]}..."))

    # ── Step 3: Test images ──
    print("\n" + info("─" * 50))
    print(info("  Step 3: Test Images"))
    print(info("─" * 50))

    img_dir, img_count = find_test_images(project_root)
    if img_dir:
        images_rel = str(img_dir.relative_to(project_root))
        print(success(f"\n  ✓ Found {img_count} images in: {images_rel}/"))
        use_it = prompt_value(f"  Use this directory? (y/n)", "y")
        if use_it.lower() != "y":
            images_rel = prompt_value("  Enter test images directory")
    else:
        print(warning("\n  ⚠ No test images directory found."))
        images_rel = prompt_value("  Enter test images directory (relative path)", "test_images")
        img_path = project_root / images_rel
        if not img_path.exists():
            print(info(f"  Creating directory: {images_rel}/"))
            img_path.mkdir(parents=True, exist_ok=True)
            print(warning(f"  ⚠ Please add test images to {images_rel}/ before running the agent."))

    # ── Step 4: Online framework ──
    print("\n" + info("─" * 50))
    print(info("  Step 4: Online Framework"))
    print(info("─" * 50))

    framework = detect_online_framework()
    frameworks_available = []
    if importlib.util.find_spec("ultralytics"):
        frameworks_available.append("ultralytics (YOLO)")
    if importlib.util.find_spec("torch"):
        frameworks_available.append("pytorch")
    if importlib.util.find_spec("onnxruntime"):
        frameworks_available.append("onnx")

    if frameworks_available:
        print(f"\n  Detected frameworks: {', '.join(frameworks_available)}")
        print(success(f"  ✓ Will use: {framework}"))
    else:
        print(warning("\n  ⚠ No ML framework detected. Install ultralytics:"))
        print("    pip install ultralytics")

    # ── Step 5: Dart source scan ──
    print("\n" + info("─" * 50))
    print(info("  Step 5: Dart Source Code Analysis"))
    print(info("─" * 50))

    dart_info = scan_dart_thresholds(project_root)
    if dart_info["patterns_found"]:
        print(success(f"\n  ✓ Found detection parameters in Dart source:"))
        for p in dart_info["patterns_found"]:
            print(f"    • {p}")
        for f in dart_info["dart_files"]:
            print(f"    📄 {f}")
    else:
        print(info("\n  ℹ No Dart detection parameters found (auto-apply may not work)"))

    # Use scanned Dart thresholds as defaults
    default_conf = dart_info["confidence_threshold"] or 0.6
    default_iou = dart_info["iou_threshold"] or 0.45

    # ── Step 6: Thresholds ──
    print("\n" + info("─" * 50))
    print(info("  Step 6: Detection Thresholds"))
    print(info("─" * 50))

    conf_str = prompt_value(f"  Offline confidence threshold", str(default_conf))
    iou_str = prompt_value(f"  Offline IoU/NMS threshold", str(default_iou))
    offline_conf = float(conf_str)
    offline_iou = float(iou_str)

    # ── Generate config.yaml ──
    print("\n" + info("─" * 50))
    print(info("  Generating config.yaml"))
    print(info("─" * 50))

    config = {
        "paths": {
            "model_tflite": model_rel,
            "labels": labels_rel if labels_rel else "assets/labels.txt",
            "test_images": images_rel + "/",
            "traces_dir": "traces/",
            "results_dir": "results/",
        },
        "model": {
            "input_size": model_info["input_size"],
            "num_classes": num_classes,
            "class_names": labels,
        },
        "online": {
            "confidence_threshold": 0.25,
            "iou_threshold": 0.45,
        },
        "offline": {
            "normalization": "divide_255",
            "resize_method": "bilinear",
            "channel_order": "rgb",
            "letterbox_padding": True,
            "padding_color": [114, 114, 114],
            "confidence_threshold": offline_conf,
            "iou_threshold": offline_iou,
            "apply_sigmoid": False,
        },
        "parity_loss": {
            "weights": {
                "tensor_l2": 1.0,
                "logits_diff": 1.0,
                "iou_mismatch": 1.0,
                "count_diff": 0.5,
                "confidence_kl": 0.5,
            },
            "threshold": 0.05,
        },
        "agent": {
            "max_iterations": 20,
            "patience": 2,
            "max_ablation_images": 5,
            "log_level": "INFO",
        },
    }

    # Write config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # ── Summary ──
    print(success(f"\n  ✓ Config saved: {config_path}\n"))
    print(banner("=" * 70))
    print(banner("  📋 CONFIGURATION SUMMARY"))
    print(banner("=" * 70))
    print(f"  Model:          {model_rel}")
    print(f"  Architecture:   {model_info['architecture']}")
    print(f"  Input size:     {model_info['input_size']}x{model_info['input_size']}")
    print(f"  Classes:        {num_classes} ({', '.join(labels[:4])}{'...' if len(labels) > 4 else ''})")
    print(f"  Test images:    {images_rel}/")
    print(f"  Framework:      {framework}")
    print(f"  Conf threshold: {offline_conf}")
    print(f"  IoU threshold:  {offline_iou}")
    print(f"  Dart files:     {len(dart_info['dart_files'])} found")
    print()
    print("  Next steps:")
    print("    1. Add test images to the test images directory (if empty)")
    print("    2. Run:  python parity_agent/run_agent.py --mode agent --images " + images_rel + "/")
    print("    3. View: streamlit run parity_agent/dashboard/app.py")
    print()
    print("=" * 70)

    return config
