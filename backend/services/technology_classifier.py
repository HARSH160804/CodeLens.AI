"""
Multi-layer intelligent technology classification system.

Classification flow:
1. Static registry lookup (local JSON)
2. Fuzzy matching
3. Ecosystem-specific metadata analysis (PyPI, npm, crates.io, etc.)
4. Keyword scoring from metadata
5. LLM fallback (Bedrock)
6. Redis caching
7. Registry persistence
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import requests
except ImportError:
    requests = None

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

logger = logging.getLogger(__name__)

# Supported categories (expanded)
VALID_CATEGORIES = {
    'frontend-framework', 'backend-framework', 'database', 'cache', 'auth',
    'cloud', 'testing', 'ml', 'infra', 'build-tool', 'orm', 'api',
    'validation', 'logging', 'state-management', 'ui-library', 'routing',
    'graphql', 'websocket', 'task-queue', 'monitoring', 'documentation',
    'linting', 'containerization', 'ci-cd', 'other'
}

# Legacy category mapping for backward compatibility
LEGACY_CATEGORY_MAP = {
    'frontend-framework': 'frontend',
    'backend-framework': 'backend',
    'build-tool': 'infra',
    'orm': 'database',
    'api': 'other',
    'validation': 'other',
    'logging': 'infra',
    'state-management': 'frontend',
    'ui-library': 'frontend',
    'routing': 'frontend',
    'graphql': 'backend',
    'websocket': 'backend',
    'task-queue': 'backend',
    'monitoring': 'infra',
    'documentation': 'other',
    'linting': 'infra',
    'containerization': 'infra',
    'ci-cd': 'infra'
}


class TechnologyClassifier:
    """
    Intelligent technology classifier with multi-layer fallback strategy.
    
    Layers:
    1. Static registry (fastest)
    2. Fuzzy matching (fast)
    3. PyPI metadata (medium)
    4. LLM classification (slowest)
    
    Results are cached in Redis and persisted to registry.
    """
    
    def __init__(
        self,
        bedrock_client=None,
        redis_client=None,
        registry_path: Optional[str] = None,
        local_registry_path: Optional[str] = None
    ):
        """
        Initialize technology classifier.
        
        Args:
            bedrock_client: AWS Bedrock client for LLM classification
            redis_client: Redis client for caching
            registry_path: Path to technology registry JSON file (discovered packages)
            local_registry_path: Path to local fallback registry JSON file
        """
        self.bedrock_client = bedrock_client
        self.redis_client = redis_client
        
        # Load discovered packages registry
        if registry_path is None:
            registry_path = Path(__file__).parent / 'technology_registry.json'
        
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()
        
        # Load local fallback registry
        if local_registry_path is None:
            local_registry_path = Path(__file__).parent.parent / 'data' / 'technology_registry.json'
        
        self.local_registry_path = Path(local_registry_path)
        self.local_registry = self._load_local_registry()
        
        logger.info(f"Loaded {len(self.registry)} technologies from discovered registry")
        logger.info(f"Loaded {sum(len(v) for v in self.local_registry.values())} technologies from local registry")
    
    def _load_registry(self) -> Dict[str, Dict[str, str]]:
        """Load technology registry from JSON file."""
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Registry not found: {self.registry_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid registry JSON: {e}")
            return {}
    
    def _save_registry(self):
        """Save updated registry to JSON file."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2, sort_keys=True)
            logger.info(f"Saved registry with {len(self.registry)} technologies")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _load_local_registry(self) -> Dict[str, List[str]]:
        """Load local fallback registry from JSON file."""
        try:
            with open(self.local_registry_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Local registry not found: {self.local_registry_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid local registry JSON: {e}")
            return {}
    
    def classify(self, package_name: str, ecosystem: str = 'python', metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a package into a technology category.
        
        Args:
            package_name: Name of the package (e.g., 'flask', 'react')
            ecosystem: Ecosystem identifier ('python', 'node', 'go', 'rust')
            metadata: Optional pre-fetched metadata from registry
            
        Returns:
            Classification result dict:
            {
                "name": str,
                "ecosystem": str,
                "category": str,
                "confidence": float (0.0-1.0),
                "metadata": dict
            }
        """
        # Normalize package name
        normalized = self._normalize_package_name(package_name)
        
        if not normalized:
            return self._build_result(package_name, ecosystem, 'other', 0.0, {})
        
        # Check Redis cache first
        cached = self._get_from_cache(normalized, ecosystem)
        if cached:
            logger.debug(f"Cache hit for {ecosystem}:{normalized}")
            return cached
        
        # Layer 1: Local fallback registry (fastest)
        category, confidence = self._check_local_registry(normalized)
        if category:
            logger.debug(f"Local registry match for {normalized}: {category}")
            result = self._build_result(package_name, ecosystem, category, confidence, metadata or {})
            self._save_to_cache(normalized, ecosystem, result)
            return result
        
        # Layer 2: Discovered packages registry
        category = self._check_static_registry(normalized)
        if category:
            logger.debug(f"Static registry match for {normalized}: {category}")
            result = self._build_result(package_name, ecosystem, category, 0.9, metadata or {})
            self._save_to_cache(normalized, ecosystem, result)
            return result
        
        # Layer 3: Fuzzy matching
        category = self._fuzzy_match(normalized)
        if category:
            logger.debug(f"Fuzzy match for {normalized}: {category}")
            result = self._build_result(package_name, ecosystem, category, 0.8, metadata or {})
            self._save_to_cache(normalized, ecosystem, result)
            return result
        
        # Layer 4: Metadata keyword scoring
        if metadata:
            category, confidence = self._classify_from_metadata(metadata)
            if category and category != 'other':
                logger.info(f"Metadata classification for {normalized}: {category}")
                result = self._build_result(package_name, ecosystem, category, confidence, metadata)
                self._save_to_cache(normalized, ecosystem, result)
                self._add_to_registry(normalized, category, ecosystem)
                return result
        
        # Layer 5: Ecosystem-specific metadata query (if not provided)
        if not metadata and ecosystem == 'python':
            pypi_metadata = self._query_pypi_metadata(normalized)
            if pypi_metadata:
                category, confidence = self._classify_from_metadata(pypi_metadata)
                if category and category != 'other':
                    logger.info(f"PyPI metadata match for {normalized}: {category}")
                    result = self._build_result(package_name, ecosystem, category, confidence, pypi_metadata)
                    self._save_to_cache(normalized, ecosystem, result)
                    self._add_to_registry(normalized, category, ecosystem)
                    return result
        
        # Layer 6: LLM fallback
        category = self._llm_classify(normalized, ecosystem)
        if category and category != 'other':
            logger.info(f"LLM classified {normalized}: {category}")
            result = self._build_result(package_name, ecosystem, category, 0.7, metadata or {})
            self._save_to_cache(normalized, ecosystem, result)
            self._add_to_registry(normalized, category, ecosystem)
            return result
        
        # Default fallback
        logger.warning(f"Could not classify {normalized}, defaulting to 'other'")
        result = self._build_result(package_name, ecosystem, 'other', 0.5, metadata or {})
        self._save_to_cache(normalized, ecosystem, result)
        return result
    
    def _build_result(
        self,
        package_name: str,
        ecosystem: str,
        category: str,
        confidence: float,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build normalized classification result.
        
        Args:
            package_name: Package name
            ecosystem: Ecosystem identifier
            category: Classification category
            confidence: Confidence score (0.0-1.0)
            metadata: Package metadata
            
        Returns:
            Normalized result dict
        """
        # Map to legacy category for backward compatibility
        legacy_category = LEGACY_CATEGORY_MAP.get(category, category)
        
        return {
            "name": package_name,
            "ecosystem": ecosystem,
            "category": category,
            "legacy_category": legacy_category,  # For backward compatibility
            "confidence": max(0.0, min(1.0, confidence)),
            "metadata": metadata
        }
    
    def _normalize_package_name(self, package_name: str) -> str:
        """
        Normalize package name for consistent matching.
        
        Args:
            package_name: Raw package name
            
        Returns:
            Normalized package name (lowercase, no version specifiers)
        """
        if not package_name:
            return ''
        
        # Remove version specifiers (==, >=, <=, ~=, etc.)
        name = re.split(r'[=<>!~]', package_name)[0]
        
        # Remove extras (e.g., requests[security])
        name = re.split(r'[\[\]]', name)[0]
        
        # Lowercase and strip whitespace
        name = name.lower().strip()
        
        # Remove common prefixes/suffixes
        name = name.replace('python-', '').replace('-python', '')
        
        return name
    
    def _check_local_registry(self, package_name: str) -> tuple[Optional[str], float]:
        """
        Check local fallback registry for package.
        
        Args:
            package_name: Normalized package name
            
        Returns:
            Tuple of (category, confidence) or (None, 0.0) if not found
        """
        for category, packages in self.local_registry.items():
            if package_name in packages:
                return category, 1.0
        return None, 0.0
    
    def _check_static_registry(self, package_name: str) -> Optional[str]:
        """
        Check static registry for package.
        
        Args:
            package_name: Normalized package name
            
        Returns:
            Category if found, None otherwise
        """
        if package_name in self.registry:
            return self.registry[package_name].get('category')
        return None
    
    def _fuzzy_match(self, package_name: str) -> Optional[str]:
        """
        Use fuzzy matching to find similar packages in registry.
        
        Args:
            package_name: Normalized package name
            
        Returns:
            Category if match found (score > 80), None otherwise
        """
        if fuzz is None:
            logger.debug("rapidfuzz not available, skipping fuzzy matching")
            return None
        
        best_match = None
        best_score = 0
        
        for registered_name, metadata in self.registry.items():
            score = fuzz.ratio(package_name, registered_name)
            if score > best_score:
                best_score = score
                best_match = metadata.get('category')
        
        # Threshold: 80% similarity
        if best_score > 80:
            logger.debug(f"Fuzzy match: {package_name} -> score {best_score}")
            return best_match
        
        return None
    
    def _query_pypi_metadata(self, package_name: str) -> Optional[str]:
        """
        Query PyPI API for package metadata and infer category.
        
        Args:
            package_name: Normalized package name
            
        Returns:
            Inferred category or None
        """
        if requests is None:
            logger.debug("requests library not available, skipping PyPI query")
            return None
        
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                logger.debug(f"PyPI returned {response.status_code} for {package_name}")
                return None
            
            data = response.json()
            classifiers = data.get('info', {}).get('classifiers', [])
            
            # Analyze classifiers
            category = self._infer_category_from_classifiers(classifiers)
            return category
            
        except requests.RequestException as e:
            logger.debug(f"PyPI query failed for {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying PyPI for {package_name}: {e}")
            return None
    
    def _query_pypi_metadata(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Query PyPI API for package metadata.
        
        Args:
            package_name: Normalized package name
            
        Returns:
            Package metadata dict or None
        """
        if requests is None:
            logger.debug("requests library not available, skipping PyPI query")
            return None
        
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                logger.debug(f"PyPI returned {response.status_code} for {package_name}")
                return None
            
            data = response.json()
            info = data.get('info', {})
            
            return {
                'description': info.get('summary', '') or info.get('description', ''),
                'keywords': info.get('keywords', '').split(',') if info.get('keywords') else [],
                'classifiers': info.get('classifiers', []),
                'license': info.get('license', ''),
                'homepage': info.get('home_page', '')
            }
            
        except requests.RequestException as e:
            logger.debug(f"PyPI query failed for {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying PyPI for {package_name}: {e}")
            return None
    
    def _classify_from_metadata(self, metadata: Dict[str, Any]) -> tuple[Optional[str], float]:
        """
        Classify package from metadata using keyword scoring.
        
        Args:
            metadata: Package metadata dict
            
        Returns:
            Tuple of (category, confidence)
        """
        description = metadata.get('description', '').lower()
        keywords = [k.lower() for k in metadata.get('keywords', [])]
        classifiers = [c.lower() for c in metadata.get('classifiers', [])]
        
        # Combine all text for analysis
        text = f"{description} {' '.join(keywords)} {' '.join(classifiers)}"
        
        # Category detection patterns with scores
        patterns = {
            'frontend-framework': {
                'keywords': ['react', 'vue', 'angular', 'frontend', 'ui', 'component', 'web interface'],
                'score': 0
            },
            'backend-framework': {
                'keywords': ['web framework', 'wsgi', 'asgi', 'http server', 'api', 'rest', 'backend', 'server'],
                'score': 0
            },
            'database': {
                'keywords': ['database', 'sql', 'orm', 'mongodb', 'postgresql', 'mysql', 'data storage'],
                'score': 0
            },
            'cache': {
                'keywords': ['cache', 'caching', 'redis', 'memcached', 'in-memory'],
                'score': 0
            },
            'testing': {
                'keywords': ['testing', 'test framework', 'pytest', 'unittest', 'test runner'],
                'score': 0
            },
            'ml': {
                'keywords': ['machine learning', 'artificial intelligence', 'data science', 'neural network', 'deep learning'],
                'score': 0
            },
            'auth': {
                'keywords': ['authentication', 'authorization', 'oauth', 'jwt', 'security', 'login'],
                'score': 0
            },
            'cloud': {
                'keywords': ['aws', 'azure', 'gcp', 'cloud', 'serverless', 's3', 'lambda'],
                'score': 0
            },
            'build-tool': {
                'keywords': ['build', 'bundler', 'compiler', 'transpiler', 'webpack', 'vite'],
                'score': 0
            },
            'orm': {
                'keywords': ['orm', 'object-relational', 'database abstraction', 'query builder'],
                'score': 0
            }
        }
        
        # Score each category
        for category, data in patterns.items():
            for keyword in data['keywords']:
                if keyword in text:
                    data['score'] += 1
        
        # Find best match
        best_category = None
        best_score = 0
        
        for category, data in patterns.items():
            if data['score'] > best_score:
                best_score = data['score']
                best_category = category
        
        if best_category and best_score > 0:
            # Calculate confidence based on score
            confidence = min(0.95, 0.7 + (best_score * 0.05))
            return best_category, confidence
        
        return None, 0.0
    
    def _infer_category_from_classifiers(self, classifiers: list) -> Optional[str]:
        """
        Infer category from PyPI classifiers.
        
        Args:
            classifiers: List of PyPI classifier strings
            
        Returns:
            Inferred category or None
        """
        classifier_text = ' '.join(classifiers).lower()
        
        # Category detection patterns
        patterns = {
            'backend': ['web framework', 'wsgi', 'asgi', 'http server', 'api'],
            'database': ['database', 'sql', 'orm', 'mongodb', 'postgresql', 'mysql'],
            'cache': ['cache', 'caching', 'redis', 'memcached'],
            'testing': ['testing', 'test framework', 'pytest', 'unittest'],
            'ml': ['machine learning', 'artificial intelligence', 'data science', 'neural network'],
            'auth': ['authentication', 'authorization', 'oauth', 'jwt', 'security'],
            'cloud': ['aws', 'azure', 'gcp', 'cloud', 'serverless'],
            'infra': ['deployment', 'devops', 'ci/cd', 'monitoring', 'logging'],
            'frontend': ['frontend', 'ui', 'web interface', 'html', 'css']
        }
        
        for category, keywords in patterns.items():
            if any(keyword in classifier_text for keyword in keywords):
                return category
        
        return None
    
    def _llm_classify(self, package_name: str, ecosystem: str) -> Optional[str]:
        """
        Use LLM (Bedrock) to classify package as fallback.
        
        Args:
            package_name: Normalized package name
            ecosystem: Ecosystem identifier
            
        Returns:
            LLM-classified category or None
        """
        if self.bedrock_client is None:
            logger.debug("Bedrock client not available, skipping LLM classification")
            return None
        
        try:
            categories_str = ', '.join(sorted(VALID_CATEGORIES))
            prompt = f"""Classify this {ecosystem} package into one of these categories:
{categories_str}

Package: {package_name}
Ecosystem: {ecosystem}

Return only the category name, nothing else."""
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                prompt=prompt,
                max_tokens=20,
                temperature=0.1
            )
            
            # Extract and validate category
            category = response.strip().lower()
            
            if category in VALID_CATEGORIES:
                return category
            
            logger.warning(f"LLM returned invalid category: {category}")
            return None
            
        except Exception as e:
            logger.error(f"LLM classification failed for {package_name}: {e}")
            return None
    
    def _get_from_cache(self, package_name: str, ecosystem: str) -> Optional[Dict[str, Any]]:
        """
        Get classification from Redis cache.
        
        Args:
            package_name: Normalized package name
            ecosystem: Ecosystem identifier
            
        Returns:
            Cached classification result or None
        """
        if self.redis_client is None:
            return None
        
        try:
            key = f"tech:{ecosystem}:{package_name}"
            cached = self.redis_client.get(key)
            
            if cached:
                if isinstance(cached, bytes):
                    cached = cached.decode('utf-8')
                return json.loads(cached)
            
        except Exception as e:
            logger.debug(f"Redis get failed for {ecosystem}:{package_name}: {e}")
        
        return None
    
    def _save_to_cache(self, package_name: str, ecosystem: str, result: Dict[str, Any]):
        """
        Save classification to Redis cache.
        
        Args:
            package_name: Normalized package name
            ecosystem: Ecosystem identifier
            result: Classification result dict
        """
        if self.redis_client is None:
            return
        
        try:
            key = f"tech:{ecosystem}:{package_name}"
            value = json.dumps(result)
            # TTL: 7 days
            self.redis_client.setex(key, 7 * 24 * 60 * 60, value)
            logger.debug(f"Cached {ecosystem}:{package_name}")
            
        except Exception as e:
            logger.debug(f"Redis set failed for {ecosystem}:{package_name}: {e}")
    
    def _add_to_registry(self, package_name: str, category: str, ecosystem: str):
        """
        Add newly discovered package to registry.
        
        Args:
            package_name: Normalized package name
            category: Classification category
            ecosystem: Package ecosystem (e.g., 'python')
        """
        if package_name not in self.registry:
            self.registry[package_name] = {
                'category': category,
                'ecosystem': ecosystem
            }
            self._save_registry()
            logger.info(f"Added {package_name} to registry: {category}")
    
    def classify_batch(self, packages: List[tuple[str, str]], metadata_map: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Classify multiple packages efficiently.
        
        Args:
            packages: List of (package_name, ecosystem) tuples
            metadata_map: Optional dict mapping package names to metadata
            
        Returns:
            List of classification result dicts
        """
        results = []
        metadata_map = metadata_map or {}
        
        for package_name, ecosystem in packages:
            metadata = metadata_map.get(package_name)
            result = self.classify(package_name, ecosystem, metadata)
            results.append(result)
        
        return results
