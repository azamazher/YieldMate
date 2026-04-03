"""
LangGraph Orchestration — State machine for the Parity Agent.

Replaces the hand-written while loop with a proper LangGraph StateGraph.
Provides branching, retries, human-in-the-loop checkpoints, and persistence.

Run with:
    python parity_agent/run_agent.py --mode graph --images test_images/
"""

import os
import sys
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from pathlib import Path

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class AgentState(TypedDict):
    """State that flows through the LangGraph nodes."""
    # Configuration
    config: Dict[str, Any]
    current_config: Dict[str, Any]  # Offline pipeline config being tuned
    model_path: str
    labels: List[str]
    image_paths: List[str]

    # Trace data
    online_traces: List[Any]      # List[PipelineTrace]
    offline_traces: List[Any]     # List[PipelineTrace]
    golden_traces: List[Any]      # List[GoldenTrace]

    # Analysis
    parity_loss: float
    metrics: Dict[str, float]
    profile: Dict[str, Any]
    hypotheses: List[Dict[str, Any]]

    # Ablation
    ablation_results: Dict[str, Any]

    # Agent state
    iteration: int
    max_iterations: int
    patience: int
    no_improve_count: int
    best_loss: float
    alignment_history: List[Dict[str, Any]]

    # Control
    should_stop: bool
    stop_reason: str


def trace_node(state: AgentState) -> AgentState:
    """Node: Run offline tracing (online traces are pre-loaded)."""
    from parity_agent.trace.offline_tracer import OfflineTracer
    from parity_agent.trace.schema import GoldenTrace
    from parity_agent.trace.storage import TraceStorage
    from parity_agent.utils.colors import banner, info

    config = state["config"]
    iteration = state["iteration"]
    print("\n" + banner("─" * 60))
    print(banner(f"  ITERATION {iteration}/{state['max_iterations']}"))
    print(banner("─" * 60))
    print(info("  [1/5] Tracing offline pipeline..."))

    online_traces = state["online_traces"]

    # Offline traces regenerated each iteration with current config
    offline_tracer = OfflineTracer(
        state["model_path"], state["labels"], state["current_config"]
    )
    offline_traces = offline_tracer.trace_batch(state["image_paths"])

    # Build golden traces
    online_by_id = {t.image_id: t for t in online_traces}
    golden_traces = []
    for off_trace in offline_traces:
        on_trace = online_by_id.get(off_trace.image_id)
        if on_trace:
            gt = GoldenTrace(
                image_id=off_trace.image_id,
                image_path=off_trace.metadata.get("image_path", ""),
                online=on_trace,
                offline=off_trace,
            )
            golden_traces.append(gt)

    # Save traces to disk so the Streamlit dashboard always shows latest
    traces_dir = config.get("paths", {}).get("traces_dir", "traces")
    storage = TraceStorage(str(PROJECT_ROOT / traces_dir))
    for gt in golden_traces:
        storage.save_golden_trace(gt)

    state["offline_traces"] = offline_traces
    state["golden_traces"] = golden_traces
    return state


def diff_node(state: AgentState) -> AgentState:
    """Node: Compute parity loss."""
    from parity_agent.diff.parity_loss import ParityLoss
    import numpy as np
    from parity_agent.utils.colors import info, highlight, success
    from parity_agent.utils.snapshots import save_snapshot

    weights = state["config"]["parity_loss"]["weights"]
    parity_loss = ParityLoss(weights=weights)
    batch_result = parity_loss.compute_batch(state["golden_traces"])

    current_loss = batch_result["aggregate"]["mean_loss"]
    state["parity_loss"] = current_loss

    # Compute average metrics from per-image results
    per_image = batch_result.get("per_image", [])
    if per_image:
        metric_keys = per_image[0].get("metrics", {}).keys()
        state["metrics"] = {
            k: float(np.mean([img["metrics"][k] for img in per_image if "metrics" in img]))
            for k in metric_keys
        }
    else:
        state["metrics"] = {}

    print(info("  [2/5] ") + f"Current parity loss: " + highlight(f"{current_loss:.6f}"))

    # Save baseline snapshot on first iteration (captures the broken state)
    results_dir = str(PROJECT_ROOT / state["config"].get("paths", {}).get("results_dir", "results"))
    if state["iteration"] == 0:
        save_snapshot(state["golden_traces"], current_loss, state["current_config"],
                      "baseline", results_dir)
        print(info("        ") + "Baseline snapshot saved.")

    # Check convergence
    threshold = state["config"]["parity_loss"]["threshold"]
    if current_loss < threshold:
        state["should_stop"] = True
        state["stop_reason"] = f"CONVERGED! Loss {current_loss:.6f} < {threshold}"
        print(success(f"\n  ✓ {state['stop_reason']}"))
        # Save final snapshot on convergence
        save_snapshot(state["golden_traces"], current_loss, state["current_config"],
                      "final", results_dir)
        print(info("        ") + "Final snapshot saved (converged).")

    return state


