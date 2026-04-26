"""
Recommendation Engine for Architecture Analysis

Generates actionable improvement recommendations.
"""

import json
import logging
from typing import List, Dict, Any

from bedrock_client import BedrockClient
from models.architecture_models import Recommendation, CodeLocation

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generates actionable improvement recommendations."""
    
    CATEGORIES = ['refactoring', 'security', 'scalability']
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize recommendation engine.
        
        Args:
            bedrock_client: Optional Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def generate_recommendations(
        self,
        analysis_results: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        Generate improvement recommendations.
        
        Args:
            analysis_results: Combined results from all modules
            
        Returns:
            Prioritized list of recommendations
        """
        try:
            recommendations = []
            
            # Generate recommendations from different sources
            recommendations.extend(self._recommendations_from_patterns(analysis_results))
            recommendations.extend(self._recommendations_from_metrics(analysis_results))
            recommendations.extend(self._recommendations_from_dependencies(analysis_results))
            recommendations.extend(self._recommendations_from_hotspots(analysis_results))
            
            # Prioritize security recommendations
            recommendations = self._prioritize_security(recommendations)
            
            # Calculate effort and impact
            for rec in recommendations:
                rec.estimated_effort = self._calculate_effort(rec)
                rec.expected_impact = self._calculate_impact(rec)
            
            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations[:20]  # Limit to top 20
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def _recommendations_from_patterns(self, analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations from detected patterns."""
        recommendations = []
        patterns = analysis_results.get('patterns', [])
        
        for pattern in patterns:
            # Low confidence patterns suggest architectural improvements
            if pattern.confidence < 0.7:
                rec = Recommendation(
                    id=f"rec-pattern-{pattern.name.lower().replace(' ', '-')}",
                    category='refactoring',
                    title=f"Strengthen {pattern.name} pattern implementation",
                    description=f"The {pattern.name} pattern is detected with low confidence ({pattern.confidence:.2f}). "
                               f"Consider refactoring to better align with this pattern.",
                    priority='medium',
                    estimated_effort='',
                    expected_impact='',
                    file_paths=pattern.evidence_files[:5],
                    code_locations=[],
                    rationale=f"Clear architectural patterns improve maintainability and team understanding"
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _recommendations_from_metrics(self, analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations from quality metrics."""
        recommendations = []
        metrics = analysis_results.get('metrics')
        
        if not metrics:
            return recommendations
        
        # High complexity recommendation
        if metrics.complexity_metrics.average_cyclomatic > 10:
            rec = Recommendation(
                id='rec-complexity-high',
                category='refactoring',
                title='Reduce code complexity',
                description=f"Average cyclomatic complexity is {metrics.complexity_metrics.average_cyclomatic:.1f}, "
                           f"which is above the recommended threshold of 10.",
                priority='high',
                estimated_effort='',
                expected_impact='',
                file_paths=metrics.complexity_metrics.high_complexity_files,
                code_locations=[],
                rationale='High complexity makes code harder to understand, test, and maintain'
            )
            recommendations.append(rec)
        
        # Code duplication recommendation
        if metrics.technical_debt.code_duplication_percentage > 10:
            rec = Recommendation(
                id='rec-duplication',
                category='refactoring',
                title='Reduce code duplication',
                description=f"Code duplication is at {metrics.technical_debt.code_duplication_percentage:.1f}%, "
                           f"above the recommended 10% threshold.",
                priority='medium',
                estimated_effort='',
                expected_impact='',
                file_paths=[block.files[0] for block in metrics.technical_debt.duplicated_blocks[:5]],
                code_locations=[],
                rationale='Code duplication increases maintenance burden and bug risk'
            )
            recommendations.append(rec)
        
        # Test coverage recommendation
        if len(metrics.technical_debt.test_coverage_gaps) > 10:
            rec = Recommendation(
                id='rec-test-coverage',
                category='refactoring',
                title='Improve test coverage',
                description=f"{len(metrics.technical_debt.test_coverage_gaps)} files lack test coverage.",
                priority='medium',
                estimated_effort='',
                expected_impact='',
                file_paths=metrics.technical_debt.test_coverage_gaps[:10],
                code_locations=[],
                rationale='Comprehensive tests prevent regressions and enable confident refactoring'
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _recommendations_from_dependencies(self, analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations from dependency analysis."""
        recommendations = []
        dependencies = analysis_results.get('dependencies')
        
        if not dependencies:
            return recommendations
        
        # Circular dependencies
        if dependencies.circular_dependencies:
            for circ_dep in dependencies.circular_dependencies[:3]:  # Top 3
                rec = Recommendation(
                    id=f"rec-circular-{len(recommendations)}",
                    category='refactoring',
                    title='Resolve circular dependency',
                    description=circ_dep.description,
                    priority=circ_dep.severity,
                    estimated_effort='',
                    expected_impact='',
                    file_paths=circ_dep.cycle_path,
                    code_locations=[],
                    rationale='Circular dependencies make code harder to test and can cause import issues'
                )
                recommendations.append(rec)
        
        # Outdated packages
        if dependencies.outdated_packages:
            rec = Recommendation(
                id='rec-outdated-packages',
                category='security',
                title='Update outdated packages',
                description=f"{len(dependencies.outdated_packages)} packages are outdated.",
                priority='medium',
                estimated_effort='',
                expected_impact='',
                file_paths=['requirements.txt', 'package.json'],
                code_locations=[],
                rationale='Outdated packages may contain security vulnerabilities and miss important features'
            )
            recommendations.append(rec)
        
        # Vulnerabilities
        if dependencies.vulnerabilities:
            for vuln in dependencies.vulnerabilities[:5]:  # Top 5
                rec = Recommendation(
                    id=f"rec-vuln-{vuln.package_name}",
                    category='security',
                    title=f"Fix vulnerability in {vuln.package_name}",
                    description=f"Package {vuln.package_name} v{vuln.version} has known vulnerability: "
                               f"{vuln.vulnerability.cve_id} ({vuln.vulnerability.severity})",
                    priority='critical' if vuln.vulnerability.severity in ['critical', 'high'] else 'high',
                    estimated_effort='',
                    expected_impact='',
                    file_paths=['requirements.txt', 'package.json'],
                    code_locations=[],
                    rationale=f"Security vulnerability: {vuln.vulnerability.description}"
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _recommendations_from_hotspots(self, analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations from hotspots."""
        recommendations = []
        metrics = analysis_results.get('metrics')
        
        if not metrics or not metrics.hotspots:
            return recommendations
        
        for hotspot in metrics.hotspots[:5]:  # Top 5
            rec = Recommendation(
                id=f"rec-hotspot-{hotspot.type}-{len(recommendations)}",
                category='refactoring',
                title=f"Address {hotspot.type} hotspot",
                description=hotspot.recommendation,
                priority=hotspot.severity,
                estimated_effort='',
                expected_impact='',
                file_paths=[hotspot.file_path],
                code_locations=[],
                rationale=f"Hotspots indicate areas that need attention to improve code quality"
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _prioritize_security(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """
        Elevate security recommendations.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            Recommendations with security items prioritized
        """
        # Ensure security recommendations have high priority
        for rec in recommendations:
            if rec.category == 'security':
                if rec.priority == 'medium':
                    rec.priority = 'high'
                elif rec.priority == 'low':
                    rec.priority = 'medium'
        
        return recommendations
    
    def _calculate_effort(self, recommendation: Recommendation) -> str:
        """
        Estimate implementation effort.
        
        Args:
            recommendation: Recommendation object
            
        Returns:
            Effort estimate (e.g., "2 hours", "1 day")
        """
        # Simple heuristic based on category and file count
        file_count = len(recommendation.file_paths)
        
        if recommendation.category == 'security':
            if file_count <= 2:
                return '1-2 hours'
            else:
                return '4-8 hours'
        
        elif recommendation.category == 'refactoring':
            if file_count <= 1:
                return '2-4 hours'
            elif file_count <= 5:
                return '1-2 days'
            else:
                return '3-5 days'
        
        else:  # scalability
            return '1-2 weeks'
    
    def _calculate_impact(self, recommendation: Recommendation) -> str:
        """
        Estimate improvement impact.
        
        Args:
            recommendation: Recommendation object
            
        Returns:
            Impact level (high/medium/low)
        """
        # Security and critical items have high impact
        if recommendation.category == 'security' or recommendation.priority == 'critical':
            return 'high'
        
        # High priority items have medium-high impact
        if recommendation.priority == 'high':
            return 'high'
        
        # Medium priority items have medium impact
        if recommendation.priority == 'medium':
            return 'medium'
        
        return 'low'
    
    def _identify_locations(self, file_paths: List[str]) -> List[CodeLocation]:
        """
        Find specific file paths and code locations.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            List of code locations
        """
        # This would identify specific line numbers in production
        locations = []
        
        for file_path in file_paths[:5]:  # Limit to 5
            location = CodeLocation(
                file_path=file_path,
                line_start=1,
                line_end=10,
                snippet=None
            )
            locations.append(location)
        
        return locations
