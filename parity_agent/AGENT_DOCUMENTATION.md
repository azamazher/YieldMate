# Parity Agent v0.3 — Complete Documentation

## What Is the Parity Agent?

The **Parity Agent** is an autonomous system that detects and fixes accuracy differences between two ML inference pipelines:

- **Online Pipeline** — PyTorch/Ultralytics YOLO running on desktop (the "ground truth")
- **Offline Pipeline** — TFLite running on-device in Flutter (the deployed model)

When you export a YOLO model to TFLite and run it on a phone, subtle differences in preprocessing, post-processing, NMS thresholds, and sigmoid activation can cause the on-device results to differ from the desktop results. The Parity Agent finds these differences and fixes them automatically.

---

## Getting Started (For New Users)

### Step 1: Clone the Repository

```bash
git clone https://github.com/azamazher/YieldMate.git
cd YieldMate
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r parity_agent/requirements-agent.txt
```

This installs: `ultralytics`, `tensorflow`, `langgraph`, `streamlit`, `numpy`, `pyyaml`, `pillow`, and other dependencies.

### Step 4: Run the Setup Wizard

```bash
python parity_agent/run_agent.py --mode setup
```

The wizard will:
1. Scan your project for `.tflite` models
2. Find label files (`labels.txt`, `classes.txt`)
3. Load the model and detect input size, number of classes, and architecture
4. Find test image directories
5. Detect which ML framework you have installed
6. Scan your Dart source code for threshold values
7. Generate a ready-to-use `config.yaml`

**Example wizard output:**
```
======================================================================
  🧙 PARITY AGENT — SETUP WIZARD
  Auto-configure the agent for your project
======================================================================

──────────────────────────────────────────────────
  Step 1: TFLite Model
──────────────────────────────────────────────────

  Found 1 TFLite model(s):

Select model:
  [1] assets/model.tflite ← default

Choice [1-1] (default: 1):
  ✓ Model loaded: input=640x640, output=[1, 12, 8400], arch=yolov8
  ✓ Detected 8 classes from output shape

──────────────────────────────────────────────────
  Step 2: Class Labels
──────────────────────────────────────────────────

  Found 1 label file(s):

Select labels file:
  [1] assets/labels.txt ← default
  [2] Enter manually

Choice [1-2] (default: 1):
  ✓ Read 8 classes: apple, watermelon, mango, strawberry, banana...
```

### Step 5: Add Test Images

Place 5-15 test images in the `test_images/` folder. These should be representative images that your app will detect.

### Step 6: Run the Agent

```bash
# Basic run — detect issues
python parity_agent/run_agent.py --mode agent --images test_images/

# Full run — detect + auto-fix your Dart code (prompts y/n)
python parity_agent/run_agent.py --mode agent --images test_images/ --auto-apply
```

### Step 7: View Results

```bash
# Option 1: Streamlit Dashboard (interactive)
streamlit run parity_agent/dashboard/app.py

# Option 2: HTML Report (static)
python parity_agent/run_agent.py --mode report --images test_images/
# Then open: results/report/parity_report.html
```

---

## CLI Help Reference

Run `python parity_agent/run_agent.py --help` to see all options:

```
usage: run_agent.py [-h]
                    [--mode {trace,diff,agent,agent-legacy,full,report,setup}]
                    [--images IMAGES]
                    [--config CONFIG]
                    [--auto-apply]

Autonomous Cross-Platform ML Parity Agent

optional arguments:
  -h, --help            Show this help message and exit

  --mode {trace,diff,agent,agent-legacy,full,report,setup}
                        Operation mode:
                          setup         Interactive setup wizard
                          trace         Generate golden traces only
                          diff          Compute parity loss from saved traces
                          agent         Full LangGraph autonomous loop
                          agent-legacy  Old while-loop agent (fallback)
                          full          Trace → Diff → Agent (everything)
                          report        Generate visual HTML report

  --images IMAGES       Path to test images directory (default: test_images/)

  --config CONFIG       Path to config.yaml
                        (default: parity_agent/config.yaml)

  --auto-apply          Auto-apply findings to Flutter source code
                        (with y/n prompt before each change)

Examples:
  python parity_agent/run_agent.py --mode setup
  python parity_agent/run_agent.py --mode trace --images test_images/
  python parity_agent/run_agent.py --mode diff
  python parity_agent/run_agent.py --mode agent --images test_images/
  python parity_agent/run_agent.py --mode agent --images test_images/ --auto-apply
  python parity_agent/run_agent.py --mode report --images test_images/
```

