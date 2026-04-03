"""
Color utilities for terminal output.

Provides simple helper functions for consistent colored output
across the entire Parity Agent CLI. Uses raw ANSI escape codes 
to ensure colors print even when piped.
"""

# Raw ANSI escape codes
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE_BOLD = "\033[1;34m"
BOLD = "\033[1m"
DIM = "\033[2m"

# ──────────────────────────────────────────────────────────
# Color helper functions
# ──────────────────────────────────────────────────────────

def success(text: str) -> str:
    """Green — success, loaded, pass, improvements."""
    return f"{GREEN}{text}{RESET}"

def error(text: str) -> str:
    """Red — errors, failures, critical issues."""
    return f"{RED}{text}{RESET}"

def warning(text: str) -> str:
    """Yellow — warnings, patience, no improvement."""
    return f"{YELLOW}{text}{RESET}"

def info(text: str) -> str:
    """Cyan — step labels, progress indicators."""
    return f"{CYAN}{text}{RESET}"

def highlight(text: str) -> str:
    """Magenta — important values, metrics."""
    return f"{MAGENTA}{text}{RESET}"

def banner(text: str) -> str:
    """Blue + Bold — section banners, headers."""
    return f"{BLUE_BOLD}{text}{RESET}"

def bold(text: str) -> str:
    """Bold white — emphasis."""
    return f"{BOLD}{text}{RESET}"

def dim(text: str) -> str:
    """Dim — less important details."""
    return f"{DIM}{text}{RESET}"
