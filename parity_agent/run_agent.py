#!/usr/bin/env python3
"""
Autonomous Cross-Platform ML Parity Agent — Main Entry Point

Usage:
    # Run full autonomous agent loop
    python parity_agent/run_agent.py --images test_images/

    # Run individual stages
    python parity_agent/run_agent.py --mode trace --images test_images/
    python parity_agent/run_agent.py --mode diff
    python parity_agent/run_agent.py --mode align --images test_images/
    python parity_agent/run_agent.py --mode agent --images test_images/

The agent operates on a frozen model. It does NOT touch weights or training.
It only adjusts deployment-level parameters to minimize cross-platform divergence.
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parity_agent.trace.schema import GoldenTrace
from parity_agent.trace.online_tracer import OnlineTracer
from parity_agent.trace.offline_tracer import OfflineTracer
from parity_agent.trace.storage import TraceStorage
from parity_agent.diff.parity_loss import ParityLoss
from parity_agent.diff.report import DiffReport
from parity_agent.alignment.experiment_runner import ExperimentRunner
from parity_agent.alignment.parameters import get_default_config
from parity_agent.agents.profiler import ProfilerAgent
from parity_agent.agents.hypothesis import HypothesisAgent
from parity_agent.agents.ablation import AblationAgent
from parity_agent.agents.alignment import AlignmentAgent
from parity_agent.agents.auto_apply import AutoApplyAgent
from parity_agent.utils.image_loader import get_test_images
from parity_agent.utils.colors import banner, success, error, info, highlight


def load_config(config_path: str = None) -> dict:
    """Load agent configuration from YAML."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_trace(config: dict, image_dir: str):
    """Phase 2: Generate Golden Traces for all test images."""
    print("\n" + banner("=" * 70))
    print(banner("  PHASE 2 — GOLDEN TRACE SYSTEM"))
    print(banner("=" * 70))

    model_path = os.path.join(PROJECT_ROOT, config["paths"]["model_tflite"])
    labels = config["model"]["class_names"]
    storage = TraceStorage(os.path.join(PROJECT_ROOT, config["paths"]["traces_dir"]))

    # Discover test images
    image_paths = get_test_images(image_dir)
    print(f"\nFound {len(image_paths)} test images in {image_dir}")

    if not image_paths:
        print(error("ERROR: No test images found. Add images to the test_images/ directory."))
        return

    # --- Online traces ---
    print("\n" + info("[Online Pipeline] Tracing with Ultralytics..."))
    online_tracer = OnlineTracer(
        model_path=model_path,
        labels=labels,
        conf_threshold=config["online"]["confidence_threshold"],
        iou_threshold=config["online"]["iou_threshold"],
    )
    online_traces = online_tracer.trace_batch(image_paths)
    for t in online_traces:
        storage.save_trace(t)
    print(success(f"  Saved {len(online_traces)} online traces"))

    # --- Offline traces ---
    print("\n" + info("[Offline Pipeline] Tracing with TFLite..."))
    offline_tracer = OfflineTracer(
        model_path=model_path,
        labels=labels,
        config=config["offline"],
    )
    offline_traces = offline_tracer.trace_batch(image_paths)
    for t in offline_traces:
        storage.save_trace(t)
    print(success(f"  Saved {len(offline_traces)} offline traces"))

    # --- Pair into Golden Traces ---
    online_by_id = {t.image_id: t for t in online_traces}
    for off_trace in offline_traces:
        on_trace = online_by_id.get(off_trace.image_id)
        if on_trace:
            golden = GoldenTrace(
                image_id=off_trace.image_id,
                image_path=off_trace.metadata.get("image_path", ""),
                online=on_trace,
                offline=off_trace,
            )
            storage.save_golden_trace(golden)

    print(success(f"\n✓ Golden Trace complete. Traces saved to {config['paths']['traces_dir']}"))