---

## Purpose and Use Cases

### Primary Purpose
Ensure that the **Flutter fruit detection app** produces identical detection results to the Ultralytics YOLO desktop pipeline. This is critical because:
- Users expect the same accuracy on their phone as shown during model evaluation
- Small threshold or preprocessing differences can cause missed detections or false positives
- Manual debugging of ML pipeline differences is extremely time-consuming

### When to Use
- **After exporting a model** — Run the agent to verify TFLite matches PyTorch
- **After changing detection parameters** — Verify parity is maintained
- **During development** — Catch regressions early with the visual report
- **For debugging** — Use the trace viewer to see exactly where pipelines diverge

---

## How It Works — The LangGraph State Machine

The agent is orchestrated by **LangGraph**, a state machine framework. It runs as a directed graph with 6 nodes that loop automatically:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│  TRACE   │───▶│   DIFF   │───▶│ PROFILE  │───▶│ HYPOTHESIZE │───▶│ ABLATION │───▶│  DECIDE  │
│          │    │          │    │          │    │             │    │          │    │          │
│ Run both │    │ Compute  │    │ Find root│    │ Generate    │    │ Sweep    │    │ Apply or │
│ pipelines│    │ parity   │    │ cause    │    │ fix ideas   │    │ params   │    │ stop     │
│ on images│    │ loss     │    │ stage    │    │             │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └─────────────┘    └──────────┘    └────┬─────┘
     ▲                                                                                  │
     └──────────────────────── Loop until converged or patience exhausted ───────────────┘
