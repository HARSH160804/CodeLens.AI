"""
Unit tests for Architecture Confidence Score Calculator
"""

import unittest
from backend.lib.analysis.confidence_calculator import ConfidenceCalculator
from backend.lib.models.architecture_models import (
    Layer,
    Component,
    Technology,
    DependencyAnalysis,
    DependencyTree,
    DependencyNode,
    CircularDependency
)


class TestConfidenceCalculator(unittest.TestCase):
    """Test suite for ConfidenceCalculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = ConfidenceCalculator()
    
    def test_perfect_architecture_high_confidence(self):
        """Test that a perfect architecture gets high confidence score (> 0.85)."""
        # Create 4 layers (presentation, api, business, data)
        layers = [
            Layer(
                name='presentation',
                description='Presentation layer',
                components=[
                    Component(
                        name='UserInterface',
                        type='ui',
                        file_path='src/ui/user_interface.py',
                        line_count=100,
                        complexity_score=5,
                        dependencies=['api.UserController'],
                        health_score=0.9,
                        responsibilities=['Display data']
                    )
                ],
                technologies=['react'],
                entry_points=['index.html'],
                connections=[]
            ),
            Layer(
                name='api',
                description='API layer',
                components=[
                    Component(
                        name='UserController',
                        type='controller',
                        file_path='src/api/user_controller.py',
                        line_count=150,
                        complexity_score=7,
                        dependencies=['business.UserService'],
                        health_score=0.85,
                        responsibilities=['Handle requests']
                    )
                ],
                technologies=['flask'],
                entry_points=['/api/users'],
                connections=[]
            ),
            Layer(
                name='business',
                description='Business logic layer',
                components=[
                    Component(
                        name='UserService',
                        type='service',
                        file_path='src/business/user_service.py',
                        line_count=200,
                        complexity_score=10,
                        dependencies=['data.UserRepository'],
                        health_score=0.8,
                        responsibilities=['Business logic']
                    )
                ],
                technologies=['python'],
                entry_points=[],
                connections=[]
            ),
            Layer(
                name='data',
                description='Data access layer',
                components=[
                    Component(
                        name='UserRepository',
                        type='repository',
                        file_path='src/data/user_repository.py',
                        line_count=120,
                        complexity_score=6,
                        dependencies=[],
                        health_score=0.9,
                        responsibilities=['Data access']
                    )
                ],
                technologies=['sqlalchemy'],
                entry_points=[],
                connections=[]
            )
        ]
        
        # Create tech stack with backend framework and database
        tech_stack = [
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
            ),
            Technology(
                name='sqlalchemy',
                category='orm',
                icon='si:sqlalchemy:000000',
                version='1.4.0',
                latest_version='2.0.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='MIT',
                vulnerabilities=[]
            ),
            Technology(
                name='postgresql',
                category='database',
                icon='si:postgresql:336791',
                version='14.0',
                latest_version='15.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='PostgreSQL',
                vulnerabilities=[]
            )
        ]
        
        # Create dependency tree with no circular dependencies
        root_node = DependencyNode(
            package_name='myapp',
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[
                DependencyNode(
                    package_name='flask',
                    version='2.0.0',
                    license='BSD',
                    depth=1,
                    children=[
                        DependencyNode(
                            package_name='werkzeug',
                            version='2.0.0',
                            license='BSD',
                            depth=2,
                            children=[],
                            security_status='safe'
                        )
                    ],
                    security_status='safe'
                )
            ],
            security_status='safe'
        )
        
        dependencies = DependencyAnalysis(
            dependency_tree=DependencyTree(
                root=root_node,
                total_dependencies=3,
                max_depth=3
            ),
            circular_dependencies=[],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
        
        # Create file summaries with consistent naming
        file_summaries = [
            {'file_path': 'src/ui/user_interface.py', 'line_count': 100},
            {'file_path': 'src/api/user_controller.py', 'line_count': 150},
            {'file_path': 'src/business/user_service.py', 'line_count': 200},
            {'file_path': 'src/data/user_repository.py', 'line_count': 120}
        ]
        
        # Calculate confidence
        result = self.calculator.calculate_confidence(
            layers=layers,
            tech_stack=tech_stack,
            dependencies=dependencies,
            file_summaries=file_summaries
        )
        
        # Assert high confidence
        self.assertGreater(result['confidence'], 0.85)
        self.assertIn('signals', result)
        self.assertEqual(result['signals']['layer_separation_score'], 1.0)
        self.assertEqual(result['signals']['framework_detection_score'], 1.0)
        self.assertEqual(result['signals']['database_integration_score'], 1.0)
        self.assertEqual(result['signals']['dependency_direction_score'], 1.0)
    
    def test_missing_layers_lower_score(self):
        """Test that missing layers result in lower confidence score."""
        # Only 2 layers instead of 4
        layers = [
            Layer(
                name='api',
                description='API layer',
                components=[],
                technologies=[],
                entry_points=[],
                connections=[]
            ),
            Layer(
                name='data',
                description='Data layer',
                components=[],
                technologies=[],
                entry_points=[],
                connections=[]
            )
        ]
        
        result = self.calculator.calculate_confidence(
            layers=layers,
            tech_stack=[],
            dependencies=None,
            file_summaries=[]
        )
        
        # LSS should be 2/4 = 0.5
        self.assertEqual(result['signals']['layer_separation_score'], 0.5)
        self.assertLess(result['confidence'], 0.7)
    
    def test_circular_dependencies_reduce_score(self):
        """Test that circular dependencies reduce dependency direction score."""
        # Create dependency tree with circular dependencies
        root_node = DependencyNode(
            package_name='myapp',
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[],
            security_status='safe'
        )
        
        dependencies = DependencyAnalysis(
            dependency_tree=DependencyTree(
                root=root_node,
                total_dependencies=10,
                max_depth=3
            ),
            circular_dependencies=[
                CircularDependency(
                    cycle_path=['A', 'B', 'C', 'A'],
                    severity='high',
                    description='Circular dependency detected'
                ),
                CircularDependency(
                    cycle_path=['X', 'Y', 'X'],
                    severity='medium',
                    description='Another circular dependency'
                )
            ],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=dependencies,
            file_summaries=[]
        )
        
        # DDS should be 1 - (2/10) = 0.8
        self.assertEqual(result['signals']['dependency_direction_score'], 0.8)
    
    def test_no_framework_detected_lower_score(self):
        """Test that missing backend framework results in lower FDS."""
        # Tech stack without backend framework
        tech_stack = [
            Technology(
                name='requests',
                category='http-client',
                icon='si:python:3776AB',
                version='2.28.0',
                latest_version='2.31.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='Apache-2.0',
                vulnerabilities=[]
            )
        ]
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=tech_stack,
            dependencies=None,
            file_summaries=[]
        )
        
        # FDS should be 0.0
        self.assertEqual(result['signals']['framework_detection_score'], 0.0)
    
    def test_shallow_dependency_depth_moderate_score(self):
        """Test that shallow dependency depth gets moderate score."""
        # Dependency tree with depth = 1
        root_node = DependencyNode(
            package_name='myapp',
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[
                DependencyNode(
                    package_name='flask',
                    version='2.0.0',
                    license='BSD',
                    depth=1,
                    children=[],
                    security_status='safe'
                )
            ],
            security_status='safe'
        )
        
        dependencies = DependencyAnalysis(
            dependency_tree=DependencyTree(
                root=root_node,
                total_dependencies=2,
                max_depth=1
            ),
            circular_dependencies=[],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=dependencies,
            file_summaries=[]
        )
        
        # DDpS should be 0.5 for depth = 1
        self.assertEqual(result['signals']['dependency_depth_score'], 0.5)
    
    def test_naming_inconsistency_reduces_score(self):
        """Test that inconsistent file naming reduces FNCS."""
        # Mix of naming conventions (inconsistent)
        file_summaries = [
            {'file_path': 'src/UserController.py', 'line_count': 100},  # PascalCase
            {'file_path': 'src/user-service.py', 'line_count': 150},    # kebab-case
            {'file_path': 'src/USERREPO.py', 'line_count': 120},        # UPPERCASE (inconsistent)
            {'file_path': 'src/data_access.py', 'line_count': 80}       # snake_case
        ]
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=None,
            file_summaries=file_summaries
        )
        
        # FNCS should be less than 1.0 due to inconsistency
        self.assertLess(result['signals']['naming_consistency_score'], 1.0)
    
    def test_clamping_between_zero_and_one(self):
        """Test that confidence score is clamped between 0 and 1."""
        # Empty inputs should still produce valid score
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=None,
            file_summaries=[]
        )
        
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)
    
    def test_database_only_partial_score(self):
        """Test that database without ORM gets partial DIS score."""
        tech_stack = [
            Technology(
                name='postgresql',
                category='database',
                icon='si:postgresql:336791',
                version='14.0',
                latest_version='15.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='PostgreSQL',
                vulnerabilities=[]
            )
        ]
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=tech_stack,
            dependencies=None,
            file_summaries=[]
        )
        
        # DIS should be 0.5 (database only, no ORM)
        self.assertEqual(result['signals']['database_integration_score'], 0.5)
    
    def test_orm_and_database_full_score(self):
        """Test that ORM + database gets full DIS score."""
        tech_stack = [
            Technology(
                name='sqlalchemy',
                category='orm',
                icon='si:sqlalchemy:000000',
                version='1.4.0',
                latest_version='2.0.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='MIT',
                vulnerabilities=[]
            ),
            Technology(
                name='postgresql',
                category='database',
                icon='si:postgresql:336791',
                version='14.0',
                latest_version='15.0',
                is_deprecated=False,
                deprecation_warning=None,
                license='PostgreSQL',
                vulnerabilities=[]
            )
        ]
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=tech_stack,
            dependencies=None,
            file_summaries=[]
        )
        
        # DIS should be 1.0 (ORM + database)
        self.assertEqual(result['signals']['database_integration_score'], 1.0)
    
    def test_ideal_dependency_depth_full_score(self):
        """Test that ideal dependency depth (2-5) gets full score."""
        # Dependency tree with depth = 3 (ideal)
        root_node = DependencyNode(
            package_name='myapp',
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[
                DependencyNode(
                    package_name='flask',
                    version='2.0.0',
                    license='BSD',
                    depth=1,
                    children=[
                        DependencyNode(
                            package_name='werkzeug',
                            version='2.0.0',
                            license='BSD',
                            depth=2,
                            children=[
                                DependencyNode(
                                    package_name='markupsafe',
                                    version='2.0.0',
                                    license='BSD',
                                    depth=3,
                                    children=[],
                                    security_status='safe'
                                )
                            ],
                            security_status='safe'
                        )
                    ],
                    security_status='safe'
                )
            ],
            security_status='safe'
        )
        
        dependencies = DependencyAnalysis(
            dependency_tree=DependencyTree(
                root=root_node,
                total_dependencies=4,
                max_depth=3
            ),
            circular_dependencies=[],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=dependencies,
            file_summaries=[]
        )
        
        # DDpS should be 1.0 for depth = 3 (ideal range 2-5)
        self.assertEqual(result['signals']['dependency_depth_score'], 1.0)
    
    def test_deep_dependency_depth_reduced_score(self):
        """Test that very deep dependency depth reduces score."""
        # Dependency tree with depth = 10 (too deep)
        root_node = DependencyNode(
            package_name='myapp',
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[],
            security_status='safe'
        )
        
        dependencies = DependencyAnalysis(
            dependency_tree=DependencyTree(
                root=root_node,
                total_dependencies=15,
                max_depth=10
            ),
            circular_dependencies=[],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
        
        result = self.calculator.calculate_confidence(
            layers=[],
            tech_stack=[],
            dependencies=dependencies,
            file_summaries=[]
        )
        
        # DDpS should be reduced: 1 - (10 - 5) * 0.1 = 0.5
        self.assertEqual(result['signals']['dependency_depth_score'], 0.5)


if __name__ == '__main__':
    unittest.main()
