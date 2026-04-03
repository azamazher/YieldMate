"""
Ablation Agent — Runs controlled experiments to test hypotheses.

For each hypothesis, systematically tests parameter changes and measures
their effect on parity loss.

Supports:
  - Single-parameter ablation (change one factor → measure)
  - Multi-parameter combo ablation (change linked factors together)
"""

from typing import Dict, List, Any

from ..trace.schema import PipelineTrace
from ..alignment.experiment_runner import ExperimentRunner
from ..alignment.parameters import get_linked_params
from ..diff.parity_loss import ParityLoss
from ..utils.colors import info, highlight, warning, success


class AblationAgent:
    """
    Automated ablation testing: change one factor → measure parity loss.
    Falls back to combo ablation when single-param tests find no improvement
    and the parameter has known co-dependent (linked) params.
    """

    def __init__(self, experiment_runner: ExperimentRunner):
        self.runner = experiment_runner

    def test_hypotheses(
        self,
        hypotheses: List[Dict[str, Any]],
        current_config: Dict[str, Any],
        image_paths: List[str],
        online_traces: List[PipelineTrace],
    ) -> Dict[str, Any]:
        """
        Test a list of hypotheses via controlled ablation.

        For each hypothesis, ablates the suggested parameters and
        records which values reduce parity loss.

        If single-parameter ablation finds no improvement AND the
        parameter has linked co-dependent params, automatically
        falls back to combo (multi-parameter) ablation.

        Args:
            hypotheses: Output from HypothesisAgent.generate()
            current_config: Current offline pipeline config.
            image_paths: Test image paths.
            online_traces: Fixed online reference traces.

        Returns:
            Dict with ablation results per hypothesis, ranked by improvement.
        """
        results = []

        for hypothesis in hypotheses:
            h_name = hypothesis["hypothesis"]
            params = hypothesis["params_to_test"]

            print(f"\n" + info(f"[AblationAgent] Testing hypothesis: {h_name}"))
            print(f"  Parameters: " + highlight(str(params)))

            # ── Phase 1: Single-parameter ablation ──
            param_results = []
            for param in params:
                ablation = self.runner.run_ablation(
                    param_name=param,
                    base_config=current_config,
                    image_paths=image_paths,
                    online_traces=online_traces,
                )
                param_results.append(ablation)

            # Find the best result across all params for this hypothesis
            best_improvement = 0.0
            best_param = None
            best_value = None
            best_loss = float("inf")

            for pr in param_results:
                if pr["improvement"] > best_improvement:
                    best_improvement = pr["improvement"]
                    best_param = pr["parameter"]
                    best_value = pr["best_config"]
                    best_loss = pr["best_loss"]

            # ── Phase 2: Combo ablation fallback ──
            # If single-param found nothing useful, check for linked params
            if best_improvement <= 0.001:
                combo_tried = set()
                for param in params:
                    linked = get_linked_params(param)
                    if linked:
                        # Build full combo group (this param + its linked ones)
                        combo_group = sorted(set([param] + linked))
                        combo_key = tuple(combo_group)

                        if combo_key in combo_tried:
                            continue
                        combo_tried.add(combo_key)

                        print("\n" + warning(
                            f"  [AblationAgent] Single-param ablation found no improvement."
                        ))
                        print(info(
                            f"  Trying COMBO ablation: {' + '.join(combo_group)}"
                        ))

                        combo_result = self.runner.run_combo_ablation(
                            param_names=combo_group,
                            base_config=current_config,
                            image_paths=image_paths,
                            online_traces=online_traces,
                        )

                        if combo_result["improvement"] > best_improvement:
                            best_improvement = combo_result["improvement"]
                            best_param = combo_result["parameter"]
                            best_value = combo_result["best_config"]
                            best_loss = combo_result["best_loss"]

                            # Also apply ALL combo changes to current_config
                            # so AlignmentAgent picks them up
                            if "best_full_config" in combo_result:
                                param_results.append(combo_result)

                            print(success(
                                f"  ✓ Combo ablation found improvement: "
                                f"{combo_result['improvement']:.6f}"
                            ))

            results.append({
                "hypothesis": h_name,
                "description": hypothesis["description"],
                "priority": hypothesis["priority"],
                "param_results": param_results,
                "best_param": best_param,
                "best_value": best_value,
                "best_loss": best_loss,
                "improvement": best_improvement,
            })

        # Sort by improvement (largest first)
        results.sort(key=lambda r: r["improvement"], reverse=True)

        return {
            "ablation_results": results,
            "best_overall": results[0] if results else None,
        }
