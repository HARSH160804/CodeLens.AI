"""
npm Registry Adapter

Fetches package metadata from npm (Node Package Manager).
"""

import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from .base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class NPMRegistry(BaseRegistry):
    """Adapter for npm (Node Package Manager)."""
    
    BASE_URL = "https://registry.npmjs.org"
    TIMEOUT = 5  # seconds
    
    def fetch_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata from npm.
        
        Args:
            package_name: Name of the npm package
            
        Returns:
            Normalized metadata dict or None if fetch fails
        """
        if requests is None:
            logger.warning("requests library not available, cannot fetch npm metadata")
            return None
        
        try:
            url = f"{self.BASE_URL}/{package_name}"
            response = requests.get(url, timeout=self.TIMEOUT)
            
            if response.status_code != 200:
                logger.debug(f"npm returned {response.status_code} for {package_name}")
                return None
            
            data = response.json()
            
            # Get latest version metadata
            latest_version = data.get('dist-tags', {}).get('latest', '')
            version_data = data.get('versions', {}).get(latest_version, {})
            
            # Extract metadata (prefer latest version, fallback to root)
            description = version_data.get('description', '') or data.get('description', '')
            keywords = version_data.get('keywords', []) or data.get('keywords', [])
            homepage = version_data.get('homepage', '') or data.get('homepage', '')
            license_info = self._extract_license(version_data) or self._extract_license(data)
            
            return self.normalize_metadata(
                package_name=package_name,
                ecosystem="node",
                description=description,
                keywords=keywords if isinstance(keywords, list) else [],
                license_info=license_info,
                homepage=homepage
            )
            
        except requests.RequestException as e:
            logger.debug(f"npm request failed for {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching npm metadata for {package_name}: {e}")
            return None
    
    def _extract_license(self, data: dict) -> str:
        """
        Extract license information from npm data.
        
        Args:
            data: npm package data
            
        Returns:
            License string
        """
        license_info = data.get('license', '')
        
        # Handle different license formats
        if isinstance(license_info, dict):
            return license_info.get('type', '')
        elif isinstance(license_info, str):
            return license_info
        elif isinstance(license_info, list) and len(license_info) > 0:
            # Multiple licenses
            if isinstance(license_info[0], dict):
                return license_info[0].get('type', '')
            return str(license_info[0])
        
        return ''
