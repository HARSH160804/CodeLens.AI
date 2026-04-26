# TechAnalyzer - Quick Reference

## Import

```python
from tech_analyzer import TechAnalyzer
```

## Basic Usage

```python
# Initialize
analyzer = TechAnalyzer()

# Analyze
analysis = analyzer.analyze(repo_path, files)

# Summary
print(f"Total: {analysis.summary.total}")
print(f"Secure: {analysis.summary.secure}")
print(f"Vulnerable: {analysis.summary.vulnerable}")
```

## Access Technologies

```python
# All technologies
for tech in analysis.technologies:
    print(f"{tech.name} {tech.version} - {tech.security.status}")

# By category
frontend = analysis.categories['frontend']
backend = analysis.categories['backend']
database = analysis.categories['database']
```

## Security Check

```python
# Find vulnerabilities
for tech in analysis.technologies:
    if tech.security.status == 'vulnerable':
        for vuln in tech.security.vulnerabilities:
            print(f"{vuln.cve_id}: {vuln.severity}")
```

## Recommendations

```python
# Get recommendations
for rec in analysis.recommendations:
    print(f"{rec.priority}: {rec.message}")
    print(f"Action: {rec.action}")
```

## Export JSON

```python
json_data = analyzer.to_dict(analysis)
import json
print(json.dumps(json_data, indent=2))
```

## Data Structures

### Technology
```python
tech.id              # react
tech.name            # React
tech.version         # 18.2.0
tech.category        # frontend
tech.icon_svg        # si:react
tech.description     # Description
tech.usage           # UsageStats
tech.security        # SecurityInfo
tech.license         # MIT
tech.confidence      # 0.0-1.0
tech.alternatives    # [Vue, Angular]
```

### SecurityInfo
```python
security.status           # secure/vulnerable/outdated/unknown
security.vulnerabilities  # List[Vulnerability]
security.last_audit       # 2024-01-15
```

### UsageStats
```python
usage.files_using    # 15
usage.total_imports  # 42
usage.percentage     # 12.5
```

### Summary
```python
summary.total        # 12
summary.by_category  # {frontend: 3, backend: 4}
summary.secure       # 8
summary.vulnerable   # 1
summary.outdated     # 2
summary.unknown      # 1
```

## Detection Methods

| Method | Confidence | Source |
|--------|------------|--------|
| Package files | 1.0 | package.json, requirements.txt |
| Imports | 0.8 | Source code analysis |
| Config files | 0.9 | docker-compose.yml |
| Extensions | 0.7 | .tsx, .py, .go |

## Security Statuses

| Status | Icon | Meaning |
|--------|------|---------|
| secure | ✓ | No vulnerabilities |
| vulnerable | ✗ | Known CVEs |
| outdated | ⚠ | Old version |
| unknown | ? | Unknown status |

## Recommendation Priorities

| Priority | Icon | Action |
|----------|------|--------|
| critical | 🔴 | Immediate |
| high | 🟠 | Soon |
| medium | 🟡 | Should address |
| low | 🟢 | Nice to have |

## Categories

- `frontend`: React, Vue, Angular, TypeScript
- `backend`: Express, FastAPI, Flask, Django
- `database`: PostgreSQL, MySQL, MongoDB, Redis
- `devops`: Docker, Kubernetes, AWS
- `testing`: Jest, pytest, Mocha
- `auth`: Auth0, JWT, OAuth

## Icon Format

```python
icon_svg = "si:react"  # Simple Icons identifier

# Frontend usage:
# https://cdn.simpleicons.org/react
# https://cdn.simpleicons.org/vue
```

## Test

```bash
cd backend/lib
python test_tech_analyzer.py
```

## Files

- `backend/lib/tech_analyzer.py` - Main implementation
- `backend/lib/test_tech_analyzer.py` - Test script
- `TECH_ANALYZER_DOCUMENTATION.md` - Full docs
- `TECH_ANALYZER_SUMMARY.md` - Summary
- `TECH_ANALYZER_QUICK_REFERENCE.md` - This file