def run_diff(config: dict):
    """Phase 3: Compute diff metrics and generate report."""
    print("\n" + banner("=" * 70))
    print(banner("  PHASE 3 — DIFF ENGINE"))
    print(banner("=" * 70))

    storage = TraceStorage(os.path.join(PROJECT_ROOT, config["paths"]["traces_dir"]))
    weights = config["parity_loss"]["weights"]
    parity_loss = ParityLoss(weights=weights)
    report_gen = DiffReport(parity_loss)

    # Load all golden traces
    image_ids = storage.list_image_ids()
    print(f"\nFound {len(image_ids)} traced images")

    golden_traces = []
    for image_id in image_ids:
        gt = storage.load_golden_trace(image_id)
        if gt and gt.is_complete:
            golden_traces.append(gt)

    if not golden_traces:
        print(error("ERROR: No complete golden traces found. Run --mode trace first."))
        return

    # Generate report
    report = report_gen.generate(golden_traces)
    print(report["text"])

    # Save markdown report
    results_dir = Path(PROJECT_ROOT) / config["paths"]["results_dir"] / "diffs"
    results_dir.mkdir(parents=True, exist_ok=True)
    md_report = report_gen.to_markdown(golden_traces)
    md_path = results_dir / f"diff_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_path, "w") as f:
        f.write(md_report)
    print(success(f"\n✓ Diff report saved to {md_path}"))


def _preload_online_traces(config: dict, image_dir: str):
    """
    Pre-load online traces in the main thread BEFORE langgraph is imported.

    This is critical on macOS: TFLite/YOLO model loading must happen before
    langgraph's threading infrastructure is set up, otherwise a mutex lock
    crash occurs.
    """
    from parity_agent.trace.online_tracer import OnlineTracer
    from parity_agent.utils.image_loader import get_test_images

    model_path = os.path.join(PROJECT_ROOT, config["paths"]["model_tflite"])
    labels = config["model"]["class_names"]
    image_paths = get_test_images(image_dir)
    online_cfg = config.get("online", {})

    print("\n  [Pre-load] Loading YOLO model and generating online traces...")
    tracer = OnlineTracer(
        model_path, labels,
        conf_threshold=online_cfg.get("confidence_threshold", 0.25),
        iou_threshold=online_cfg.get("iou_threshold", 0.45),
    )
    traces = tracer.trace_batch(image_paths)
    print(f"  [Pre-load] Got {len(traces)} online traces ✓")
    return traces


def run_report(config: dict, image_dir: str):
    """Generate a visual parity report with side-by-side detection images."""
    print("\n" + "=" * 70)
    print("  VISUAL PARITY REPORT")
    print("=" * 70)

    # Check if traces exist; if not, generate them first
    from parity_agent.trace.storage import TraceStorage
    traces_dir = os.path.join(PROJECT_ROOT, config["paths"]["traces_dir"])
    storage = TraceStorage(traces_dir)
    image_ids = storage.list_image_ids()

    if not image_ids:
        print("\n  No saved traces found. Generating traces first...")
        run_trace(config, image_dir)
        # Reload
        image_ids = storage.list_image_ids()
        if not image_ids:
            print("  ERROR: Could not generate traces.")
            return

    from parity_agent.diff.visual_report import generate_visual_report
    report_path = generate_visual_report(
        config=config,
        project_root=str(PROJECT_ROOT),
    )
    if report_path:
        print(f"\n✓ Open the report: {report_path}")