def profile_node(state: AgentState) -> AgentState:
    """Node: Profile divergence to find dominant stage."""
    from parity_agent.agents.profiler import ProfilerAgent
    from parity_agent.diff.parity_loss import ParityLoss
    from parity_agent.utils.colors import info, warning

    if state["should_stop"]:
        return state

    # Profiler needs batch_result from ParityLoss, not raw golden traces
    weights = state["config"]["parity_loss"]["weights"]
    parity_loss = ParityLoss(weights=weights)
    batch_result = parity_loss.compute_batch(state["golden_traces"])

    profiler = ProfilerAgent()
    profile = profiler.analyze(batch_result)
    state["profile"] = profile

    print(info("  [3/5] ") + "Profiling divergence...")
    print(f"        Dominant stage: " + warning(profile['dominant_stage']))
    return state


def hypothesize_node(state: AgentState) -> AgentState:
    """Node: Generate hypotheses."""
    from parity_agent.agents.hypothesis import HypothesisAgent
    from parity_agent.utils.colors import info, error

    if state["should_stop"]:
        return state

    hypothesis_agent = HypothesisAgent()
    hypotheses = hypothesis_agent.generate(state["profile"])
    state["hypotheses"] = hypotheses

    print(info("  [4/5] ") + f"Generated {len(hypotheses)} hypotheses")
    for h in hypotheses:
        print(f"        • {error(h['hypothesis']) if h['priority'] == 'critical' else h['hypothesis']} ({h['priority']})")

    if not hypotheses:
        state["should_stop"] = True
        state["stop_reason"] = "No hypotheses generated"

    return state


def ablate_node(state: AgentState) -> AgentState:
    """Node: Run ablation experiments."""
    from parity_agent.agents.ablation import AblationAgent
    from parity_agent.alignment.experiment_runner import ExperimentRunner
    from parity_agent.diff.parity_loss import ParityLoss
    from parity_agent.utils.colors import info

    if state["should_stop"]:
        return state

    print(info("  [5/5] ") + "Running ablation experiments...")

    weights = state["config"]["parity_loss"]["weights"]
    parity_loss = ParityLoss(weights=weights)
    experiment_runner = ExperimentRunner(
        state["model_path"], state["labels"], parity_loss,
    )
    ablation_agent = AblationAgent(experiment_runner)

    # Use subset for ablation
    max_abl = state["config"].get("agent", {}).get("max_ablation_images", len(state["image_paths"]))
    abl_images = state["image_paths"][:max_abl]
    abl_online = [t for t in state["online_traces"] if any(
        Path(p).stem == t.image_id for p in abl_images
    )]

    results = ablation_agent.test_hypotheses(
        hypotheses=state["hypotheses"][:3],
        current_config=state["current_config"],
        image_paths=abl_images,
        online_traces=abl_online,
    )
    state["ablation_results"] = results

    # Save experiment log to disk for dashboard
    results_dir = os.path.join(str(PROJECT_ROOT), state["config"]["paths"]["results_dir"])
    experiment_runner.save_log()

    return state


