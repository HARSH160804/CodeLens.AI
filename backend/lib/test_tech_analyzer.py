"""
Test script for TechAnalyzer

Demonstrates intelligent tech stack detection with rich metadata.
"""

import json
from tech_analyzer import TechAnalyzer


def test_tech_analyzer():
    """Test TechAnalyzer with mock repository."""
    
    print("=" * 60)
    print("Tech Stack Analyzer - Test Run")
    print("=" * 60)
    print()
    
    # Initialize analyzer
    analyzer = TechAnalyzer()
    
    # Mock repository structure
    repo_path = "/mock/repo"
    files = [
        "package.json",
        "src/App.tsx",
        "src/components/Button.tsx",
        "src/api/server.js",
        "requirements.txt",
        "backend/main.py",
        "backend/models.py",
        "tests/test_api.py",
        "docker-compose.yml",
        "Dockerfile",
        ".github/workflows/ci.yml"
    ]
    
    # Run analysis
    print("Analyzing repository...")
    analysis = analyzer.analyze(repo_path, files)
    
    # Display results
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total Technologies: {analysis.summary.total}")
    print(f"Secure: {analysis.summary.secure}")
    print(f"Vulnerable: {analysis.summary.vulnerable}")
    print(f"Outdated: {analysis.summary.outdated}")
    print(f"Unknown: {analysis.summary.unknown}")
    print()
    
    print("By Category:")
    for category, count in analysis.summary.by_category.items():
        print(f"  {category.title()}: {count}")
    print()
    
    # Display technologies
    print(f"\n{'='*60}")
    print("DETECTED TECHNOLOGIES")
    print(f"{'='*60}")
    
    for tech in analysis.technologies:
        print(f"\n{tech.name} ({tech.id})")
        print(f"  Version: {tech.version}")
        print(f"  Category: {tech.category}")
        print(f"  License: {tech.license}")
        print(f"  Security: {tech.security.status}")
        print(f"  Confidence: {tech.confidence:.2f}")
        print(f"  Icon: {tech.icon_svg}")
        
        if tech.usage.files_using > 0:
            print(f"  Files Using: {tech.usage.files_using}")
        if tech.usage.total_imports > 0:
            print(f"  Total Imports: {tech.usage.total_imports}")
        
        if tech.security.vulnerabilities:
            print(f"  Vulnerabilities:")
            for vuln in tech.security.vulnerabilities:
                print(f"    - {vuln.cve_id} ({vuln.severity}): {vuln.description}")
        
        if tech.alternatives:
            print(f"  Alternatives: {', '.join(tech.alternatives)}")
    
    # Display categories
    print(f"\n{'='*60}")
    print("TECHNOLOGIES BY CATEGORY")
    print(f"{'='*60}")
    
    for category, techs in analysis.categories.items():
        if techs:
            print(f"\n{category.upper()}:")
            for tech in techs:
                status_icon = {
                    'secure': '✓',
                    'vulnerable': '✗',
                    'outdated': '⚠',
                    'unknown': '?'
                }.get(tech.security.status, '?')
                print(f"  {status_icon} {tech.name} {tech.version}")
    
    # Display recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    if analysis.recommendations:
        for rec in analysis.recommendations:
            priority_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(rec.priority, '⚪')
            
            print(f"\n{priority_icon} {rec.type.upper()} - {rec.priority.upper()}")
            print(f"  {rec.message}")
            if rec.technologies:
                print(f"  Affected: {', '.join(rec.technologies)}")
            if rec.action:
                print(f"  Action: {rec.action}")
    else:
        print("\nNo recommendations - tech stack looks good!")
    
    # Export to JSON
    print(f"\n{'='*60}")
    print("JSON OUTPUT")
    print(f"{'='*60}")
    
    json_output = analyzer.to_dict(analysis)
    print(json.dumps(json_output, indent=2)[:1000] + "...")
    
    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}")


if __name__ == '__main__':
    test_tech_analyzer()
