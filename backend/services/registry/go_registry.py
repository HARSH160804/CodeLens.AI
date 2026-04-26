"""
Go Registry Adapter

Fetches package metadata from pkg.go.dev (best effort).
"""

import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from .base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class GoRegistry(BaseRegistry):
    """Adapter for Go packages (pkg.go.dev)."""
    
    # Note: pkg.go.dev doesn't have a public JSON API
    # This is a best-effort implementation
    TIMEOUT = 5  # seconds
    
    def fetch_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata for Go packages.
        
        Note: pkg.go.dev doesn't have a public JSON API.
        This implementation provides basic fallback metadata.
        
        Args:
            package_name: Name of the Go package (e.g., github.com/user/repo)
            
        Returns:
            Normalized metadata dict with basic information
        """
        # For now, return basic metadata
        # In the future, could scrape pkg.go.dev or use go.mod parsing
        
        logger.debug(f"Go registry: providing fallback metadata for {package_name}")
        
        # Extract repository info from package path
        description = f"Go package: {package_name}"
        homepage = ""
        keywords = ["go", "golang"]
        
        # Try to extract homepage from common patterns
        if package_name.startswith("github.com/"):
            homepage = f"https://{package_name}"
        elif package_name.startswith("gitlab.com/"):
            homepage = f"https://{package_name}"
        
        return self.normalize_metadata(
            package_name=package_name,
            ecosystem="go",
            description=description,
            keywords=keywords,
            license_info="",  # Would need to fetch from repository
            homepage=homepage
        )