```

### Node 1: Trace
- Runs the **Online Pipeline** (Ultralytics YOLO) on all test images
- Runs the **Offline Pipeline** (TFLite with current config) on the same images
- Captures **4 checkpoints** per image per pipeline:
  1. **Input tensor** — The preprocessed image fed to the model
  2. **Raw output** — The model's raw output tensor
  3. **Decoded boxes** — Boxes after decoding (before NMS)
  4. **NMS boxes** — Final detections after Non-Maximum Suppression
- Pairs online + offline results into **Golden Traces**

### Node 2: Diff
- Computes **5 divergence metrics** between online and offline for each image:

| Metric | What It Measures | Weight |
|--------|-----------------|--------|
| `tensor_l2` | Raw tensor distance between outputs | 1.0 |
| `logits_diff` | Pre-NMS logit differences | 1.0 |
| `iou_mismatch` | Bounding box position accuracy | 1.0 |
| `count_diff` | Detection count mismatch | 0.5 |
| `confidence_kl` | Confidence score distribution divergence | 0.5 |

- Combines metrics into a single **Parity Loss** score (weighted sum)
- If loss < threshold (0.05), pipelines are aligned ✅

### Node 3: Profile
- Analyzes which **pipeline stage** is causing the most divergence:
  - `preprocessing` — Input normalization, resize, channel order
  - `calibration` — Sigmoid, confidence scaling
  - `nms_behavior` — NMS threshold, suppression differences
  - `localization` — Box coordinate differences
- This determines which hypotheses to generate

### Node 4: Hypothesize
- Generates ranked **hypotheses** based on the profile:
  - `sigmoid_missing_or_double` (critical) — Sigmoid may be missing or double-applied
  - `confidence_threshold_mismatch` (high) — Threshold gap causing count difference
  - `nms_threshold_mismatch` (high) — IoU threshold differs
  - `normalization_mismatch` (high) — Input normalization differs
  - `iou_threshold_sweep` (medium) — IoU mismatch detected
  - `exhaustive_parameter_sweep` (low) — Fallback: sweep everything
- Each hypothesis lists parameters to test

### Node 5: Ablation
- For each hypothesis, **sweeps the suggested parameters**:
  - e.g., `confidence_threshold`: tests 0.1, 0.2, 0.3, ..., 0.9
  - e.g., `apply_sigmoid`: tests True, False
  - e.g., `iou_threshold`: tests 0.2, 0.25, 0.3, ..., 0.85
- For each value, re-runs the offline pipeline and computes parity loss
- Records the **best value** and **improvement** for each parameter
- Saves all experiments to `results/experiments/experiment_log.json`

#### Combo Ablation (Multi-Parameter)
When single-parameter sweeps find no improvement, the agent automatically
falls back to **combo ablation** for linked parameters:

| Parameter | Linked With | Why They're Linked |
|-----------|------------|--------------------|
| `apply_sigmoid` | `confidence_threshold` | Without sigmoid, raw logits (0–80) blow past any threshold. With sigmoid, values are 0–1. Both must change together. |
| `confidence_threshold` | `apply_sigmoid` | Threshold scale depends entirely on whether sigmoid is applied. |

**How it works:**
1. Single-param ablation tests `apply_sigmoid` alone → no improvement
2. Single-param ablation tests `confidence_threshold` alone → no improvement
3. Agent detects these params are **linked** → triggers combo ablation
4. Combo ablation tests ALL combinations (2 sigmoid × 9 thresholds = 18 configs)
5. Finds the winning combo (e.g., `sigmoid=True + conf=0.6`) and applies **both**

This solves the fundamental problem where two co-dependent parameters must
change simultaneously for any improvement to occur.

### Node 6: Decide
- If the best ablation result improves loss by > 0.001:
  - **Applies the fix** — updates config.yaml with the new value
  - Records the change in **alignment history**
  - Saves history to `results/alignment_history.json`
  - Loops back to Node 1 (Trace) for another iteration
- If no improvement:
  - Increments `no_improve_count`
  - After `patience` (default: 2) iterations without improvement → **stops**

---

## Operation Modes

The agent has 7 operating modes, selected via `--mode`:

| Mode | Command | What It Does |
|------|---------|-------------|
| **setup** | `python parity_agent/run_agent.py --mode setup` | Interactive wizard — auto-configures for any project |
| **agent** | `python parity_agent/run_agent.py --mode agent --images test_images/` | Full LangGraph autonomous loop. |
| **agent + auto-apply** | `... --mode agent --images test_images/ --auto-apply` | Same as above + prompts y/n to patch Dart source files |
| **agent-legacy** | `... --mode agent-legacy --images test_images/` | Original while-loop agent (fallback if LangGraph not installed) |
| **trace** | `... --mode trace --images test_images/` | Generate golden traces only (saves to `traces/`) |
| **diff** | `... --mode diff` | Compute parity loss from saved traces |
| **report** | `... --mode report --images test_images/` | Generate visual HTML report with side-by-side images |
| **full** | `... --mode full --images test_images/` | Trace → Diff → Agent (everything) |

### Auto-Apply Feature
When running with `--auto-apply`, after fixing the config parameters, the agent:
1. Scans your Flutter/Dart source files for detection parameters
2. Finds values like `confThreshold = 0.3`
3. Generates patches with the optimized values
4. Prompts you `Apply patch? [y/n]` for each change
5. If you accept, directly edits your Dart code

### Setup Wizard (`--mode setup`)
For new users or new projects, the wizard automatically:
1. **Scans for TFLite models** — Finds all `.tflite` files in the project
2. **Reads label files** — Auto-detects `labels.txt`, `classes.txt`, etc.
3. **Infers model info** — Loads the TFLite model to detect input size, num_classes, and architecture (YOLOv8/SSD/EfficientDet)
4. **Finds test images** — Looks for `test_images/`, `images/`, etc.
5. **Detects ML framework** — Checks if Ultralytics, PyTorch, or ONNX is installed
6. **Scans Dart source** — Finds `confThreshold`, `iouThreshold`, and similar patterns in your code
7. **Generates `config.yaml`** — Ready to use with the agent

This means a new user just runs `--mode setup` and can immediately start the agent without manually editing config.

---

## Folders Created by the Agent

### `traces/` — Golden Trace Storage
Created by: `--mode trace` or `--mode agent`

```
traces/
├── online/
│   ├── apple_online.json          ← Online pipeline trace for "apple" image
│   ├── mango_online.json
│   ├── Orange_online.json
│   └── ...                        ← One file per test image
└── offline/
    ├── apple_offline.json         ← Offline pipeline trace for "apple" image
    ├── mango_offline.json
    ├── Orange_offline.json
    └── ...                        ← One file per test image
