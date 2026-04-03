"""
Diff Report Generator — Human-readable reports of parity analysis.

Generates console-formatted and markdown reports showing per-image
and aggregate parity metrics between online and offline pipelines.
"""

from typing import Dict, List, Any
from datetime import datetime

from ..trace.schema import GoldenTrace
from .parity_loss import ParityLoss


class DiffReport:
    """Generate human-readable parity reports."""

    def __init__(self, parity_loss: ParityLoss):
        self.parity_loss = parity_loss

    def generate(self, golden_traces: List[GoldenTrace]) -> Dict[str, Any]:
        """
        Generate a full diff report for a set of golden traces.

        Returns:
            Dict containing structured report data + formatted text.
        """
        batch_result = self.parity_loss.compute_batch(golden_traces)
        agg = batch_result["aggregate"]

        # Build text report
        lines = []
        lines.append("=" * 70)
        lines.append("  PARITY AGENT — DIFF REPORT")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

        # Aggregate summary
        lines.append("  AGGREGATE SUMMARY")
        lines.append("  " + "-" * 40)
        lines.append(f"  Images analyzed:  {agg['num_images']}")
        lines.append(f"  Mean Parity Loss: {agg['mean_loss']:.6f}")
        lines.append(f"  Std Parity Loss:  {agg['std_loss']:.6f}")
        lines.append(f"  Min Parity Loss:  {agg['min_loss']:.6f}")
        lines.append(f"  Max Parity Loss:  {agg['max_loss']:.6f}")
        lines.append("")

        # Per-image breakdown
        if batch_result["per_image"]:
            lines.append("  PER-IMAGE METRICS")
            lines.append("  " + "-" * 40)
            lines.append(
                f"  {'Image':<20} {'TensorL2':<12} {'Logits':<12} "
                f"{'IoU-M':<10} {'Count':<8} {'KL':<10} {'TOTAL':<10}"
            )
            lines.append("  " + "-" * 82)

            for img_result in batch_result["per_image"]:
                m = img_result["metrics"]
                image_id = img_result.get("image_id", "?")[:18]
                lines.append(
                    f"  {image_id:<20} "
                    f"{m['tensor_l2']:>10.6f}  "
                    f"{m['logits_diff']:>10.6f}  "
                    f"{m['iou_mismatch']:>8.4f}  "
                    f"{m['count_diff']:>6.0f}  "
                    f"{m['confidence_kl']:>8.6f}  "
                    f"{img_result['total_loss']:>8.6f}"
                )

            lines.append("")

        # Detection comparison
        lines.append("  DETECTION COMPARISON")
        lines.append("  " + "-" * 40)
        for gt in golden_traces:
            if not gt.is_complete:
                continue
            on_count = len(gt.online.nms_boxes)
            off_count = len(gt.offline.nms_boxes)
            delta = off_count - on_count
            marker = "✓" if delta == 0 else f"{'+'if delta > 0 else ''}{delta}"
            lines.append(
                f"  {gt.image_id:<20} "
                f"Online: {on_count:>3}  Offline: {off_count:>3}  Δ: {marker}"
            )

        lines.append("")
        lines.append("=" * 70)

        text_report = "\n".join(lines)

        return {
            "text": text_report,
            "data": batch_result,
            "timestamp": datetime.now().isoformat(),
        }

    def to_markdown(self, golden_traces: List[GoldenTrace]) -> str:
        """Generate a Markdown-formatted diff report."""
        batch_result = self.parity_loss.compute_batch(golden_traces)
        agg = batch_result["aggregate"]

        md = []
        md.append("# Parity Diff Report")
        md.append(f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")

        md.append("## Aggregate Summary\n")
        md.append(f"| Metric | Value |")
        md.append(f"|--------|-------|")
        md.append(f"| Images Analyzed | {agg['num_images']} |")
        md.append(f"| Mean Parity Loss | {agg['mean_loss']:.6f} |")
        md.append(f"| Std Deviation | {agg['std_loss']:.6f} |")
        md.append(f"| Min Loss | {agg['min_loss']:.6f} |")
        md.append(f"| Max Loss | {agg['max_loss']:.6f} |")
        md.append("")

        if batch_result["per_image"]:
            md.append("## Per-Image Metrics\n")
            md.append("| Image | Tensor L2 | Logits Diff | IoU Mismatch | Count Diff | Confidence KL | Total Loss |")
            md.append("|-------|-----------|-------------|--------------|------------|---------------|------------|")

            for img_result in batch_result["per_image"]:
                m = img_result["metrics"]
                image_id = img_result.get("image_id", "?")
                md.append(
                    f"| {image_id} "
                    f"| {m['tensor_l2']:.6f} "
                    f"| {m['logits_diff']:.6f} "
                    f"| {m['iou_mismatch']:.4f} "
                    f"| {m['count_diff']:.0f} "
                    f"| {m['confidence_kl']:.6f} "
                    f"| **{img_result['total_loss']:.6f}** |"
                )
            md.append("")

        return "\n".join(md)
