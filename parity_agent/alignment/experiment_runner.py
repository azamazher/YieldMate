"""
Experiment Runner — Systematic ablation experiments with logging.

Runs controlled experiments: change one factor → re-run offline tracer →
compute parity loss → log results.
"""

import json
import copy
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..trace.offline_tracer import OfflineTracer
from ..trace.schema import PipelineTrace, GoldenTrace
from ..diff.parity_loss import ParityLoss
from .parameters import generate_ablation_configs, generate_combo_ablation_configs, get_default_config, PARAMETER_SPACE
from ..utils.colors import info, success, warning, highlight


class ExperimentRunner:
    """Run controlled ablation experiments and log results."""

    def __init__(
        self,
        model_path: str,
        labels: List[str],
        parity_loss: ParityLoss,
        results_dir: str = "results/experiments",
    ):
        self.model_path = model_path
        self.labels = labels
        self.parity_loss = parity_loss
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_log: List[Dict[str, Any]] = []

    def run_single_experiment(
        self,
        config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
        experiment_name: str = "",
    ) -> Dict[str, Any]:
        """
        Run one experiment with a given offline config.

        Args:
            config: Offline pipeline configuration to test.
            image_paths: List of image paths to trace.
            online_traces: Pre-computed online traces (fixed reference).
            experiment_name: Human-readable name for this experiment.

        Returns:
            Experiment result dict with config, parity loss, and details.
        """
        # Create offline tracer with this config
        tracer = OfflineTracer(self.model_path, self.labels, config)

        # Trace all images
        offline_traces = tracer.trace_batch(image_paths)

        # Build golden traces (pair online+offline by image_id)
        golden_traces = []
        online_by_id = {t.image_id: t for t in online_traces}
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

        # Compute parity loss
        batch_result = self.parity_loss.compute_batch(golden_traces)

        result = {
            "experiment_name": experiment_name,
            "config": config,
            "aggregate": batch_result["aggregate"],
            "per_image": batch_result["per_image"],
            "timestamp": datetime.now().isoformat(),
        }

        self.experiment_log.append(result)
        return result

    def run_ablation(
        self,
        param_name: str,
        base_config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> Dict[str, Any]:
        """
        Run single-parameter ablation: vary one parameter, keep others fixed.

        Args:
            param_name: Which parameter to ablate.
            base_config: Current offline config (baseline).
            image_paths: Test images.
            online_traces: Reference online traces.

        Returns:
            Ablation results with baseline and all variants.
        """
        print("\n" + info(f"[Ablation] Sweeping parameter: {param_name}"))
        print(f"  Search space: {PARAMETER_SPACE.get(param_name, {}).get('values', '?')}")

        # Run baseline first
        baseline = self.run_single_experiment(
            config=base_config,
            image_paths=image_paths,
            online_traces=online_traces,
            experiment_name=f"baseline_{param_name}",
        )

        # Run each variant
        variant_configs = generate_ablation_configs(base_config, param_name)
        variants = []

        for i, config in enumerate(variant_configs):
            value = config[param_name]
            print(f"  [{i + 1}/{len(variant_configs)}] {param_name}={value}")

            result = self.run_single_experiment(
                config=config,
                image_paths=image_paths,
                online_traces=online_traces,
                experiment_name=f"ablation_{param_name}_{value}",
            )
            result["param_value"] = value
            variants.append(result)

        # Find best
        all_results = [baseline] + variants
        best = min(all_results, key=lambda r: r["aggregate"]["mean_loss"])

        ablation_result = {
            "parameter": param_name,
            "baseline_loss": baseline["aggregate"]["mean_loss"],
            "baseline_config": base_config.get(param_name),
            "best_loss": best["aggregate"]["mean_loss"],
            "best_config": best["config"].get(param_name),
            "improvement": baseline["aggregate"]["mean_loss"] - best["aggregate"]["mean_loss"],
            "all_results": [
                {
                    "value": r.get("param_value", base_config.get(param_name)),
                    "mean_loss": r["aggregate"]["mean_loss"],
                }
                for r in all_results
            ],
        }

        print(f"  Baseline loss: " + warning(f"{ablation_result['baseline_loss']:.6f}"))
        
        # Color best loss based on whether it improved
        if ablation_result['improvement'] > 0:
            best_str = success(f"{ablation_result['best_loss']:.6f}")
            imp_str = success(f"{ablation_result['improvement']:.6f}")
        else:
            best_str = warning(f"{ablation_result['best_loss']:.6f}")
            imp_str = warning(f"None")

        print(f"  Best loss:     {best_str} ({param_name}={highlight(str(ablation_result['best_config']))})")
        print(f"  Improvement:   {imp_str}")

        return ablation_result

    def run_combo_ablation(
        self,
        param_names: List[str],
        base_config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> Dict[str, Any]:
        """
        Run multi-parameter combo ablation: vary multiple parameters together.

        This handles co-dependent parameters (e.g., apply_sigmoid and
        confidence_threshold) that must change simultaneously.

        Args:
            param_names: Parameters to vary together.
            base_config: Current offline config (baseline).
            image_paths: Test images.
            online_traces: Reference online traces.

        Returns:
            Combo ablation results with baseline and best combination.
        """
        combo_label = " + ".join(param_names)
        print("\n" + info(f"[Combo Ablation] Sweeping linked params: {combo_label}"))

        # Run baseline first
        baseline = self.run_single_experiment(
            config=base_config,
            image_paths=image_paths,
            online_traces=online_traces,
            experiment_name=f"combo_baseline_{'_'.join(param_names)}",
        )

        # Generate all combo configs
        combo_configs = generate_combo_ablation_configs(base_config, param_names)
        print(f"  Testing {len(combo_configs)} parameter combinations...")

        variants = []
        for i, config in enumerate(combo_configs):
            values = {p: config[p] for p in param_names}
            vals_str = ", ".join(f"{p}={v}" for p, v in values.items())
            print(f"  [{i + 1}/{len(combo_configs)}] {vals_str}")

            result = self.run_single_experiment(
                config=config,
                image_paths=image_paths,
                online_traces=online_traces,
                experiment_name=f"combo_{'_'.join(param_names)}_{i}",
            )
            result["param_values"] = values
            variants.append(result)

        # Find best across all (including baseline)
        all_results = [baseline] + variants
        best = min(all_results, key=lambda r: r["aggregate"]["mean_loss"])

        # Build a result for each param changed in the best config
        best_changes = {}
        for p in param_names:
            best_changes[p] = {
                "old": base_config.get(p),
                "new": best["config"].get(p),
            }

        # Identify the single "most important" parameter change (the one with
        # the biggest individual value delta, or the boolean toggle).
        # AlignmentAgent expects a single best_param/best_value.
        best_param = param_names[0]
        best_value = best["config"].get(param_names[0])
        for p in param_names:
            if best["config"].get(p) != base_config.get(p):
                best_param = p
                best_value = best["config"].get(p)
                break  # Use the first changed param

        combo_result = {
            "parameter": best_param,
            "baseline_loss": baseline["aggregate"]["mean_loss"],
            "baseline_config": base_config.get(best_param),
            "best_loss": best["aggregate"]["mean_loss"],
            "best_config": best_value,
            "improvement": baseline["aggregate"]["mean_loss"] - best["aggregate"]["mean_loss"],
            "combo_changes": best_changes,
            "best_full_config": best["config"],
            "all_results": [
                {
                    "values": r.get("param_values", {p: base_config.get(p) for p in param_names}),
                    "mean_loss": r["aggregate"]["mean_loss"],
                }
                for r in all_results
            ],
        }

        print(f"  Baseline loss: " + warning(f"{combo_result['baseline_loss']:.6f}"))

        if combo_result['improvement'] > 0:
            best_str = success(f"{combo_result['best_loss']:.6f}")
            imp_str = success(f"{combo_result['improvement']:.6f}")
        else:
            best_str = warning(f"{combo_result['best_loss']:.6f}")
            imp_str = warning("None")

        best_vals = ", ".join(f"{p}={best['config'].get(p)}" for p in param_names)
        print(f"  Best loss:     {best_str} ({highlight(best_vals)})")
        print(f"  Improvement:   {imp_str}")

        return combo_result

    def save_log(self, filename: str = "experiment_log.json") -> str:
        """Save experiment log to disk."""
        path = self.results_dir / filename
        with open(path, "w") as f:
            # Serialize — skip non-serializable items
            serializable = []
            for entry in self.experiment_log:
                s = {
                    "experiment_name": entry["experiment_name"],
                    "config": entry["config"],
                    "aggregate": entry["aggregate"],
                    "timestamp": entry["timestamp"],
                }
                serializable.append(s)
            json.dump(serializable, f, indent=2, default=str)
        return str(path)

