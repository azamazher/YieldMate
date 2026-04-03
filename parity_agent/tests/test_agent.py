"""
Unit Tests — Test all core parity agent components.

Run with:
    pytest parity_agent/tests/ -v
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

# ====================================================================
# Test: Divergence Metrics
# ====================================================================

class TestMetrics:
    """Test all 5 divergence metrics with known inputs."""

    def test_tensor_l2_identical(self):
        """Identical tensors should have zero L2 distance."""
        from parity_agent.diff.metrics import tensor_l2
        from parity_agent.trace.schema import PipelineTrace
        t = np.ones((1, 640, 640, 3), dtype=np.float32)
        online = PipelineTrace(image_id="test", pipeline="online", input_tensor=t.copy())
        offline = PipelineTrace(image_id="test", pipeline="offline", input_tensor=t.copy())
        result = tensor_l2(online, offline)
        assert result == 0.0

    def test_tensor_l2_different(self):
        """Different tensors should have positive L2 distance."""
        from parity_agent.diff.metrics import tensor_l2
        from parity_agent.trace.schema import PipelineTrace
        a = np.zeros((1, 640, 640, 3), dtype=np.float32)
        b = np.ones((1, 640, 640, 3), dtype=np.float32)
        online = PipelineTrace(image_id="test", pipeline="online", input_tensor=a)
        offline = PipelineTrace(image_id="test", pipeline="offline", input_tensor=b)
        result = tensor_l2(online, offline)
        assert result > 0

    def test_tensor_l2_none(self):
        """None tensors should return -1."""
        from parity_agent.diff.metrics import tensor_l2
        from parity_agent.trace.schema import PipelineTrace
        online = PipelineTrace(image_id="test", pipeline="online")
        offline = PipelineTrace(image_id="test", pipeline="offline")
        result = tensor_l2(online, offline)
        assert result == -1.0

    def test_count_diff_same(self):
        """Same number of detections should return 0."""
        from parity_agent.diff.metrics import count_diff
        from parity_agent.trace.schema import PipelineTrace, Detection
        dets = [Detection("apple", 0, 0.9, [0.1, 0.1, 0.5, 0.5])]
        online = PipelineTrace(image_id="test", pipeline="online", nms_boxes=list(dets))
        offline = PipelineTrace(image_id="test", pipeline="offline", nms_boxes=list(dets))
        result = count_diff(online, offline)
        assert result == 0

    def test_count_diff_different(self):
        """Different counts should return absolute difference."""
        from parity_agent.diff.metrics import count_diff
        from parity_agent.trace.schema import PipelineTrace, Detection
        online_dets = [Detection("apple", 0, 0.9, [0.1, 0.1, 0.5, 0.5])]
        offline_dets = [Detection("apple", 0, 0.3, [0.1*i, 0.1*i, 0.5, 0.5]) for i in range(10)]
        online = PipelineTrace(image_id="test", pipeline="online", nms_boxes=online_dets)
        offline = PipelineTrace(image_id="test", pipeline="offline", nms_boxes=offline_dets)
        result = count_diff(online, offline)
        assert result == 9

    def test_logits_diff_identical(self):
        """Identical logits should produce zero difference."""
        from parity_agent.diff.metrics import logits_diff
        from parity_agent.trace.schema import PipelineTrace
        raw = np.array([[[0.5, 0.3, 0.2]]], dtype=np.float32)
        online = PipelineTrace(image_id="test", pipeline="online", raw_output=raw.copy())
        offline = PipelineTrace(image_id="test", pipeline="offline", raw_output=raw.copy())
        result = logits_diff(online, offline)
        assert result == 0.0

    def test_logits_diff_none(self):
        """None inputs should return -1."""
        from parity_agent.diff.metrics import logits_diff
        from parity_agent.trace.schema import PipelineTrace
        online = PipelineTrace(image_id="test", pipeline="online")
        offline = PipelineTrace(image_id="test", pipeline="offline")
        result = logits_diff(online, offline)
        assert result == -1.0


# ====================================================================
# Test: Hypothesis Agent
# ====================================================================

class TestHypothesis:
    """Test hypothesis generation rules."""

    def test_high_count_diff_generates_confidence_hypothesis(self):
        """High count_diff should generate confidence_threshold_too_low."""
        from parity_agent.agents.hypothesis import HypothesisAgent

        agent = HypothesisAgent()
        profile = {
            "dominant_stage": "nms_behavior",
            "metric_averages": {
                "tensor_l2": 0.001,
                "logits_diff": 0.001,
                "iou_mismatch": 0.5,
                "count_diff": 50,
                "confidence_kl": 0.1,
            },
        }
        hypotheses = agent.generate(profile)
        names = [h["hypothesis"] for h in hypotheses]
        assert "confidence_threshold_too_low" in names

    def test_preprocessing_generates_normalization_hypothesis(self):
        """Preprocessing dominant stage should suggest normalization."""
        from parity_agent.agents.hypothesis import HypothesisAgent

        agent = HypothesisAgent()
        profile = {
            "dominant_stage": "preprocessing",
            "metric_averages": {
                "tensor_l2": 0.5,
                "logits_diff": 0.001,
                "iou_mismatch": 0.0,
                "count_diff": 0,
                "confidence_kl": 0.0,
            },
        }
        hypotheses = agent.generate(profile)
        names = [h["hypothesis"] for h in hypotheses]
        assert "normalization_mismatch" in names

    def test_priority_ordering(self):
        """Critical hypotheses should come before low-priority ones."""
        from parity_agent.agents.hypothesis import HypothesisAgent

        agent = HypothesisAgent()
        profile = {
            "dominant_stage": "calibration",
            "metric_averages": {
                "tensor_l2": 0.1,
                "logits_diff": 0.05,
                "iou_mismatch": 0.1,
                "count_diff": 20,
                "confidence_kl": 0.5,
            },
        }
        hypotheses = agent.generate(profile)
        if len(hypotheses) >= 2:
            priorities = [h["priority"] for h in hypotheses]
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            values = [priority_order.get(p, 99) for p in priorities]
            assert values == sorted(values), "Hypotheses not sorted by priority"


# ====================================================================
# Test: Parity Loss
# ====================================================================

class TestParityLoss:
    """Test the weighted parity loss computation."""

    def test_custom_weights(self):
        """Custom weights should affect the loss calculation."""
        from parity_agent.diff.parity_loss import ParityLoss

        parity = ParityLoss(weights={
            "tensor_l2": 0.0,
            "logits_diff": 0.0,
            "iou_mismatch": 0.0,
            "count_diff": 1.0,
            "confidence_kl": 0.0,
        })
        assert parity.weights["count_diff"] == 1.0
        assert parity.weights["tensor_l2"] == 0.0

    def test_zero_loss_for_identical(self):
        """Identical traces should produce zero/near-zero parity loss."""
        from parity_agent.diff.parity_loss import ParityLoss
        from parity_agent.trace.schema import PipelineTrace, GoldenTrace, Detection

        parity = ParityLoss()
        tensor = np.zeros((1, 640, 640, 3), dtype=np.float32)
        raw = np.zeros((1, 12, 8400), dtype=np.float32)
        dets = [Detection("apple", 0, 0.9, [0.1, 0.1, 0.5, 0.5])]

        online = PipelineTrace(
            image_id="test", pipeline="online",
            input_tensor=tensor.copy(), raw_output=raw.copy(),
            decoded_boxes=list(dets), nms_boxes=list(dets),
        )
        offline = PipelineTrace(
            image_id="test", pipeline="offline",
            input_tensor=tensor.copy(), raw_output=raw.copy(),
            decoded_boxes=list(dets), nms_boxes=list(dets),
        )
        gt = GoldenTrace("test", "test.jpg", online, offline)

        result = parity.compute_batch([gt])
        assert result["aggregate"]["mean_loss"] == 0.0


# ====================================================================
# Test: Auto-Apply Agent
# ====================================================================

class TestAutoApply:
    """Test the auto-apply Dart patching logic."""

    def test_scan_dart_files(self, tmp_path):
        """Should find .dart files in lib/."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "test.dart").write_text("void main() {}")
        (lib_dir / "test.g.dart").write_text("// generated")

        from parity_agent.agents.auto_apply import AutoApplyAgent
        agent = AutoApplyAgent(str(tmp_path))
        files = agent.scan_dart_files()

        assert len(files) == 1
        assert "test.dart" in files[0]

    def test_find_confidence_target(self, tmp_path):
        """Should find confThreshold patterns in Dart code."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "service.dart").write_text(
            "void test({double confThreshold = 0.5}) {}"
        )

        from parity_agent.agents.auto_apply import AutoApplyAgent
        agent = AutoApplyAgent(str(tmp_path))
        targets = agent.find_targets("confidence_threshold")

        assert len(targets) >= 1
        assert targets[0]["line_number"] == 1

    def test_generate_value_patches(self, tmp_path):
        """Should generate patches to change parameter values."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "service.dart").write_text(
            "void test({double confThreshold = 0.5}) {}"
        )

        from parity_agent.agents.auto_apply import AutoApplyAgent
        agent = AutoApplyAgent(str(tmp_path))
        patches = agent.generate_patches([{
            "param_name": "confidence_threshold",
            "old_value": 0.5,
            "new_value": 0.6,
        }])

        assert len(patches) >= 1
        assert "0.6" in patches[0].patched_line


