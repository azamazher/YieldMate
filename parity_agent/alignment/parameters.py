"""
Alignment Parameters — Define the search space for pipeline configuration.

These are the parameters the agent is allowed to modify on the offline pipeline.
The model weights are FROZEN — the agent only touches deployment-level config.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import yaml
import copy


# Default search space for each tunable parameter
PARAMETER_SPACE = {
    "normalization": {
        "type": "categorical",
        "values": ["divide_255", "neg1_pos1", "none"],
        "default": "divide_255",
        "description": "Input tensor normalization method",
    },
    "resize_method": {
        "type": "categorical",
        "values": ["bilinear", "nearest", "area", "lanczos"],
        "default": "bilinear",
        "description": "Image resize interpolation",
    },
    "channel_order": {
        "type": "categorical",
        "values": ["rgb", "bgr"],
        "default": "rgb",
        "description": "Color channel order",
    },
    "confidence_threshold": {
        "type": "continuous",
        "min": 0.1,
        "max": 0.9,
        "step": 0.1,
        "default": 0.5,
        "description": "Detection confidence threshold",
    },
    "iou_threshold": {
        "type": "continuous",
        "min": 0.2,
        "max": 0.8,
        "step": 0.05,
        "default": 0.45,
        "description": "NMS IoU threshold",
    },
    "apply_sigmoid": {
        "type": "categorical",
        "values": [True, False],
        "default": True,
        "description": "Apply sigmoid to raw class logits",
    },
    "letterbox_padding": {
        "type": "categorical",
        "values": [True, False],
        "default": True,
        "description": "Use letterbox padding vs stretch resize",
    },
    "padding_color": {
        "type": "categorical",
        "values": [[114, 114, 114], [0, 0, 0], [128, 128, 128]],
        "default": [114, 114, 114],
        "description": "Letterbox padding fill color",
    },
}


def get_default_config() -> Dict[str, Any]:
    """Get the default offline pipeline configuration."""
    return {k: v["default"] for k, v in PARAMETER_SPACE.items()}


def get_parameter_variants(param_name: str) -> List[Any]:
    """Get all possible values for a parameter."""
    space = PARAMETER_SPACE.get(param_name)
    if not space:
        return []

    if space["type"] == "categorical":
        return space["values"]
    elif space["type"] == "continuous":
        import numpy as np
        return list(np.arange(space["min"], space["max"] + space["step"], space["step"]))
    return []


def generate_ablation_configs(
    base_config: Dict[str, Any],
    param_name: str,
) -> List[Dict[str, Any]]:
    """
    Generate configs for single-parameter ablation.
    
    Changes only one parameter at a time, keeping all others fixed.
    This is the controlled experiment approach.
    
    Args:
        base_config: Current offline config.
        param_name: Which parameter to vary.
    
    Returns:
        List of config dicts, each with one parameter changed.
    """
    configs = []
    variants = get_parameter_variants(param_name)

    for value in variants:
        if value == base_config.get(param_name):
            continue  # Skip current value
        new_config = copy.deepcopy(base_config)
        new_config[param_name] = value
        configs.append(new_config)

    return configs


# ============================================================================
# LINKED PARAMETERS — Co-dependent params that must be tested together
# ============================================================================

LINKED_PARAMS = {
    # When sigmoid is toggled, the confidence threshold scale changes entirely.
    # Without sigmoid: raw logits (0–80+), so threshold 0.6 means nothing.
    # With sigmoid: probabilities (0–1), so threshold 0.6 is meaningful.
    "apply_sigmoid": ["confidence_threshold"],
    "confidence_threshold": ["apply_sigmoid"],
}


def get_linked_params(param_name: str) -> List[str]:
    """Get parameters that are co-dependent with the given parameter."""
    return LINKED_PARAMS.get(param_name, [])


def generate_combo_ablation_configs(
    base_config: Dict[str, Any],
    param_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Generate configs for multi-parameter combo ablation.

    Tests ALL combinations of the given parameters (Cartesian product).
    This handles co-dependent params that must change together.

    Example: param_names = ["apply_sigmoid", "confidence_threshold"]
    Produces configs like:
        {apply_sigmoid: True,  confidence_threshold: 0.1}
        {apply_sigmoid: True,  confidence_threshold: 0.2}
        ...
        {apply_sigmoid: False, confidence_threshold: 0.1}
        ...

    Args:
        base_config: Current offline config.
        param_names: List of parameters to vary together.

    Returns:
        List of config dicts with all parameter combinations.
    """
    from itertools import product as itertools_product

    # Deduplicate param names
    param_names = list(dict.fromkeys(param_names))

    # Get all variant values for each param
    all_variants = []
    for param in param_names:
        variants = get_parameter_variants(param)
        all_variants.append([(param, v) for v in variants])

    # Generate Cartesian product of all param/value pairs
    configs = []
    for combo in itertools_product(*all_variants):
        new_config = copy.deepcopy(base_config)
        is_baseline = True
        for param, value in combo:
            new_config[param] = value
            if value != base_config.get(param):
                is_baseline = False

        # Skip if this is exactly the current config (baseline)
        if is_baseline:
            continue

        configs.append(new_config)

    return configs

