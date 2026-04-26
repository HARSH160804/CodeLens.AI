"""
Deterministic code complexity analyzer.
No LLM usage — pure static analysis via regex and line inspection.
"""
import re
from typing import Dict, Any


# Regex patterns for common constructs across Python, JS/TS, and Java-like languages
_FUNCTION_PATTERNS = [
    re.compile(r'^\s*def\s+\w+'),                          # Python
    re.compile(r'^\s*(export\s+)?(async\s+)?function\s+'),  # JS/TS function declaration
    re.compile(r'^\s*(const|let|var)\s+\w+\s*=\s*(async\s+)?\(.*\)\s*=>'),  # JS arrow fn
    re.compile(r'^\s*(public|private|protected|static|\s)*\s+\w+\s+\w+\s*\('),  # Java/C#
]

_CLASS_PATTERNS = [
    re.compile(r'^\s*class\s+\w+'),                         # Python / JS / TS / Java
]

_ASYNC_PATTERNS = [
    re.compile(r'^\s*async\s+(def|function)\s+'),           # Python async def / JS async function
    re.compile(r'^\s*(const|let|var)\s+\w+\s*=\s*async\s+'),  # JS async arrow
]

_TRY_PATTERNS = [
    re.compile(r'^\s*try\s*[:{]'),                          # Python try: / JS try {
]

_CATCH_PATTERNS = [
    re.compile(r'^\s*(except|catch)\s*[\s(:]'),             # Python except / JS catch
]

# Indentation thresholds — "deep nesting" is > 2 logical levels
_INDENT_UNIT = 4  # spaces per level (also handles tabs → 4 spaces)
_DEEP_NESTING_THRESHOLD = 3  # level 3+ counts as deep


def _matches_any(line: str, patterns: list) -> bool:
    """Return True if the line matches any of the given compiled patterns."""
    return any(p.search(line) for p in patterns)


def _indentation_level(line: str) -> int:
    """Return the logical indentation level of a line."""
    expanded = line.replace('\t', ' ' * _INDENT_UNIT)
    stripped = expanded.lstrip(' ')
    if not stripped:
        return 0
    spaces = len(expanded) - len(stripped)
    return spaces // _INDENT_UNIT


def compute_complexity(code_content: str) -> Dict[str, Any]:
    """
    Compute deterministic complexity metrics for a code string.

    Args:
        code_content: Raw source code as a string.

    Returns:
        {
            "score": int (1-10),
            "metrics": {
                "total_lines": int,
                "function_count": int,
                "class_count": int,
                "async_count": int,
                "nesting_estimate": int,
                "try_catch_count": int
            }
        }
    """
    lines = code_content.split('\n')
    total_lines = len(lines)

    function_count = 0
    class_count = 0
    async_count = 0
    nesting_estimate = 0
    try_count = 0
    catch_count = 0

    for line in lines:
        if _matches_any(line, _FUNCTION_PATTERNS):
            function_count += 1
        if _matches_any(line, _CLASS_PATTERNS):
            class_count += 1
        if _matches_any(line, _ASYNC_PATTERNS):
            async_count += 1
        if _matches_any(line, _TRY_PATTERNS):
            try_count += 1
        if _matches_any(line, _CATCH_PATTERNS):
            catch_count += 1

        # Count lines that exceed the deep nesting threshold
        if line.strip() and _indentation_level(line) >= _DEEP_NESTING_THRESHOLD:
            nesting_estimate += 1

    try_catch_count = try_count + catch_count

    # ── Weighted score formula (1-10) ──────────────────────────────
    #
    # Each dimension contributes a partial score that is clamped
    # before being combined.  The weights reflect relative impact on
    # "how hard is this file to understand at a glance".
    #
    # Dimension        | Weight | Rationale
    # -----------------+--------+------------------------------------------
    # Lines of code    |  0.20  | Longer files are harder to navigate
    # Function count   |  0.20  | More functions = more surface area
    # Class count      |  0.10  | OOP complexity
    # Async count      |  0.10  | Concurrency adds cognitive load
    # Deep nesting     |  0.25  | Hardest to follow; highest weight
    # Try/catch blocks |  0.15  | Error handling paths add branches

    def _norm(value: float, low: float, high: float) -> float:
        """Normalize value to 0-1 range between low and high."""
        if high <= low:
            return 0.0
        return max(0.0, min(1.0, (value - low) / (high - low)))

    raw = (
        0.20 * _norm(total_lines, 0, 500) +
        0.20 * _norm(function_count, 0, 30) +
        0.10 * _norm(class_count, 0, 10) +
        0.10 * _norm(async_count, 0, 10) +
        0.25 * _norm(nesting_estimate, 0, 50) +
        0.15 * _norm(try_catch_count, 0, 15)
    )

    # Map 0-1 raw score to 1-10 integer
    score = max(1, min(10, round(raw * 9 + 1)))

    return {
        'score': score,
        'metrics': {
            'total_lines': total_lines,
            'function_count': function_count,
            'class_count': class_count,
            'async_count': async_count,
            'nesting_estimate': nesting_estimate,
            'try_catch_count': try_catch_count,
        }
    }