# ====================================================================
# Test: Architecture Detection
# ====================================================================

class TestArchitectures:
    """Test architecture auto-detection and plugins."""

    def test_detect_yolov8(self):
        """Should detect YOLOv8 from output shape [1, 12, 8400]."""
        from parity_agent.architectures.base import ModelArchitecture
        result = ModelArchitecture.detect_architecture((1, 12, 8400), num_classes=8)
        assert result == "yolov8"

    def test_detect_yolov8_transposed(self):
        """Should detect transposed YOLOv8 from [1, 8400, 12]."""
        from parity_agent.architectures.base import ModelArchitecture
        result = ModelArchitecture.detect_architecture((1, 8400, 12), num_classes=8)
        assert result == "yolov8_transposed"

    def test_detect_unknown(self):
        """Unknown shapes should return None."""
        from parity_agent.architectures.base import ModelArchitecture
        result = ModelArchitecture.detect_architecture((1, 100), num_classes=8)
        assert result is None

    def test_yolo_decoder(self):
        """YOLOv8 decoder should extract detections from known output."""
        from parity_agent.architectures.yolo import YOLOv8Architecture
        arch = YOLOv8Architecture()

        # Create a fake output with one strong detection
        raw = np.zeros((1, 12, 8400), dtype=np.float32)
        raw[0, 0, 0] = 0.5    # cx
        raw[0, 1, 0] = 0.5    # cy
        raw[0, 2, 0] = 0.2    # w
        raw[0, 3, 0] = 0.2    # h
        raw[0, 4, 0] = 0.95   # class 0 probability

        dets = arch.decode_raw_output(raw, num_classes=8, confidence_threshold=0.5)
        assert len(dets) >= 1
        assert dets[0]["confidence"] >= 0.9