def decide_node(state: AgentState) -> AgentState:
    """
    Node: Decide whether to apply changes, retry, or stop.

    This is the branching point of the graph.
    Handles both single-param and combo ablation results.
    """
    from parity_agent.agents.alignment import AlignmentAgent
    import copy

    if state["should_stop"]:
        return state

    alignment_agent = AlignmentAgent(
        str(PROJECT_ROOT / "parity_agent" / "config.yaml"),
        str(PROJECT_ROOT / state["config"]["paths"]["results_dir"]),
    )
    # Restore history
    alignment_agent.history = list(state["alignment_history"])

    new_config = alignment_agent.apply_best(state["current_config"], state["ablation_results"])

    # If combo ablation found a multi-param improvement, apply ALL linked changes
    best_overall = state["ablation_results"].get("best_overall", {})
    if best_overall and new_config != state["current_config"]:
        # Check if this result came from combo ablation
        for pr in best_overall.get("param_results", []):
            if "best_full_config" in pr and pr.get("improvement", 0) > 0:
                # Apply ALL params from the combo config, not just the primary one
                combo_config = pr["best_full_config"]
                combo_changes = pr.get("combo_changes", {})
                for param, change in combo_changes.items():
                    if change["old"] != change["new"]:
                        new_config[param] = change["new"]
                        # Log each combo change in alignment history
                        if not any(h.get("parameter") == param for h in alignment_agent.history):
                            from datetime import datetime
                            alignment_agent.history.append({
                                "timestamp": datetime.now().isoformat(),
                                "parameter": param,
                                "old_value": change["old"],
                                "new_value": change["new"],
                                "improvement": pr["improvement"],
                                "new_loss": pr["best_loss"],
                                "hypothesis": best_overall.get("hypothesis", "combo_ablation"),
                            })

    if new_config == state["current_config"]:
        state["no_improve_count"] += 1
    else:
        state["current_config"] = new_config
        state["no_improve_count"] = 0
        new_loss = state["ablation_results"].get("best_overall", {}).get("best_loss", state["parity_loss"])
        if new_loss < state["best_loss"]:
            state["best_loss"] = new_loss
        state["alignment_history"] = alignment_agent.history

    # Always save history to disk (even if empty, so dashboard is up to date)
    alignment_agent.save_history()

    state["iteration"] += 1

    # Check stopping conditions
    if state["iteration"] > state["max_iterations"]:
        state["should_stop"] = True
        state["stop_reason"] = "Max iterations reached"
    elif state["no_improve_count"] >= state["patience"]:
        state["should_stop"] = True
        state["stop_reason"] = f"Patience exhausted ({state['patience']} iterations without improvement)"

    if state["should_stop"]:
        from parity_agent.utils.colors import warning
        from parity_agent.utils.snapshots import save_snapshot
        print(warning(f"\n  {state['stop_reason']}. Stopping."))
        # Save final snapshot when agent stops (patience/max_iter)
        results_dir = str(PROJECT_ROOT / state["config"].get("paths", {}).get("results_dir", "results"))
        save_snapshot(state["golden_traces"], state["parity_loss"], state["current_config"],
                      "final", results_dir)
        print(warning("        Final snapshot saved."))

    return state



def should_continue(state: AgentState) -> str:
    """Routing function: continue iterating or stop."""
    if state["should_stop"]:
        return "end"
    return "trace"


def build_parity_graph() -> Optional["StateGraph"]:
    """
    Build the LangGraph state machine for the parity agent.

    Graph topology:
        trace → diff → profile → hypothesize → ablate → decide
              ↘ (if converged) END
              → decide → (if should_continue) → trace (loop)
                       → (if should_stop) → END
    """
    if not LANGGRAPH_AVAILABLE:
        print("LangGraph not installed. Install with: pip install langgraph")
        return None

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("trace", trace_node)
    graph.add_node("diff", diff_node)
    graph.add_node("profile", profile_node)
    graph.add_node("hypothesize", hypothesize_node)
    graph.add_node("ablate", ablate_node)
    graph.add_node("decide", decide_node)

    # Add edges (linear flow within an iteration)
    graph.add_edge("trace", "diff")
    graph.add_edge("diff", "profile")
    graph.add_edge("profile", "hypothesize")
    graph.add_edge("hypothesize", "ablate")
    graph.add_edge("ablate", "decide")

    # Conditional edge: loop or stop
    graph.add_conditional_edges(
        "decide",
        should_continue,
        {"trace": "trace", "end": END},
    )

    # Entry point
    graph.set_entry_point("trace")

    return graph.compile()