```

Each trace JSON contains the 4 checkpoints:
- Input tensor shape and metadata
- Raw model output
- Decoded bounding boxes (before NMS)
- Final NMS detections with class, confidence, and bbox coordinates

The agent loads these and pairs them into **Golden Traces** (online + offline for the same image).

---

### `results/` — Agent Outputs
Created by: `--mode agent` and `--mode report`

```
results/
├── alignment_history.json         ← Every parameter change the agent applied
├── experiments/
│   └── experiment_log.json        ← All ablation experiment results (66+ entries)
└── report/
    ├── parity_report.md           ← Markdown report
    ├── parity_report.html         ← Styled HTML report (open in browser)
    └── images/
        ├── apple_comparison.jpg   ← Side-by-side: Online vs Offline detections
        ├── Orange_comparison.jpg
        ├── mango_comparison.jpg
        └── ...                    ← One comparison image per test image
```

#### `alignment_history.json`
Records every config change the agent made:
```json
[
  {
    "parameter": "confidence_threshold",
    "old_value": 0.3,
    "new_value": 0.6,
    "improvement": 741.82,
    "timestamp": "2026-02-23T19:40:00"
  }
]
```
If empty (`[]`), the agent found the config was already optimal.

#### `experiment_log.json`
Records every ablation experiment:
```json
[
  {
    "experiment_name": "ablation_confidence_threshold_0.6",
    "config": { "confidence_threshold": 0.6 },
    "aggregate": { "mean_loss": 0.071310 },
    "timestamp": "2026-02-24T00:06:00"
  }
]
```

#### `report/` — Visual Parity Report
- `parity_report.html` — Open in browser for a styled dark-themed report
- `parity_report.md` — Markdown version
- `images/` — Side-by-side comparison images showing Online (left) vs Offline (right) detections with bounding boxes

---

## Streamlit Dashboard

**Command (same for all users):**
```bash
streamlit run parity_agent/dashboard/app.py
```

This opens a browser at `http://localhost:8501` with **5 interactive pages**:

### Page 1: 📊 Overview
- **4 KPI cards**: Mean Parity Loss, Images analyzed, Threshold, Changes Applied
- **Per-Image Parity Loss chart**: Bar chart showing loss per image (red bars = highest divergence)
- **Detection Count: Online vs Offline**: Grouped bar chart comparing detection counts

### Page 2: 🖼️ Trace Viewer
- **Image selector**: Dropdown to pick any test image
- **Side-by-side view**: Online Pipeline (left) vs Offline Pipeline (right) with bounding boxes drawn
- **Checkpoint Data**: Expandable sections showing:
  - Input tensor shape
  - Raw output shape
  - Number of decoded boxes
  - Number of NMS boxes
  - Individual detection details (class, confidence, bbox coordinates)

### Page 3: 📈 Metrics
- **Per-Image Metrics Table**: Shows all 5 metrics for each image
- **Metric Averages Chart**: Bar chart of average values across all images
- Columns: tensor_l2, logits_diff, iou_mismatch, count_diff, confidence_kl, Total Loss

### Page 4: 🧪 Ablation Explorer
- **Total experiments count**
- **Parameter sweep cards**: For each parameter tested (e.g., confidence_threshold):
  - Bar chart showing loss at each tested value
  - Best Value and Best Loss metrics
  - Data table with all tested values and losses
- Shows data from `results/experiments/experiment_log.json`

### Page 5: 📜 Alignment History
- **Timeline of changes**: Each parameter change the agent applied
  - Parameter name, old value → new value, improvement amount
- **Total improvement metric**
- Shows data from `results/alignment_history.json`
- If no changes were applied (config was already optimal), shows "No changes applied yet"

---

## Config File: `parity_agent/config.yaml`

The agent reads and writes this file. You can either edit it manually or let `--mode setup` generate it.

