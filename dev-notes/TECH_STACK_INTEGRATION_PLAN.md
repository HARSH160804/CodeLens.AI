# Tech Stack Detection - Integration Plan

## Current State

We now have TWO tech stack detection implementations:

### 1. TechStackDetector (Analysis Module)
**Location**: `backend/lib/analysis/tech_stack_detector.py`
**Purpose**: Integrated with Analysis Engine for architecture analysis
**Status**: Basic implementation (Task 5.1 complete)
**Features**:
- Package file parsing
- File extension detection
- Framework detection
- Returns `List[Technology]` from architecture_models

### 2. TechAnalyzer (Standalone)
**Location**: `backend/lib/tech_analyzer.py`
**Purpose**: Comprehensive standalone tech stack analyzer
**Status**: Phase 2 complete (real file I/O, 60+ tech database)
**Features**:
- ✅ Real file I/O (package.json, requirements.txt)
- ✅ Real import parsing (Python, JavaScript/TypeScript)
- ✅ 60+ technology database with metadata
- ✅ Security status (mock data, ready for OSV API)
- ✅ License detection
- ✅ Usage statistics
- ✅ Confidence scoring
- ✅ Icon system (Simple Icons integration)
- ✅ Recommendations engine
- ✅ Comprehensive error handling
- ✅ JSON export

## Data Model Compatibility

### Architecture Models (analysis module)
```python
@dataclass
class Technology:
    name: str
    category: str
    version: Optional[str]
    icon: Optional[str]
    vulnerabilities: List[Vulnerability]
    license: Optional[str]
    deprecated: bool
    recommended_version: Optional[str]
```

### TechAnalyzer Models (standalone)
```python
@dataclass
class Technology:
    id: str
    name: str
    version: str
    category: str
    icon_svg: str
    description: str
    usage: UsageStats
    security: SecurityInfo
    license: str
    confidence: float
    alternatives: List[str]
```

**Key Differences**:
- TechAnalyzer has MORE fields (id, description, usage, confidence, alternatives)
- TechAnalyzer has nested SecurityInfo with vulnerabilities
- TechAnalyzer has icon_svg (Simple Icons format)
- Architecture model has deprecated flag and recommended_version

## Integration Options

### Option 1: Replace TechStackDetector with TechAnalyzer (Recommended)
**Pros**:
- More comprehensive detection
- Real file I/O already implemented
- Better error handling
- Richer metadata
- Confidence scoring

**Cons**:
- Need to adapt data models
- More complex

**Implementation**:
1. Create adapter to convert TechAnalyzer output to Architecture Technology model
2. Update TechStackDetector to use TechAnalyzer internally
3. Map fields appropriately

### Option 2: Enhance TechStackDetector with TechAnalyzer Features
**Pros**:
- Keeps existing integration
- Gradual migration

**Cons**:
- Duplicate code
- More maintenance

**Implementation**:
1. Copy real file I/O logic from TechAnalyzer
2. Copy technology database
3. Copy import parsing logic

### Option 3: Keep Both (Current State)
**Pros**:
- No changes needed
- Both can evolve independently

**Cons**:
- Code duplication
- Inconsistent results
- Maintenance burden

## Recommended Approach: Option 1 with Adapter

### Step 1: Create Adapter
```python
# backend/lib/analysis/tech_stack_detector.py

from backend.lib.tech_analyzer import TechAnalyzer as ComprehensiveTechAnalyzer
from backend.lib.models.architecture_models import Technology, Vulnerability

class TechStackDetector:
    def __init__(self):
        self.analyzer = ComprehensiveTechAnalyzer()
    
    def detect_tech_stack(self, context: Dict[str, Any]) -> List[Technology]:
        # Use comprehensive analyzer
        repo_path = context.get('repo_path')
        files = context.get('files', [])
        
        analysis = self.analyzer.analyze(repo_path, files)
        
        # Convert to architecture model
        return self._convert_to_architecture_model(analysis.technologies)
    
    def _convert_to_architecture_model(self, techs) -> List[Technology]:
        result = []
        for tech in techs:
            # Map vulnerabilities
            vulns = [
                Vulnerability(
                    cve_id=v.cve_id,
                    severity=v.severity,
                    cvss_score=v.cvss_score,
                    description=v.description,
                    fixed_version=v.fixed_version
                )
                for v in tech.security.vulnerabilities
            ]
            
            # Create architecture Technology
            arch_tech = Technology(
                name=tech.name,
                category=tech.category,
                version=tech.version if tech.version != 'unknown' else None,
                icon=tech.icon_svg,
                vulnerabilities=vulns,
                license=tech.license if tech.license != 'Unknown' else None,
                deprecated=(tech.security.status == 'outdated'),
                recommended_version=None  # Could extract from recommendations
            )
            result.append(arch_tech)
        
        return result
```

### Step 2: Update Analysis Engine
No changes needed - TechStackDetector interface remains the same.

### Step 3: Test Integration
```python
# Test that Analysis Engine still works
context = {
    'repo_path': '/path/to/repo',
    'files': ['package.json', 'requirements.txt', ...]
}

detector = TechStackDetector()
technologies = detector.detect_tech_stack(context)

# Should return List[Technology] compatible with architecture_models
```

## Benefits of Integration

1. **Immediate**: Get real file I/O and 60+ tech database
2. **Confidence Scoring**: Know which detections are reliable
3. **Usage Statistics**: See which techs are actually used
4. **Better Icons**: Simple Icons integration
5. **Recommendations**: Actionable suggestions
6. **Extensibility**: Easy to add Phase 3 features (OSV API, npm audit)

## Next Steps

1. ✅ Phase 2 Complete - TechAnalyzer with real file I/O
2. 🔄 Create adapter in TechStackDetector (30 minutes)
3. 🔄 Test integration with Analysis Engine (30 minutes)
4. 🔄 Update architecture.py handler if needed (15 minutes)
5. 🔄 Run integration tests (15 minutes)
6. ⏭️ Phase 3 - Add OSV API, npm audit, pip-audit

## Timeline

- **Adapter Implementation**: 30 minutes
- **Integration Testing**: 30 minutes
- **Total**: 1 hour to integrate TechAnalyzer into Analysis Engine

## Conclusion

The TechAnalyzer (Phase 2 complete) is production-ready and significantly more capable than the basic TechStackDetector. Integrating it via an adapter pattern will immediately enhance the architecture analysis system with:
- Real file reading
- 60+ technology database
- Confidence scoring
- Usage statistics
- Better error handling
- Richer metadata

This sets the foundation for Phase 3 (security scanning) and Phase 4 (performance optimizations).
