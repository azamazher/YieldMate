"""
Streamlit Dashboard — Visual interface for the Parity Agent.

Run with:
    streamlit run parity_agent/dashboard/app.py

Shows:
- Trace viewer (4 checkpoints per image)
- Metrics charts (5 divergence metrics)
- Ablation explorer (parameter sweep curves)
- Agent runner (live progress)
"""

import os
import sys
import json
import numpy as np
import streamlit as st
from pathlib import Path
from PIL import Image

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parity_agent.run_agent import load_config
from parity_agent.trace.storage import TraceStorage
from parity_agent.diff.parity_loss import ParityLoss
from parity_agent.diff.metrics import compute_all_metrics
from parity_agent.diff.visual_report import draw_detections


# ──────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Parity Agent Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        border: 1px solid #0f3460;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #e94560;
    }
    .metric-label {
        color: #a0a0a0;
        font-size: 0.9rem;
    }
    .status-pass { color: #4CAF50; font-weight: bold; }
    .status-fail { color: #f44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load config, traces, and results."""
    config = load_config()
    traces_dir = PROJECT_ROOT / config["paths"]["traces_dir"]
    results_dir = PROJECT_ROOT / config["paths"]["results_dir"]

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

    # Compute metrics
    batch_result = parity_loss.compute_batch(golden_traces) if golden_traces else None

    # Load alignment history
    history_path = results_dir / "alignment_history.json"
    alignment_history = []
    if history_path.exists():
        with open(history_path) as f:
            alignment_history = json.load(f)

    # Load experiment log
    exp_path = results_dir / "experiments" / "experiment_log.json"
    experiment_log = []
    if exp_path.exists():
        with open(exp_path) as f:
            experiment_log = json.load(f)

    return config, golden_traces, batch_result, alignment_history, experiment_log


def main():
    st.title("🔬 Parity Agent Dashboard")
    st.caption("Autonomous Cross-Platform ML Parity Agent v0.2")

    try:
        config, golden_traces, batch_result, alignment_history, experiment_log = load_data()
    except Exception as e:
        st.error(f"Could not load data: {e}")
        st.info("Run `python parity_agent/run_agent.py --mode trace --images test_images/` first.")
        return

    if not golden_traces or not batch_result:
        st.warning("No traces found. Run the agent first.")
        return

    # ──────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Page", [
            "📊 Overview",
            "🖼️ Trace Viewer",
            "📈 Metrics",
            "🧪 Ablation Explorer",
            "📜 Alignment History",
            "📄 Paper Overview (BMVC)",
        ], label_visibility="collapsed")

    # ──────────────────────────────────────────────────────
    # OVERVIEW PAGE
    # ──────────────────────────────────────────────────────
    if page == "📊 Overview":
        agg = batch_result["aggregate"]
        threshold = config["parity_loss"]["threshold"]
        passed = agg["mean_loss"] < threshold

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mean Parity Loss", f"{agg['mean_loss']:.4f}",
                     delta=f"{'✅ PASS' if passed else '❌ FAIL'}")
        col2.metric("Images", agg["num_images"])
        col3.metric("Threshold", threshold)
        col4.metric("Changes Applied", len(alignment_history))

        st.divider()

        # Per-image loss chart
        st.subheader("Per-Image Parity Loss")
        image_ids = [r["image_id"][:20] for r in batch_result["per_image"]]
        losses = [r["total_loss"] for r in batch_result["per_image"]]

        chart_data = {"Image": image_ids, "Parity Loss": losses}
        st.bar_chart(chart_data, x="Image", y="Parity Loss", color="#e94560")

        # Detection count comparison
        st.subheader("Detection Count: Online vs Offline")
        online_counts = []
        offline_counts = []
        names = []
        for gt in golden_traces:
            names.append(gt.image_id[:20])
            online_counts.append(len(gt.online.nms_boxes))
            offline_counts.append(len(gt.offline.nms_boxes))

        count_data = {"Image": names, "Online": online_counts, "Offline": offline_counts}
        st.bar_chart(count_data, x="Image", y=["Online", "Offline"])

    # ──────────────────────────────────────────────────────
    # TRACE VIEWER
    # ──────────────────────────────────────────────────────
    elif page == "🖼️ Trace Viewer":
        st.subheader("4-Checkpoint Trace Viewer")

        image_options = [gt.image_id for gt in golden_traces]
        selected = st.selectbox("Select Image", image_options)

        gt = next(g for g in golden_traces if g.image_id == selected)

        # Load original image
        image_path = gt.online.metadata.get("image_path", "")
        if image_path and os.path.exists(image_path):
            original = Image.open(image_path).convert("RGB")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Online Pipeline**")
                online_img = draw_detections(original, gt.online.nms_boxes,
                                              title=f"ONLINE ({len(gt.online.nms_boxes)} det)")
                st.image(online_img, use_container_width=True)

            with col2:
                st.markdown("**Offline Pipeline**")
                offline_img = draw_detections(original, gt.offline.nms_boxes,
                                               title=f"OFFLINE ({len(gt.offline.nms_boxes)} det)")
                st.image(offline_img, use_container_width=True)

        # Checkpoint details
        st.divider()
        st.subheader("Checkpoint Data")

        for label, trace in [("Online", gt.online), ("Offline", gt.offline)]:
            with st.expander(f"{label} — {trace.pipeline}"):
                st.write(f"**Input tensor shape:** {trace.input_tensor.shape if trace.input_tensor is not None else 'N/A'}")
                st.write(f"**Raw output shape:** {trace.raw_output.shape if trace.raw_output is not None else 'N/A'}")
                st.write(f"**Decoded boxes:** {len(trace.decoded_boxes)}")
                st.write(f"**NMS boxes:** {len(trace.nms_boxes)}")
                if trace.nms_boxes:
                    for det in trace.nms_boxes:
                        st.write(f"  • {det.class_name}: {det.confidence:.4f} | bbox: {[f'{x:.3f}' for x in det.bbox]}")

        # ── Before vs After Agent Comparison ──
        st.divider()
        st.subheader("🔍 Before vs After Agent (Detection Box Comparison)")
        st.caption(
            "**Left panel:** Online (PyTorch) ground truth (blue) vs Offline (TFLite) detections. "
            "**Before:** Broken config produces ~1,200 red boxes. **After:** Fixed config produces 2-4 clean green boxes."
        )

        results_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "results"
        baseline_img_dir = results_dir / "snapshots" / "baseline_images"
        final_img_dir = results_dir / "snapshots" / "final_images"

        # Match image file by image_id
        safe_selected = selected.replace(" ", "_").replace("/", "_")

        baseline_path = baseline_img_dir / f"{safe_selected}.jpg"
        final_path = final_img_dir / f"{safe_selected}.jpg"

        if baseline_path.exists() or final_path.exists():
            tab_before, tab_after, tab_both = st.tabs([
                "❌ Before Agent (Broken)", "✅ After Agent (Fixed)", "↔️ Side-by-Side"
            ])

            with tab_before:
                if baseline_path.exists():
                    st.image(str(baseline_path), caption=f"BEFORE: {selected} — Broken config (sigmoid=ON, conf=0.25)", use_container_width=True)
                    st.error("⚠️ Notice the massive flood of red bounding boxes — the offline pipeline "
                             "detects ~1,200 false objects per image because double-sigmoid inflates all confidence scores above threshold.")
                else:
                    st.info("Baseline image not found. Run: `python parity_agent/save_annotated_images.py`")

            with tab_after:
                if final_path.exists():
                    st.image(str(final_path), caption=f"AFTER: {selected} — Fixed config (sigmoid=OFF, conf=0.6)", use_container_width=True)
                    st.success("✅ After the Parity Agent's fix, the offline pipeline produces clean, "
                               "accurate detections matching the online ground truth.")
                else:
                    st.info("Final image not found. Run: `python parity_agent/save_annotated_images.py`")

            with tab_both:
                if baseline_path.exists() and final_path.exists():
                    col_b, col_a = st.columns(2)
                    with col_b:
                        st.markdown("**❌ BEFORE** (broken config)")
                        st.image(str(baseline_path), use_container_width=True)
                    with col_a:
                        st.markdown("**✅ AFTER** (agent-fixed config)")
                        st.image(str(final_path), use_container_width=True)
                else:
                    st.info("Both images needed for side-by-side. Run: `python parity_agent/save_annotated_images.py`")
        else:
            st.info("📸 No annotated images found. Generate them with:\n\n"
                    "```bash\npython parity_agent/save_annotated_images.py\n```")

    # ──────────────────────────────────────────────────────
    # METRICS PAGE
    # ──────────────────────────────────────────────────────
    elif page == "📈 Metrics":
        st.subheader("Divergence Metrics")

        metric_names = ["tensor_l2", "logits_diff", "iou_mismatch", "count_diff", "confidence_kl"]

        # Heatmap-style table
        st.markdown("#### Metric Values Per Image")
        rows = []
        for r in batch_result["per_image"]:
            row = {"Image": r["image_id"][:20]}
            for m in metric_names:
                row[m] = r["metrics"].get(m, 0)
            row["Total Loss"] = r["total_loss"]
            rows.append(row)

        st.dataframe(rows, use_container_width=True)

        # Averages
        st.divider()
        st.markdown("#### Metric Averages")
        avg_data = {"Metric": metric_names}
        avg_values = []
        for m in metric_names:
            vals = [r["metrics"].get(m, 0) for r in batch_result["per_image"]]
            avg_values.append(sum(vals) / len(vals) if vals else 0)
        avg_data["Average"] = avg_values
        st.bar_chart(avg_data, x="Metric", y="Average", color="#33b5e5")

    # ──────────────────────────────────────────────────────
    # ABLATION EXPLORER
    # ──────────────────────────────────────────────────────
    elif page == "🧪 Ablation Explorer":
        st.subheader("Ablation Experiment Results")

        if not experiment_log:
            st.warning("No experiments found. Run the agent first.")
        else:
            st.write(f"Total experiments: {len(experiment_log)}")

            # Group experiments by parameter name
            # Format: "ablation_{param}_{value}" or "baseline_{param}"
            by_param = {}
            for exp in experiment_log:
                name = exp.get("experiment_name", "")
                config_dict = exp.get("config", {})
                loss = exp.get("aggregate", {}).get("mean_loss", None)
                if loss is None:
                    continue

                if name.startswith("baseline_"):
                    param = name.replace("baseline_", "")
                    by_param.setdefault(param, []).append({
                        "value": config_dict.get(param, "baseline"),
                        "loss": loss,
                        "label": "baseline",
                    })
                elif name.startswith("ablation_"):
                    # Extract param: everything between "ablation_" and the last "_value"
                    rest = name[len("ablation_"):]
                    # Find which config key this matches
                    matched_param = None
                    for key in config_dict:
                        if rest.startswith(key + "_") or rest.startswith(key):
                            matched_param = key
                            break
                    if matched_param:
                        val = config_dict.get(matched_param, "?")
                        by_param.setdefault(matched_param, []).append({
                            "value": val,
                            "loss": loss,
                            "label": str(val),
                        })

            if not by_param:
                st.info("No ablation sweep data found in experiment log.")
            else:
                for param, exps in by_param.items():
                    with st.expander(f"📊 {param} ({len(exps)} experiments)", expanded=True):
                        # Sort by value for numeric params
                        try:
                            exps_sorted = sorted(exps, key=lambda x: float(x["value"]))
                        except (ValueError, TypeError):
                            exps_sorted = exps

                        values = [str(e["value"]) for e in exps_sorted]
                        losses = [e["loss"] for e in exps_sorted]

                        # Show as both chart and table
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            chart_data = {"Parameter Value": values, "Parity Loss": losses}
                            st.bar_chart(chart_data, x="Parameter Value", y="Parity Loss",
                                         color="#e94560")
                        with col2:
                            best_idx = losses.index(min(losses))
                            st.metric("Best Value", values[best_idx])
                            st.metric("Best Loss", f"{losses[best_idx]:.4f}")
                            st.metric("Worst Loss", f"{max(losses):.4f}")

                        # Data table
                        table_rows = [{"Value": v, "Loss": f"{l:.6f}"} for v, l in zip(values, losses)]
                        st.dataframe(table_rows, use_container_width=True)

    # ──────────────────────────────────────────────────────
    # ALIGNMENT HISTORY
    # ──────────────────────────────────────────────────────
    elif page == "📜 Alignment History":
        st.subheader("Parameter Changes Applied by Agent")

        if not alignment_history:
            st.info("No changes applied yet.")
        else:
            for i, change in enumerate(alignment_history, 1):
                param = change.get("parameter", "?")
                old = change.get("old_value", "?")
                new = change.get("new_value", "?")
                imp = change.get("improvement", 0)

                st.markdown(f"""
                **Step {i}: `{param}`**
                - Old value: `{old}`
                - New value: `{new}`
                - Loss improvement: **{imp:.4f}**
                """)

            total = sum(c.get("improvement", 0) for c in alignment_history)
            st.success(f"Total improvement: {total:.4f}")

    # ──────────────────────────────────────────────────────
    # BMVC PAPER OVERVIEW PAGE
    # ──────────────────────────────────────────────────────
    elif page == "📄 Paper Overview (BMVC)":
        st.header("📄 Paper Overview — BMVC Conference")
        st.markdown("Academic figures and tables generated from the Parity Agent's experimental data.")

        figures_dir = PROJECT_ROOT / "results" / "figures"

        if not figures_dir.exists() or not list(figures_dir.glob("*.png")):
            st.warning("No figures found. Run `python parity_agent/bmvc_figures.py` to generate them.")
            if st.button("🔄 Generate Figures Now"):
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "parity_agent" / "bmvc_figures.py")],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )
                st.code(result.stdout)
                if result.returncode == 0:
                    st.success("Figures generated! Refresh the page.")
                else:
                    st.error(result.stderr)
                st.rerun()
        else:
            # Load snapshots for dynamic tables
            from parity_agent.utils.snapshots import load_snapshot
            import pandas as pd

            results_dir = str(PROJECT_ROOT / config["paths"]["results_dir"])
            baseline_snap = load_snapshot(results_dir, "baseline")
            final_snap = load_snapshot(results_dir, "final")

            if baseline_snap:
                st.subheader("Table 2: Baseline Discrepancy (Before Agent)")
                bs = baseline_snap["summary"]
                rows = []
                rows.append({
                    "Metric": "Total Detections",
                    "Online (PyTorch)": str(bs["total_online_detections"]),
                    "Offline (TFLite Edge)": f"{bs['total_offline_detections']:,}",
                    "Δ Gap": f"+{bs['total_offline_detections'] - bs['total_online_detections']:,}",
                })
                rows.append({
                    "Metric": "Parity Loss",
                    "Online (PyTorch)": "—",
                    "Offline (TFLite Edge)": "—",
                    "Δ Gap": f"{baseline_snap['parity_loss']:.2f}",
                })
                # Per-class rows
                for cls, conf in sorted(bs["online_classes_avg"].items()):
                    off_conf = bs.get("offline_classes_avg", {}).get(cls, None)
                    rows.append({
                        "Metric": f"{cls.capitalize()} Confidence",
                        "Online (PyTorch)": f"{conf:.0f}%",
                        "Offline (TFLite Edge)": f"{off_conf:.0f}%" if off_conf else "N/A (raw logits)",
                        "Δ Gap": f"−{conf - off_conf:.0f} pp" if off_conf else "—",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No baseline snapshot. Run the agent to generate it.")

            if final_snap:
                st.subheader("Table 3: Post-Harmonisation Parity (After Agent)")
                fs = final_snap["summary"]
                rows2 = []
                rows2.append({
                    "Metric": "Total Detections",
                    "Online (PyTorch)": str(fs["total_online_detections"]),
                    "Offline (TFLite Edge)": str(fs["total_offline_detections"]),
                    "Δ Gap": str(abs(fs["total_offline_detections"] - fs["total_online_detections"])),
                })
                rows2.append({
                    "Metric": "Parity Loss",
                    "Online (PyTorch)": "—",
                    "Offline (TFLite Edge)": "—",
                    "Δ Gap": f"{final_snap['parity_loss']:.4f}",
                })
                match = "✓" if fs["total_online_detections"] == fs["total_offline_detections"] else "✗"
                rows2.append({
                    "Metric": "Detection Count Match",
                    "Online (PyTorch)": match,
                    "Offline (TFLite Edge)": match,
                    "Δ Gap": "Perfect" if match == "✓" else "Mismatch",
                })
                for cls, conf in sorted(fs["online_classes_avg"].items()):
                    off_conf = fs.get("offline_classes_avg", {}).get(cls, None)
                    rows2.append({
                        "Metric": f"{cls.capitalize()} Confidence",
                        "Online (PyTorch)": f"{conf:.0f}%",
                        "Offline (TFLite Edge)": f"{off_conf:.0f}%" if off_conf else "—",
                        "Δ Gap": f"−{conf - off_conf:.0f} pp" if off_conf else "—",
                    })
                st.dataframe(pd.DataFrame(rows2), use_container_width=True, hide_index=True)

                st.info("💡 Confidence gaps are expected from TFLite quantisation. "
                        "The critical metric is **detection count parity**.")
            else:
                st.warning("No final snapshot. Run the full agent pipeline to generate it.")

            # ── IoU-Based Detection Metrics ──
            st.divider()
            st.subheader("📊 IoU-Based Detection Metrics (Precision, Recall, F1, mAP)")

            metric_cols = ["Metric", "Before Agent", "After Agent", "Δ Change"]

            bm = baseline_snap.get("metrics", {}) if baseline_snap else {}
            fm = final_snap.get("metrics", {}) if final_snap else {}

            if bm and "precision" in bm and fm and "precision" in fm:
                st.markdown("**Table: Aggregate Cross-Platform Metrics**")
                metric_rows = [
                    {"Metric": "Precision", "Before Agent": f"{bm['precision']:.4f}",
                     "After Agent": f"{fm['precision']:.4f}",
                     "Δ Change": f"+{fm['precision'] - bm['precision']:.4f}"},
                    {"Metric": "Recall", "Before Agent": f"{bm['recall']:.4f}",
                     "After Agent": f"{fm['recall']:.4f}",
                     "Δ Change": f"{fm['recall'] - bm['recall']:+.4f}"},
                    {"Metric": "F1-Score", "Before Agent": f"{bm['f1']:.4f}",
                     "After Agent": f"{fm['f1']:.4f}",
                     "Δ Change": f"+{fm['f1'] - bm['f1']:.4f}"},
                    {"Metric": "mAP@0.5", "Before Agent": f"{bm['mAP_50']:.4f}",
                     "After Agent": f"{fm['mAP_50']:.4f}",
                     "Δ Change": f"{fm['mAP_50'] - bm['mAP_50']:+.4f}"},
                    {"Metric": "mAP@0.5:0.95", "Before Agent": f"{bm['mAP_50_95']:.4f}",
                     "After Agent": f"{fm['mAP_50_95']:.4f}",
                     "Δ Change": f"{fm['mAP_50_95'] - bm['mAP_50_95']:+.4f}"},
                    {"Metric": "TP / FP / FN", "Before Agent": f"{bm['total_tp']} / {bm['total_fp']:,} / {bm['total_fn']}",
                     "After Agent": f"{fm['total_tp']} / {fm['total_fp']} / {fm['total_fn']}",
                     "Δ Change": f"FP: -{bm['total_fp'] - fm['total_fp']:,}"},
                ]
                st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

                # Per-class comparison
                if "per_class" in bm and "per_class" in fm:
                    st.markdown("**Per-Class F1-Score Comparison:**")
                    all_classes = sorted(set(list(bm["per_class"].keys()) + list(fm["per_class"].keys())))
                    cls_rows = []
                    for cls in all_classes:
                        b_cls = bm["per_class"].get(cls, {})
                        f_cls = fm["per_class"].get(cls, {})
                        cls_rows.append({
                            "Class": cls.capitalize(),
                            "Before P": f"{b_cls.get('precision', 0):.4f}",
                            "Before R": f"{b_cls.get('recall', 0):.4f}",
                            "Before F1": f"{b_cls.get('f1', 0):.4f}",
                            "After P": f"{f_cls.get('precision', 0):.4f}",
                            "After R": f"{f_cls.get('recall', 0):.4f}",
                            "After F1": f"{f_cls.get('f1', 0):.4f}",
                        })
                    st.dataframe(pd.DataFrame(cls_rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No metrics in snapshots. Re-run the baseline/final simulation.")

            # ── Figures ──
            fig_files = {
                "Figure 1: Per-Class Confidence Comparison": "fig1_confidence_comparison.png",
                "Figure 2: Detection Count Recovery": "fig2_detection_count_recovery.png",
                "Figure 3: Parity Loss Convergence": "fig3_parity_loss_convergence.png",
                "Figure 4: Combo Ablation Heatmap": "fig4_ablation_heatmap.png",
                "Figure 5: Per-Image Detection Comparison": "fig5_per_image_comparison.png",
            }

            for title, filename in fig_files.items():
                path = figures_dir / filename
                if path.exists():
                    st.subheader(title)
                    st.image(str(path), use_container_width=True)

            st.divider()
            st.markdown("### Optimal Configuration Found by Agent")
            if final_snap:
                fc = final_snap.get("config", {})
                col1, col2, col3 = st.columns(3)
                col1.metric("apply_sigmoid", str(fc.get("apply_sigmoid", "—")))
                col2.metric("confidence_threshold", str(fc.get("confidence_threshold", "—")))
                loss_delta = ""
                if baseline_snap:
                    loss_delta = f"-{baseline_snap['parity_loss'] - final_snap['parity_loss']:.2f}"
                col3.metric("Parity Loss", f"{final_snap['parity_loss']:.4f}", loss_delta)

            st.markdown("---")
            st.caption("Figures saved to `results/figures/` — use for LaTeX/Word paper insertion.")


if __name__ == "__main__":
    main()
