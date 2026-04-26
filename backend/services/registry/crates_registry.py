"""
Crates.io Registry Adapter

Fetches package metadata from crates.io (Rust packages).
"""

import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from .base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class CratesRegistry(BaseRegistry):
    """Adapter for crates.io (Rust packages)."""
    
    BASE_URL = "https://crates.io/api/v1/crates"
    TIMEOUT = 5  # seconds
    
    def fetch_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata from crates.io.
        
        Args:
            package_name: Name of the Rust crate
            
        Returns:
            Normalized metadata dict or None if fetch fails
        """
        if requests is None:
            logger.warning("requests library not available, cannot fetch crates.io metadata")
            return None
        
        try:
            url = f"{self.BASE_URL}/{package_name}"
            headers = {
                'User-Agent': 'BloomWay-Architecture-Analyzer/1.0'
            }
            response = requests.get(url, headers=headers, timeout=self.TIMEOUT)
            
            if response.status_code != 200:
                logger.debug(f"crates.io returned {response.status_code} for {package_name}")
                return None
            
            data = response.json()
            crate = data.get('crate', {})
            
            # Extract metadata
            description = crate.get('description', '')
            homepage = crate.get('homepage', '') or crate.get('repository', '')
            keywords = crate.get('keywords', [])
            
            # Get license from versions
            versions = data.get('versions', [])
            license_info = ''
            if versions and len(versions) > 0:
                license_info = versions[0].get('license', '')
            
            return self.normalize_metadata(
                package_name=package_name,
                ecosystem="rust",
                description=description,
                keywords=keywords,
                license_info=license_info,
                homepage=homepage
            )
            
        except requests.RequestException as e:
            logger.debug(f"crates.io request failed for {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching crates.io metadata for {package_name}: {e}")
            return None
