"""
Test script for TechAnalyzer with REAL file reading

Tests the analyzer against the actual backend directory.
"""

import json
import os
from pathlib import Path
from tech_analyzer import TechAnalyzer


def test_with_real_backend():
    """Test TechAnalyzer with actual backend directory."""
    
    print("=" * 60)
    print("Tech Stack Analyzer - Real Backend Test")
    print("=" * 60)
    print()
    
    # Initialize analyzer
    analyzer = TechAnalyzer()
    
    # Get backend directory path
    backend_path = Path(__file__).parent.parent
    print(f"Analyzing: {backend_path}")
    print()
    
    # Collect all files in backend
    files = []
    for root, dirs, filenames in os.walk(backend_path):
        # Skip virtual environments and cache directories
        dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.pytest_cache', 'node_modules']]
        
        for filename in filenames:
            file_path = os.path.join(root, filename)
            # Make path relative to backend_path
            rel_path = os.path.relpath(file_path, backend_path)
            files.append(rel_path)
    
    print(f"Found {len(files)} files")
    print()
    
    # Run analysis
    print("Analyzing repository...")
    analysis = analyzer.analyze(str(backend_path), files)
    
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
    for category, count in sorted(analysis.summary.by_category.items()):
        if count > 0:
            print(f"  {category.title()}: {count}")
    print()
    
    # Display technologies
    print(f"\n{'='*60}")
    print("DETECTED TECHNOLOGIES")
    print(f"{'='*60}")
    
    # Sort by confidence (highest first)
    sorted_techs = sorted(analysis.technologies, key=lambda t: t.confidence, reverse=True)
    
    for tech in sorted_techs:
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
        if tech.usage.percentage > 0:
            print(f"  Usage: {tech.usage.percentage:.1f}%")
        
        if tech.security.vulnerabilities:
            print(f"  Vulnerabilities:")
            for vuln in tech.security.vulnerabilities:
                print(f"    - {vuln.cve_id} ({vuln.severity}): {vuln.description}")
        
        if tech.alternatives:
            print(f"  Alternatives: {', '.join(tech.alternatives[:3])}")
    
    # Display categories
    print(f"\n{'='*60}")
    print("TECHNOLOGIES BY CATEGORY")
    print(f"{'='*60}")
    
    for category, techs in sorted(analysis.categories.items()):
        if techs:
            print(f"\n{category.upper()}:")
            for tech in sorted(techs, key=lambda t: t.name):
                status_icon = {
                    'secure': '✓',
                    'vulnerable': '✗',
                    'outdated': '⚠',
                    'unknown': '?'
                }.get(tech.security.status, '?')
                print(f"  {status_icon} {tech.name} {tech.version} (confidence: {tech.confidence:.2f})")
    
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
    
    # Export to JSON file
    output_file = backend_path / 'tech_stack_analysis.json'
    json_output = analyzer.to_dict(analysis)
    
    with open(output_file, 'w') as f:
        json.dump(json_output, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Full analysis exported to: {output_file}")
    print(f"{'='*60}")
    
    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}")


if __name__ == '__main__':
    test_with_real_backend()
