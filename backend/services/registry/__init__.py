"""
Unified Multi-Language Technology Registry System

Provides adapters for fetching package metadata from multiple ecosystems:
- Python (PyPI)
- Node.js (npm)
- Go (pkg.go.dev)
- Rust (crates.io)
"""

from .base_registry import BaseRegistry
from .pypi_registry import PyPIRegistry
from .npm_registry import NPMRegistry
from .go_registry import GoRegistry
from .crates_registry import CratesRegistry
from .unified_registry import UnifiedRegistry

__all__ = [
    'BaseRegistry',
    'PyPIRegistry',
    'NPMRegistry',
    'GoRegistry',
    'CratesRegistry',
    'UnifiedRegistry'
]
