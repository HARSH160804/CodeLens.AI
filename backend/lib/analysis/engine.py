"""
Analysis Engine for Architecture Analysis

Orchestrates all analysis modules and generates comprehensive architecture report.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Use relative imports for Lambda compatibility
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bedrock_client import BedrockClient
from models.architecture_models import (
    ArchitectureAnalysis,
    CodebaseStatistics,
    LegacyArchitecture
)
from analysis.pattern_detector import PatternDetector
from analysis.layer_analyzer import LayerAnalyzer
from analysis.tech_stack_detector import TechStackDetector
from analysis.metrics_calculator import MetricsCalculator
from analysis.dependency_analyzer import DependencyAnalyzer
from analysis.visualization_generator import VisualizationGenerator
from analysis.recommendation_engine import RecommendationEngine
from analysis.data_flow_analyzer import DataFlowAnalyzer
from analysis.confidence_calculator import ConfidenceCalculator
from diagram_generator_v2 import DiagramGenerator

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Orchestrates all analysis modules and generates comprehensive report."""
    
    # Lambda timeout management
    LAMBDA_TIMEOUT = 120  # seconds
    RESERVED_TIME = 10  # seconds for response formatting
    ANALYSIS_TIMEOUT = LAMBDA_TIMEOUT - RESERVED_TIME  # 110 seconds
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize analysis engine.
        
        Args:
            bedrock_client: Optional Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        
        # Initialize Redis client for caching (optional)
        redis_client = None
        try:
            import redis
            redis_host = os.environ.get('REDIS_HOST')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            if redis_host:
                redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                redis_client.ping()
                logger.info("Redis client initialized for TechnologyClassifier caching")
        except Exception as e:
            logger.info(f"Redis not available: {str(e)}, TechnologyClassifier will work without caching")
            redis_client = None
        
        # Initialize all modules
        self.pattern_detector = PatternDetector(self.bedrock_client)
        self.layer_analyzer = LayerAnalyzer(self.bedrock_client)
        self.tech_stack_detector = TechStackDetector(
            bedrock_client=self.bedrock_client,
            redis_client=redis_client
        )
        self.metrics_calculator = MetricsCalculator()
        self.dependency_analyzer = DependencyAnalyzer(self.bedrock_client)
        self.visualization_generator = VisualizationGenerator()  # Keep as fallback
        self.diagram_generator = DiagramGenerator(self.bedrock_client)  # New v2 generator
        self.recommendation_engine = RecommendationEngine(self.bedrock_client)
        self.data_flow_analyzer = DataFlowAnalyzer()
        self.confidence_calculator = ConfidenceCalculator()
    
    def analyze(
        self,
        repo_id: str,
        repo_metadata: Dict[str, Any],
        file_summaries: List[Dict[str, Any]],
        level: str
    ) -> Dict[str, Any]:
        """
        Orchestrate complete architecture analysis.
        
        Args:
            repo_id: Repository identifier
            repo_metadata: Repository metadata from DynamoDB
            file_summaries: File content summaries from vector store
            level: Analysis depth (basic/intermediate/advanced)
            
        Returns:
            Complete architecture analysis result as dictionary
        """
        start_time = time.time()
        errors = {}
        
        try:
            # Build analysis context
            context = self._build_context(repo_metadata, file_summaries, level)
            
            # Execute parallel modules
            parallel_results = self._execute_parallel_modules(context, start_time)
            
            # Extract results
            patterns = parallel_results.get('patterns', [])
            layers = parallel_results.get('layers', [])
            tech_stack = parallel_results.get('tech_stack', [])
            metrics = parallel_results.get('metrics')
            
            # Merge errors
            errors.update(parallel_results.get('errors', {}))
            
            # Execute dependent modules
            dependent_results = self._execute_dependent_modules(
                context,
                patterns,
                layers,
                tech_stack,
                metrics,
                start_time
            )
            
            # Extract dependent results
            dependencies = dependent_results.get('dependencies')
            data_flows = dependent_results.get('data_flows', [])
            visualizations = dependent_results.get('visualizations', {})
            recommendations = dependent_results.get('recommendations', [])
            
            # Merge errors
            errors.update(dependent_results.get('errors', {}))
            
            # Calculate architecture confidence score
            confidence_result = self._calculate_confidence_score(
                layers=layers,
                tech_stack=tech_stack,
                dependencies=dependencies,
                file_summaries=file_summaries
            )
            
            # Calculate statistics
            statistics = self._calculate_statistics(file_summaries, repo_metadata)
            
            # Build legacy architecture for backward compatibility
            legacy_architecture = self._build_legacy_architecture(
                patterns,
                layers,
                visualizations,
                confidence_result.get('confidence', 0.0)
            )
            
            # Calculate execution duration
            execution_duration_ms = int((time.time() - start_time) * 1000)
            
            # Build final response
            analysis = {
                'schema_version': '2.0',
                'repo_id': repo_id,
                'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'execution_duration_ms': execution_duration_ms,
                'analysis_level': level,
                'confidence': confidence_result.get('confidence', 0.0),
                'confidence_signals': confidence_result.get('signals', {}),
                'statistics': statistics,
                'patterns': [self._pattern_to_dict(p) for p in patterns],
                'layers': [self._layer_to_dict(l) for l in layers],
                'tech_stack': [self._technology_to_dict(t) for t in tech_stack],
                'data_flows': [self._dataflow_to_dict(df) for df in data_flows],
                'dependencies': self._dependencies_to_dict(dependencies) if dependencies else {},
                'metrics': self._metrics_to_dict(metrics) if metrics else {},
                'recommendations': [self._recommendation_to_dict(r) for r in recommendations],
                'visualizations': {k: self._visualization_to_dict(v) if hasattr(v, 'diagram_type') else v for k, v in visualizations.items()},
                'architecture': legacy_architecture,
                'diagram': visualizations.get('system_architecture').mermaid if visualizations.get('system_architecture') and hasattr(visualizations.get('system_architecture'), 'mermaid') else ''
            }
            
            # Add errors if any
            if errors:
                analysis['errors'] = errors
                analysis['warnings'] = [f"{module} analysis unavailable" for module in errors.keys()]
            
            logger.info(f"Analysis completed in {execution_duration_ms}ms")
            return analysis
            
        except Exception as e:
            logger.error(f"Fatal error in analysis: {str(e)}")
            # Return partial results with error
            execution_duration_ms = int((time.time() - start_time) * 1000)
            return {
                'schema_version': '2.0',
                'repo_id': repo_id,
                'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'execution_duration_ms': execution_duration_ms,
                'analysis_level': level,
                'error': str(e),
                'status': 'partial_failure'
            }
    
    def _build_context(
        self,
        repo_metadata: Dict[str, Any],
        file_summaries: List[Dict[str, Any]],
        level: str
    ) -> Dict[str, Any]:
        """
        Prepare analysis context.
        
        Args:
            repo_metadata: Repository metadata
            file_summaries: File summaries
            level: Analysis level
            
        Returns:
            Analysis context dictionary
        """
        return {
            'repo_metadata': repo_metadata,
            'file_summaries': file_summaries,
            'level': level
        }
    
    def _execute_parallel_modules(
        self,
        context: Dict[str, Any],
        start_time: float
    ) -> Dict[str, Any]:
        """
        Run independent modules concurrently.
        
        Args:
            context: Analysis context
            start_time: Start timestamp
            
        Returns:
            Dictionary with results and errors
        """
        results = {}
        errors = {}
        
        # Check timeout
        if time.time() - start_time > self.ANALYSIS_TIMEOUT:
            logger.warning("Timeout reached before parallel execution")
            return {'errors': {'timeout': 'Analysis timeout'}}
        
        # Execute modules in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.pattern_detector.detect_patterns, context): 'patterns',
                executor.submit(self.layer_analyzer.analyze_layers, context): 'layers',
                executor.submit(self.tech_stack_detector.detect_tech_stack, context): 'tech_stack',
            }
            
            for future in as_completed(futures):
                module_name = futures[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout per module
                    results[module_name] = result
                except Exception as e:
                    logger.error(f"Module {module_name} failed: {str(e)}")
                    errors[module_name] = str(e)
                    results[module_name] = [] if module_name != 'metrics' else None
        
        # Calculate metrics (depends on layers)
        try:
            layers = results.get('layers', [])
            metrics = self.metrics_calculator.calculate_metrics(context, layers)
            results['metrics'] = metrics
        except Exception as e:
            logger.error(f"Metrics calculation failed: {str(e)}")
            errors['metrics'] = str(e)
            results['metrics'] = None
        
        results['errors'] = errors
        return results
    
    def _execute_dependent_modules(
        self,
        context: Dict[str, Any],
        patterns: List,
        layers: List,
        tech_stack: List,
        metrics: Any,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Run modules that depend on earlier results.
        
        Args:
            context: Analysis context
            patterns: Detected patterns
            layers: Detected layers
            tech_stack: Detected technologies
            metrics: Quality metrics
            start_time: Start timestamp
            
        Returns:
            Dictionary with results and errors
        """
        results = {}
        errors = {}
        
        # Check timeout
        if time.time() - start_time > self.ANALYSIS_TIMEOUT:
            logger.warning("Timeout reached before dependent execution")
            return {'errors': {'timeout': 'Analysis timeout'}}
        
        # Dependency analysis
        try:
            dependencies = self.dependency_analyzer.analyze_dependencies(context)
            results['dependencies'] = dependencies
        except Exception as e:
            logger.error(f"Dependency analysis failed: {str(e)}")
            errors['dependencies'] = str(e)
            results['dependencies'] = None
        
        # Data flow analysis
        try:
            data_flows = self.data_flow_analyzer.generate_data_flows(context, layers)
            results['data_flows'] = data_flows
        except Exception as e:
            logger.error(f"Data flow analysis failed: {str(e)}")
            errors['data_flows'] = str(e)
            results['data_flows'] = []
        
        # Visualization generation
        try:
            # Use new DiagramGenerator v2 for enhanced visualizations
            visualizations = {}
            
            # Generate system architecture diagram
            components_for_diagram = []
            for layer in layers:
                for comp in layer.components:
                    components_for_diagram.append({
                        'name': comp.name,
                        'type': comp.type,
                        'file_path': comp.file_path,
                        'health_score': comp.health_score,
                        'complexity_score': comp.complexity_score,
                        'line_count': comp.line_count,
                        'dependencies': comp.dependencies
                    })
            
            # Generate system architecture with layered layout
            system_arch_output = self.diagram_generator.generate_system_architecture(
                components=components_for_diagram,
                layout='layered'
            )
            
            # Convert DiagramOutput to Visualization format for backward compatibility
            visualizations['system_architecture'] = self._diagram_output_to_visualization(
                system_arch_output,
                'system_architecture'
            )
            
            # Generate data flow scenarios
            data_flow_scenarios = self.diagram_generator.generate_data_flow_scenarios(
                repo_path=context.get('repo_metadata', {}).get('repo_path', ''),
                entry_points=[],
                components=components_for_diagram
            )
            
            # Store scenarios in visualizations
            visualizations['data_flow_scenarios'] = data_flow_scenarios
            
            # Generate tech stack cards
            tech_stack_cards = self.diagram_generator.generate_tech_stack_cards(
                [self._technology_to_dict(t) for t in tech_stack]
            )
            visualizations['tech_stack_cards'] = tech_stack_cards
            
            # Fallback to old generator for other diagram types if needed
            try:
                analysis_data = {
                    'patterns': patterns,
                    'layers': layers,
                    'tech_stack': tech_stack,
                    'dependencies': results.get('dependencies'),
                    'data_flows': results.get('data_flows', [])
                }
                legacy_visualizations = self.visualization_generator.generate_visualizations(analysis_data)
                
                # Add dependency_graph and layer_diagram from legacy generator
                if 'dependency_graph' in legacy_visualizations:
                    visualizations['dependency_graph'] = legacy_visualizations['dependency_graph']
                if 'layer_diagram' in legacy_visualizations:
                    visualizations['layer_diagram'] = legacy_visualizations['layer_diagram']
            except Exception as e:
                logger.warning(f"Legacy visualization generation failed: {str(e)}")
            
            results['visualizations'] = visualizations
        except Exception as e:
            logger.error(f"Visualization generation failed: {str(e)}")
            errors['visualizations'] = str(e)
            results['visualizations'] = {}
        
        # Recommendation engine (runs last)
        try:
            analysis_results = {
                'patterns': patterns,
                'layers': layers,
                'tech_stack': tech_stack,
                'metrics': metrics,
                'dependencies': results.get('dependencies')
            }
            recommendations = self.recommendation_engine.generate_recommendations(analysis_results)
            results['recommendations'] = recommendations
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            errors['recommendations'] = str(e)
            results['recommendations'] = []
        
        results['errors'] = errors
        return results
    
    def _calculate_statistics(
        self,
        file_summaries: List[Dict[str, Any]],
        repo_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate codebase statistics."""
        total_files = len(file_summaries)
        total_lines = sum(f.get('line_count', 0) for f in file_summaries)
        
        # Language breakdown
        language_breakdown = {}
        for f in file_summaries:
            file_path = f.get('file_path', '')
            if '.' in file_path:
                ext = '.' + file_path.split('.')[-1]
                language_breakdown[ext] = language_breakdown.get(ext, 0) + 1
        
        # Find largest file
        largest_file = max(file_summaries, key=lambda f: f.get('line_count', 0)) if file_summaries else {}
        
        # Calculate folder depth
        max_depth = max(f.get('file_path', '').count('/') for f in file_summaries) if file_summaries else 0
        
        return {
            'total_files': total_files,
            'total_lines': total_lines,
            'primary_language': repo_metadata.get('primary_language', 'Unknown'),
            'language_breakdown': language_breakdown,
            'folder_depth': max_depth,
            'largest_file': {
                'path': largest_file.get('file_path', ''),
                'lines': largest_file.get('line_count', 0)
            }
        }
    
    def _calculate_confidence_score(
        self,
        layers: List,
        tech_stack: List,
        dependencies: Any,
        file_summaries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate architecture confidence score using ConfidenceCalculator.
        
        Args:
            layers: Detected architecture layers
            tech_stack: Detected technologies
            dependencies: Dependency analysis result
            file_summaries: List of file summaries
            
        Returns:
            Dict containing confidence score and signal breakdown
        """
        try:
            result = self.confidence_calculator.calculate_confidence(
                layers=layers,
                tech_stack=tech_stack,
                dependencies=dependencies,
                file_summaries=file_summaries
            )
            logger.info(f"Architecture confidence score: {result['confidence']:.2f}")
            return result
        except Exception as e:
            logger.error(f"Failed to calculate confidence score: {str(e)}")
            # Return default confidence
            return {
                'confidence': 0.5,
                'signals': {},
                'error': str(e)
            }
    
    def _diagram_output_to_visualization(self, diagram_output, diagram_type: str):
        """
        Convert DiagramGenerator v2 DiagramOutput to Visualization format.
        
        Args:
            diagram_output: DiagramOutput from DiagramGenerator v2
            diagram_type: Type of diagram
            
        Returns:
            Visualization object compatible with existing API
        """
        from models.architecture_models import Visualization, VisualizationMetadata
        
        # Extract interactive data
        interactive = diagram_output.interactive
        metadata = diagram_output.metadata
        
        # Convert interactive JSON to D3 and Cytoscape formats
        d3_json = {
            'nodes': interactive.get('nodes', []),
            'links': [
                {
                    'source': edge['source'],
                    'target': edge['target'],
                    'label': edge.get('label'),
                    'type': edge.get('type')
                }
                for edge in interactive.get('edges', [])
            ]
        }
        
        cytoscape_json = {
            'elements': {
                'nodes': [
                    {'data': node}
                    for node in interactive.get('nodes', [])
                ],
                'edges': [
                    {
                        'data': {
                            'id': f"{edge['source']}-{edge['target']}",
                            'source': edge['source'],
                            'target': edge['target'],
                            'label': edge.get('label'),
                            'type': edge.get('type')
                        }
                    }
                    for edge in interactive.get('edges', [])
                ]
            },
            'layout': {
                'name': metadata.get('layout_algorithm', 'layered')
            }
        }
        
        return Visualization(
            diagram_type=diagram_type,
            mermaid=diagram_output.mermaid,
            d3_json=d3_json,
            cytoscape_json=cytoscape_json,
            metadata=VisualizationMetadata(
                node_count=metadata.get('node_count', 0),
                edge_count=metadata.get('edge_count', 0),
                layout_hints=interactive.get('viewport', {}),
                interaction_handlers={
                    'node_click': 'show_component_details',
                    'edge_click': 'show_connection_details',
                    'zoom': 'enabled',
                    'pan': 'enabled'
                }
            )
        )
    
    def _build_legacy_architecture(
        self,
        patterns: List,
        layers: List,
        visualizations: Dict,
        confidence: float = 0.0
    ) -> Dict[str, Any]:
        """Build legacy v1.0 architecture format for backward compatibility."""
        # Extract primary pattern
        primary_pattern = patterns[0] if patterns else None
        
        # Build components list
        components = []
        for layer in layers:
            for component in layer.components[:3]:  # Limit to 3 per layer
                components.append({
                    'name': component.name,
                    'type': component.type,
                    'file_path': component.file_path,
                    'role': layer.name
                })
        
        # Build data flow steps
        data_flow_steps = [
            'Client sends request',
            'API layer processes request',
            'Business logic executes',
            'Data layer queries database',
            'Response returned to client'
        ]
        
        # Get mermaid diagram
        mermaid_diagram = ''
        if visualizations.get('system_architecture'):
            mermaid_diagram = visualizations['system_architecture'].mermaid
        
        return {
            'overview': f"Architecture analysis for repository",
            'architectureStyle': primary_pattern.name if primary_pattern else 'Unknown',
            'components': components,
            'dataFlowSteps': data_flow_steps,
            'mermaidDiagram': mermaid_diagram,
            'confidence': confidence  # Use calculated confidence instead of pattern confidence
        }
    
    # Conversion methods to dictionaries
    def _pattern_to_dict(self, pattern) -> Dict[str, Any]:
        """Convert DetectedPattern to dictionary."""
        return {
            'name': pattern.name,
            'confidence': pattern.confidence,
            'evidence_files': pattern.evidence_files,
            'description': pattern.description,
            'pros': pattern.pros,
            'cons': pattern.cons,
            'alternatives': pattern.alternatives
        }
    
    def _layer_to_dict(self, layer) -> Dict[str, Any]:
        """Convert Layer to dictionary."""
        return {
            'name': layer.name,
            'description': layer.description,
            'components': [self._component_to_dict(c) for c in layer.components],
            'technologies': layer.technologies,
            'entry_points': layer.entry_points,
            'connections': [self._connection_to_dict(c) for c in layer.connections]
        }
    
    def _component_to_dict(self, component) -> Dict[str, Any]:
        """Convert Component to dictionary."""
        return {
            'name': component.name,
            'type': component.type,
            'file_path': component.file_path,
            'line_count': component.line_count,
            'complexity_score': component.complexity_score,
            'dependencies': component.dependencies,
            'health_score': component.health_score,
            'responsibilities': component.responsibilities
        }
    
    def _connection_to_dict(self, connection) -> Dict[str, Any]:
        """Convert LayerConnection to dictionary."""
        return {
            'from_layer': connection.from_layer,
            'to_layer': connection.to_layer,
            'connection_type': connection.connection_type,
            'file_paths': connection.file_paths
        }
    
    def _technology_to_dict(self, tech) -> Dict[str, Any]:
        """Convert Technology to dictionary."""
        return {
            'name': tech.name,
            'category': tech.category,
            'icon': tech.icon,
            'version': tech.version,
            'latest_version': tech.latest_version,
            'is_deprecated': tech.is_deprecated,
            'deprecation_warning': tech.deprecation_warning,
            'license': tech.license,
            'vulnerabilities': [self._vulnerability_to_dict(v) for v in tech.vulnerabilities]
        }
    
    def _vulnerability_to_dict(self, vuln) -> Dict[str, Any]:
        """Convert Vulnerability to dictionary."""
        return {
            'cve_id': vuln.cve_id,
            'severity': vuln.severity,
            'description': vuln.description,
            'fixed_version': vuln.fixed_version,
            'cvss_score': vuln.cvss_score
        }
    
    def _dataflow_to_dict(self, dataflow) -> Dict[str, Any]:
        """Convert DataFlowScenario to dictionary."""
        return {
            'name': dataflow.name,
            'description': dataflow.description,
            'steps': [self._flowstep_to_dict(s) for s in dataflow.steps],
            'bottlenecks': [self._bottleneck_to_dict(b) for b in dataflow.bottlenecks]
        }
    
    def _flowstep_to_dict(self, step) -> Dict[str, Any]:
        """Convert FlowStep to dictionary."""
        return {
            'step_number': step.step_number,
            'component': step.component,
            'action': step.action,
            'next_steps': step.next_steps,
            'is_conditional': step.is_conditional
        }
    
    def _bottleneck_to_dict(self, bottleneck) -> Dict[str, Any]:
        """Convert Bottleneck to dictionary."""
        return {
            'location': bottleneck.location,
            'severity': bottleneck.severity,
            'description': bottleneck.description,
            'suggested_optimization': bottleneck.suggested_optimization
        }
    
    def _dependencies_to_dict(self, dependencies) -> Dict[str, Any]:
        """Convert DependencyAnalysis to dictionary."""
        if not dependencies:
            return {}
        
        return {
            'dependency_tree': self._deptree_to_dict(dependencies.dependency_tree),
            'circular_dependencies': [self._circular_to_dict(c) for c in dependencies.circular_dependencies],
            'outdated_packages': [self._outdated_to_dict(o) for o in dependencies.outdated_packages],
            'vulnerabilities': [],
            'license_issues': []
        }
    
    def _deptree_to_dict(self, tree) -> Dict[str, Any]:
        """Convert DependencyTree to dictionary."""
        return {
            'root': self._depnode_to_dict(tree.root),
            'total_dependencies': tree.total_dependencies,
            'max_depth': tree.max_depth
        }
    
    def _depnode_to_dict(self, node) -> Dict[str, Any]:
        """Convert DependencyNode to dictionary."""
        return {
            'package_name': node.package_name,
            'version': node.version,
            'license': node.license,
            'depth': node.depth,
            'children': [self._depnode_to_dict(c) for c in node.children],
            'security_status': node.security_status
        }
    
    def _circular_to_dict(self, circular) -> Dict[str, Any]:
        """Convert CircularDependency to dictionary."""
        return {
            'cycle_path': circular.cycle_path,
            'severity': circular.severity,
            'description': circular.description
        }
    
    def _outdated_to_dict(self, outdated) -> Dict[str, Any]:
        """Convert OutdatedPackage to dictionary."""
        return {
            'package_name': outdated.package_name,
            'current_version': outdated.current_version,
            'latest_version': outdated.latest_version,
            'versions_behind': outdated.versions_behind
        }
    
    def _metrics_to_dict(self, metrics) -> Dict[str, Any]:
        """Convert QualityMetrics to dictionary."""
        if not metrics:
            return {}
        
        return {
            'health_score': metrics.health_score,
            'complexity_metrics': {
                'average_cyclomatic': metrics.complexity_metrics.average_cyclomatic,
                'average_cognitive': metrics.complexity_metrics.average_cognitive,
                'max_cyclomatic': metrics.complexity_metrics.max_cyclomatic,
                'max_cognitive': metrics.complexity_metrics.max_cognitive,
                'high_complexity_files': metrics.complexity_metrics.high_complexity_files
            },
            'hotspots': [self._hotspot_to_dict(h) for h in metrics.hotspots],
            'technical_debt': {
                'code_duplication_percentage': metrics.technical_debt.code_duplication_percentage,
                'duplicated_blocks': [],
                'test_coverage_gaps': metrics.technical_debt.test_coverage_gaps,
                'estimated_debt_hours': metrics.technical_debt.estimated_debt_hours
            }
        }
    
    def _hotspot_to_dict(self, hotspot) -> Dict[str, Any]:
        """Convert Hotspot to dictionary."""
        return {
            'file_path': hotspot.file_path,
            'type': hotspot.type,
            'complexity_score': hotspot.complexity_score,
            'change_frequency': hotspot.change_frequency,
            'severity': hotspot.severity,
            'recommendation': hotspot.recommendation
        }
    
    def _recommendation_to_dict(self, rec) -> Dict[str, Any]:
        """Convert Recommendation to dictionary."""
        return {
            'id': rec.id,
            'category': rec.category,
            'title': rec.title,
            'description': rec.description,
            'priority': rec.priority,
            'estimated_effort': rec.estimated_effort,
            'expected_impact': rec.expected_impact,
            'file_paths': rec.file_paths,
            'code_locations': [self._codelocation_to_dict(c) for c in rec.code_locations],
            'rationale': rec.rationale
        }
    
    def _codelocation_to_dict(self, location) -> Dict[str, Any]:
        """Convert CodeLocation to dictionary."""
        return {
            'file_path': location.file_path,
            'line_start': location.line_start,
            'line_end': location.line_end,
            'snippet': location.snippet
        }
    
    def _visualization_to_dict(self, viz) -> Dict[str, Any]:
        """Convert Visualization to dictionary."""
        return {
            'diagram_type': viz.diagram_type,
            'mermaid': viz.mermaid,
            'd3_json': viz.d3_json,
            'cytoscape_json': viz.cytoscape_json,
            'metadata': {
                'node_count': viz.metadata.node_count,
                'edge_count': viz.metadata.edge_count,
                'layout_hints': viz.metadata.layout_hints,
                'interaction_handlers': viz.metadata.interaction_handlers
            }
        }
