# TechAnalyzer - Production-Grade Tech Stack Detection

## Overview

`TechAnalyzer` is an intelligent technology stack analyzer that detects technologies from multiple sources and provides rich metadata including versions, security status, icons, licenses, and usage statistics.

## Features

### 🔍 Multi-Source Detection
- **Package Files**: package.json, requirements.txt, Gemfile, go.mod, etc.
- **Import Statements**: Analyzes actual code imports
- **Configuration Files**: docker-compose.yml, .github/workflows, etc.
- **File Extensions**: Detects languages from file patterns

### 🛡️ Security Scanning
- Vulnerability detection (CVE database)
- Outdated package identification
- Security status for each technology
- CVSS scores and severity levels

### 🎨 Visual Assets
- Official SVG icons from simple-icons
- Icon caching for performance
- Fallback icons for unknown technologies

### 📊 Rich Metadata
- Exact version detection
- License information
- Usage statistics (files using, import counts)
- Confidence scores
- Alternative technologies

### 💡 Intelligent Recommendations
- Security updates (critical priority)
- Version updates (high priority)
- Security audits (medium priority)
- Actionable next steps

## Installation

```python
from tech_analyzer import TechAnalyzer

analyzer = TechAnalyzer()
```

## Usage

### Basic Analysis

```python
# Analyze repository
analysis = analyzer.analyze(
    repo_path="/path/to/repo",
    files=["package.json", "src/App.tsx", "requirements.txt"]
)

# Access results
print(f"Total technologies: {analysis.summary.total}")
print(f"Secure: {analysis.summary.secure}")
print(f"Vulnerable: {analysis.summary.vulnerable}")
```

### Accessing Technologies

```python
# Iterate through all technologies
for tech in analysis.technologies:
    print(f"{tech.name} {tech.version}")
    print(f"  Category: {tech.category}")
    print(f"  Security: {tech.security.status}")
    print(f"  License: {tech.license}")
    print(f"  Confidence: {tech.confidence}")
```

### Accessing by Category

```python
# Get frontend technologies
frontend_techs = analysis.categories['frontend']
for tech in frontend_techs:
    print(f"{tech.name} - {tech.description}")

# Get backend technologies
backend_techs = analysis.categories['backend']

# Get database technologies
database_techs = analysis.categories['database']
```

### Security Information

```python
# Check for vulnerabilities
for tech in analysis.technologies:
    if tech.security.status == 'vulnerable':
        print(f"{tech.name} has vulnerabilities:")
        for vuln in tech.security.vulnerabilities:
            print(f"  {vuln.cve_id}: {vuln.description}")
            print(f"  Severity: {vuln.severity}")
            print(f"  Fixed in: {vuln.fixed_version}")
```

### Recommendations

```python
# Get actionable recommendations
for rec in analysis.recommendations:
    print(f"{rec.priority.upper()}: {rec.message}")
    print(f"  Type: {rec.type}")
    print(f"  Action: {rec.action}")
    print(f"  Affected: {', '.join(rec.technologies)}")
```

### Export to JSON

```python
# Convert to dictionary for JSON serialization
json_data = analyzer.to_dict(analysis)

import json
print(json.dumps(json_data, indent=2))
```

## Data Structures

### TechStackAnalysis

Main analysis result containing all detected technologies and metadata.

```python
@dataclass
class TechStackAnalysis:
    technologies: List[Technology]
    categories: Dict[str, List[Technology]]
    summary: TechSummary
    recommendations: List[TechRecommendation]
```

### Technology

Complete information about a detected technology.

```python
@dataclass
class Technology:
    id: str                    # react, nodejs, postgresql
    name: str                  # React
    version: str               # 18.2.0
    category: str              # frontend, backend, database, etc.
    icon_svg: str              # SVG string or icon identifier
    description: str           # Technology description
    usage: UsageStats          # Usage statistics
    security: SecurityInfo     # Security status
    license: str               # License type
    confidence: float          # Detection confidence (0-1)
    alternatives: List[str]    # Alternative technologies
```

### SecurityInfo

Security status and vulnerability information.

```python
@dataclass
class SecurityInfo:
    status: str                        # secure, vulnerable, outdated, unknown
    vulnerabilities: List[Vulnerability]
    last_audit: str                    # Last audit date
```

### Vulnerability

