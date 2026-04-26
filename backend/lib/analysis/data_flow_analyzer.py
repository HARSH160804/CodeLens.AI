"""
Data Flow Analyzer for Architecture Analysis

Generates data flow scenarios with bottleneck identification.
"""

import logging
from typing import List, Dict, Any

from models.architecture_models import (
    DataFlowScenario,
    FlowStep,
    Bottleneck,
    Layer
)

logger = logging.getLogger(__name__)


class DataFlowAnalyzer:
    """Generates data flow scenarios and identifies bottlenecks."""
    
    def __init__(self):
        """Initialize data flow analyzer."""
        pass
    
    def generate_data_flows(
        self,
        context: Dict[str, Any],
        layers: List[Layer]
    ) -> List[DataFlowScenario]:
        """
        Generate data flow scenarios.
        
        Args:
            context: Analysis context
            layers: Detected layers
            
        Returns:
            List of data flow scenarios
        """
        try:
            scenarios = []
            
            # Generate happy path scenario
            happy_path = self._generate_happy_path(layers)
            scenarios.append(happy_path)
            
            # Generate error handling scenario
            error_scenario = self._generate_error_scenario(layers)
            scenarios.append(error_scenario)
            
            # Generate edge case scenario
            edge_case = self._generate_edge_case(layers)
            scenarios.append(edge_case)
            
            logger.info(f"Generated {len(scenarios)} data flow scenarios")
            return scenarios
            
        except Exception as e:
            logger.error(f"Error generating data flows: {str(e)}")
            return []
    
    def _generate_happy_path(self, layers: List[Layer]) -> DataFlowScenario:
        """Generate happy path scenario."""
        steps = []
        step_num = 1
        
        # Start with presentation/api layer
        api_layer = next((l for l in layers if l.name in ['api', 'presentation']), None)
        if api_layer and api_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Receive request',
                next_steps=[step_num + 1],
                is_conditional=False
            ))
            step_num += 1
        
        # Business layer
        business_layer = next((l for l in layers if l.name == 'business'), None)
        if business_layer and business_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=business_layer.components[0].name,
                action='Process business logic',
                next_steps=[step_num + 1],
                is_conditional=False
            ))
            step_num += 1
        
        # Data layer
        data_layer = next((l for l in layers if l.name == 'data'), None)
        if data_layer and data_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=data_layer.components[0].name,
                action='Query database',
                next_steps=[step_num + 1],
                is_conditional=False
            ))
            step_num += 1
        
        # Return response
        if api_layer and api_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Return response',
                next_steps=[],
                is_conditional=False
            ))
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(steps, layers)
        
        return DataFlowScenario(
            name='Happy Path',
            description='Normal execution flow with successful outcome',
            steps=steps,
            bottlenecks=bottlenecks
        )
    
    def _generate_error_scenario(self, layers: List[Layer]) -> DataFlowScenario:
        """Generate error handling scenario."""
        steps = []
        step_num = 1
        
        # Start with API layer
        api_layer = next((l for l in layers if l.name in ['api', 'presentation']), None)
        if api_layer and api_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Receive request',
                next_steps=[step_num + 1],
                is_conditional=False
            ))
            step_num += 1
            
            # Validation step (conditional)
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Validate input',
                next_steps=[step_num + 1, step_num + 2],  # Success or error
                is_conditional=True
            ))
            step_num += 1
            
            # Error response
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Return error response',
                next_steps=[],
                is_conditional=False
            ))
            step_num += 1
            
            # Continue with business logic
            business_layer = next((l for l in layers if l.name == 'business'), None)
            if business_layer and business_layer.components:
                steps.append(FlowStep(
                    step_number=step_num,
                    component=business_layer.components[0].name,
                    action='Process business logic',
                    next_steps=[step_num + 1],
                    is_conditional=False
                ))
        
        bottlenecks = []
        
        return DataFlowScenario(
            name='Error Handling',
            description='Execution flow with error conditions and recovery',
            steps=steps,
            bottlenecks=bottlenecks
        )
    
    def _generate_edge_case(self, layers: List[Layer]) -> DataFlowScenario:
        """Generate edge case scenario."""
        steps = []
        step_num = 1
        
        # API layer with edge case
        api_layer = next((l for l in layers if l.name in ['api', 'presentation']), None)
        if api_layer and api_layer.components:
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Receive request with edge case data',
                next_steps=[step_num + 1],
                is_conditional=False
            ))
            step_num += 1
            
            # Special handling
            steps.append(FlowStep(
                step_number=step_num,
                component=api_layer.components[0].name,
                action='Apply special handling',
                next_steps=[step_num + 1],
                is_conditional=True
            ))
        
        bottlenecks = []
        
        return DataFlowScenario(
            name='Edge Cases',
            description='Execution flow with boundary conditions and special cases',
            steps=steps,
            bottlenecks=bottlenecks
        )
    
    def _identify_bottlenecks(
        self,
        steps: List[FlowStep],
        layers: List[Layer]
    ) -> List[Bottleneck]:
        """
        Identify performance bottlenecks based on complexity and dependency depth.
        
        Args:
            steps: Flow steps
            layers: Detected layers
            
        Returns:
            List of bottlenecks
        """
        bottlenecks = []
        
        # Check for database queries (common bottleneck)
        for step in steps:
            if 'database' in step.action.lower() or 'query' in step.action.lower():
                bottleneck = Bottleneck(
                    location=step.component,
                    severity='medium',
                    description='Database query may cause performance issues under load',
                    suggested_optimization='Consider caching, query optimization, or connection pooling'
                )
                bottlenecks.append(bottleneck)
        
        # Check for sequential processing
        if len(steps) > 5:
            bottleneck = Bottleneck(
                location='Overall flow',
                severity='low',
                description='Long sequential flow may impact response time',
                suggested_optimization='Consider parallelizing independent operations'
            )
            bottlenecks.append(bottleneck)
        
        return bottlenecks
