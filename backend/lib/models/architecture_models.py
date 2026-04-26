"""
Data models for Enhanced Architecture Analysis System

All dataclasses representing the architecture analysis domain.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Vulnerability:
    """Security vulnerability information."""
    cve_id: str
    severity: str  # critical/high/medium/low
    description: str
    fixed_version: Optional[str] = None
    cvss_score: Optional[float] = None


@dataclass
class Technology:
    """Detected technology with metadata."""
    name: str
    category: str  # e.g., "framework", "library", "database"
    icon: str  # Icon identifier for UI
    version: Optional[str] = None
    latest_version: Optional[str] = None
    is_deprecated: bool = False
    deprecation_warning: Optional[str] = None
    license: Optional[str] = None
    vulnerabilities: List[Vulnerability] = field(default_factory=list)


@dataclass
class DetectedPattern:
    """Architectural pattern detection result."""
    name: str  # e.g., "MVC", "Microservices"
    confidence: float  # 0.0 to 1.0
    evidence_files: List[str]  # File paths supporting detection
    description: str
    pros: List[str]
    cons: List[str]
    alternatives: List[str]


@dataclass
class LayerConnection:
    """Connection between layers."""
    from_layer: str
    to_layer: str
    connection_type: str  # e.g., "API call", "Database query"
    file_paths: List[str]


@dataclass
class Component:
    """Component within a layer."""
    name: str
    type: str  # e.g., "Controller", "Service", "Repository"
    file_path: str
    line_count: int
    complexity_score: float
    dependencies: List[str]  # Other component names
    health_score: float  # 0-100
    responsibilities: List[str]


@dataclass
class Layer:
    """Architectural layer with components."""
    name: str  # presentation/api/business/data/infrastructure
    description: str
    components: List[Component]
    technologies: List[str]
    entry_points: List[str]  # File paths
    connections: List[LayerConnection]


@dataclass
class FlowStep:
    """Single step in data flow."""
    step_number: int
    component: str
    action: str
    next_steps: List[int]  # Possible next step numbers (for branching)
    is_conditional: bool


@dataclass
class Bottleneck:
    """Performance bottleneck in data flow."""
    location: str  # Component or file path
    severity: str  # critical/high/medium/low
    description: str
    suggested_optimization: str


@dataclass
class DataFlowScenario:
    """Data flow execution path."""
    name: str  # e.g., "Happy Path", "Error Handling"
    description: str
    steps: List[FlowStep]
    bottlenecks: List[Bottleneck]


@dataclass
class DependencyNode:
    """Node in dependency tree."""
    package_name: str
    version: str
    license: Optional[str]
    depth: int
    children: List['DependencyNode']
    security_status: str  # secure/vulnerable/unknown


@dataclass
class DependencyTree:
    """Hierarchical dependency tree."""
    root: DependencyNode
    total_dependencies: int
    max_depth: int


@dataclass
class CircularDependency:
    """Circular dependency cycle."""
    cycle_path: List[str]  # [A, B, C, A]
    severity: str  # critical/high/medium
    description: str


@dataclass
class OutdatedPackage:
    """Outdated package information."""
    package_name: str
    current_version: str
    latest_version: str
    versions_behind: int


@dataclass
class DependencyVulnerability:
    """Vulnerability in dependency."""
    package_name: str
    version: str
    vulnerability: Vulnerability


@dataclass
class LicenseIssue:
    """License compatibility issue."""
    package_name: str
    license: str
    conflict_with: str
    description: str


@dataclass
class DependencyAnalysis:
    """Complete dependency analysis."""
    dependency_tree: DependencyTree
    circular_dependencies: List[CircularDependency]
    outdated_packages: List[OutdatedPackage]
    vulnerabilities: List[DependencyVulnerability]
    license_issues: List[LicenseIssue]


@dataclass
class ComplexityMetrics:
    """Complexity measurements."""
    average_cyclomatic: float
    average_cognitive: float
    max_cyclomatic: float
    max_cognitive: float
    high_complexity_files: List[str]


@dataclass
class DuplicatedBlock:
    """Duplicated code block."""
    files: List[str]
    line_count: int
    similarity_percentage: float


@dataclass
class TechnicalDebt:
    """Technical debt indicators."""
    code_duplication_percentage: float
    duplicated_blocks: List[DuplicatedBlock]
    test_coverage_gaps: List[str]  # File paths without tests
    estimated_debt_hours: float


@dataclass
class Hotspot:
    """Code hotspot (high complexity or change frequency)."""
    file_path: str
    type: str  # complexity/change_frequency/performance
    complexity_score: float
    change_frequency: Optional[int]
    severity: str  # critical/high/medium/low
    recommendation: str


@dataclass
class QualityMetrics:
    """Code quality metrics."""
    health_score: float  # 0-100
    complexity_metrics: ComplexityMetrics
    hotspots: List[Hotspot]
    technical_debt: TechnicalDebt


@dataclass
class CodeLocation:
    """Specific code location."""
    file_path: str
    line_start: int
    line_end: int
    snippet: Optional[str] = None


@dataclass
class Recommendation:
    """Improvement recommendation."""
    id: str
    category: str  # refactoring/security/scalability
    title: str
    description: str
    priority: str  # critical/high/medium/low
    estimated_effort: str  # hours or story points
    expected_impact: str  # high/medium/low
    file_paths: List[str]
    code_locations: List[CodeLocation]
    rationale: str


@dataclass
class VisualizationMetadata:
    """Metadata for interactive visualizations."""
    node_count: int
    edge_count: int
    layout_hints: Dict[str, Any]
    interaction_handlers: Dict[str, str]  # {node_id: handler_type}


@dataclass
class Visualization:
    """Diagram visualization in multiple formats."""
    diagram_type: str  # system_architecture/data_flow/dependency_graph/layer_diagram
    mermaid: str  # Mermaid syntax
    d3_json: Dict[str, Any]  # D3.js compatible format
    cytoscape_json: Dict[str, Any]  # Cytoscape.js compatible format
    metadata: VisualizationMetadata


@dataclass
class LegacyArchitecture:
    """Legacy v1.0 architecture format for backward compatibility."""
    overview: str
    architectureStyle: str
    components: List[Dict[str, Any]]
    dataFlowSteps: List[str]
    mermaidDiagram: str
    confidence: float


@dataclass
class CodebaseStatistics:
    """Codebase metrics and statistics."""
    total_files: int
    total_lines: int
    primary_language: str
    language_breakdown: Dict[str, int]  # {extension: file_count}
    folder_depth: int
    largest_file: Dict[str, Any]  # {path: str, lines: int}


@dataclass
class ArchitectureAnalysis:
    """Complete architecture analysis result."""
    
    # Metadata
    schema_version: str  # "2.0" for enhanced version
    repo_id: str
    generated_at: str  # ISO 8601 timestamp
    execution_duration_ms: int
    analysis_level: str  # basic/intermediate/advanced
    
    # Codebase statistics
    statistics: CodebaseStatistics
    
    # Analysis results
    patterns: List[DetectedPattern]
    layers: List[Layer]
    tech_stack: List[Technology]
    data_flows: List[DataFlowScenario]
    dependencies: DependencyAnalysis
    metrics: QualityMetrics
    recommendations: List[Recommendation]
    visualizations: Dict[str, Visualization]
    
    # Backward compatibility (v1.0 fields)
    architecture: LegacyArchitecture
    diagram: str  # Mermaid diagram for backward compatibility
