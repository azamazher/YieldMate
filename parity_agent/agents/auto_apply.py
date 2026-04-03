"""
Auto-Apply Agent — Automatically patches Dart source files with agent findings.

After the parity agent finds optimal parameters, this agent:
1. Scans the Flutter project for relevant Dart files
2. Locates the exact code patterns that need changing
3. Generates code patches (diffs)
4. Prompts the user with a preview and y/n confirmation
5. Applies the patches if approved

This closes the loop: trace → diff → fix → APPLY.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CodePatch:
    """A single code patch to apply to a Dart file."""
    file_path: str
    description: str
    original_line: str
    patched_line: str
    line_number: int
    param_name: str
    old_value: Any
    new_value: Any


class AutoApplyAgent:
    """
    Scans Flutter/Dart source code, generates patches from alignment findings,
    and applies them with user confirmation.
    """

    # Patterns to search for in Dart files
    DART_PATTERNS = {
        "confidence_threshold": [
            # Named parameter: confThreshold: 0.5
            r"(confThreshold\s*[:=]\s*)([\d.]+)",
            # Default parameter: double confThreshold = 0.5
            r"(double\s+confThreshold\s*=\s*)([\d.]+)",
            # Variable: confidenceThreshold = 0.5
            r"(confidenceThreshold\s*=\s*)([\d.]+)",
        ],
        "iou_threshold": [
            # Named parameter: iouThreshold: 0.45
            r"(iouThreshold\s*[:=]\s*)([\d.]+)",
            # Default parameter: double iouThreshold = 0.45
            r"(double\s+iouThreshold\s*=\s*)([\d.]+)",
        ],
        "apply_sigmoid": [
            # Sigmoid application pattern
            r"(.*1\.0\s*/\s*\(1\.0\s*\+\s*math\.exp\s*\(\s*-.*\)\s*\).*)",
            # Sigmoid function call
            r"(.*sigmoid.*)",
        ],
    }

    def __init__(self, project_root: str, lib_dir: str = "lib"):
        self.project_root = Path(project_root)
        self.lib_dir = self.project_root / lib_dir
        self.patches: List[CodePatch] = []

    def scan_dart_files(self) -> List[str]:
        """Find all Dart source files in the lib/ directory."""
        dart_files = []
        for f in self.lib_dir.rglob("*.dart"):
            # Skip generated files and backups
            if ".g.dart" in f.name or ".freezed.dart" in f.name or ".backup" in str(f):
                continue
            dart_files.append(str(f))
        return sorted(dart_files)

    def find_targets(self, param_name: str) -> List[Dict[str, Any]]:
        """
        Scan Dart files for occurrences of a specific parameter.

        Returns list of targets with file, line number, current value, and context.
        """
        targets = []
        patterns = self.DART_PATTERNS.get(param_name, [])
        if not patterns:
            return targets

        for dart_file in self.scan_dart_files():
            try:
                with open(dart_file, "r") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            targets.append({
                                "file": dart_file,
                                "line_number": line_num,
                                "line_content": line.rstrip(),
                                "match": match,
                                "pattern": pattern,
                            })
            except Exception as e:
                print(f"  Warning: Could not read {dart_file}: {e}")

        return targets

    def generate_patches(self, alignment_history: List[Dict[str, Any]]) -> List[CodePatch]:
        """
        Generate code patches from the agent's alignment history.

        Args:
            alignment_history: List of parameter changes from AlignmentAgent.
                Each entry has: param_name, old_value, new_value, improvement.

        Returns:
            List of CodePatch objects ready to apply.
        """
        self.patches = []

        for change in alignment_history:
            param_name = change["param_name"]
            old_value = change["old_value"]
            new_value = change["new_value"]

            print(f"\n[AutoApply] Scanning for: {param_name} ({old_value} → {new_value})")

            if param_name == "apply_sigmoid" and new_value is False:
                # Special handling: remove sigmoid transformation
                self._generate_sigmoid_patches()
            elif param_name == "apply_sigmoid" and new_value is True:
                # Special handling: ADD sigmoid transformation back
                self._generate_add_sigmoid_patches()
            else:
                # Standard value replacement
                targets = self.find_targets(param_name)
                for target in targets:
                    self._generate_value_patch(target, param_name, old_value, new_value)

        return self.patches

    def _generate_value_patch(self, target: Dict, param_name: str,
                               old_value: Any, new_value: Any):
        """Generate a patch that changes a numeric value."""
        line = target["line_content"]
        match = target["match"]

        # Replace the value in the matched pattern
        prefix = match.group(1)
        current_val = match.group(2)

        # Build new line
        new_line = line.replace(
            f"{prefix}{current_val}",
            f"{prefix}{new_value}"
        )

        # Add comment about the change
        if "//" not in new_line:
            new_line += f"  // Parity Agent: was {current_val}"

        self.patches.append(CodePatch(
            file_path=target["file"],
            description=f"Change {param_name}: {current_val} → {new_value}",
            original_line=line,
            patched_line=new_line,
            line_number=target["line_number"],
            param_name=param_name,
            old_value=current_val,
            new_value=new_value,
        ))

    def _generate_sigmoid_patches(self):
        """Generate patches to remove sigmoid double-application."""
        for dart_file in self.scan_dart_files():
            try:
                with open(dart_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Look for the sigmoid pattern block
                for i, line in enumerate(lines):
                    if "math.exp(-" in line and "1.0 /" in line:
                        # Found sigmoid line — replace with direct value usage
                        # Find the variable being assigned
                        # Pattern: final prob = 1.0 / (1.0 + math.exp(-clampedLogit));
                        sigmoid_match = re.search(
                            r"(\s*final\s+\w+\s*=\s*)1\.0\s*/\s*\(1\.0\s*\+\s*math\.exp\(\s*-(\w+)\s*\)\s*\);",
                            line
                        )
                        if sigmoid_match:
                            indent = sigmoid_match.group(1)
                            input_var = sigmoid_match.group(2)

                            # Also need to remove the clamping line above
                            clamp_line = None
                            if i > 0 and "clamp(" in lines[i - 1]:
                                clamp_line = i - 1

                            # Replace sigmoid with direct usage
                            original_var = input_var
                            # Find what the clamped var was derived from
                            if clamp_line is not None:
                                clamp_match = re.search(
                                    r"final\s+\w+\s*=\s*(\w+)\.clamp",
                                    lines[clamp_line]
                                )
                                if clamp_match:
                                    original_var = clamp_match.group(1)

                                self.patches.append(CodePatch(
                                    file_path=dart_file,
                                    description=f"Remove sigmoid clamping (line {clamp_line + 1})",
                                    original_line=lines[clamp_line],
                                    patched_line=f"        // REMOVED by Parity Agent: {lines[clamp_line].strip()}",
                                    line_number=clamp_line + 1,
                                    param_name="apply_sigmoid",
                                    old_value="sigmoid(clamped)",
                                    new_value="direct",
                                ))

                            new_line = f"{indent}{original_var};"
                            # Reconstruct: final prob = det[i];
                            prob_match = re.search(r"final\s+(\w+)", line)
                            if prob_match:
                                prob_var = prob_match.group(1)
                                new_line = f"        final {prob_var} = {original_var};"

                            self.patches.append(CodePatch(
                                file_path=dart_file,
                                description=f"Remove sigmoid: use raw probability instead (line {i + 1})",
                                original_line=line,
                                patched_line=new_line,
                                line_number=i + 1,
                                param_name="apply_sigmoid",
                                old_value="sigmoid(logit)",
                                new_value="raw probability",
                            ))
            except Exception as e:
                print(f"  Warning: Could not scan {dart_file}: {e}")

    def _generate_add_sigmoid_patches(self):
        """Generate patches to ADD sigmoid activation back to Dart code.

        Detects patterns where sigmoid was previously removed:
          - `final prob = logit;` (direct assignment without sigmoid)
          - `final prob = det[i];` (raw value without sigmoid)
          - Lines with '// REMOVED by Parity Agent' comments about sigmoid
        And restores the full sigmoid computation:
          final clampedLogit = logit.clamp(-20.0, 20.0);
          final prob = 1.0 / (1.0 + math.exp(-clampedLogit));
        """
        for dart_file in self.scan_dart_files():
            try:
                with open(dart_file, "r") as f:
                    lines = f.readlines()

                i = 0
                while i < len(lines):
                    line = lines[i].rstrip()

                    # Pattern 1: Find "REMOVED by Parity Agent" comment + direct prob assignment
                    if "REMOVED by Parity Agent" in line and "clamp" in line:
                        # This line is a commented-out clamp, next line should be `final prob = logit;`
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].rstrip()
                            # Match: `final prob = logit;` or `final prob = <variable>;`
                            prob_match = re.search(
                                r"(\s*)final\s+(\w+)\s*=\s*(\w+);",
                                next_line
                            )
                            if prob_match:
                                indent = prob_match.group(1)
                                prob_var = prob_match.group(2)
                                input_var = prob_match.group(3)

                                # Restore: clamp + sigmoid on two lines
                                restored_clamp = f"{indent}final clampedLogit = {input_var}.clamp(-20.0, 20.0);"
                                restored_sigmoid = f"{indent}final {prob_var} = 1.0 / (1.0 + math.exp(-clampedLogit));"

                                # Patch the comment line → restore clamping
                                self.patches.append(CodePatch(
                                    file_path=dart_file,
                                    description=f"Restore sigmoid clamping (line {i + 1})",
                                    original_line=line,
                                    patched_line=restored_clamp,
                                    line_number=i + 1,
                                    param_name="apply_sigmoid",
                                    old_value="removed",
                                    new_value="sigmoid(clamped)",
                                ))

                                # Patch the prob line → restore sigmoid
                                self.patches.append(CodePatch(
                                    file_path=dart_file,
                                    description=f"Restore sigmoid activation (line {i + 2})",
                                    original_line=next_line,
                                    patched_line=restored_sigmoid,
                                    line_number=i + 2,
                                    param_name="apply_sigmoid",
                                    old_value="raw logit",
                                    new_value="sigmoid(logit)",
                                ))
                                i += 2
                                continue

                    # Pattern 2: Find direct prob = logit without any preceding REMOVED comment
                    # Look for: `final prob = logit;` in a sigmoid context
                    if re.search(r"final\s+prob\s*=\s*logit\s*;", line):
                        indent_match = re.match(r"(\s*)", line)
                        indent = indent_match.group(1) if indent_match else "        "

                        restored_clamp = f"{indent}final clampedLogit = logit.clamp(-20.0, 20.0);"
                        restored_sigmoid = f"{indent}final prob = 1.0 / (1.0 + math.exp(-clampedLogit));"

                        # Check if previous line is the REMOVED comment — if so, replace both
                        if i > 0 and "REMOVED" in lines[i - 1]:
                            self.patches.append(CodePatch(
                                file_path=dart_file,
                                description=f"Restore sigmoid clamping (line {i})",
                                original_line=lines[i - 1].rstrip(),
                                patched_line=restored_clamp,
                                line_number=i,
                                param_name="apply_sigmoid",
                                old_value="removed",
                                new_value="sigmoid(clamped)",
                            ))

                        self.patches.append(CodePatch(
                            file_path=dart_file,
                            description=f"Restore sigmoid: apply sigmoid to logit (line {i + 1})",
                            original_line=line,
                            patched_line=restored_sigmoid,
                            line_number=i + 1,
                            param_name="apply_sigmoid",
                            old_value="raw logit",
                            new_value="sigmoid(logit)",
                        ))

                    i += 1

            except Exception as e:
                print(f"  Warning: Could not scan {dart_file}: {e}")

    def preview_patches(self) -> str:
        """Generate a human-readable preview of all patches."""
        if not self.patches:
            return "\n  No patches to apply.\n"

        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"  AUTO-APPLY: {len(self.patches)} code patches found")
        lines.append(f"{'=' * 60}\n")

        # Group by file
        by_file: Dict[str, List[CodePatch]] = {}
        for patch in self.patches:
            rel_path = os.path.relpath(patch.file_path, self.project_root)
            by_file.setdefault(rel_path, []).append(patch)

        for file_path, patches in by_file.items():
            lines.append(f"  📄 {file_path}")
            for patch in patches:
                lines.append(f"    Line {patch.line_number}: {patch.description}")
                lines.append(f"    - {patch.original_line.strip()}")
                lines.append(f"    + {patch.patched_line.strip()}")
                lines.append("")

        lines.append(f"{'─' * 60}")
        return "\n".join(lines)

    def prompt_and_apply(self, auto_yes: bool = False) -> bool:
        """
        Show patches preview and prompt user for confirmation.

        Args:
            auto_yes: If True, skip the prompt and apply automatically.

        Returns:
            True if patches were applied, False otherwise.
        """
        preview = self.preview_patches()
        print(preview)

        if not self.patches:
            return False

        if auto_yes:
            print("  Auto-apply mode: applying all patches...")
            apply = True
        else:
            response = input("  Apply these changes? [y/n]: ").strip().lower()
            apply = response in ("y", "yes")

        if apply:
            return self.apply_patches()
        else:
            print("  ❌ Changes not applied.")
            return False

    def apply_patches(self) -> bool:
        """Apply all patches to the Dart source files."""
        # Group patches by file and sort by line number (descending)
        # to avoid line number shifts when editing
        by_file: Dict[str, List[CodePatch]] = {}
        for patch in self.patches:
            by_file.setdefault(patch.file_path, []).append(patch)

        applied = 0
        for file_path, patches in by_file.items():
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()

                # Sort patches by line number descending (apply from bottom up)
                patches.sort(key=lambda p: p.line_number, reverse=True)

                for patch in patches:
                    idx = patch.line_number - 1
                    if 0 <= idx < len(lines):
                        lines[idx] = patch.patched_line + "\n"
                        applied += 1

                with open(file_path, "w") as f:
                    f.writelines(lines)

                rel_path = os.path.relpath(file_path, self.project_root)
                print(f"  ✅ Patched {rel_path} ({len(patches)} changes)")

            except Exception as e:
                print(f"  ❌ Failed to patch {file_path}: {e}")

        print(f"\n  Applied {applied}/{len(self.patches)} patches.")
        return applied > 0

    def load_alignment_history(self, results_dir: str) -> List[Dict[str, Any]]:
        """Load the alignment history from the agent results."""
        history_path = Path(results_dir) / "alignment_history.json"
        if not history_path.exists():
            print(f"  No alignment history found at {history_path}")
            return []

        with open(history_path, "r") as f:
            history = json.load(f)

        # Convert to the format we need
        changes = []
        for entry in history:
            changes.append({
                "param_name": entry.get("parameter", entry.get("param_name", "")),
                "old_value": entry.get("old_value"),
                "new_value": entry.get("new_value"),
                "improvement": entry.get("improvement", 0),
            })

        return changes
