"""
Unified Registry

Provides a unified interface for fetching package metadata from multiple ecosystems.
Includes ecosystem detection and caching.
"""

import logging
from typing import Dict, Any, Optional, List
from functools import lru_cache

from .base_registry import BaseRegistry
from .pypi_registry import PyPIRegistry
from .npm_registry import NPMRegistry
from .go_registry import GoRegistry
from .crates_registry import CratesRegistry

logger = logging.getLogger(__name__)


class UnifiedRegistry:
    """
    Unified registry for fetching package metadata from multiple ecosystems.
    
    Supports:
    - Python (PyPI)
    - Node.js (npm)
    - Go (pkg.go.dev)
    - Rust (crates.io)
    """
    
    def __init__(self):
        """Initialize registry adapters."""
        self.registries = {
            'python': PyPIRegistry(),
            'node': NPMRegistry(),
            'go': GoRegistry(),
            'rust': CratesRegistry()
        }
    
    def detect_ecosystem(self, repo_files: List[str]) -> str:
        """
        Detect ecosystem from repository files.
        
        Args:
            repo_files: List of file paths in repository
            
        Returns:
            Ecosystem identifier: 'python', 'node', 'go', 'rust', or 'unknown'
        """
        # Convert to lowercase for case-insensitive matching
        files_lower = [f.lower() for f in repo_files]
        
        # Check for ecosystem-specific files
        # Priority order: most specific first
        
        # Node.js
        if 'package.json' in files_lower:
            return 'node'
        
        # Python
        if 'requirements.txt' in files_lower or 'pipfile' in files_lower or 'setup.py' in files_lower:
            return 'python'
        
        # Go
        if 'go.mod' in files_lower or 'go.sum' in files_lower:
            return 'go'
        
        # Rust
        if 'cargo.toml' in files_lower or 'cargo.lock' in files_lower:
            return 'rust'
        
        # Check for file extensions as fallback
        extensions = set()
        for file_path in files_lower:
            if '.' in file_path:
                ext = file_path.split('.')[-1]
                extensions.add(ext)
        
        # Count file extensions
        if 'py' in extensions:
            return 'python'
        elif 'js' in extensions or 'ts' in extensions or 'jsx' in extensions or 'tsx' in extensions:
            return 'node'
        elif 'go' in extensions:
            return 'go'
        elif 'rs' in extensions:
            return 'rust'
        
        return 'unknown'
    
    def get_registry(self, ecosystem: str) -> Optional[BaseRegistry]:
        """
        Get registry adapter for ecosystem.
        
        Args:
            ecosystem: Ecosystem identifier
            
        Returns:
            Registry adapter or None if ecosystem not supported
        """
        return self.registries.get(ecosystem)
    
    @lru_cache(maxsize=1000)
    def fetch(self, ecosystem: str, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata with caching.
        
        Uses LRU cache to avoid repeated API calls within the same Lambda execution.
        Cache key: ecosystem:package_name
        Cache size: 1000 entries
        Cache lifetime: Lambda warm container lifetime (~15 minutes)
        
        Args:
            ecosystem: Ecosystem identifier ('python', 'node', 'go', 'rust')
            package_name: Name of the package
            
        Returns:
            Normalized metadata dict or None if fetch fails
        """
        registry = self.get_registry(ecosystem)
        
        if registry is None:
            logger.warning(f"No registry adapter for ecosystem: {ecosystem}")
            return None
        
        try:
            metadata = registry.fetch_metadata(package_name)
            
            if metadata:
                logger.debug(f"Fetched metadata for {ecosystem}:{package_name}")
            else:
                logger.debug(f"No metadata found for {ecosystem}:{package_name}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching metadata for {ecosystem}:{package_name}: {e}")
            return None
    
    def fetch_batch(
        self,
        ecosystem: str,
        package_names: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Fetch metadata for multiple packages.
        
        Args:
            ecosystem: Ecosystem identifier
            package_names: List of package names
            
        Returns:
            Dictionary mapping package names to metadata (or None if fetch failed)
        """
        results = {}
        
        for package_name in package_names:
            results[package_name] = self.fetch(ecosystem, package_name)
        
        return results
    
    def clear_cache(self):
        """Clear the LRU cache."""
        self.fetch.cache_clear()
        logger.info("Cleared unified registry cache")
