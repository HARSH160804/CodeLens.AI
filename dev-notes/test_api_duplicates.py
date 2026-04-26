#!/usr/bin/env python3
"""
Test script to check for duplicate technologies in API response
"""
import requests
import json

# API endpoint
API_URL = "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"

# Test with your repo ID
REPO_ID = "e914711e-5d3c-47c4-a3cb-149145332521"

print(f"Fetching architecture for repo: {REPO_ID}")
print(f"URL: {API_URL}/repos/{REPO_ID}/architecture")
print("=" * 60)

try:
    response = requests.get(f"{API_URL}/repos/{REPO_ID}/architecture")
    response.raise_for_status()
    
    data = response.json()
    
    tech_stack = data.get('tech_stack', [])
    
    print(f"\nTotal technologies: {len(tech_stack)}")
    print("\nTech Stack from API:")
    print("-" * 60)
    
    # Group by lowercase name to find duplicates
    by_name = {}
    for tech in tech_stack:
        name = tech.get('name', '')
        name_lower = name.lower()
        
        if name_lower not in by_name:
            by_name[name_lower] = []
        by_name[name_lower].append(tech)
    
    # Show all technologies
    for name_lower, techs in sorted(by_name.items()):
        if len(techs) > 1:
            print(f"\n🔴 DUPLICATE: {name_lower}")
            for tech in techs:
                print(f"   - {tech.get('name')} (category: {tech.get('category')}, icon: {tech.get('icon')})")
        else:
            tech = techs[0]
            print(f"✅ {tech.get('name')} (category: {tech.get('category')})")
    
    # Summary
    duplicates = [name for name, techs in by_name.items() if len(techs) > 1]
    if duplicates:
        print(f"\n{'=' * 60}")
        print(f"❌ Found {len(duplicates)} duplicate technology names:")
        for dup in duplicates:
            print(f"   - {dup}")
    else:
        print(f"\n{'=' * 60}")
        print("✅ No duplicates found!")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Error fetching data: {e}")
except json.JSONDecodeError as e:
    print(f"❌ Error parsing JSON: {e}")
