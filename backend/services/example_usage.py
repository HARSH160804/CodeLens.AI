"""
Example usage of TechnologyClassifier

Demonstrates how to integrate the classifier into existing code.
"""

from technology_classifier import TechnologyClassifier


def example_basic_usage():
    """Basic classification example."""
    print("=" * 60)
    print("Example 1: Basic Classification")
    print("=" * 60)
    
    # Initialize classifier (no Bedrock or Redis for this example)
    classifier = TechnologyClassifier()
    
    # Classify some packages
    packages = [
        "flask",
        "sqlalchemy",
        "pytest",
        "boto3",
        "numpy",
        "unknown-package-xyz"
    ]
    
    for package in packages:
        category = classifier.classify(package)
        print(f"{package:30} -> {category}")
    
    print()


def example_batch_classification():
    """Batch classification example."""
    print("=" * 60)
    print("Example 2: Batch Classification")
    print("=" * 60)
    
    classifier = TechnologyClassifier()
    
    # Classify multiple packages at once
    packages = [
        "flask==2.0.0",
        "django>=4.0",
        "fastapi",
        "sqlalchemy",
        "redis",
        "pytest",
        "boto3",
        "numpy",
        "pandas"
    ]
    
    results = classifier.classify_batch(packages)
    
    # Group by category
    by_category = {}
    for package, category in results.items():
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(package)
    
    # Display grouped results
    for category, pkgs in sorted(by_category.items()):
        print(f"\n{category.upper()}:")
        for pkg in pkgs:
            print(f"  - {pkg}")
    
    print()


def example_with_requirements_txt():
    """Parse requirements.txt and classify packages."""
    print("=" * 60)
    print("Example 3: Classify from requirements.txt")
    print("=" * 60)
    
    classifier = TechnologyClassifier()
    
    # Simulate reading requirements.txt
    requirements = """
flask==2.0.0
sqlalchemy>=1.4.0
pytest>=7.0.0
redis>=4.0.0
boto3>=1.34.0
numpy>=1.24.0
requests>=2.31.0
    """.strip().split('\n')
    
    print("Analyzing requirements.txt...\n")
    
    results = {}
    for line in requirements:
        line = line.strip()
        if line and not line.startswith('#'):
            category = classifier.classify(line)
            results[line] = category
    
    # Display results
    for package, category in results.items():
        print(f"{package:30} -> {category}")
    
    # Summary
    print(f"\nTotal packages: {len(results)}")
    print(f"Categories: {len(set(results.values()))}")
    
    print()


def example_integration_with_tech_detector():
    """Example integration with TechStackDetector."""
    print("=" * 60)
    print("Example 4: Integration with TechStackDetector")
    print("=" * 60)
    
    # This is how you would integrate into existing code
    
    class TechStackDetector:
        """Example tech stack detector using classifier."""
        
        def __init__(self):
            self.classifier = TechnologyClassifier()
        
        def detect_from_requirements(self, requirements_file):
            """Detect technologies from requirements.txt."""
            technologies = []
            
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name and version
                        parts = line.split('==')
                        package_name = parts[0].strip()
                        version = parts[1].strip() if len(parts) > 1 else 'unknown'
                        
                        # Classify using intelligent classifier
                        category = self.classifier.classify(package_name)
                        
                        technologies.append({
                            'name': package_name,
                            'version': version,
                            'category': category
                        })
            
            return technologies
    
    print("Integration example:")
    print("""
    class TechStackDetector:
        def __init__(self):
            self.classifier = TechnologyClassifier()
        
        def detect_from_requirements(self, requirements_file):
            for line in file:
                package_name = extract_package_name(line)
                category = self.classifier.classify(package_name)
                # Use category in Technology object
    """)
    
    print()


if __name__ == '__main__':
    example_basic_usage()
    example_batch_classification()
    example_with_requirements_txt()
    example_integration_with_tech_detector()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
