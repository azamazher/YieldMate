"""
Trace Storage — Save and load Golden Traces to/from disk.

Traces are stored as:
  - JSON file (metadata + detection lists)
  - NPZ sidecar file (numpy tensors: input_tensor, raw_output)

This separation keeps the JSON human-readable while preserving
full numerical fidelity for tensor data.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Optional

from .schema import PipelineTrace, GoldenTrace, Detection


class TraceStorage:
    """Persist and retrieve Golden Traces."""

    def __init__(self, base_dir: str = "traces"):
        """
        Args:
            base_dir: Root directory for trace storage.
        """
        self.base_dir = Path(base_dir)
        self.online_dir = self.base_dir / "online"
        self.offline_dir = self.base_dir / "offline"
        self.paired_dir = self.base_dir / "paired"

        # Create directories
        for d in [self.online_dir, self.offline_dir, self.paired_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_trace(self, trace: PipelineTrace) -> str:
        """
        Save a single pipeline trace to disk.

        Returns:
            Path to the saved JSON file.
        """
        target_dir = self.online_dir if trace.pipeline == "online" else self.offline_dir
        base_name = f"{trace.image_id}_{trace.pipeline}"

        # Save JSON (metadata + detections)
        json_path = target_dir / f"{base_name}.json"
        json_data = trace.to_dict()
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=2)

        # Save tensors as NPZ sidecar
        tensors = {}
        if trace.input_tensor is not None:
            tensors["input_tensor"] = trace.input_tensor
        if trace.raw_output is not None:
            tensors["raw_output"] = trace.raw_output

        if tensors:
            npz_path = target_dir / f"{base_name}.npz"
            np.savez_compressed(str(npz_path), **tensors)

        return str(json_path)

    def load_trace(self, json_path: str) -> PipelineTrace:
        """Load a single pipeline trace from disk."""
        json_path = Path(json_path)

        with open(json_path, "r") as f:
            data = json.load(f)

        # Load tensors from NPZ sidecar if it exists
        npz_path = json_path.with_suffix(".npz")
        tensors = {}
        if npz_path.exists():
            npz_data = np.load(str(npz_path))
            for key in npz_data.files:
                tensors[key] = npz_data[key]

        return PipelineTrace.from_dict(data, tensors)

    def save_golden_trace(self, golden: GoldenTrace) -> str:
        """Save a paired golden trace."""
        json_path = self.paired_dir / f"{golden.image_id}.json"

        # Save individual traces first
        if golden.online:
            self.save_trace(golden.online)
        if golden.offline:
            self.save_trace(golden.offline)

        # Save the paired index
        with open(json_path, "w") as f:
            json.dump(golden.to_dict(), f, indent=2)

        return str(json_path)

    def load_golden_trace(self, image_id: str) -> Optional[GoldenTrace]:
        """Load a paired golden trace by image_id."""
        # Try to load from paired index
        paired_path = self.paired_dir / f"{image_id}.json"
        if paired_path.exists():
            with open(paired_path, "r") as f:
                data = json.load(f)

            golden = GoldenTrace(
                image_id=data["image_id"],
                image_path=data["image_path"],
            )

            # Load individual traces
            online_json = self.online_dir / f"{image_id}_online.json"
            offline_json = self.offline_dir / f"{image_id}_offline.json"

            if online_json.exists():
                golden.online = self.load_trace(str(online_json))
            if offline_json.exists():
                golden.offline = self.load_trace(str(offline_json))

            return golden

        # Fallback: try loading traces directly
        golden = GoldenTrace(image_id=image_id, image_path="")

        online_json = self.online_dir / f"{image_id}_online.json"
        offline_json = self.offline_dir / f"{image_id}_offline.json"

        if online_json.exists():
            golden.online = self.load_trace(str(online_json))
        if offline_json.exists():
            golden.offline = self.load_trace(str(offline_json))

        if golden.online or golden.offline:
            return golden
        return None

    def list_image_ids(self) -> List[str]:
        """List all image IDs that have at least one trace."""
        ids = set()
        for d in [self.online_dir, self.offline_dir]:
            for f in d.glob("*.json"):
                # Remove _online or _offline suffix
                name = f.stem
                for suffix in ["_online", "_offline"]:
                    if name.endswith(suffix):
                        name = name[: -len(suffix)]
                ids.add(name)
        return sorted(ids)