```yaml
paths:                           # File locations
  model_tflite: assets/model.tflite
  labels: assets/labels.txt
  test_images: test_images/
  traces_dir: traces/
  results_dir: results/

model:                           # Model metadata
  input_size: 640
  num_classes: 8
  class_names:                   # Your class labels
    - apple
    - watermelon
    - mango
    - strawberry
    - banana
    - orange
    - pineapple
    - grape

online:                          # Online pipeline (reference — don't change this)
  confidence_threshold: 0.25
  iou_threshold: 0.45

offline:                         # Offline pipeline (AGENT TUNES THESE)
  confidence_threshold: 0.6     # ← Agent may change this
  iou_threshold: 0.45           # ← Agent may change this
  apply_sigmoid: false          # ← Agent may change this
  normalization: divide_255     # ← Agent may change this
  channel_order: rgb            # ← Agent may change this
  resize_method: bilinear
  letterbox_padding: true
  padding_color: [114, 114, 114]

parity_loss:
  threshold: 0.05               # Loss below this = PASS
  weights:                      # Relative importance of each metric
    tensor_l2: 1.0
    logits_diff: 1.0
    iou_mismatch: 1.0
    count_diff: 0.5
    confidence_kl: 0.5

agent:
  max_iterations: 20            # Maximum loop iterations
  patience: 2                   # Stop after N iterations without improvement
  max_ablation_images: 5        # Number of images used in sweeps (speed vs accuracy)
  log_level: INFO
```

---

## Project Architecture

```
parity_agent/
├── run_agent.py                  # CLI entry point — all 7 modes
├── config.yaml                   # Agent configuration (auto-updated by agent)
├── setup_wizard.py               # Interactive project setup wizard
├── requirements-agent.txt        # Python dependencies
│
├── agents/                       # LangGraph nodes
│   ├── graph.py                  # State machine (6 nodes + routing)
│   ├── alignment.py              # Applies best config, saves history
│   ├── hypothesis.py             # Generates fix hypotheses from profile
│   ├── profiler.py               # Identifies dominant divergence stage
│   ├── ablation.py               # Sweeps parameters to find best values
│   └── auto_apply.py             # Patches Dart source files
│
├── trace/                        # Tracing system
│   ├── online_tracer.py          # Runs Ultralytics YOLO inference
│   ├── offline_tracer.py         # Runs TFLite inference with config
│   ├── schema.py                 # Data models (PipelineTrace, GoldenTrace, Detection)
│   └── storage.py                # Saves/loads traces to disk (JSON)
│
├── diff/                         # Parity measurement
│   ├── parity_loss.py            # Weighted 5-metric parity loss computation
│   ├── metrics.py                # Individual metric functions
│   └── visual_report.py          # Generates HTML/Markdown report + comparison images
│
├── alignment/                    # Experiment infrastructure
│   ├── experiment_runner.py      # Runs and logs ablation experiments
│   └── parameters.py             # Default config and search spaces
│
├── architectures/                # Model architecture support
│   └── detector.py               # YOLOv8, SSD, EfficientDet decoders
│
├── utils/                        # Utilities
│   └── image_loader.py           # Test image discovery
│
├── dashboard/                    # Streamlit UI
│   └── app.py                    # 5-page dashboard
│
└── tests/                        # Unit tests
    └── test_agent.py             # 19 tests
```

---

## Tests

Run with:
```bash
pytest parity_agent/tests/ -v
```

**19 tests covering:**
- Tensor L2 metric (identical, different, None inputs)
- Count diff metric
- Logits diff metric
- Hypothesis generation (confidence, normalization, priority ordering)
- Parity loss (custom weights, zero loss for identical)
- Auto-apply (Dart file scanning, confidence target finding, patch generation)
- Architecture detection (YOLOv8, transposed, unknown, decoder)

---

## Quick Reference

| Task | Command |
|------|---------|
| **Setup wizard** | `python parity_agent/run_agent.py --mode setup` |
| **Run agent** (detect + fix) | `python parity_agent/run_agent.py --mode agent --images test_images/` |
| **Run agent + patch Dart** | `python parity_agent/run_agent.py --mode agent --images test_images/ --auto-apply` |
| **Generate traces only** | `python parity_agent/run_agent.py --mode trace --images test_images/` |
| **Compute parity loss** | `python parity_agent/run_agent.py --mode diff` |
| **Generate visual report** | `python parity_agent/run_agent.py --mode report --images test_images/` |
| **Run everything** | `python parity_agent/run_agent.py --mode full --images test_images/` |
| **Open dashboard** | `streamlit run parity_agent/dashboard/app.py` |
| **Run tests** | `pytest parity_agent/tests/ -v` |
| **Show help** | `python parity_agent/run_agent.py --help` |

