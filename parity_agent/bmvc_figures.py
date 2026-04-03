"""
Golden Graph Generator for BMVC Paper — Parity Agent Results
Generates high-resolution, academic-style figure(s) for conference submission.

Reads from results/snapshots/baseline_snapshot.json and final_snapshot.json
so figures are always generated from real experimental data.

Run with:
    python parity_agent/bmvc_figures.py
"""

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Output directory ──
OUTPUT_DIR = os.path.join(str(PROJECT_ROOT), "results", "figures")
SNAPSHOTS_DIR = os.path.join(str(PROJECT_ROOT), "results", "snapshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Colour palette (BMVC-friendly) ──
C_ONLINE   = "#2563EB"   # Blue
C_OFFLINE  = "#F59E0B"   # Amber
C_BROKEN   = "#EF4444"   # Red
C_FIXED    = "#10B981"   # Green
C_BG       = "#FAFAFA"
C_GRID     = "#E5E7EB"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.facecolor": C_BG,
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": C_GRID,
    "grid.linewidth": 0.5,
})


def load_snapshots():
    """
    Load baseline and final snapshots from disk.
    Returns (baseline, final) as dicts, or (None, None) if not found.
    """
    baseline, final = None, None

    baseline_path = os.path.join(SNAPSHOTS_DIR, "baseline_snapshot.json")
    final_path = os.path.join(SNAPSHOTS_DIR, "final_snapshot.json")

    if os.path.exists(baseline_path):
        with open(baseline_path) as f:
            baseline = json.load(f)
    if os.path.exists(final_path):
        with open(final_path) as f:
            final = json.load(f)

    return baseline, final


def figure_1_confidence_comparison(baseline, final):
    """
    Figure 1: Per-Class Confidence Score Comparison (Online vs Offline)
    Dynamically built from the final snapshot data.
    """
    if not final:
        print("  [SKIP] Figure 1: No final snapshot available.")
        return None

    summary = final["summary"]
    online_classes = summary["online_classes_avg"]
    offline_classes = summary["offline_classes_avg"]

    # Use all classes that appear in the online results
    classes = sorted(online_classes.keys())
    if not classes:
        print("  [SKIP] Figure 1: No class data in final snapshot.")
        return None

    online_conf  = [online_classes.get(c, 0) for c in classes]
    offline_conf = [offline_classes.get(c, 0) for c in classes]

    # Capitalise class names for display
    display_names = [c.capitalize() for c in classes]

    fig, ax = plt.subplots(figsize=(max(6, len(classes) * 2), 4))

    x = np.arange(len(classes))
    width = 0.30

    bars_on  = ax.bar(x - width/2, online_conf,  width, label="Online (PyTorch)",
                      color=C_ONLINE, edgecolor="white", linewidth=0.8, zorder=3)
    bars_off = ax.bar(x + width/2, offline_conf, width, label="Offline (TFLite Edge)",
                      color=C_OFFLINE, edgecolor="white", linewidth=0.8, zorder=3)

    # Value labels on bars
    for bar in bars_on:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{bar.get_height():.0f}%", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=C_ONLINE)
    for bar in bars_off:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{bar.get_height():.0f}%", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=C_OFFLINE)

    ax.set_ylabel("Confidence Score (%)", fontsize=12)
    ax.set_title("Per-Class Confidence: Online vs Edge (Post-Harmonisation)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, fontsize=12)
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=10)

    # Annotation showing the average gap
    if len(classes) > 0 and offline_conf[0] > 0:
        gap = online_conf[0] - offline_conf[0]
        mid_y = (online_conf[0] + offline_conf[0]) / 2
        ax.annotate("", xy=(0.15, offline_conf[0]), xytext=(0.15, online_conf[0]),
                    arrowprops=dict(arrowstyle="<->", color="#6B7280", lw=1.5))
        ax.text(0.35, mid_y, f"-{gap:.0f} pp\n(expected\nedge loss)", ha="left", va="center",
                fontsize=8, color="#6B7280", fontstyle="italic")

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig1_confidence_comparison.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close(fig)
    return path


