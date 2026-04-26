"""
Metrics Calculator for Architecture Analysis

Computes code quality metrics and identifies hotspots.
"""

import logging
from typing import List, Dict, Any

from models.architecture_models import (
    QualityMetrics,
    ComplexityMetrics,
    Hotspot,
    TechnicalDebt,
    DuplicatedBlock,
    Layer
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Computes code quality metrics and identifies hotspots."""
    
    def __init__(self):
        """Initialize metrics calculator."""
        pass
    
    def calculate_metrics(
        self,
        context: Dict[str, Any],
        layers: List[Layer]
    ) -> QualityMetrics:
        """
        Calculate code quality metrics.
        
        Args:
            context: Analysis context
            layers: Detected layers with components
            
        Returns:
            Quality metrics including health score and hotspots
        """
        try:
            # Calculate complexity metrics
            complexity_metrics = self._calculate_complexity(context, layers)
            
            # Identify hotspots
            hotspots = self._identify_hotspots(context, layers, complexity_metrics)
            
            # Calculate technical debt
            technical_debt = self._calculate_technical_debt(context)
            
            # Calculate overall health score
            health_score = self._calculate_health_score(
                complexity_metrics,
                hotspots,
                technical_debt
            )
            
            metrics = QualityMetrics(
                health_score=health_score,
                complexity_metrics=complexity_metrics,
                hotspots=hotspots,
                technical_debt=technical_debt
            )
            
            logger.info(f"Calculated metrics with health score: {health_score}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            # Return default metrics
            return self._default_metrics()
    
    def _calculate_health_score(
        self,
        complexity_metrics: ComplexityMetrics,
        hotspots: List[Hotspot],
        technical_debt: TechnicalDebt
    ) -> float:
        """
        Compute overall health (0-100).
        
        Args:
            complexity_metrics: Complexity measurements
            hotspots: List of hotspots
            technical_debt: Technical debt indicators
            
        Returns:
            Health score between 0 and 100
        """
        # Start with perfect score
        score = 100.0
        
        # Deduct for high complexity
        if complexity_metrics.average_cyclomatic > 10:
            score -= min(20, (complexity_metrics.average_cyclomatic - 10) * 2)
        
        if complexity_metrics.average_cognitive > 15:
            score -= min(15, (complexity_metrics.average_cognitive - 15) * 1.5)
        
        # Deduct for hotspots
        critical_hotspots = sum(1 for h in hotspots if h.severity == 'critical')
        high_hotspots = sum(1 for h in hotspots if h.severity == 'high')
        score -= min(20, critical_hotspots * 5 + high_hotspots * 2)
        
        # Deduct for technical debt
        if technical_debt.code_duplication_percentage > 10:
            score -= min(15, (technical_debt.code_duplication_percentage - 10) * 1.5)
        
        coverage_gap_penalty = min(10, len(technical_debt.test_coverage_gaps) * 0.5)
        score -= coverage_gap_penalty
        
        # Ensure score is in valid range
        return max(0.0, min(100.0, score))
    
    def _calculate_complexity(
        self,
        context: Dict[str, Any],
        layers: List[Layer]
    ) -> ComplexityMetrics:
        """
        Calculate cyclomatic and cognitive complexity.
        
        Args:
            context: Analysis context
            layers: Detected layers
            
        Returns:
            Complexity metrics
        """
        # Collect complexity scores from components
        complexity_scores = []
        cognitive_scores = []
        high_complexity_files = []
        
        for layer in layers:
            for component in layer.components:
                # Use component complexity score (already calculated)
                complexity_scores.append(component.complexity_score)
                
                # Estimate cognitive complexity (typically 1.5x cyclomatic)
                cognitive = component.complexity_score * 1.5
                cognitive_scores.append(cognitive)
                
                # Identify high complexity files
                if component.complexity_score > 15:
                    high_complexity_files.append(component.file_path)
        
        # Calculate averages
        avg_cyclomatic = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
        avg_cognitive = sum(cognitive_scores) / len(cognitive_scores) if cognitive_scores else 0
        max_cyclomatic = max(complexity_scores) if complexity_scores else 0
        max_cognitive = max(cognitive_scores) if cognitive_scores else 0
        
        return ComplexityMetrics(
            average_cyclomatic=round(avg_cyclomatic, 2),
            average_cognitive=round(avg_cognitive, 2),
            max_cyclomatic=round(max_cyclomatic, 2),
            max_cognitive=round(max_cognitive, 2),
            high_complexity_files=high_complexity_files[:10]  # Limit to top 10
        )
    
    def _identify_hotspots(
        self,
        context: Dict[str, Any],
        layers: List[Layer],
        complexity_metrics: ComplexityMetrics
    ) -> List[Hotspot]:
        """
        Find high-complexity areas.
        
        Args:
            context: Analysis context
            layers: Detected layers
            complexity_metrics: Complexity measurements
            
        Returns:
            List of hotspots
        """
        hotspots = []
        
        for layer in layers:
            for component in layer.components:
                # Check for complexity hotspots
                if component.complexity_score > 20:
                    hotspot = Hotspot(
                        file_path=component.file_path,
                        type='complexity',
                        complexity_score=component.complexity_score,
                        change_frequency=None,
                        severity='critical',
                        recommendation=f"Break down {component.name} into smaller functions"
                    )
                    hotspots.append(hotspot)
                
                elif component.complexity_score > 15:
                    hotspot = Hotspot(
                        file_path=component.file_path,
                        type='complexity',
                        complexity_score=component.complexity_score,
                        change_frequency=None,
                        severity='high',
                        recommendation=f"Consider refactoring {component.name} to reduce complexity"
                    )
                    hotspots.append(hotspot)
                
                # Check for large files (potential hotspots)
                if component.line_count > 500:
                    hotspot = Hotspot(
                        file_path=component.file_path,
                        type='size',
                        complexity_score=component.complexity_score,
                        change_frequency=None,
                        severity='medium',
                        recommendation=f"Consider splitting {component.name} into multiple files"
                    )
                    hotspots.append(hotspot)
        
        # Identify performance hotspots
        performance_hotspots = self._identify_performance_hotspots(context, layers)
        hotspots.extend(performance_hotspots)
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        hotspots.sort(key=lambda h: severity_order.get(h.severity, 4))
        
        return hotspots[:20]  # Limit to top 20
    
    def _calculate_technical_debt(self, context: Dict[str, Any]) -> TechnicalDebt:
        """
        Calculate duplication and coverage gaps.
        
        Args:
            context: Analysis context
            
        Returns:
            Technical debt indicators
        """
        file_summaries = context.get('file_summaries', [])
        
        # Estimate code duplication (simplified)
        duplicated_blocks = self._detect_duplicated_blocks(file_summaries)
        
        total_lines = sum(f.get('line_count', 0) for f in file_summaries)
        duplicated_lines = sum(block.line_count for block in duplicated_blocks)
        duplication_percentage = (duplicated_lines / total_lines * 100) if total_lines > 0 else 0
        
        # Identify test coverage gaps
        test_coverage_gaps = self._identify_test_coverage_gaps(file_summaries)
        
        # Estimate technical debt hours
        # Formula: (duplicated_blocks * 2) + (coverage_gaps * 1) + (high_complexity_files * 3)
        estimated_debt_hours = (
            len(duplicated_blocks) * 2 +
            len(test_coverage_gaps) * 1
        )
        
        return TechnicalDebt(
            code_duplication_percentage=round(duplication_percentage, 2),
            duplicated_blocks=duplicated_blocks[:10],  # Limit to top 10
            test_coverage_gaps=test_coverage_gaps[:20],  # Limit to top 20
            estimated_debt_hours=float(estimated_debt_hours)
        )
    
    def _detect_duplicated_blocks(self, file_summaries: List[Dict[str, Any]]) -> List[DuplicatedBlock]:
        """
        Detect code duplication.
        
        Args:
            file_summaries: List of file summaries
            
        Returns:
            List of duplicated blocks
        """
        # This is a simplified placeholder
        # Real implementation would use AST comparison or text similarity
        duplicated_blocks = []
        
        # Simple heuristic: files with similar names might have duplication
        file_groups = {}
        for f in file_summaries:
            file_path = f.get('file_path', '')
            base_name = file_path.split('/')[-1].split('.')[0]
            
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)
        
        for base_name, paths in file_groups.items():
            if len(paths) >= 2:
                block = DuplicatedBlock(
                    files=paths[:3],  # Limit to 3 files
                    line_count=50,  # Estimate
                    similarity_percentage=75.0  # Estimate
                )
                duplicated_blocks.append(block)
        
        return duplicated_blocks
    
    def _identify_test_coverage_gaps(self, file_summaries: List[Dict[str, Any]]) -> List[str]:
        """
        Identify files without tests.
        
        Args:
            file_summaries: List of file summaries
            
        Returns:
            List of file paths without tests
        """
        # Identify test files
        test_files = set()
        for f in file_summaries:
            file_path = f.get('file_path', '').lower()
            if any(x in file_path for x in ['test_', '_test', 'spec_', '_spec', '/tests/', '/test/']):
                # Extract the file being tested
                base_name = file_path.replace('test_', '').replace('_test', '').replace('spec_', '').replace('_spec', '')
                test_files.add(base_name)
        
        # Identify source files without tests
        coverage_gaps = []
        for f in file_summaries:
            file_path = f.get('file_path', '').lower()
            
            # Skip test files themselves
            if any(x in file_path for x in ['test_', '_test', 'spec_', '_spec', '/tests/', '/test/']):
                continue
            
            # Skip non-code files
            if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.rb', '.go']):
                continue
            
            # Check if has corresponding test
            has_test = any(file_path in test_file for test_file in test_files)
            
            if not has_test:
                coverage_gaps.append(f.get('file_path', ''))
        
        return coverage_gaps
    
    def _identify_performance_hotspots(
        self,
        context: Dict[str, Any],
        layers: List[Layer]
    ) -> List[Hotspot]:
        """
        Find algorithmic bottlenecks.
        
        Args:
            context: Analysis context
            layers: Detected layers
            
        Returns:
            List of performance hotspots
        """
        hotspots = []
        
        # Look for nested loops (O(n²) or worse)
        file_summaries = context.get('file_summaries', [])
        
        for f in file_summaries:
            content = f.get('content', '').lower()
            file_path = f.get('file_path', '')
            
            # Simple heuristic: count nested loop keywords
            loop_keywords = ['for ', 'while ', 'foreach']
            loop_count = sum(content.count(keyword) for keyword in loop_keywords)
            
            # If many loops, might have nested loops
            if loop_count >= 3:
                hotspot = Hotspot(
                    file_path=file_path,
                    type='performance',
                    complexity_score=loop_count * 5.0,
                    change_frequency=None,
                    severity='medium',
                    recommendation=f"Review {file_path} for nested loops and algorithmic complexity"
                )
                hotspots.append(hotspot)
        
        return hotspots
    
    def _default_metrics(self) -> QualityMetrics:
        """Return default metrics when calculation fails."""
        return QualityMetrics(
            health_score=50.0,
            complexity_metrics=ComplexityMetrics(
                average_cyclomatic=0.0,
                average_cognitive=0.0,
                max_cyclomatic=0.0,
                max_cognitive=0.0,
                high_complexity_files=[]
            ),
            hotspots=[],
            technical_debt=TechnicalDebt(
                code_duplication_percentage=0.0,
                duplicated_blocks=[],
                test_coverage_gaps=[],
                estimated_debt_hours=0.0
            )
        )
