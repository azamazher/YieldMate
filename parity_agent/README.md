# 🔬 Parity Agent — Developer Guide

> **An Autonomous Cross-Platform ML Parity Agent**
> The first autonomous agent capable of maintaining behavioral invariance of machine learning models across heterogeneous deployment environments.

---

## Table of Contents

- [What Is This?](#what-is-this)
- [The Problem It Solves](#the-problem-it-solves)
- [How It Works (Big Picture)](#how-it-works-big-picture)
- [Folder Structure](#folder-structure)
- [File-by-File Reference](#file-by-file-reference)
- [The Autonomous Control Loop](#the-autonomous-control-loop)
- [Configuration](#configuration)
- [How to Run](#how-to-run)
- [Key Concepts](#key-concepts)
- [FAQ](#faq)
- [Version 2 — New Features & Scripts](#version-2--new-features--scripts)
- [For New Users: Running the Agent on Your Own Project](#for-new-users-running-the-agent-on-your-own-project)

---

## What Is This?

This is a **Python-based autonomous agent** that acts as a **"debugger for ML deployments"**.

Imagine you trained a YOLOv8 object detection model. It works great on your server (using PyTorch). You export it to TFLite and run it on a phone (using Flutter). But now the phone gives **different results** — fewer detections, wrong bounding boxes, different confidence scores.

**This agent automatically finds out WHY and fixes it.**

It does this through three capabilities:
1. **Self-Observing** — Instruments both pipelines and records everything
2. **Self-Diagnosing** — Finds exactly where the divergence comes from
3. **Self-Correcting** — Runs experiments and fixes the configuration

---

## The Problem It Solves

When you deploy the same ML model to different platforms, the **results differ** even though the **model weights are identical**. This happens because of differences in:

| Factor | Example |
|--------|---------|
| **Normalization** | Server divides by 255, phone divides by 127.5 |
| **Resize method** | Server uses bilinear, phone uses nearest-neighbor |
| **Channel order** | Server expects BGR, phone sends RGB |
| **NMS threshold** | Server uses 0.45, phone uses 0.5 |
| **Sigmoid** | Server applies sigmoid internally, phone may not |
| **Padding** | Server pads with black, phone pads with gray |

These seem like small things, but they cause **real detection failures** in production.

**The Parity Agent finds and fixes all of these automatically.**

---

## How It Works (Big Picture)

The agent runs a loop — think of it like a scientific experiment on repeat:

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE AUTONOMOUS LOOP                          │
│                                                                 │
│   ┌───────┐    ┌──────┐    ┌─────────┐    ┌───────────────┐   │
│   │ TRACE │───▶│ DIFF │───▶│ PROFILE │───▶│  HYPOTHESIZE  │   │
│   └───────┘    └──────┘    └─────────┘    └──────┬────────┘   │
│       ▲                                          │             │
│       │        ┌───────┐    ┌──────────┐         │             │
│       └────────│ ALIGN │◀───│  ABLATE  │◀────────┘             │
│                └───────┘    └──────────┘                       │
│                                                                 │
│   Repeats until parity_loss < threshold (convergence)          │
└─────────────────────────────────────────────────────────────────┘
```

1. **TRACE** — Run the same image through both pipelines, record everything
2. **DIFF** — Compare the recordings, compute how different they are (parity loss)
3. **PROFILE** — Figure out which pipeline stage causes the most difference
4. **HYPOTHESIZE** — Guess what configuration change would fix it
5. **ABLATE** — Test that guess by changing one thing at a time
6. **ALIGN** — Keep the best configuration, go back to step 1

---

## Folder Structure

```
parity_agent/
│
├── README.md                     ← You are here
├── __init__.py                   ← Package marker
├── config.yaml                   ← All settings in one place
├── requirements-agent.txt        ← Python dependencies
├── run_agent.py                  ← MAIN ENTRY POINT — start here to run
│
├── trace/                        ← "The Eyes" — Making pipelines observable
│   ├── schema.py                 ← Data models (Detection, PipelineTrace, GoldenTrace)
│   ├── online_tracer.py          ← Records the server/PyTorch pipeline
│   ├── offline_tracer.py         ← Records the phone/TFLite pipeline
│   └── storage.py                ← Saves/loads traces to disk (JSON + NPZ)
│
├── diff/                         ← "The Brain" — Measuring the gap
│   ├── metrics.py                ← 5 divergence metrics
│   ├── parity_loss.py            ← Combines all 5 into one number
│   ├── report.py                 ← Pretty-prints the results
│   └── visual_report.py          ← Draws detection boxes on images
│
├── alignment/                    ← "The Hands" — Tools to fix things
│   ├── parameters.py             ← 8 tunable parameters
│   └── experiment_runner.py      ← Runs controlled experiments
│
├── agents/                       ← "The Intelligence" — Autonomous reasoning
│   ├── profiler.py               ← Finds the biggest problem
│   ├── hypothesis.py             ← Guesses the cause
│   ├── ablation.py               ← Tests the guesses
│   ├── alignment.py              ← Keeps the best fix
│   ├── auto_apply.py             ← Auto-applies fixes to Dart source code
│   └── graph.py                  ← LangGraph state machine orchestration
│
├── utils/                        ← Shared utilities
│   ├── image_loader.py           ← Finds test images on disk
│   ├── snapshots.py              ← [v0.2] Saves baseline/final detection state + metrics
│   └── parity_metrics.py         ← [v0.2] IoU-based precision/recall/F1/mAP computation
│
├── dashboard/                    ← [v0.2] Streamlit dashboard
│   └── app.py                    ← Interactive dashboard (5 tabs)
│
├── bmvc_figures.py               ← [v0.2] Generates publication-quality figures from snapshots
├── save_annotated_images.py      ← [v0.2] Before/after detection box visualisation
├── proposal.md                   ← [v0.2] BMVC conference proposal
│
└── tests/                        ← Unit tests
    └── __init__.py
```

---

## File-by-File Reference

### `run_agent.py` — The Main Entry Point

**What it does:** Loads the config, discovers test images, and orchestrates the entire pipeline.

**Key functions:**
- `main()` — Parses command-line arguments, picks which mode to run
- `run_trace()` — Phase 2: generates Golden Traces for all test images
- `run_diff()` — Phase 3: computes diff metrics and generates report
- `run_agent_loop()` — Phase 5: the full autonomous while-loop

---

### `config.yaml` — Configuration

**What it does:** Central settings file. Everything the agent needs to know is here.

**Sections:**
- **`paths`** — Where to find the model, labels, test images, and output
- **`model`** — Model info (input size, class names) — READ-ONLY
- **`online`** — Server pipeline settings — the REFERENCE (ground truth)
- **`offline`** — Phone pipeline settings — what the AGENT CAN CHANGE
- **`parity_loss.weights`** — How much each metric matters
- **`agent`** — Agent behavior (max iterations, patience)

**Important:** The `offline` section is what the agent modifies. Everything else stays fixed.

---

### `trace/schema.py` — Data Models

**Key classes:**
- **`Detection`** — One bounding box: `class_name`, `confidence`, `bbox [x1, y1, x2, y2]`
- **`PipelineTrace`** — Complete recording of one image through one pipeline (4 checkpoints)
- **`GoldenTrace`** — A PAIR of traces (online + offline) for the SAME image

**4 checkpoints per trace:** `input_tensor` → `raw_output` → `decoded_boxes` → `nms_boxes`

---

### `diff/metrics.py` — 5 Divergence Metrics

| # | Function | What it measures | Catches |
|---|----------|-----------------|---------|
| 1 | `tensor_l2()` | L2 distance of input tensors | Normalization, resize bugs |
| 2 | `logits_diff()` | Mean absolute diff of raw outputs | Quantization drift |
| 3 | `iou_mismatch()` | 1 − mean(IoU of matched boxes) | Bounding box errors |
| 4 | `count_diff()` | Detection count difference | NMS threshold issues |
| 5 | `confidence_kl()` | KL divergence of confidences | Sigmoid/calibration |

---

### `alignment/parameters.py` — The 8 Tunable Parameters

| Parameter | Type | Options | What it controls |
|-----------|------|---------|-----------------|
| `normalization` | categorical | `divide_255`, `neg1_pos1`, `none` | Pixel value scaling |
| `resize_method` | categorical | `bilinear`, `nearest`, `area`, `lanczos` | Image resizing |
| `channel_order` | categorical | `rgb`, `bgr` | Color channel order |
| `confidence_threshold` | continuous | 0.1 to 0.9 (step 0.05) | Min detection confidence |
| `iou_threshold` | continuous | 0.2 to 0.8 (step 0.05) | NMS overlap threshold |
| `apply_sigmoid` | categorical | `true`, `false` | Sigmoid on raw logits |
| `letterbox_padding` | categorical | `true`, `false` | Letterbox vs stretch |
| `padding_color` | categorical | `[114,114,114]`, `[0,0,0]`, `[128,128,128]` | Letterbox fill color |

---

## How to Run

### Prerequisites

```bash
pip install -r parity_agent/requirements-agent.txt
```

### Step 1: Add Test Images

```bash
mkdir test_images
# Copy or download 10–20 test images into this folder
```

### Step 2: Run the Agent

```bash
# Full autonomous run (recommended)
python parity_agent/run_agent.py --mode graph --images test_images/

# Or run phases individually:
python parity_agent/run_agent.py --mode trace --images test_images/   # Generate traces
python parity_agent/run_agent.py --mode diff                          # Compute diffs
python parity_agent/run_agent.py --mode agent --images test_images/   # Agent loop
```

### Step 3: Generate Figures & Visualisations (Version 2)

```bash
# Generate publication-quality BMVC figures from analysis data
python parity_agent/bmvc_figures.py

# Generate before/after annotated images (side-by-side comparisons)
python parity_agent/save_annotated_images.py

# Launch the interactive Streamlit dashboard
streamlit run parity_agent/dashboard/app.py
```

### Output

```
traces/                           ← Golden Traces (JSON + NPZ)
results/
├── diffs/                        ← Diff reports (Markdown)
├── experiments/                  ← Experiment logs (JSON)
├── snapshots/                    ← [v0.2] Baseline & final detection snapshots
│   ├── baseline_snapshot.json    ← Pre-fix state (auto-captured at iteration 0)
│   ├── final_snapshot.json       ← Post-fix state (auto-captured at convergence)
│   ├── baseline_images/          ← Annotated images BEFORE agent fix
│   └── final_images/             ← Annotated images AFTER agent fix
├── figures/                      ← [v0.2] Publication-quality figures (PNG, 300 DPI)
│   ├── fig1_confidence_comparison.png
│   ├── fig2_detection_count_recovery.png
│   ├── fig3_parity_loss_convergence.png
│   ├── fig4_ablation_heatmap.png
│   └── fig5_per_image_comparison.png
└── alignment_history.json        ← What the agent changed
```

---

## Key Concepts

### Golden Trace
A complete recording of what happens inside a pipeline for one image. Like an X-ray of the inference process.

### Parity Loss
A single number (0 = perfect match, higher = worse) measuring how different the pipelines behave. The agent minimises this.

### Ablation
A controlled experiment where you change ONE thing and measure the effect. Scientific method, automated.

### Frozen Model
The model weights are NEVER changed. The agent only adjusts the "plumbing" around the model.

---

## FAQ

**Q: Does this agent use GPT/LLM/ChatGPT?**
No. The agent uses deterministic rules and controlled experiments. No language models.

**Q: Can this work with models other than YOLO?**
Yes. The trace schema works for any model that takes an image tensor and outputs detection boxes. Update `config.yaml` with your class names and input size.

**Q: What if the parity loss never reaches zero?**
Some numerical differences are inherent to quantisation (FP32 vs INT8). The threshold in `config.yaml` defines "good enough." A loss of 0.01 typically means detections are functionally equivalent.

---

---

# Version 2 — New Features & Scripts

Version 2 introduces **automated analysis, dynamic figures, IoU-based metrics, and visual before/after comparisons**. Everything is fully portable — works with any user's project and test images.

## What's New in v0.2

| Feature | Description |
|---------|-------------|
| **Snapshot System** | Auto-captures baseline (pre-fix) and final (post-fix) detection data |
| **IoU-Based Metrics** | Precision, Recall, F1, mAP@0.5, mAP@0.5:0.95 using IoU matching |
| **Publication Figures** | 5 dynamic figures generated from real data (300 DPI) |
| **Before/After Images** | Side-by-side visualisation of detection boxes |
| **Streamlit Dashboard** | 5-tab interactive dashboard with metrics tables |
| **BMVC Proposal** | Full academic proposal with formal metric definitions |

---

## New Scripts (v0.2)

### `utils/snapshots.py` — Snapshot Utility

**What it does:** Captures structured JSON snapshots of the detection state at key moments.

**How it works:**
- At **iteration 0** of the agent run → saves `baseline_snapshot.json` (the broken state)
- At **convergence/stop** → saves `final_snapshot.json` (the fixed state)
- Each snapshot contains: per-image detection counts, per-class confidence scores, pipeline config, parity loss, and IoU-based metrics

**Key functions:**
- `save_snapshot(golden_traces, loss, config, type, dir)` — Save a snapshot
- `load_snapshot(dir, type)` — Load a snapshot

**Why this matters:** All figures, tables, and Streamlit data are generated FROM these snapshots. No hardcoded values. If you re-run the agent with new test images, everything updates automatically.

---

### `utils/parity_metrics.py` — IoU-Based Detection Metrics

**What it does:** Computes standard COCO detection evaluation metrics by treating online detections as ground truth.

**Metrics computed:**
- **Precision** = TP / (TP + FP) — "Of what offline detected, how much was correct?"
- **Recall** = TP / (TP + FN) — "Of what should have been detected, how much did offline find?"
- **F1** = harmonic mean of precision and recall
- **mAP@0.5** = Average Precision at IoU threshold 0.5, averaged across all classes
- **mAP@0.5:0.95** = mAP averaged across 10 IoU thresholds (0.5 to 0.95)

**How IoU matching works:**
1. For each image, sort offline predictions by confidence (highest first)
2. Match each prediction to the closest online detection using IoU
3. If IoU ≥ threshold AND class matches → True Positive
4. No match → False Positive
5. Unmatched online detections → False Negative

**Key function:** `compute_parity_metrics(golden_traces)` → returns dict with all metrics

---

### `bmvc_figures.py` — Publication Figure Generator

**What it does:** Generates 5 publication-quality figures (300 DPI PNG) from the snapshot data.

**Run:** `python parity_agent/bmvc_figures.py`

**Figures generated:**
1. **fig1** — Per-class confidence comparison (online vs offline, before vs after)
2. **fig2** — Detection count recovery (16,000 broken → 29 fixed)
3. **fig3** — Parity loss convergence over agent iterations
4. **fig4** — Combo ablation heatmap (sigmoid × confidence threshold sweep)
5. **fig5** — Per-image detection comparison (before vs after, every test image)

**Data source:** Reads from `results/snapshots/baseline_snapshot.json` and `results/snapshots/final_snapshot.json`. If these files don't exist, run the agent first.

---

### `save_annotated_images.py` — Before/After Visual Comparison

**What it does:** Renders bounding boxes on each test image for both the broken and fixed configurations, creating side-by-side comparison images.

**Run:** `python parity_agent/save_annotated_images.py`

**Output:**
- `results/snapshots/baseline_images/` — Each image with red (broken) and blue (online/GT) boxes
- `results/snapshots/final_images/` — Each image with green (fixed) and blue (online/GT) boxes

**Portability:** This script reads the baseline config from `baseline_snapshot.json` (not hardcoded). If someone else runs it on a different project, it uses *their* baseline config automatically.

---

### `dashboard/app.py` — Streamlit Dashboard

**What it does:** Interactive 5-tab dashboard for exploring the agent's analysis.

**Run:** `streamlit run parity_agent/dashboard/app.py`

**Tabs:**
1. **📊 Overview** — Aggregate metrics, convergence status, detection count summary
2. **🖼️ Trace Viewer** — Select any image → see online/offline box comparison + Before/After view
3. **📈 Metrics** — Per-image metric heatmap, averages bar chart
4. **🧪 Ablation Explorer** — Interactive exploration of ablation experiments
5. **📄 Paper Overview (BMVC)** — Dynamic tables, figures, and IoU metrics for the proposal

---

## For New Users: Running the Agent on Your Own Project

Everything in the Parity Agent is designed to be **fully portable**. No values are hardcoded to any specific project, model, or dataset.

### Step-by-Step Guide

```bash
# 1. Clone the repo
git clone https://github.com/azamazher/YieldMate.git
cd YieldMate

# 2. Install Python dependencies
pip install -r parity_agent/requirements-agent.txt

# 3. Place your model and labels in /assets/
#    - assets/model.tflite     (your exported TFLite model)
#    - assets/labels.txt       (one class name per line)

# 4. Update config.yaml with your class names and model settings
#    Edit: parity_agent/config.yaml
#    Change: model.class_names, model.num_classes, model.input_size

# 5. Add test images
mkdir test_images
# Copy 10-20 images that your model should detect into this folder

# 6. Run the agent (this does EVERYTHING automatically)
python parity_agent/run_agent.py --mode graph --images test_images/
# → Captures baseline snapshot, diagnoses drift, fixes config, captures final snapshot

# 7. Generate analysis outputs
python parity_agent/bmvc_figures.py          # 5 publication figures
python parity_agent/save_annotated_images.py # Before/after image comparisons
streamlit run parity_agent/dashboard/app.py  # Interactive dashboard
```

### What Happens Automatically

When you run the agent (step 6):

1. **Baseline snapshot** is saved at iteration 0 with your project's broken state
2. The agent diagnoses and fixes the drift
3. **Final snapshot** is saved at convergence with the fixed state
4. All metrics (precision, recall, F1, mAP) are computed automatically

When you generate outputs (step 7):

1. Figures read from `baseline_snapshot.json` and `final_snapshot.json`
2. Annotated images read the broken config from the baseline snapshot (not hardcoded)
3. The dashboard displays everything dynamically

**You never need to edit any Python files.** Just update `config.yaml` with your model's details.

### Note: `simulate_baseline.py`

This script is a **one-off utility** specific to our original development process. It was needed because we developed the snapshot system *after* the agent had already fixed the config. For new users, the baseline is captured automatically during the agent run — **you do not need this script**.

---

## Architecture Diagram

```
                                    ┌─────────────────┐
                                    │   CONFIG.YAML   │
                                    │  (paths, model,  │
                                    │   thresholds)    │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
              ┌─────▼──────┐          ┌──────▼──────┐         ┌──────▼──────┐
              │   ONLINE   │          │   OFFLINE   │         │  SNAPSHOTS  │
              │   TRACER   │          │   TRACER    │         │   (v0.2)    │
              │ (PyTorch)  │          │  (TFLite)   │         │  baseline   │
              └─────┬──────┘          └──────┬──────┘         │  + final    │
                    │                        │                └──────┬──────┘
                    └────────┬───────────────┘                       │
                             │                                       │
                    ┌────────▼────────┐                              │
                    │  GOLDEN TRACES  │                              │
                    │ (per image pair)│                              │
                    └────────┬────────┘                              │
                             │                                       │
                    ┌────────▼────────┐                              │
                    │   PARITY LOSS   │                              │
                    │  (5 metrics)    │                              │
                    └────────┬────────┘                              │
                             │                                       │
                    ┌────────▼────────┐              ┌───────────────▼───────┐
                    │  AGENT GRAPH    │              │    ANALYSIS (v0.2)    │
                    │  (LangGraph)    │              │  bmvc_figures.py      │
                    │  Profile →      │              │  parity_metrics.py    │
                    │  Hypothesise →  │              │  save_annotated.py    │
                    │  Ablate →       │              │  dashboard/app.py     │
                    │  Align          │              └───────────────────────┘
                    └─────────────────┘
```
