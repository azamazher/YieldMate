"""
Base Architecture — Abstract interface for model architecture plugins.

Each architecture plugin must implement this interface to support
different detection model families (YOLO, SSD, EfficientDet, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np


class ModelArchitecture(ABC):
    """
    Abstract base class for model architecture decoders.

    Each subclass handles the specific output tensor format and
    post-processing logic for a model family.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the architecture (e.g., 'YOLOv8')."""
        pass

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Description of expected output tensor format."""
        pass

    @abstractmethod
    def decode_raw_output(
        self,
        raw_output: np.ndarray,
        num_classes: int,
        confidence_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Decode raw model output tensor into detection dictionaries.

        Args:
            raw_output: Raw output from TFLite inference.
            num_classes: Number of object classes.
            confidence_threshold: Minimum confidence to keep.

        Returns:
            List of dicts with keys: bbox, confidence, class_index.
        """
        pass

    @abstractmethod
    def get_search_space(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the architecture-specific parameter search space.

        Returns:
            Dict of parameter_name → {type, values/min/max, default, description}
        """
        pass

    @abstractmethod
    def get_hypothesis_rules(self) -> List[Dict[str, Any]]:
        """
        Get architecture-specific hypothesis rules.

        Returns:
            List of hypothesis rule dicts.
        """
        pass

    def preprocess(
        self,
        image: np.ndarray,
        input_size: int = 640,
        config: Dict[str, Any] = None,
    ) -> np.ndarray:
        """
        Preprocess an image for this architecture.

        Default implementation: resize + normalize.
        Override for architecture-specific preprocessing.
        """
        from PIL import Image

        config = config or {}
        normalization = config.get("normalization", "divide_255")

        # Resize
        if image.shape[:2] != (input_size, input_size):
            pil_img = Image.fromarray(image)
            pil_img = pil_img.resize((input_size, input_size), Image.BILINEAR)
            image = np.array(pil_img)

        # Normalize
        tensor = image.astype(np.float32)
        if normalization == "divide_255":
            tensor /= 255.0
        elif normalization == "neg1_pos1":
            tensor = tensor / 127.5 - 1.0

        # Add batch dimension
        return np.expand_dims(tensor, axis=0)

    @staticmethod
    def detect_architecture(
        output_shape: Tuple[int, ...],
        num_classes: int,
    ) -> Optional[str]:
        """
        Auto-detect model architecture from output tensor shape.

        Args:
            output_shape: Shape of the model's output tensor.
            num_classes: Expected number of classes.

        Returns:
            Architecture name or None if unknown.
        """
        if len(output_shape) == 3:
            _, dim1, dim2 = output_shape
            # YOLOv8: [1, num_classes+4, num_anchors] e.g. [1, 12, 8400]
            if dim1 == num_classes + 4 and dim2 > 100:
                return "yolov8"
            if dim2 == num_classes + 4 and dim1 > 100:
                return "yolov8_transposed"
            # SSD: [1, num_anchors, num_classes+4] or [1, num_anchors, 4] + [1, num_anchors, num_classes]
            if dim2 == num_classes + 4:
                return "ssd"
        elif len(output_shape) == 2:
            _, dim1 = output_shape
            if dim1 == num_classes:
                return "classification"

        return None
