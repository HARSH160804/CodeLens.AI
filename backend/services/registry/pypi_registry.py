"""
PyPI Registry Adapter

Fetches package metadata from Python Package Index (PyPI).
"""

import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from .base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class PyPIRegistry(BaseRegistry):
    """Adapter for PyPI (Python Package Index)."""
    
    BASE_URL = "https://pypi.org/pypi"
    TIMEOUT = 5  # seconds
    
    def fetch_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch package metadata from PyPI.
        
        Args:
            package_name: Name of the Python package
            
        Returns:
            Normalized metadata dict or None if fetch fails
        """
        if requests is None:
            logger.warning("requests library not available, cannot fetch PyPI metadata")
            return None
        
        try:
            url = f"{self.BASE_URL}/{package_name}/json"
            response = requests.get(url, timeout=self.TIMEOUT)
            
            if response.status_code != 200:
                logger.debug(f"PyPI returned {response.status_code} for {package_name}")
                return None
            
            data = response.json()
            info = data.get('info', {})
            
            # Extract metadata
            description = info.get('summary', '') or info.get('description', '')
            homepage = info.get('home_page', '') or info.get('project_url', '')
            license_info = info.get('license', '')
            
            # Extract keywords from classifiers
            classifiers = info.get('classifiers', [])
            keywords = self._extract_keywords_from_classifiers(classifiers)
            
            return self.normalize_metadata(
                package_name=package_name,
                ecosystem="python",
                description=description,
                keywords=keywords,
                license_info=license_info,
                homepage=homepage
            )
            
        except requests.RequestException as e:
            logger.debug(f"PyPI request failed for {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PyPI metadata for {package_name}: {e}")
            return None
    
    def _extract_keywords_from_classifiers(self, classifiers: list) -> list:
        """
        Extract relevant keywords from PyPI classifiers.
        
        Args:
            classifiers: List of PyPI classifier strings
            
        Returns:
            List of extracted keywords
        """
        keywords = []
        
        for classifier in classifiers:
            classifier_lower = classifier.lower()
            
            # Extract framework keywords
            if 'framework' in classifier_lower:
                parts = classifier.split('::')
                if len(parts) > 1:
                    keywords.append(parts[-1].strip().lower())
            
            # Extract topic keywords
            elif 'topic' in classifier_lower:
                parts = classifier.split('::')
                if len(parts) > 1:
                    keywords.append(parts[-1].strip().lower())
            
            # Extract intended audience
            elif 'intended audience' in classifier_lower:
                parts = classifier.split('::')
                if len(parts) > 1:
                    keywords.append(parts[-1].strip().lower())
        
        return list(set(keywords))  # Remove duplicates
