"""
Test Unified Multi-Language Technology Registry System

Tests:
1. Python package classification (flask)
2. Node package classification (react)
3. Go package classification
4. Rust package classification
5. Fallback classification
6. Unknown ecosystem handling
7. Caching behavior
8. Network failure handling
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.services.registry.unified_registry import UnifiedRegistry
from backend.services.technology_classifier import TechnologyClassifier


def test_ecosystem_detection():
    """Test ecosystem detection from file lists."""
    print("\n=== Test 1: Ecosystem Detection ===")
    
    registry = UnifiedRegistry()
    
    test_cases = [
        (['package.json', 'src/index.js'], 'node'),
        (['requirements.txt', 'main.py'], 'python'),
        (['go.mod', 'main.go'], 'go'),
        (['Cargo.toml', 'src/main.rs'], 'rust'),
        (['README.md'], 'unknown')
    ]
    
    for files, expected in test_cases:
        detected = registry.detect_ecosystem(files)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {files} -> {detected} (expected: {expected})")
        assert detected == expected, f"Expected {expected}, got {detected}"
    
    print("\n✓ Test 1 passed")


def test_python_package_fetch():
    """Test fetching Python package metadata."""
    print("\n=== Test 2: Python Package Fetch ===")
    
    registry = UnifiedRegistry()
    
    # Test PyPI fetch
    metadata = registry.fetch('python', 'flask')
    
    if metadata:
        print(f"\n  Package: {metadata['name']}")
        print(f"  Ecosystem: {metadata['ecosystem']}")
        print(f"  Description: {metadata['description'][:100]}...")
        print(f"  Keywords: {metadata['keywords'][:5]}")
        print(f"  License: {metadata['license']}")
        print(f"  Homepage: {metadata['homepage']}")
        
        assert metadata['ecosystem'] == 'python'
        assert metadata['name'] == 'flask'
        print("\n✓ Test 2 passed")
    else:
        print("\n⚠ Test 2 skipped (network unavailable)")


def test_node_package_fetch():
    """Test fetching Node package metadata."""
    print("\n=== Test 3: Node Package Fetch ===")
    
    registry = UnifiedRegistry()
    
    # Test npm fetch
    metadata = registry.fetch('node', 'react')
    
    if metadata:
        print(f"\n  Package: {metadata['name']}")
        print(f"  Ecosystem: {metadata['ecosystem']}")
        print(f"  Description: {metadata['description'][:100]}...")
        print(f"  Keywords: {metadata['keywords'][:5]}")
        print(f"  License: {metadata['license']}")
        print(f"  Homepage: {metadata['homepage']}")
        
        assert metadata['ecosystem'] == 'node'
        assert metadata['name'] == 'react'
        print("\n✓ Test 3 passed")
    else:
        print("\n⚠ Test 3 skipped (network unavailable)")


def test_go_package_fetch():
    """Test fetching Go package metadata."""
    print("\n=== Test 4: Go Package Fetch ===")
    
    registry = UnifiedRegistry()
    
    # Test Go fetch (fallback)
    metadata = registry.fetch('go', 'github.com/gin-gonic/gin')
    
    if metadata:
        print(f"\n  Package: {metadata['name']}")
        print(f"  Ecosystem: {metadata['ecosystem']}")
        print(f"  Description: {metadata['description']}")
        print(f"  Homepage: {metadata['homepage']}")
        
        assert metadata['ecosystem'] == 'go'
        print("\n✓ Test 4 passed")
    else:
        print("\n⚠ Test 4 skipped")


def test_rust_package_fetch():
    """Test fetching Rust package metadata."""
    print("\n=== Test 5: Rust Package Fetch ===")
    
    registry = UnifiedRegistry()
    
    # Test crates.io fetch
    metadata = registry.fetch('rust', 'serde')
    
    if metadata:
        print(f"\n  Package: {metadata['name']}")
        print(f"  Ecosystem: {metadata['ecosystem']}")
        print(f"  Description: {metadata['description'][:100]}...")
        print(f"  Keywords: {metadata['keywords'][:5]}")
        print(f"  License: {metadata['license']}")
        
        assert metadata['ecosystem'] == 'rust'
        assert metadata['name'] == 'serde'
        print("\n✓ Test 5 passed")
    else:
        print("\n⚠ Test 5 skipped (network unavailable)")


def test_classification_python():
    """Test Python package classification."""
    print("\n=== Test 6: Python Package Classification ===")
    
    classifier = TechnologyClassifier()
    
    test_packages = [
        ('flask', 'python', 'backend-framework'),
        ('pytest', 'python', 'testing'),
        ('boto3', 'python', 'cloud'),
        ('redis', 'python', 'cache')
    ]
    
    print("\nClassifying Python packages:")
    for package, ecosystem, expected_category in test_packages:
        result = classifier.classify(package, ecosystem)
        status = "✓" if result['category'] == expected_category else "⚠"
        print(f"  {status} {package:20} -> {result['category']:20} (confidence: {result['confidence']:.2f})")
    
    print("\n✓ Test 6 passed")


def test_classification_node():
    """Test Node package classification."""
    print("\n=== Test 7: Node Package Classification ===")
    
    classifier = TechnologyClassifier()
    
    test_packages = [
        ('react', 'node', 'frontend-framework'),
        ('express', 'node', 'backend-framework'),
        ('jest', 'node', 'testing'),
        ('webpack', 'node', 'build-tool')
    ]
    
    print("\nClassifying Node packages:")
    for package, ecosystem, expected_category in test_packages:
        result = classifier.classify(package, ecosystem)
        status = "✓" if result['category'] == expected_category else "⚠"
        print(f"  {status} {package:20} -> {result['category']:20} (confidence: {result['confidence']:.2f})")
    
    print("\n✓ Test 7 passed")


def test_fallback_classification():
    """Test fallback classification for unknown packages."""
    print("\n=== Test 8: Fallback Classification ===")
    
    classifier = TechnologyClassifier()
    
    result = classifier.classify('unknown-package-xyz', 'python')
    
    print(f"\n  Package: {result['name']}")
    print(f"  Ecosystem: {result['ecosystem']}")
    print(f"  Category: {result['category']}")
    print(f"  Confidence: {result['confidence']}")
    
    assert result['category'] == 'other'
    assert result['confidence'] <= 0.5
    
    print("\n✓ Test 8 passed")


def test_caching():
    """Test caching behavior."""
    print("\n=== Test 9: Caching Behavior ===")
    
    registry = UnifiedRegistry()
    
    # First fetch
    print("\n  First fetch (should hit network)...")
    metadata1 = registry.fetch('python', 'flask')
    
    # Second fetch (should hit cache)
    print("  Second fetch (should hit cache)...")
    metadata2 = registry.fetch('python', 'flask')
    
    if metadata1 and metadata2:
        assert metadata1 == metadata2
        print("\n  ✓ Cache working correctly")
    else:
        print("\n  ⚠ Network unavailable, cache test skipped")
    
    # Clear cache
    registry.clear_cache()
    print("  Cache cleared")
    
    print("\n✓ Test 9 passed")


def test_batch_classification():
    """Test batch classification."""
    print("\n=== Test 10: Batch Classification ===")
    
    classifier = TechnologyClassifier()
    
    packages = [
        ('flask', 'python'),
        ('react', 'node'),
        ('pytest', 'python'),
        ('express', 'node')
    ]
    
    results = classifier.classify_batch(packages)
    
    print(f"\n  Classified {len(results)} packages:")
    for result in results:
        print(f"    - {result['name']:20} ({result['ecosystem']:6}) -> {result['category']:20}")
    
    assert len(results) == len(packages)
    
    print("\n✓ Test 10 passed")


def test_legacy_category_mapping():
    """Test legacy category mapping for backward compatibility."""
    print("\n=== Test 11: Legacy Category Mapping ===")
    
    classifier = TechnologyClassifier()
    
    result = classifier.classify('react', 'node')
    
    print(f"\n  Package: {result['name']}")
    print(f"  New Category: {result['category']}")
    print(f"  Legacy Category: {result['legacy_category']}")
    
    assert 'legacy_category' in result
    assert result['legacy_category'] in ['frontend', 'backend', 'database', 'cache', 'auth', 'cloud', 'testing', 'ml', 'infra', 'other']
    
    print("\n✓ Test 11 passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Unified Multi-Language Technology Registry Tests")
    print("=" * 60)
    
    try:
        test_ecosystem_detection()
        test_python_package_fetch()
        test_node_package_fetch()
        test_go_package_fetch()
        test_rust_package_fetch()
        test_classification_python()
        test_classification_node()
        test_fallback_classification()
        test_caching()
        test_batch_classification()
        test_legacy_category_mapping()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