Detailed vulnerability information.

```python
@dataclass
class Vulnerability:
    cve_id: str              # CVE-2018-6341
    severity: str            # critical, high, medium, low
    cvss_score: float        # 7.5
    fixed_version: str       # 16.4.2
    description: str         # Vulnerability description
```

### UsageStats

Usage statistics for a technology.

```python
@dataclass
class UsageStats:
    files_using: int         # Number of files using this tech
    total_imports: int       # Total import statements
    percentage: float        # Percentage of files using (0-100)
```

### TechSummary

Summary statistics for the entire tech stack.

```python
@dataclass
class TechSummary:
    total: int                      # Total technologies
    by_category: Dict[str, int]     # Count by category
    secure: int                     # Secure technologies
    vulnerable: int                 # Vulnerable technologies
    outdated: int                   # Outdated technologies
    unknown: int                    # Unknown security status
```

### TechRecommendation

Actionable recommendation for tech stack improvements.

```python
@dataclass
class TechRecommendation:
    type: str                # update, security, alternative, deprecation
    priority: str            # critical, high, medium, low
    message: str             # Recommendation message
    technologies: List[str]  # Affected technologies
    action: str              # Suggested action
```

## Supported Technologies

### Frontend
- React, Vue.js, Angular, Svelte
- Next.js, Nuxt, Gatsby
- TypeScript, JavaScript
- Tailwind CSS, Bootstrap

### Backend
- Express, Fastify, Koa, NestJS
- FastAPI, Flask, Django
- Spring Boot, Ruby on Rails
- Go, Rust frameworks

### Database
- PostgreSQL, MySQL, MariaDB
- MongoDB, CouchDB, Cassandra
- Redis, Memcached
- SQLite, DynamoDB

### DevOps
- Docker, Kubernetes
- GitHub Actions, GitLab CI
- Terraform, Ansible
- AWS, Azure, GCP

### Testing
- Jest, Mocha, Vitest
- pytest, unittest
- JUnit, TestNG
- Cypress, Playwright

### Auth
- Auth0, Okta
- Passport.js, JWT
- OAuth, SAML

## Detection Methods

### 1. Package File Parsing

Exact version detection from:
- `package.json` (Node.js)
- `requirements.txt` (Python)
- `Pipfile` (Python)
- `Gemfile` (Ruby)
- `pom.xml` (Java)
- `go.mod` (Go)
- `Cargo.toml` (Rust)
- `composer.json` (PHP)

**Confidence**: 1.0 (highest)

### 2. Import Statement Analysis

Detects technologies from actual code imports:
- Python: `import fastapi`, `from sqlalchemy import`
- JavaScript: `import React from 'react'`, `require('express')`
- Java: `import org.springframework`
- Go: `import "github.com/gin-gonic/gin"`

**Confidence**: 0.8

### 3. Configuration File Detection

Detects from config files:
- `docker-compose.yml` → Docker
- `Dockerfile` → Docker
- `.github/workflows/*.yml` → GitHub Actions
- `terraform/*.tf` → Terraform
- `k8s/*.yaml` → Kubernetes

**Confidence**: 0.9

### 4. File Extension Analysis

Infers technologies from file patterns:
- `.tsx`, `.jsx` → React (likely)
- `.vue` → Vue.js
- `.py` → Python
- `.go` → Go
- `.rs` → Rust

**Confidence**: 0.7

## Security Scanning

### Vulnerability Database

In production, queries:
- **NVD** (National Vulnerability Database)
- **GitHub Advisory Database**
- **Snyk Vulnerability DB**
- **npm audit** / **pip-audit**

### Security Statuses

- **secure**: No known vulnerabilities, up-to-date version
- **vulnerable**: Known CVEs exist
- **outdated**: Old version, may have security issues
- **unknown**: Unable to determine security status

### Severity Levels

- **critical**: CVSS 9.0-10.0
- **high**: CVSS 7.0-8.9
- **medium**: CVSS 4.0-6.9
- **low**: CVSS 0.1-3.9

## Icon System

### Simple Icons Integration

