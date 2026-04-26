"""
Base Registry Abstract Class

Defines the interface for all package registry adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseRegistry(ABC):
    """Abstract base class for package registry adapters."""
    
    @abstractmethod
    def fetch_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata from registry.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Normalized metadata dict or None if fetch fails
            
        Expected return format:
        {
            "name": str,
            "ecosystem": str,
            "description": str,
            "keywords": List[str],
            "license": str,
            "homepage": str
        }
        """
        raise NotImplementedError("Subclasses must implement fetch_metadata()")
    
    def normalize_metadata(
        self,
        package_name: str,
        ecosystem: str,
        description: str = "",
        keywords: list = None,
        license_info: str = "",
        homepage: str = ""
    ) -> Dict[str, Any]:
        """
        Normalize metadata to standard format.
        
        Args:
            package_name: Package name
            ecosystem: Ecosystem identifier
            description: Package description
            keywords: List of keywords
            license_info: License string
            homepage: Homepage URL
            
        Returns:
            Normalized metadata dict
        """
        return {
            "name": package_name,
            "ecosystem": ecosystem,
            "description": description or "",
            "keywords": keywords or [],
            "license": license_info or "",
            "homepage": homepage or ""
        }