def run_graph(config: dict, image_dir: str, auto_apply: bool = False,
              online_traces=None):
    """Run the parity agent using LangGraph orchestration."""
    from parity_agent.utils.image_loader import get_test_images
    from parity_agent.agents.alignment import AlignmentAgent

    graph = build_parity_graph()
    if graph is None:
        print("LangGraph not installed. Falling back to legacy agent loop...")
        from parity_agent.run_agent import run_agent_loop
        run_agent_loop(config, image_dir, auto_apply=auto_apply)
        return

    model_path = os.path.join(str(PROJECT_ROOT), config["paths"]["model_tflite"])
    image_paths = get_test_images(image_dir)
    labels = config["model"]["class_names"]
    offline_config = config.get("offline", {})

    print("\n" + "=" * 70)
    print("  LANGGRAPH PARITY AGENT")
    print("  State machine orchestration for ML deployment parity")
    print("=" * 70)
    print(f"\nImages: {len(image_paths)}")

    # Online traces must be pre-loaded by caller (run_agent.py)
    # to avoid macOS mutex crash with TFLite + LangGraph threading
    if online_traces is None:
        print("ERROR: online_traces must be pre-loaded before importing langgraph.")
        print("Falling back to legacy agent loop...")
        from parity_agent.run_agent import run_agent_loop
        run_agent_loop(config, image_dir, auto_apply=auto_apply)
        return

    print(f"Online traces: {len(online_traces)} (pre-loaded)")

    initial_state: AgentState = {
        "config": config,
        "current_config": dict(offline_config),
        "model_path": model_path,
        "labels": labels,
        "image_paths": image_paths,
        "online_traces": online_traces,
        "offline_traces": [],
        "golden_traces": [],
        "parity_loss": float("inf"),
        "metrics": {},
        "profile": {},
        "hypotheses": [],
        "ablation_results": {},
        "iteration": 1,
        "max_iterations": config.get("agent", {}).get("max_iterations", 20),
        "patience": config.get("agent", {}).get("patience", 2),
        "no_improve_count": 0,
        "best_loss": float("inf"),
        "alignment_history": [],
        "should_stop": False,
        "stop_reason": "",
    }

    print(f"Max iterations: {initial_state['max_iterations']}")
    print(f"Patience: {initial_state['patience']}")

    # Run the graph
    final_state = graph.invoke(initial_state)

    # Print summary
    print("\n" + "=" * 70)
    print("  GRAPH RUN COMPLETE")
    print("=" * 70)
    print(f"\n  Final parity loss: {final_state['best_loss']:.6f}")
    print(f"  Stop reason: {final_state['stop_reason']}")
    print(f"  Iterations: {final_state['iteration'] - 1}")
    if final_state["alignment_history"]:
        print(f"\n  Changes applied:")
        for i, change in enumerate(final_state["alignment_history"], 1):
            print(f"    {i}. {change['parameter']}: {change['old_value']} → {change['new_value']} "
                  f"(Δ={change['improvement']:.4f})")

    # Save results
    results_dir = os.path.join(str(PROJECT_ROOT), config["paths"]["results_dir"])
    alignment_agent = AlignmentAgent(
        str(PROJECT_ROOT / "parity_agent" / "config.yaml"), results_dir
    )
    alignment_agent.history = final_state["alignment_history"]
    alignment_agent.save_history()
    alignment_agent.save_config(final_state["current_config"])
    print(f"\n  Results saved to {results_dir}/")

    # Auto-apply: patch Dart source code
    if auto_apply and final_state["alignment_history"]:
        print("\n" + "=" * 70)
        print("  PHASE 6 — AUTO-APPLY TO FLUTTER SOURCE")
        print("=" * 70)

        from parity_agent.agents.auto_apply import AutoApplyAgent
        applier = AutoApplyAgent(str(PROJECT_ROOT))
        changes = applier.load_alignment_history(results_dir)
        if changes:
            applier.generate_patches(changes)
            applier.prompt_and_apply()
        else:
            print("  No changes to apply.")