---

## For Other Users — What You Need to Change

If you want to use this agent for **your own** Flutter + TFLite project:

### Option A: Use the Setup Wizard (Recommended)
```bash
# Just run the wizard — it auto-detects everything
python parity_agent/run_agent.py --mode setup
```

### Option B: Manual Configuration
Edit `parity_agent/config.yaml`:

| What to change | Where | Example |
|----------------|-------|---------|
| Model path | `paths.model_tflite` | `assets/your_model.tflite` |
| Labels | `model.class_names` | Your class names list |
| `num_classes` | `model.num_classes` | Must match your model |
| Test images | `paths.test_images` | Your test images folder |
| Confidence threshold | `offline.confidence_threshold` | Match your Dart code |
| IoU threshold | `offline.iou_threshold` | Match your Dart code |

### What works universally (no changes needed):
- ✅ LangGraph state machine
- ✅ All 5 divergence metrics
- ✅ Single + combo ablation sweep engine
- ✅ Hypothesis generation
- ✅ Streamlit dashboard
- ✅ HTML report generation
- ✅ Architecture auto-detection (YOLOv8, SSD, EfficientDet)

---

## Full Agent Capabilities Summary

Here is everything your Parity Agent can do:

### ✅ What the Agent CAN Do

| Capability | How |
|-----------|-----|
| **Detect accuracy drift** | Runs both pipelines on the same images and computes 5 divergence metrics |
| **Pinpoint the root cause** | Profiles which pipeline stage (preprocessing, calibration, NMS) is diverging most |
| **Generate fix hypotheses** | Uses domain knowledge rules to suggest which parameters to tune |
| **Single-parameter sweeps** | Tests one parameter at a time across its full range |
| **Multi-parameter combo sweeps** | Tests co-dependent parameters together (e.g., sigmoid + threshold) |
| **Apply fixes to config.yaml** | Automatically updates the offline pipeline configuration |
| **Patch your Dart source code** | With `--auto-apply`, finds and patches threshold values in your Flutter code |
| **Prompt before applying** | Shows you the patch diff and asks `y/n` before modifying any source file |
| **Generate visual reports** | Side-by-side HTML comparison images for each test image |
| **Interactive dashboard** | 5-page Streamlit UI showing traces, metrics, experiments, and history |
| **Converge automatically** | Loops until parity loss < threshold or patience is exhausted |
| **Handle any YOLO model** | Auto-detects YOLOv8, SSD, EfficientDet architectures |
| **Setup for new projects** | Interactive wizard auto-configures everything for any Flutter+TFLite project |

### ❌ What the Agent CANNOT Do

| Limitation | Why |
|-----------|-----|
| **Retrain the model** | Model weights are FROZEN — the agent only tunes deployment config |
| **Fix model architecture bugs** | If your TFLite export is corrupted, the agent can't fix the model itself |
| **Fix non-threshold Dart bugs** | The auto-apply only patches numeric thresholds and sigmoid patterns |
| **Test on real devices** | The offline pipeline runs in Python, not on actual Android/iOS hardware |
| **Fix network/server issues** | The agent only handles ML pipeline parity, not connectivity issues |

### Parameters the Agent Can Tune

| Parameter | Type | Search Range | What It Controls |
|-----------|------|-------------|------------------|
| `confidence_threshold` | Continuous | 0.1 – 0.9 (step 0.1) | Minimum detection confidence to keep |
| `iou_threshold` | Continuous | 0.2 – 0.8 (step 0.05) | NMS overlap threshold for suppression |
| `apply_sigmoid` | Boolean | True / False | Whether to apply sigmoid to raw logits |
| `normalization` | Categorical | divide_255, neg1_pos1, none | Input pixel normalization method |
| `channel_order` | Categorical | rgb, bgr | Color channel ordering |
| `resize_method` | Categorical | bilinear, nearest, area, lanczos | Image resize interpolation |
| `letterbox_padding` | Boolean | True / False | Whether to use letterbox or stretch |
| `padding_color` | Categorical | [114,114,114], [0,0,0], [128,128,128] | Letterbox padding fill color |
