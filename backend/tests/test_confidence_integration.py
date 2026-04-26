"""
Integration test for Architecture Confidence Score in Analysis Engine
"""

import unittest
from unittest.mock import Mock, patch
from backend.lib.analysis.engine import AnalysisEngine
from backend.lib.models.architecture_models import (
    Layer,
    Component,
    Technology,
    DetectedPattern
)


class TestConfidenceIntegration(unittest.TestCase):
    """Test confidence score integration in Analysis Engine."""
    
    @patch('backend.lib.analysis.engine.BedrockClient')
    def test_confidence_in_analysis_response(self, mock_bedrock):
        """Test that confidence score is included in analysis response."""
        # Create engine
        engine = AnalysisEngine(bedrock_client=mock_bedrock)
        
        # Mock module responses
        with patch.object(engine.pattern_detector, 'detect_patterns') as mock_patterns, \
             patch.object(engine.layer_analyzer, 'analyze_layers') as mock_layers, \
             patch.object(engine.tech_stack_detector, 'detect_tech_stack') as mock_tech, \
             patch.object(engine.metrics_calculator, 'calculate_metrics') as mock_metrics, \
             patch.object(engine.dependency_analyzer, 'analyze_dependencies') as mock_deps, \
             patch.object(engine.data_flow_analyzer, 'generate_data_flows') as mock_flows, \
             patch.object(engine.recommendation_engine, 'generate_recommendations') as mock_recs, \
             patch.object(engine.diagram_generator, 'generate_system_architecture') as mock_diagram, \
             patch.object(engine.diagram_generator, 'generate_data_flow_scenarios') as mock_flow_diagram, \
             patch.object(engine.diagram_generator, 'generate_tech_stack_cards') as mock_cards:
            
            # Setup mock returns
            mock_patterns.return_value = [
                DetectedPattern(
                    name='Layered',
                    confidence=0.8,
                    evidence_files=['src/api/controller.py'],
                    description='Layered architecture',
                    pros=['Clear separation'],
                    cons=['Can be rigid'],
                    alternatives=['Hexagonal']
                )
            ]
            
            mock_layers.return_value = [
                Layer(
                    name='api',
                    description='API layer',
                    components=[
                        Component(
                            name='UserController',
                            type='controller',
                            file_path='src/api/user_controller.py',
                            line_count=100,
                            complexity_score=5,
                            dependencies=[],
                            health_score=0.9,
                            responsibilities=['Handle requests']
                        )
                    ],
                    technologies=['flask'],
                    entry_points=['/api/users'],
                    connections=[]
                )
            ]
            
            mock_tech.return_value = [
                Technology(
                    name='flask',
                    category='backend-framework',
                    icon='si:flask:000000',
                    version='2.0.0',
                    latest_version='2.3.0',
                    is_deprecated=False,
                    deprecation_warning=None,
                    license='BSD',
                    vulnerabilities=[]
                )
            ]
            
            mock_metrics.return_value = None
            mock_deps.return_value = None
            mock_flows.return_value = []
            mock_recs.return_value = []
            
            # Mock diagram outputs
            mock_diagram_output = Mock()
            mock_diagram_output.mermaid = 'graph TD'
            mock_diagram_output.interactive = {'nodes': [], 'edges': []}
            mock_diagram_output.metadata = {'node_count': 0, 'edge_count': 0}
            mock_diagram.return_value = mock_diagram_output
            mock_flow_diagram.return_value = []
            mock_cards.return_value = []
            
            # Run analysis
            result = engine.analyze(
                repo_id='test-repo',
                repo_metadata={'name': 'test', 'primary_language': 'Python'},
                file_summaries=[
                    {'file_path': 'src/api/user_controller.py', 'line_count': 100}
                ],
                level='basic'
            )
            
            # Verify confidence is in response
            self.assertIn('confidence', result)
            self.assertIsInstance(result['confidence'], float)
            self.assertGreaterEqual(result['confidence'], 0.0)
            self.assertLessEqual(result['confidence'], 1.0)
            
            # Verify confidence signals are in response
            self.assertIn('confidence_signals', result)
            self.assertIn('layer_separation_score', result['confidence_signals'])
            self.assertIn('framework_detection_score', result['confidence_signals'])
            self.assertIn('database_integration_score', result['confidence_signals'])
            self.assertIn('dependency_direction_score', result['confidence_signals'])
            self.assertIn('dependency_depth_score', result['confidence_signals'])
            self.assertIn('naming_consistency_score', result['confidence_signals'])
            
            # Verify legacy architecture uses calculated confidence
            self.assertIn('architecture', result)
            self.assertEqual(result['architecture']['confidence'], result['confidence'])
    
    @patch('backend.lib.analysis.engine.BedrockClient')
    def test_confidence_calculation_error_handling(self, mock_bedrock):
        """Test that confidence calculation errors are handled gracefully."""
        # Create engine
        engine = AnalysisEngine(bedrock_client=mock_bedrock)
        
        # Mock confidence calculator to raise exception
        with patch.object(engine.confidence_calculator, 'calculate_confidence') as mock_calc, \
             patch.object(engine.pattern_detector, 'detect_patterns') as mock_patterns, \
             patch.object(engine.layer_analyzer, 'analyze_layers') as mock_layers, \
             patch.object(engine.tech_stack_detector, 'detect_tech_stack') as mock_tech, \
             patch.object(engine.metrics_calculator, 'calculate_metrics') as mock_metrics, \
             patch.object(engine.dependency_analyzer, 'analyze_dependencies') as mock_deps, \
             patch.object(engine.data_flow_analyzer, 'generate_data_flows') as mock_flows, \
             patch.object(engine.recommendation_engine, 'generate_recommendations') as mock_recs, \
             patch.object(engine.diagram_generator, 'generate_system_architecture') as mock_diagram, \
             patch.object(engine.diagram_generator, 'generate_data_flow_scenarios') as mock_flow_diagram, \
             patch.object(engine.diagram_generator, 'generate_tech_stack_cards') as mock_cards:
            
            # Setup mock to raise exception
            mock_calc.side_effect = Exception("Calculation failed")
            
            # Setup other mocks
            mock_patterns.return_value = []
            mock_layers.return_value = []
            mock_tech.return_value = []
            mock_metrics.return_value = None
            mock_deps.return_value = None
            mock_flows.return_value = []
            mock_recs.return_value = []
            
            mock_diagram_output = Mock()
            mock_diagram_output.mermaid = 'graph TD'
            mock_diagram_output.interactive = {'nodes': [], 'edges': []}
            mock_diagram_output.metadata = {'node_count': 0, 'edge_count': 0}
            mock_diagram.return_value = mock_diagram_output
            mock_flow_diagram.return_value = []
            mock_cards.return_value = []
            
            # Run analysis
            result = engine.analyze(
                repo_id='test-repo',
                repo_metadata={'name': 'test', 'primary_language': 'Python'},
                file_summaries=[],
                level='basic'
            )
            
            # Verify default confidence is returned
            self.assertIn('confidence', result)
            self.assertEqual(result['confidence'], 0.5)  # Default fallback


if __name__ == '__main__':
    unittest.main()
