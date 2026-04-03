"""
Golden Trace Schema — Data models for pipeline instrumentation.

A PipelineTrace captures the complete internal state of an inference pipeline
at four checkpoints: input_tensor → raw_output → decoded_boxes → nms_boxes.

This is the scientific instrumentation that makes the agent possible.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime


def _sanitize_for_json(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj


@dataclass
class Detection:
    """A single detection (bounding box + class + confidence)."""
    class_name: str
    class_index: int
    confidence: float
    bbox: List[float]           # [x1, y1, x2, y2] normalized 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": str(self.class_name),
            "class_index": int(self.class_index),
            "confidence": float(self.confidence),
            "bbox": [float(x) for x in self.bbox],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Detection":
        return cls(
            class_name=d["class_name"],
            class_index=d["class_index"],
            confidence=d["confidence"],
            bbox=d["bbox"],
        )


@dataclass
class PipelineTrace:
    """
    Complete trace of one image through one pipeline.
    
    Captures tensor data at each checkpoint:
        1. input_tensor   — preprocessed tensor fed to the model
        2. raw_output     — raw model output (before decode/sigmoid)
        3. decoded_boxes  — decoded detections (after sigmoid, before NMS)
        4. nms_boxes      — final detections (after NMS)
    """
    image_id: str
    pipeline: str                       # "online" or "offline"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Checkpoint 1: Preprocessed input tensor
    input_tensor: Optional[np.ndarray] = None       # shape: [1, H, W, 3]

    # Checkpoint 2: Raw model output (logits)
    raw_output: Optional[np.ndarray] = None          # shape: varies by model

    # Checkpoint 3: Decoded boxes (before NMS)
    decoded_boxes: List[Detection] = field(default_factory=list)

    # Checkpoint 4: Final boxes (after NMS)
    nms_boxes: List[Detection] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict (tensors stored separately)."""
        return {
            "image_id": self.image_id,
            "pipeline": self.pipeline,
            "timestamp": self.timestamp,
            "input_tensor_shape": [int(x) for x in self.input_tensor.shape] if self.input_tensor is not None else None,
            "raw_output_shape": [int(x) for x in self.raw_output.shape] if self.raw_output is not None else None,
            "decoded_boxes": [d.to_dict() for d in self.decoded_boxes],
            "nms_boxes": [d.to_dict() for d in self.nms_boxes],
            "metadata": _sanitize_for_json(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], tensors: Optional[Dict[str, np.ndarray]] = None) -> "PipelineTrace":
        """Deserialize from dict + optional tensor data."""
        trace = cls(
            image_id=d["image_id"],
            pipeline=d["pipeline"],
            timestamp=d.get("timestamp", ""),
            decoded_boxes=[Detection.from_dict(det) for det in d.get("decoded_boxes", [])],
            nms_boxes=[Detection.from_dict(det) for det in d.get("nms_boxes", [])],
            metadata=d.get("metadata", {}),
        )
        if tensors:
            trace.input_tensor = tensors.get("input_tensor")
            trace.raw_output = tensors.get("raw_output")
        return trace


@dataclass
class GoldenTrace:
    """
    A paired trace — online + offline for the same image.
    
    This is the fundamental unit of comparison for the Diff Engine.
    """
    image_id: str
    image_path: str
    online: Optional[PipelineTrace] = None
    offline: Optional[PipelineTrace] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "online": self.online.to_dict() if self.online else None,
            "offline": self.offline.to_dict() if self.offline else None,
        }

    @property
    def is_complete(self) -> bool:
        """True if both online and offline traces are present."""
        return self.online is not None and self.offline is not None
