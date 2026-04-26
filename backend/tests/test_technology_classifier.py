"""
Unit tests for TechnologyClassifier.

Tests all classification layers:
1. Static registry
2. Fuzzy matching
3. PyPI metadata
4. LLM fallback
5. Redis caching
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backend.services.technology_classifier import TechnologyClassifier, VALID_CATEGORIES


@pytest.fixture
def mock_registry_file(tmp_path):
    """Create a temporary registry file for testing."""
    registry_data = {
        "flask": {"category": "backend", "ecosystem": "python"},
        "sqlalchemy": {"category": "database", "ecosystem": "python"},
        "pytest": {"category": "testing", "ecosystem": "python"},
        "redis": {"category": "cache", "ecosystem": "python"}
    }
    
    registry_path = tmp_path / "test_registry.json"
    with open(registry_path, 'w') as f:
        json.dump(registry_data, f)
    
    return registry_path


@pytest.fixture
def classifier(mock_registry_file):
    """Create classifier instance with test registry."""
    return TechnologyClassifier(
        bedrock_client=None,
        redis_client=None,
        registry_path=str(mock_registry_file)
    )


@pytest.fixture
def mock_bedrock_client():
    """Create mock Bedrock client."""
    client = Mock()
    client.invoke_model = Mock(return_value="backend")
    return client


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = Mock()
    client.get = Mock(return_value=None)
    client.setex = Mock()
    return client


class TestNormalization:
    """Test package name normalization."""
    
    def test_normalize_basic(self, classifier):
        """Test basic normalization."""
        assert classifier._normalize_package_name("Flask") == "flask"
        assert classifier._normalize_package_name("SQLAlchemy") == "sqlalchemy"
    
    def test_normalize_with_version(self, classifier):
        """Test normalization with version specifiers."""
        assert classifier._normalize_package_name("flask==2.0.0") == "flask"
        assert classifier._normalize_package_name("requests>=2.28.0") == "requests"
        assert classifier._normalize_package_name("django~=4.0") == "django"
    
    def test_normalize_with_extras(self, classifier):
        """Test normalization with extras."""
        assert classifier._normalize_package_name("requests[security]") == "requests"
        assert classifier._normalize_package_name("celery[redis]") == "celery"
    
    def test_normalize_with_prefix(self, classifier):
        """Test normalization with python prefix."""
        assert classifier._normalize_package_name("python-dateutil") == "dateutil"
        assert classifier._normalize_package_name("requests-python") == "requests"
    
    def test_normalize_empty(self, classifier):
        """Test normalization with empty string."""
        assert classifier._normalize_package_name("") == ""
        assert classifier._normalize_package_name(None) == ""


class TestStaticRegistry:
    """Test static registry classification."""
    
    def test_registry_hit(self, classifier):
        """Test classification from static registry."""
        assert classifier.classify("flask") == "backend"
        assert classifier.classify("sqlalchemy") == "database"
        assert classifier.classify("pytest") == "testing"
        assert classifier.classify("redis") == "cache"
    
    def test_registry_case_insensitive(self, classifier):
        """Test case-insensitive registry lookup."""
        assert classifier.classify("Flask") == "backend"
        assert classifier.classify("SQLALCHEMY") == "database"
    
    def test_registry_with_version(self, classifier):
        """Test registry lookup with version specifiers."""
        assert classifier.classify("flask==2.0.0") == "backend"
        assert classifier.classify("pytest>=7.0") == "testing"


class TestFuzzyMatching:
    """Test fuzzy matching classification."""
    
    @patch('backend.services.technology_classifier.fuzz')
    def test_fuzzy_match_high_score(self, mock_fuzz, classifier):
        """Test fuzzy matching with high similarity score."""
        # Mock fuzz.ratio to return high score for flask-login
        def ratio_side_effect(a, b):
            if a == "flasklogin" and b == "flask":
                return 85
            return 50
        
        mock_fuzz.ratio = Mock(side_effect=ratio_side_effect)
        
        result = classifier._fuzzy_match("flasklogin")
        assert result == "backend"
    
    @patch('backend.services.technology_classifier.fuzz')
    def test_fuzzy_match_low_score(self, mock_fuzz, classifier):
        """Test fuzzy matching with low similarity score."""
        mock_fuzz.ratio = Mock(return_value=50)
        
        result = classifier._fuzzy_match("unknown-package")
        assert result is None
    
    @patch('backend.services.technology_classifier.fuzz', None)
    def test_fuzzy_match_unavailable(self, classifier):
        """Test fuzzy matching when rapidfuzz is not available."""
        result = classifier._fuzzy_match("flask-login")
        assert result is None


class TestPyPIMetadata:
    """Test PyPI metadata classification."""
    
    @patch('backend.services.technology_classifier.requests')
    def test_pypi_success(self, mock_requests, classifier):
        """Test successful PyPI metadata query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {
                'classifiers': [
                    'Framework :: Django',
                    'Topic :: Internet :: WWW/HTTP :: WSGI',
                    'Development Status :: 5 - Production/Stable'
                ]
            }
        }
        mock_requests.get.return_value = mock_response
        
        result = classifier._query_pypi_metadata("django-extensions")
        assert result == "backend"
    
    @patch('backend.services.technology_classifier.requests')
    def test_pypi_not_found(self, mock_requests, classifier):
        """Test PyPI query for non-existent package."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        result = classifier._query_pypi_metadata("nonexistent-package")
        assert result is None
    
    @patch('backend.services.technology_classifier.requests')
    def test_pypi_timeout(self, mock_requests, classifier):
        """Test PyPI query timeout."""
        mock_requests.get.side_effect = mock_requests.RequestException("Timeout")
        
        result = classifier._query_pypi_metadata("some-package")
        assert result is None
    
    @patch('backend.services.technology_classifier.requests', None)
    def test_pypi_unavailable(self, classifier):
        """Test PyPI query when requests is not available."""
        result = classifier._query_pypi_metadata("some-package")
        assert result is None
    
    def test_infer_category_database(self, classifier):
        """Test category inference for database packages."""
        classifiers = [
            'Topic :: Database',
            'Framework :: Django :: ORM'
        ]
        assert classifier._infer_category_from_classifiers(classifiers) == "database"
    
    def test_infer_category_testing(self, classifier):
        """Test category inference for testing packages."""
        classifiers = [
            'Framework :: Pytest',
            'Topic :: Software Development :: Testing'
        ]
        assert classifier._infer_category_from_classifiers(classifiers) == "testing"
    
    def test_infer_category_ml(self, classifier):
        """Test category inference for ML packages."""
        classifiers = [
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Intended Audience :: Science/Research'
        ]
        assert classifier._infer_category_from_classifiers(classifiers) == "ml"
    
    def test_infer_category_unknown(self, classifier):
        """Test category inference with no matching patterns."""
        classifiers = [
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License'
        ]
        assert classifier._infer_category_from_classifiers(classifiers) is None


class TestLLMClassification:
    """Test LLM fallback classification."""
    
    def test_llm_success(self, mock_registry_file, mock_bedrock_client):
        """Test successful LLM classification."""
        mock_bedrock_client.invoke_model.return_value = "backend"
        
        classifier = TechnologyClassifier(
            bedrock_client=mock_bedrock_client,
            redis_client=None,
            registry_path=str(mock_registry_file)
        )
        
        result = classifier._llm_classify("unknown-web-framework")
        assert result == "backend"
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_llm_invalid_category(self, mock_registry_file, mock_bedrock_client):
        """Test LLM returning invalid category."""
        mock_bedrock_client.invoke_model.return_value = "invalid-category"
        
        classifier = TechnologyClassifier(
            bedrock_client=mock_bedrock_client,
            redis_client=None,
            registry_path=str(mock_registry_file)
        )
        
        result = classifier._llm_classify("unknown-package")
        assert result is None
    
    def test_llm_exception(self, mock_registry_file, mock_bedrock_client):
        """Test LLM classification with exception."""
        mock_bedrock_client.invoke_model.side_effect = Exception("API Error")
        
        classifier = TechnologyClassifier(
            bedrock_client=mock_bedrock_client,
            redis_client=None,
            registry_path=str(mock_registry_file)
        )
        
        result = classifier._llm_classify("unknown-package")
        assert result is None
    
    def test_llm_unavailable(self, classifier):
        """Test LLM classification when Bedrock is not available."""
        result = classifier._llm_classify("unknown-package")
        assert result is None


class TestRedisCaching:
    """Test Redis caching functionality."""
    
    def test_cache_hit(self, mock_registry_file, mock_redis_client):
        """Test cache hit returns cached value."""
        mock_redis_client.get.return_value = b"backend"
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=mock_redis_client,
            registry_path=str(mock_registry_file)
        )
        
        result = classifier.classify("unknown-package")
        assert result == "backend"
        mock_redis_client.get.assert_called_once()
    
    def test_cache_miss_then_save(self, mock_registry_file, mock_redis_client):
        """Test cache miss triggers classification and saves result."""
        mock_redis_client.get.return_value = None
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=mock_redis_client,
            registry_path=str(mock_registry_file)
        )
        
        result = classifier.classify("flask")
        assert result == "backend"
        
        # Should save to cache
        mock_redis_client.setex.assert_called_once()
        args = mock_redis_client.setex.call_args[0]
        assert args[0] == "tech:flask"
        assert args[1] == 7 * 24 * 60 * 60  # 7 days TTL
        assert args[2] == "backend"
    
    def test_cache_exception_handled(self, mock_registry_file, mock_redis_client):
        """Test Redis exceptions are handled gracefully."""
        mock_redis_client.get.side_effect = Exception("Redis error")
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=mock_redis_client,
            registry_path=str(mock_registry_file)
        )
        
        # Should still work without cache
        result = classifier.classify("flask")
        assert result == "backend"


class TestRegistryPersistence:
    """Test registry persistence functionality."""
    
    @patch('backend.services.technology_classifier.requests')
    def test_add_to_registry(self, mock_requests, mock_registry_file):
        """Test adding new package to registry."""
        # Mock PyPI response - PyPI uses the original package name with hyphens
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {
                'classifiers': ['Framework :: Django', 'Topic :: Internet :: WWW/HTTP :: WSGI']
            }
        }
        mock_requests.get.return_value = mock_response
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=None,
            registry_path=str(mock_registry_file)
        )
        
        # Classify new package
        result = classifier.classify("django-extensions")
        assert result == "backend"
        
        # Check registry was updated
        # Note: PyPI query uses original name, so registry stores "django-extensions"
        with open(mock_registry_file, 'r') as f:
            registry = json.load(f)
        
        # Package is stored with the name used in PyPI query (with hyphens)
        assert "django-extensions" in registry
        assert registry["django-extensions"]["category"] == "backend"
        assert registry["django-extensions"]["ecosystem"] == "python"


class TestFullClassificationFlow:
    """Test complete classification flow."""
    
    def test_unknown_package_fallback(self, classifier):
        """Test unknown package defaults to 'other'."""
        result = classifier.classify("completely-unknown-package-xyz")
        assert result == "other"
    
    def test_batch_classification(self, classifier):
        """Test batch classification."""
        packages = ["flask", "sqlalchemy", "pytest", "unknown-pkg"]
        results = classifier.classify_batch(packages)
        
        assert results["flask"] == "backend"
        assert results["sqlalchemy"] == "database"
        assert results["pytest"] == "testing"
        assert results["unknown-pkg"] == "other"
    
    def test_valid_categories(self):
        """Test all valid categories are defined."""
        expected = {
            'frontend', 'backend', 'database', 'cache', 'auth',
            'cloud', 'testing', 'ml', 'infra', 'other'
        }
        assert VALID_CATEGORIES == expected


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_package_name(self, classifier):
        """Test classification with empty package name."""
        assert classifier.classify("") == "other"
        assert classifier.classify(None) == "other"
    
    def test_malformed_registry(self, tmp_path):
        """Test handling of malformed registry file."""
        registry_path = tmp_path / "bad_registry.json"
        with open(registry_path, 'w') as f:
            f.write("{ invalid json }")
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=None,
            registry_path=str(registry_path)
        )
        
        # Should handle gracefully
        assert len(classifier.registry) == 0
    
    def test_missing_registry(self, tmp_path):
        """Test handling of missing registry file."""
        registry_path = tmp_path / "nonexistent.json"
        
        classifier = TechnologyClassifier(
            bedrock_client=None,
            redis_client=None,
            registry_path=str(registry_path)
        )
        
        # Should handle gracefully
        assert len(classifier.registry) == 0