def run_agent_loop(config: dict, image_dir: str, auto_apply: bool = False):
    """Phase 5: Full autonomous agent loop."""
    print("\n" + "=" * 70)
    print("  AUTONOMOUS PARITY AGENT")
    print("  The first autonomous agent for ML deployment parity")
    print("=" * 70)

    model_path = os.path.join(PROJECT_ROOT, config["paths"]["model_tflite"])
    labels = config["model"]["class_names"]
    weights = config["parity_loss"]["weights"]
    threshold = config["parity_loss"]["threshold"]
    max_iterations = config["agent"]["max_iterations"]
    patience = config["agent"]["patience"]

    # Initialize components
    parity_loss = ParityLoss(weights=weights)
    config_path = str(Path(__file__).parent / "config.yaml")
    experiment_runner = ExperimentRunner(
        model_path=model_path,
        labels=labels,
        parity_loss=parity_loss,
        results_dir=os.path.join(PROJECT_ROOT, config["paths"]["results_dir"], "experiments"),
    )
    profiler = ProfilerAgent()
    hypothesis_agent = HypothesisAgent()
    ablation_agent = AblationAgent(experiment_runner)
    alignment_agent = AlignmentAgent(
        config_path=config_path,
        results_dir=os.path.join(PROJECT_ROOT, config["paths"]["results_dir"]),
    )

    # Discover test images
    image_paths = get_test_images(image_dir)
    print(f"\nTest images: {len(image_paths)}")
    print(f"Threshold: {threshold}")
    print(f"Max iterations: {max_iterations}")
    print(f"Patience: {patience}")

    # Generate fixed online traces (reference — never changes)
    print("\n[Step 0] Generating online reference traces...")
    online_tracer = OnlineTracer(
        model_path=model_path,
        labels=labels,
        conf_threshold=config["online"]["confidence_threshold"],
        iou_threshold=config["online"]["iou_threshold"],
    )
    online_traces = online_tracer.trace_batch(image_paths)
    print(f"  Generated {len(online_traces)} reference traces")

    # Initialize offline config
    current_config = dict(config["offline"])
    best_loss = float("inf")
    no_improve_count = 0

    # ================================================================
    # THE AUTONOMOUS CONTROL LOOP
    # ================================================================
    for iteration in range(1, max_iterations + 1):
        print(f"\n{'─' * 60}")
        print(f"  ITERATION {iteration}/{max_iterations}")
        print(f"{'─' * 60}")

        # 1. Trace offline with current config
        print(f"\n  [1/5] Tracing offline pipeline...")
        offline_tracer = OfflineTracer(model_path, labels, current_config)
        offline_traces = offline_tracer.trace_batch(image_paths)

        # 2. Build golden traces
        golden_traces = []
        online_by_id = {t.image_id: t for t in online_traces}
        for off_trace in offline_traces:
            on_trace = online_by_id.get(off_trace.image_id)
            if on_trace:
                golden_traces.append(GoldenTrace(
                    image_id=off_trace.image_id,
                    image_path=off_trace.metadata.get("image_path", ""),
                    online=on_trace,
                    offline=off_trace,
                ))

        # 3. Compute parity loss
        batch_result = parity_loss.compute_batch(golden_traces)
        current_loss = batch_result["aggregate"]["mean_loss"]
        print(f"  [2/5] Current parity loss: {current_loss:.6f}")

        # Check convergence
        if current_loss < threshold:
            print(f"\n  ✓ CONVERGED! Parity loss {current_loss:.6f} < threshold {threshold}")
            break

        # 4. Profile → Hypothesize
        print(f"  [3/5] Profiling divergence...")
        profile = profiler.analyze(batch_result)
        print(f"        Dominant stage: {profile['dominant_stage']}")

        hypotheses = hypothesis_agent.generate(profile)
        print(f"  [4/5] Generated {len(hypotheses)} hypotheses")
        for h in hypotheses[:3]:
            print(f"        • {h['hypothesis']} ({h['priority']})")

        if not hypotheses:
            print("  No hypotheses generated. Stopping.")
            break

        # 5. Ablation → Alignment
        print(f"  [5/5] Running ablation experiments...")

        # Use a subset of images for ablation sweeps (faster)
        max_ablation = config.get("agent", {}).get("max_ablation_images", len(image_paths))
        ablation_images = image_paths[:max_ablation]
        ablation_online = [t for t in online_traces if any(
            Path(p).stem == t.image_id for p in ablation_images
        )]

        ablation_results = ablation_agent.test_hypotheses(
            hypotheses=hypotheses[:3],  # Test top 3 hypotheses
            current_config=current_config,
            image_paths=ablation_images,
            online_traces=ablation_online,
        )

        # Apply best change
        new_config = alignment_agent.apply_best(
            current_config, ablation_results
        )

        # Track improvement
        if ablation_results["best_overall"]:
            new_loss = ablation_results["best_overall"]["best_loss"]
            if new_loss < best_loss - 0.001:
                best_loss = new_loss
                no_improve_count = 0
            else:
                no_improve_count += 1
        else:
            no_improve_count += 1

        current_config = new_config

        # Check patience
        if no_improve_count >= patience:
            print(f"\n  Patience exhausted ({patience} iterations without improvement). Stopping.")
            break

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print("\n" + "=" * 70)
    print("  AGENT RUN COMPLETE")
    print("=" * 70)
    print(f"\n  Final parity loss: {best_loss:.6f}")
    print(f"\n  {alignment_agent.get_summary()}")

    # Save results
    alignment_agent.save_history()
    alignment_agent.save_config(current_config)
    experiment_runner.save_log()
    print(f"\n  Results saved to {config['paths']['results_dir']}/")

    # ================================================================
    # AUTO-APPLY: Patch Dart source code with findings
    # ================================================================
    if auto_apply:
        print("\n" + "=" * 70)
        print("  PHASE 6 — AUTO-APPLY TO FLUTTER SOURCE")
        print("=" * 70)

        applier = AutoApplyAgent(str(PROJECT_ROOT))
        changes = applier.load_alignment_history(
            os.path.join(PROJECT_ROOT, config["paths"]["results_dir"])
        )
        if changes:
            applier.generate_patches(changes)
            applier.prompt_and_apply()
        else:
            print("  No changes to apply.")


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Cross-Platform ML Parity Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Golden Traces
  python parity_agent/run_agent.py --mode trace --images test_images/

  # Run Diff Engine
  python parity_agent/run_agent.py --mode diff

  # Run full autonomous agent loop
  python parity_agent/run_agent.py --mode agent --images test_images/
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["trace", "diff", "agent", "agent-legacy", "full", "report", "setup"],
        default="full",
        help="Operation mode: trace, diff, agent (LangGraph), agent-legacy (while loop), full, report, or setup",
    )
    parser.add_argument(
        "--images",
        default="test_images/",
        help="Path to test images directory",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: parity_agent/config.yaml)",
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Auto-apply findings to Flutter source code (with y/n prompt)",
    )
    args = parser.parse_args()

    # Handle setup mode early (no config needed)
    if args.mode == "setup":
        from parity_agent.setup_wizard import run_setup_wizard
        run_setup_wizard(PROJECT_ROOT)
        return

    # Load config
    config = load_config(args.config)
    image_dir = os.path.join(PROJECT_ROOT, args.images)

    print("\n" + banner("=" * 70))
    print(banner("  AUTONOMOUS CROSS-PLATFORM ML PARITY AGENT v0.2"))
    print(banner(f"  Mode: {args.mode}"))
    print(banner(f"  Images: {args.images}"))
    print(banner("=" * 70))

    if args.mode == "trace":
        run_trace(config, image_dir)
    elif args.mode == "diff":
        run_diff(config)
    elif args.mode == "agent":
        # Pre-load online traces BEFORE importing langgraph
        # (TFLite model must load before langgraph's threading setup)
        online_traces = _preload_online_traces(config, image_dir)
        from parity_agent.agents.graph import run_graph
        run_graph(config, image_dir, auto_apply=args.auto_apply,
                  online_traces=online_traces)
    elif args.mode == "agent-legacy":
        run_agent_loop(config, image_dir, auto_apply=args.auto_apply)
    elif args.mode == "report":
        run_report(config, image_dir)
    elif args.mode == "full":
        run_trace(config, image_dir)
        run_diff(config)
        online_traces = _preload_online_traces(config, image_dir)
        from parity_agent.agents.graph import run_graph
        run_graph(config, image_dir, auto_apply=args.auto_apply,
                  online_traces=online_traces)


if __name__ == "__main__":
    main()