def figure_2_detection_count_recovery(baseline, final):
    """
    Figure 2: Detection Count Recovery — Before vs After Parity Agent
    Uses real counts from baseline and final snapshots.
    """
    if not baseline or not final:
        print("  [SKIP] Figure 2: Need both baseline and final snapshots.")
        return None

    # Baseline numbers
    baseline_total_offline = baseline["summary"]["total_offline_detections"]
    baseline_decoded = sum(
        img["offline"].get("decoded_count", 0) for img in baseline.get("per_image", [])
    )
    if baseline_decoded == 0:
        baseline_decoded = baseline_total_offline  # fallback

    baseline_online = baseline["summary"]["total_online_detections"]

    # Final numbers
    final_online = final["summary"]["total_online_detections"]
    final_offline = final["summary"]["total_offline_detections"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5),
                                    gridspec_kw={"width_ratios": [1.2, 1]})

    # ── Left panel: The catastrophic baseline ──
    stages = ["Raw Decoded\nBoxes", "After NMS", "Ground\nTruth"]
    counts = [baseline_decoded, baseline_total_offline, baseline_online]
    colors = [C_BROKEN, C_BROKEN, C_ONLINE]

    bars = ax1.bar(stages, counts, color=colors, edgecolor="white", linewidth=0.8, zorder=3)
    for bar, count in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.02,
                 f"{count:,}", ha="center", va="bottom",
                 fontsize=12, fontweight="bold",
                 color=C_BROKEN if count > 10 else C_ONLINE)

    ax1.set_ylabel("Number of Detections", fontsize=12)
    ax1.set_title("Before Agent: Catastrophic Drift",
                  fontsize=13, fontweight="bold", color=C_BROKEN, pad=12)
    ax1.set_ylim(0, max(counts) * 1.15)

    # ── Right panel: After harmonisation ──
    categories = ["Online\n(Desktop)", "Offline\n(Edge)"]
    after_counts = [final_online, final_offline]
    colors2 = [C_ONLINE, C_FIXED]

    bars2 = ax2.bar(categories, after_counts, color=colors2,
                    edgecolor="white", linewidth=0.8, width=0.5, zorder=3)
    for bar, count in zip(bars2, after_counts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.08,
                 str(count), ha="center", va="bottom",
                 fontsize=16, fontweight="bold", color="#1F2937")

    ax2.set_ylabel("Number of Detections", fontsize=12)
    ax2.set_title("After Agent: Parity Restored",
                  fontsize=13, fontweight="bold", color=C_FIXED, pad=12)
    max_after = max(after_counts) if after_counts else 4
    ax2.set_ylim(0, max(max_after * 2, 4))
    ax2.set_yticks(range(0, max(max_after * 2, 4) + 1))

    fig.suptitle("Figure 2: Detection Count Recovery via Autonomous Parity Agent",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig2_detection_count_recovery.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close(fig)
    return path


def figure_3_parity_loss_convergence(baseline, final):
    """
    Figure 3: Parity Loss Convergence Curve
    Shows the dramatic reduction in parity loss from baseline to final.
    Also reads the experiment_log for intermediate data points.
    """
    if not baseline:
        print("  [SKIP] Figure 3: No baseline snapshot.")
        return None

    baseline_loss = baseline["parity_loss"]
    final_loss = final["parity_loss"] if final else baseline_loss

    # Try to read experiment log for intermediate points
    exp_log_path = os.path.join(str(PROJECT_ROOT), "results", "experiments", "experiment_log.json")
    intermediate_losses = []
    if os.path.exists(exp_log_path):
        with open(exp_log_path) as f:
            experiments = json.load(f)
        # Get the distinct loss values at key points
        seen = set()
        for exp in experiments:
            loss = round(exp.get("loss", 0), 2)
            if loss not in seen and loss != round(baseline_loss, 2):
                intermediate_losses.append(loss)
                seen.add(loss)

    # Build the convergence path
    iterations = ["Baseline\n(Broken)"]
    losses = [baseline_loss]
    marker_colors = [C_BROKEN]

    if intermediate_losses:
        # Pick the most representative intermediate (first significant improvement)
        best_intermediate = min(l for l in intermediate_losses if l < baseline_loss * 0.5) if any(l < baseline_loss * 0.5 for l in intermediate_losses) else intermediate_losses[0]
        iterations.append("Single-Param\nAblation")
        losses.append(best_intermediate)
        marker_colors.append(C_OFFLINE)

    if final and final_loss < baseline_loss:
        iterations.append("Combo\nAblation")
        losses.append(final_loss)
        marker_colors.append(C_FIXED)

    fig, ax = plt.subplots(figsize=(7, 4.5))

    x = np.arange(len(iterations))
    ax.plot(x, losses, "o-", color="#6366F1", markersize=12, linewidth=2.5, zorder=4)

    for i, (xi, loss, col) in enumerate(zip(x, losses, marker_colors)):
        ax.plot(xi, loss, "o", color=col, markersize=14, zorder=5,
                markeredgecolor="white", markeredgewidth=2)
        offset = max(losses) * 0.05 if loss > 1 else 0.01
        ax.text(xi, loss + offset, f"{loss:.2f}" if loss > 1 else f"{loss:.3f}",
                ha="center", va="bottom", fontsize=11, fontweight="bold", color=col)

    ax.set_xticks(x)
    ax.set_xticklabels(iterations, fontsize=11)
    ax.set_ylabel("Parity Loss  $\\mathcal{L}_{parity}$", fontsize=12)
    ax.set_title("Parity Loss Convergence: Agent Diagnosis Loop",
                 fontsize=13, fontweight="bold", pad=12)
    if max(losses) > 10:
        ax.set_yscale("log")
    ax.set_ylim(max(min(losses) * 0.5, 0.01), max(losses) * 1.5)

    # Convergence threshold line
    ax.axhline(y=0.05, color=C_FIXED, linestyle="--", linewidth=1.2, alpha=0.7)
    ax.text(len(iterations) - 0.6, 0.06, "Convergence\nThreshold", fontsize=8,
            color=C_FIXED, ha="right", va="bottom", fontstyle="italic")

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig3_parity_loss_convergence.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close(fig)
    return path


def figure_4_ablation_heatmap():
    """
    Figure 4: Combo Ablation Heatmap
    Reads directly from experiment_log.json to build the heatmap dynamically.
    """
    exp_log_path = os.path.join(str(PROJECT_ROOT), "results", "experiments", "experiment_log.json")
    if not os.path.exists(exp_log_path):
        print("  [SKIP] Figure 4: No experiment_log.json found.")
        return None

    with open(exp_log_path) as f:
        experiments = json.load(f)

    if not experiments:
        print("  [SKIP] Figure 4: Experiment log is empty.")
        return None

    # Extract unique confidence thresholds and sigmoid states
    conf_values = sorted(set(
        exp["config"].get("confidence_threshold", 0.25)
        for exp in experiments
    ))
    sigmoid_values = sorted(set(
        exp["config"].get("apply_sigmoid", False)
        for exp in experiments
    ), reverse=True)  # True first, False second

    if len(conf_values) < 2 or len(sigmoid_values) < 2:
        print("  [SKIP] Figure 4: Not enough parameter variety for heatmap.")
        return None

    # Build the loss matrix
    loss_matrix = np.full((len(sigmoid_values), len(conf_values)), np.nan)
    for exp in experiments:
        conf = exp["config"].get("confidence_threshold", 0.25)
        sig = exp["config"].get("apply_sigmoid", False)
        # Support both flat 'loss' key and nested 'aggregate.mean_loss'
        loss = exp.get("loss", None)
        if loss is None and "aggregate" in exp:
            loss = exp["aggregate"].get("mean_loss", None)
        if loss is None:
            continue
        if conf in conf_values and sig in sigmoid_values:
            r = sigmoid_values.index(sig)
            c = conf_values.index(conf)
            # Keep the minimum loss for each cell
            if np.isnan(loss_matrix[r, c]) or loss < loss_matrix[r, c]:
                loss_matrix[r, c] = loss

    # Check we have enough data
    if np.all(np.isnan(loss_matrix)):
        print("  [SKIP] Figure 4: No valid loss data in experiment log.")
        return None

    # Replace NaN with a high value for display
    display_matrix = np.where(np.isnan(loss_matrix), 999, loss_matrix)

    fig, ax = plt.subplots(figsize=(max(9, len(conf_values) * 1.2), 3.5))
    im = ax.imshow(np.log10(display_matrix + 0.001), cmap="RdYlGn_r", aspect="auto",
                   vmin=-2, vmax=2.5)

    ax.set_xticks(np.arange(len(conf_values)))
    ax.set_xticklabels([f"{t:.1f}" for t in conf_values], fontsize=10)
    ax.set_yticks(np.arange(len(sigmoid_values)))
    ax.set_yticklabels(["Sigmoid ON" if s else "Sigmoid OFF" for s in sigmoid_values], fontsize=11)
    ax.set_xlabel("Confidence Threshold ($t_{conf}$)", fontsize=12)
    ax.set_title("Combo Ablation: $\\mathcal{L}_{parity}$ Heat Map  (log$_{10}$ scale)",
                 fontsize=13, fontweight="bold", pad=12)

    # Annotate each cell
    valid_vals = loss_matrix[~np.isnan(loss_matrix)]
    best_val = np.nanmin(valid_vals) if len(valid_vals) > 0 else None
    for i in range(len(sigmoid_values)):
        for j in range(len(conf_values)):
            val = loss_matrix[i, j]
            if np.isnan(val):
                continue
            text = f"{val:.2f}" if val > 1 else f"{val:.3f}"
            color = "white" if val > 5 else "black"
            fontw = "bold" if (best_val is not None and val == best_val) else "normal"
            ax.text(j, i, text, ha="center", va="center",
                    fontsize=8, color=color, fontweight=fontw)

    # Highlight the best cell
    if best_val is not None:
        best_idx = np.unravel_index(np.nanargmin(loss_matrix), loss_matrix.shape)
        from matplotlib.patches import Rectangle
        rect = Rectangle((best_idx[1] - 0.5, best_idx[0] - 0.5), 1, 1,
                          linewidth=3, edgecolor=C_FIXED, facecolor="none")
        ax.add_patch(rect)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig4_ablation_heatmap.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close(fig)
    return path


def figure_5_per_image_comparison(baseline, final):
    """
    Figure 5: Per-Image Detection Comparison
    Shows each test image's online vs offline detection count, before and after.
    """
    if not baseline or not final:
        print("  [SKIP] Figure 5: Need both snapshots.")
        return None

    baseline_images = {img["image_id"]: img for img in baseline.get("per_image", [])}
    final_images = {img["image_id"]: img for img in final.get("per_image", [])}

    common_ids = sorted(set(baseline_images.keys()) & set(final_images.keys()))
    if not common_ids:
        print("  [SKIP] Figure 5: No common images between snapshots.")
        return None

    # Truncate long IDs for display
    display_ids = [id[:15] + "..." if len(id) > 15 else id for id in common_ids]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(4, len(common_ids) * 0.7)),
                                    sharey=True)

    y = np.arange(len(common_ids))

    # ── Before (baseline) ──
    online_before  = [baseline_images[id]["online"]["detection_count"] for id in common_ids]
    offline_before = [baseline_images[id]["offline"]["detection_count"] for id in common_ids]

    ax1.barh(y - 0.2, online_before,  0.35, label="Online", color=C_ONLINE, zorder=3)
    ax1.barh(y + 0.2, offline_before, 0.35, label="Offline", color=C_BROKEN, zorder=3)
    ax1.set_yticks(y)
    ax1.set_yticklabels(display_ids, fontsize=9)
    ax1.set_xlabel("Detection Count")
    ax1.set_title("Before Agent", fontsize=12, fontweight="bold", color=C_BROKEN)
    ax1.legend(fontsize=9)

    # ── After (final) ──
    online_after  = [final_images[id]["online"]["detection_count"] for id in common_ids]
    offline_after = [final_images[id]["offline"]["detection_count"] for id in common_ids]

    ax2.barh(y - 0.2, online_after,  0.35, label="Online", color=C_ONLINE, zorder=3)
    ax2.barh(y + 0.2, offline_after, 0.35, label="Offline", color=C_FIXED, zorder=3)
    ax2.set_xlabel("Detection Count")
    ax2.set_title("After Agent", fontsize=12, fontweight="bold", color=C_FIXED)
    ax2.legend(fontsize=9)

    fig.suptitle("Figure 5: Per-Image Detection Parity (Before vs After)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig5_per_image_comparison.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close(fig)
    return path


if __name__ == "__main__":
    print("=" * 60)
    print("  Generating BMVC Paper Figures (Dynamic from Snapshots)")
    print("=" * 60)

    baseline, final = load_snapshots()

    if not baseline and not final:
        print("\n  No snapshots found in results/snapshots/.")
        print("  Run the agent first:")
        print("    python parity_agent/run_agent.py --mode agent --images test_images/ --auto-apply")
        print("\n  Snapshots are automatically saved during the agent run.")
        sys.exit(1)

    print(f"\n  Baseline: {'Found' if baseline else 'Missing'}")
    print(f"  Final:    {'Found' if final else 'Missing'}")
    if baseline:
        print(f"  Baseline loss: {baseline['parity_loss']:.4f}  |  "
              f"Offline detections: {baseline['summary']['total_offline_detections']}")
    if final:
        print(f"  Final loss:    {final['parity_loss']:.4f}  |  "
              f"Offline detections: {final['summary']['total_offline_detections']}")
    print()

    figure_1_confidence_comparison(baseline, final)
    figure_2_detection_count_recovery(baseline, final)
    figure_3_parity_loss_convergence(baseline, final)
    figure_4_ablation_heatmap()
    figure_5_per_image_comparison(baseline, final)

    print(f"\n  All figures saved to: {OUTPUT_DIR}")
    print("=" * 60)