Icons are sourced from [simple-icons.org](https://simpleicons.org/):

```python
# Icon identifier format
icon_svg = "si:react"  # Simple Icons: react

# Frontend can use:
# https://cdn.simpleicons.org/react
# https://cdn.simpleicons.org/vue
# https://cdn.simpleicons.org/angular
```

### Icon Cache

Icons are cached in memory for performance:

```python
self.icon_cache = {
    'react': 'si:react',
    'vue': 'si:vuedotjs',
    'angular': 'si:angular'
}
```

## Recommendations Engine

### Recommendation Types

1. **Security** (Critical/High)
   - Fix known vulnerabilities
   - Update packages with CVEs
   - Run security audits

2. **Update** (High/Medium)
   - Update outdated packages
   - Migrate to supported versions
   - Review breaking changes

3. **Alternative** (Medium/Low)
   - Consider modern alternatives
   - Evaluate deprecated technologies
   - Assess migration paths

4. **Deprecation** (High)
   - Replace deprecated technologies
   - Plan migration timeline
   - Update documentation

### Priority Levels

- **Critical**: Immediate action required (security vulnerabilities)
- **High**: Action needed soon (outdated packages, deprecations)
- **Medium**: Should be addressed (unknown security status)
- **Low**: Nice to have (alternative suggestions)

## Performance Considerations

### Caching

- Icon cache prevents repeated lookups
- Security database cached in memory
- Detection results deduplicated

### Optimization

- Parallel file processing (future)
- Lazy loading of security data
- Incremental analysis support

## Testing

### Run Tests

```bash
cd backend/lib
python test_tech_analyzer.py
```

### Test Output

```
============================================================
Tech Stack Analyzer - Test Run
============================================================

Analyzing repository...

============================================================
SUMMARY
============================================================
Total Technologies: 12
Secure: 3
Vulnerable: 0
Outdated: 4
Unknown: 5
```

## Integration Examples

### With Analysis Engine

```python
from tech_analyzer import TechAnalyzer
from analysis.engine import AnalysisEngine

# In TechStackDetector
analyzer = TechAnalyzer()
analysis = analyzer.analyze(repo_path, files)

# Convert to Technology objects
technologies = [
    Technology(
        name=tech.name,
        category=tech.category,
        version=tech.version,
        # ... other fields
    )
    for tech in analysis.technologies
]
```

### With API Response

```python
# In architecture handler
analysis = tech_analyzer.analyze(repo_path, files)
json_data = tech_analyzer.to_dict(analysis)

return {
    'statusCode': 200,
    'body': json.dumps({
        'tech_stack': json_data['technologies'],
        'categories': json_data['categories'],
        'summary': json_data['summary'],
        'recommendations': json_data['recommendations']
    })
}
```

## Future Enhancements

### Planned Features

1. **Real Security Scanning**
   - Integration with NVD API
   - GitHub Advisory Database queries
   - Snyk API integration
   - npm audit / pip-audit execution

2. **Real Icon Fetching**
   - Simple Icons API integration
   - SVG caching and optimization
   - Custom icon support

3. **Version Comparison**
   - Latest version checking
   - Semantic version parsing
   - Breaking change detection

4. **License Compliance**
   - License compatibility checking
   - GPL/MIT/Apache analysis
   - Commercial license detection

5. **Dependency Analysis**
   - Transitive dependency detection
   - Dependency tree visualization
   - Circular dependency detection

6. **Performance Optimization**
   - Parallel file processing
   - Incremental analysis
   - Result caching

## API Reference

### TechAnalyzer

```python
class TechAnalyzer:
    def __init__(self)
    def analyze(repo_path: str, files: List[str]) -> TechStackAnalysis
    def to_dict(analysis: TechStackAnalysis) -> Dict
```

### Private Methods

```python
def _detect_from_package_files(repo_path, files) -> List[Technology]
def _detect_from_imports(files) -> List[Technology]
def _detect_from_config(repo_path, files) -> List[Technology]
def _detect_from_extensions(files) -> List[Technology]
def _create_technology(tech_id, version, confidence, source) -> Technology
def _get_official_icon(tech_name) -> str
def _check_security_status(tech_name, version) -> SecurityInfo
def _deduplicate_and_enrich(technologies, files) -> List[Technology]
def _categorize_technologies(technologies) -> Dict[str, List[Technology]]
def _generate_summary(technologies) -> TechSummary
def _generate_recommendations(technologies) -> List[TechRecommendation]
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## Support

For issues and questions, please open a GitHub issue.
