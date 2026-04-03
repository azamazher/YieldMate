"""
Bayesian Optimizer — Smart parameter search using Optuna.

Replaces the exhaustive grid sweep with Bayesian optimization,
finding optimal parameters in ~5 trials instead of 13+.

Usage:
    Set `optimization_method: bayesian` in config.yaml to enable.
"""

import copy
from typing import Dict, List, Any, Optional

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from ..trace.offline_tracer import OfflineTracer
from ..trace.schema import PipelineTrace, GoldenTrace
from ..diff.parity_loss import ParityLoss
from .parameters import PARAMETER_SPACE


class BayesianOptimizer:
    """
    Uses Optuna TPE sampler for intelligent parameter search.

    Advantages over grid sweep:
    - Explores promising regions first
    - Typically converges in 5-8 trials vs 13+ for grid
    - Handles continuous and categorical parameters naturally
    """

    def __init__(
        self,
        model_path: str,
        labels: List[str],
        parity_loss: ParityLoss,
        n_trials: int = 10,
    ):
        if not OPTUNA_AVAILABLE:
            raise ImportError(
                "Optuna not installed. Install with: pip install optuna"
            )

        self.model_path = model_path
        self.labels = labels
        self.parity_loss = parity_loss
        self.n_trials = n_trials
        self.study: Optional[optuna.Study] = None

    def _suggest_param(
        self, trial: optuna.Trial, param_name: str, base_value: Any
    ) -> Any:
        """Suggest a parameter value using Optuna's sampler."""
        space = PARAMETER_SPACE.get(param_name)
        if not space:
            return base_value

        if space["type"] == "categorical":
            return trial.suggest_categorical(param_name, space["values"])
        elif space["type"] == "continuous":
            return trial.suggest_float(
                param_name,
                space["min"],
                space["max"],
                step=space.get("step", 0.01),
            )
        return base_value

    def optimize_single(
        self,
        param_name: str,
        base_config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> Dict[str, Any]:
        """
        Optimize a single parameter using Bayesian search.

        Args:
            param_name: Which parameter to optimize.
            base_config: Current offline config.
            image_paths: Test images.
            online_traces: Reference online traces.

        Returns:
            Result dict with best value, loss, and improvement.
        """
        print(f"\n[Bayesian] Optimizing: {param_name} ({self.n_trials} trials)")

        # Compute baseline
        baseline_loss = self._evaluate(base_config, image_paths, online_traces)
        print(f"  Baseline loss: {baseline_loss:.6f}")

        def objective(trial: optuna.Trial) -> float:
            config = copy.deepcopy(base_config)
            config[param_name] = self._suggest_param(trial, param_name, base_config.get(param_name))
            loss = self._evaluate(config, image_paths, online_traces)
            return loss

        self.study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        self.study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        best_trial = self.study.best_trial
        best_value = best_trial.params.get(param_name, base_config.get(param_name))
        best_loss = best_trial.value

        improvement = baseline_loss - best_loss

        print(f"  Best: {param_name}={best_value} → loss={best_loss:.6f}")
        print(f"  Improvement: {improvement:.6f} (in {len(self.study.trials)} trials)")

        return {
            "parameter": param_name,
            "baseline_loss": baseline_loss,
            "best_value": best_value,
            "best_loss": best_loss,
            "improvement": improvement,
            "n_trials": len(self.study.trials),
            "all_trials": [
                {
                    "value": t.params.get(param_name),
                    "loss": t.value,
                }
                for t in self.study.trials
            ],
        }

    def optimize_multi(
        self,
        param_names: List[str],
        base_config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> Dict[str, Any]:
        """
        Optimize multiple parameters jointly using Bayesian search.

        This can find interactions between parameters that
        single-parameter ablation misses.
        """
        print(f"\n[Bayesian] Joint optimization: {param_names} ({self.n_trials} trials)")

        baseline_loss = self._evaluate(base_config, image_paths, online_traces)

        def objective(trial: optuna.Trial) -> float:
            config = copy.deepcopy(base_config)
            for param_name in param_names:
                config[param_name] = self._suggest_param(trial, param_name, base_config.get(param_name))
            return self._evaluate(config, image_paths, online_traces)

        self.study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        self.study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        best_trial = self.study.best_trial
        best_config = {p: best_trial.params.get(p, base_config.get(p)) for p in param_names}

        return {
            "parameters": param_names,
            "baseline_loss": baseline_loss,
            "best_config": best_config,
            "best_loss": best_trial.value,
            "improvement": baseline_loss - best_trial.value,
            "n_trials": len(self.study.trials),
        }

    def _evaluate(
        self,
        config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> float:
        """Evaluate a config by running offline tracer and computing parity loss."""
        tracer = OfflineTracer(self.model_path, self.labels, config)
        offline_traces = tracer.trace_batch(image_paths)

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

        batch_result = self.parity_loss.compute_batch(golden_traces)
        return batch_result["aggregate"]["mean_loss"]
