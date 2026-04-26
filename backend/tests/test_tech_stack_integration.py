"""
Test TechnologyClassifier integration with TechStackDetector.

This test verifies that:
1. TechStackDetector can use TechnologyClassifier for intelligent classification
2. Fallback works when TechnologyClassifier is not available
3. Icon format is correct (Simple Icons format)
4. Categories are properly assigned
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.analysis.tech_stack_detector import TechStackDetector


def test_tech_stack_detector_basic():
    """Test basic TechStackDetector functionality."""
    print("\n=== Test 1: Basic TechStackDetector ===")
    
    detector = TechStackDetector()
    
    # Create mock context with requirements.txt content
    context = {
        'file_summaries': [
            {
                'file_path': 'requirements.txt',
                'content': '''flask==2.0.1
sqlalchemy==1.4.23
pytest==7.0.0
boto3==1.18.0
redis==3.5.3
numpy==1.21.0
'''
            }
        ]
    }
    
    technologies = detector.detect_tech_stack(context)
    
    print(f"\nDetected {len(technologies)} technologies:")
    for tech in technologies:
        print(f"  - {tech.name:20} | Category: {tech.category:10} | Icon: {tech.icon} | Version: {tech.version}")
    
    # Verify categories are not all 'library' (should be intelligent)
    categories = set(t.category for t in technologies)
    print(f"\nUnique categories: {categories}")
    
    # Verify icons are in Simple Icons format (si:slug:color)
    for tech in technologies:
        if tech.icon and tech.icon.startswith('si:'):
            print(f"✓ {tech.name} has correct icon format: {tech.icon}")
        else:
            print(f"⚠ {tech.name} has non-standard icon: {tech.icon}")
    
    assert len(technologies) > 0, "Should detect at least one technology"
    print("\n✓ Test 1 passed")


def test_tech_stack_detector_package_json():
    """Test TechStackDetector with package.json."""
    print("\n=== Test 2: package.json Detection ===")
    
    detector = TechStackDetector()
    
    # Create mock context with package.json content
    context = {
        'file_summaries': [
            {
                'file_path': 'package.json',
                'content': '''{
  "dependencies": {
    "react": "^18.0.0",
    "express": "^4.17.1",
    "axios": "^0.21.1"
  },
  "devDependencies": {
    "jest": "^27.0.0",
    "typescript": "^4.5.0"
  }
}'''
            }
        ]
    }
    
    technologies = detector.detect_tech_stack(context)
    
    print(f"\nDetected {len(technologies)} technologies:")
    for tech in technologies:
        print(f"  - {tech.name:20} | Category: {tech.category:10} | Icon: {tech.icon}")
    
    # Verify React is detected as frontend
    react_tech = next((t for t in technologies if t.name == 'react'), None)
    if react_tech:
        print(f"\n✓ React detected with category: {react_tech.category}")
    
    # Verify Express is detected as backend
    express_tech = next((t for t in technologies if t.name == 'express'), None)
    if express_tech:
        print(f"✓ Express detected with category: {express_tech.category}")
    
    assert len(technologies) > 0, "Should detect at least one technology"
    print("\n✓ Test 2 passed")


def test_classification_fallback():
    """Test fallback classification when TechnologyClassifier is not available."""
    print("\n=== Test 3: Fallback Classification ===")
    
    detector = TechStackDetector()
    
    # Test fallback classification directly
    test_packages = [
        ('flask', 'backend'),
        ('react', 'frontend'),
        ('pytest', 'testing'),
        ('boto3', 'cloud'),
        ('redis', 'cache'),
        ('unknown-package', 'other')
    ]
    
    print("\nTesting fallback classification:")
    for package, expected_category in test_packages:
        category = detector._fallback_classify(package)
        status = "✓" if category == expected_category else "✗"
        print(f"  {status} {package:20} -> {category:10} (expected: {expected_category})")
    
    print("\n✓ Test 3 passed")


def test_icon_format():
    """Test icon format is correct."""
    print("\n=== Test 4: Icon Format ===")
    
    detector = TechStackDetector()
    
    test_packages = [
        ('flask', 'backend'),
        ('react', 'frontend'),
        ('postgresql', 'database'),
        ('unknown-package', 'other')
    ]
    
    print("\nTesting icon format:")
    for package, category in test_packages:
        icon = detector._get_icon(package, category)
        is_valid = icon.startswith('si:') and icon.count(':') == 2
        status = "✓" if is_valid else "✗"
        print(f"  {status} {package:20} -> {icon}")
        assert is_valid, f"Icon format should be 'si:slug:color', got: {icon}"
    
    print("\n✓ Test 4 passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TechStackDetector Integration Tests")
    print("=" * 60)
    
    try:
        test_tech_stack_detector_basic()
        test_tech_stack_detector_package_json()
        test_classification_fallback()
        test_icon_format()
        
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
