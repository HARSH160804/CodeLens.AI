"""
Visualization Generator for Architecture Analysis

Generates multiple diagram formats for interactive visualization.
"""

import logging
from typing import Dict, Any, List

from models.architecture_models import (
    Visualization,
    VisualizationMetadata,
    Layer,
    DetectedPattern,
    DependencyAnalysis,
    DataFlowScenario
)

logger = logging.getLogger(__name__)


class VisualizationGenerator:
    """Generates multiple diagram formats for interactive visualization."""
    
    DIAGRAM_TYPES = ['system_architecture', 'data_flow', 'dependency_graph', 'layer_diagram']
    FORMATS = ['mermaid', 'd3', 'cytoscape']
    
    def __init__(self):
        """Initialize visualization generator."""
        pass
    
    def generate_visualizations(
        self,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Visualization]:
        """
        Generate all visualization formats.
        
        Args:
            analysis_data: Combined data from all analysis modules
            
        Returns:
            Dictionary of visualizations by diagram type
        """
        try:
            visualizations = {}
            
            # Generate system architecture diagram
            visualizations['system_architecture'] = self._generate_system_architecture(analysis_data)
            
            # Generate data flow diagram
            visualizations['data_flow'] = self._generate_data_flow(analysis_data)
            
            # Generate dependency graph
            visualizations['dependency_graph'] = self._generate_dependency_graph(analysis_data)
            
            # Generate layer diagram
            visualizations['layer_diagram'] = self._generate_layer_diagram(analysis_data)
            
            logger.info(f"Generated {len(visualizations)} visualizations")
            return visualizations
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            return {}
    
    def _generate_system_architecture(self, analysis_data: Dict[str, Any]) -> Visualization:
        """Generate system architecture diagram."""
        layers = analysis_data.get('layers', [])
        
        # Generate Mermaid
        mermaid = self._generate_mermaid_system(layers)
        
        # Generate D3.js JSON
        d3_json = self._generate_d3_system(layers)
        
        # Generate Cytoscape.js JSON
        cytoscape_json = self._generate_cytoscape_system(layers)
        
        # Create metadata
        metadata = VisualizationMetadata(
            node_count=len(layers),
            edge_count=sum(len(layer.connections) for layer in layers),
            layout_hints={'algorithm': 'hierarchical', 'direction': 'TB'},
            interaction_handlers={layer.name: 'show_layer_details' for layer in layers}
        )
        
        return Visualization(
            diagram_type='system_architecture',
            mermaid=mermaid,
            d3_json=d3_json,
            cytoscape_json=cytoscape_json,
            metadata=metadata
        )
    
    def _generate_mermaid_system(self, layers: List[Layer]) -> str:
        """Create Mermaid syntax for system architecture."""
        lines = ['flowchart TD']
        
        # Add nodes for each layer
        for i, layer in enumerate(layers):
            node_id = f"L{i}"
            label = f"{layer.name.capitalize()}<br/>{len(layer.components)} components"
            lines.append(f"    {node_id}[\"{label}\"]")
        
        # Add connections
        for i, layer in enumerate(layers):
            for conn in layer.connections:
                # Find target layer index
                target_idx = next((j for j, l in enumerate(layers) if l.name == conn.to_layer), None)
                if target_idx is not None:
                    lines.append(f"    L{i} --> L{target_idx}")
        
        return '\n'.join(lines)
    
    def _generate_d3_system(self, layers: List[Layer]) -> Dict[str, Any]:
        """Create D3.js compatible JSON for system architecture."""
        nodes = []
        links = []
        
        # Create nodes
        for i, layer in enumerate(layers):
            nodes.append({
                'id': f"layer_{i}",
                'label': layer.name.capitalize(),
                'type': 'layer',
                'component_count': len(layer.components),
                'technologies': layer.technologies
            })
        
        # Create links
        for i, layer in enumerate(layers):
            for conn in layer.connections:
                target_idx = next((j for j, l in enumerate(layers) if l.name == conn.to_layer), None)
                if target_idx is not None:
                    links.append({
                        'source': f"layer_{i}",
                        'target': f"layer_{target_idx}",
                        'type': conn.connection_type
                    })
        
        return {'nodes': nodes, 'links': links}
    
    def _generate_cytoscape_system(self, layers: List[Layer]) -> Dict[str, Any]:
        """Create Cytoscape.js compatible JSON for system architecture."""
        elements = {'nodes': [], 'edges': []}
        
        # Create nodes
        for i, layer in enumerate(layers):
            elements['nodes'].append({
                'data': {
                    'id': f"layer_{i}",
                    'label': layer.name.capitalize(),
                    'type': 'layer',
                    'component_count': len(layer.components)
                }
            })
        
        # Create edges
        edge_id = 0
        for i, layer in enumerate(layers):
            for conn in layer.connections:
                target_idx = next((j for j, l in enumerate(layers) if l.name == conn.to_layer), None)
                if target_idx is not None:
                    elements['edges'].append({
                        'data': {
                            'id': f"edge_{edge_id}",
                            'source': f"layer_{i}",
                            'target': f"layer_{target_idx}",
                            'type': conn.connection_type
                        }
                    })
                    edge_id += 1
        
        return {'elements': elements}
    
    def _generate_data_flow(self, analysis_data: Dict[str, Any]) -> Visualization:
        """Generate data flow diagram."""
        data_flows = analysis_data.get('data_flows', [])
        
        # Use first data flow scenario
        scenario = data_flows[0] if data_flows else None
        
        if not scenario:
            # Return empty visualization
            return self._empty_visualization('data_flow')
        
        # Generate Mermaid
        mermaid = self._generate_mermaid_dataflow(scenario)
        
        # Generate D3.js JSON
        d3_json = self._generate_d3_dataflow(scenario)
        
        # Generate Cytoscape.js JSON
        cytoscape_json = self._generate_cytoscape_dataflow(scenario)
        
        # Create metadata
        metadata = VisualizationMetadata(
            node_count=len(scenario.steps),
            edge_count=sum(len(step.next_steps) for step in scenario.steps),
            layout_hints={'algorithm': 'dagre', 'direction': 'LR'},
            interaction_handlers={f"step_{step.step_number}": 'show_step_details' for step in scenario.steps}
        )
        
        return Visualization(
            diagram_type='data_flow',
            mermaid=mermaid,
            d3_json=d3_json,
            cytoscape_json=cytoscape_json,
            metadata=metadata
        )
    
    def _generate_mermaid_dataflow(self, scenario: DataFlowScenario) -> str:
        """Create Mermaid syntax for data flow."""
        lines = ['flowchart LR']
        
        # Add nodes
        for step in scenario.steps:
            node_id = f"S{step.step_number}"
            label = f"{step.component}<br/>{step.action}"
            shape = '{' if step.is_conditional else '['
            end_shape = '}' if step.is_conditional else ']'
            lines.append(f"    {node_id}{shape}\"{label}\"{end_shape}")
        
        # Add edges
        for step in scenario.steps:
            for next_step in step.next_steps:
                lines.append(f"    S{step.step_number} --> S{next_step}")
        
        return '\n'.join(lines)
    
    def _generate_d3_dataflow(self, scenario: DataFlowScenario) -> Dict[str, Any]:
        """Create D3.js compatible JSON for data flow."""
        nodes = []
        links = []
        
        for step in scenario.steps:
            nodes.append({
                'id': f"step_{step.step_number}",
                'label': step.component,
                'action': step.action,
                'is_conditional': step.is_conditional
            })
        
        for step in scenario.steps:
            for next_step in step.next_steps:
                links.append({
                    'source': f"step_{step.step_number}",
                    'target': f"step_{next_step}"
                })
        
        return {'nodes': nodes, 'links': links}
    
    def _generate_cytoscape_dataflow(self, scenario: DataFlowScenario) -> Dict[str, Any]:
        """Create Cytoscape.js compatible JSON for data flow."""
        elements = {'nodes': [], 'edges': []}
        
        for step in scenario.steps:
            elements['nodes'].append({
                'data': {
                    'id': f"step_{step.step_number}",
                    'label': step.component,
                    'action': step.action,
                    'is_conditional': step.is_conditional
                }
            })
        
        edge_id = 0
        for step in scenario.steps:
            for next_step in step.next_steps:
                elements['edges'].append({
                    'data': {
                        'id': f"edge_{edge_id}",
                        'source': f"step_{step.step_number}",
                        'target': f"step_{next_step}"
                    }
                })
                edge_id += 1
        
        return {'elements': elements}
    
    def _generate_dependency_graph(self, analysis_data: Dict[str, Any]) -> Visualization:
        """Generate dependency graph diagram."""
        dependencies = analysis_data.get('dependencies')
        
        if not dependencies or not dependencies.dependency_tree:
            return self._empty_visualization('dependency_graph')
        
        tree = dependencies.dependency_tree
        
        # Generate Mermaid
        mermaid = self._generate_mermaid_dependencies(tree)
        
        # Generate D3.js JSON
        d3_json = self._generate_d3_dependencies(tree)
        
        # Generate Cytoscape.js JSON
        cytoscape_json = self._generate_cytoscape_dependencies(tree)
        
        # Create metadata
        metadata = VisualizationMetadata(
            node_count=tree.total_dependencies + 1,
            edge_count=tree.total_dependencies,
            layout_hints={'algorithm': 'breadthfirst', 'direction': 'TB'},
            interaction_handlers={}
        )
        
        return Visualization(
            diagram_type='dependency_graph',
            mermaid=mermaid,
            d3_json=d3_json,
            cytoscape_json=cytoscape_json,
            metadata=metadata
        )
    
    def _generate_mermaid_dependencies(self, tree) -> str:
        """Create Mermaid syntax for dependency graph."""
        lines = ['graph TD']
        lines.append(f"    ROOT[\"{tree.root.package_name}\"]")
        
        for i, child in enumerate(tree.root.children[:10]):  # Limit to 10
            child_id = f"DEP{i}"
            lines.append(f"    {child_id}[\"{child.package_name}<br/>{child.version}\"]")
            lines.append(f"    ROOT --> {child_id}")
        
        return '\n'.join(lines)
    
    def _generate_d3_dependencies(self, tree) -> Dict[str, Any]:
        """Create D3.js compatible JSON for dependency graph."""
        nodes = [{'id': 'root', 'label': tree.root.package_name, 'version': tree.root.version}]
        links = []
        
        for i, child in enumerate(tree.root.children[:10]):
            child_id = f"dep_{i}"
            nodes.append({'id': child_id, 'label': child.package_name, 'version': child.version})
            links.append({'source': 'root', 'target': child_id})
        
        return {'nodes': nodes, 'links': links}
    
    def _generate_cytoscape_dependencies(self, tree) -> Dict[str, Any]:
        """Create Cytoscape.js compatible JSON for dependency graph."""
        elements = {'nodes': [], 'edges': []}
        
        elements['nodes'].append({
            'data': {'id': 'root', 'label': tree.root.package_name, 'version': tree.root.version}
        })
        
        edge_id = 0
        for i, child in enumerate(tree.root.children[:10]):
            child_id = f"dep_{i}"
            elements['nodes'].append({
                'data': {'id': child_id, 'label': child.package_name, 'version': child.version}
            })
            elements['edges'].append({
                'data': {'id': f"edge_{edge_id}", 'source': 'root', 'target': child_id}
            })
            edge_id += 1
        
        return {'elements': elements}
    
    def _generate_layer_diagram(self, analysis_data: Dict[str, Any]) -> Visualization:
        """Generate layer diagram."""
        layers = analysis_data.get('layers', [])
        
        # Generate Mermaid
        mermaid = self._generate_mermaid_layers(layers)
        
        # Generate D3.js JSON
        d3_json = self._generate_d3_layers(layers)
        
        # Generate Cytoscape.js JSON
        cytoscape_json = self._generate_cytoscape_layers(layers)
        
        # Create metadata
        metadata = VisualizationMetadata(
            node_count=len(layers),
            edge_count=0,
            layout_hints={'algorithm': 'grid', 'rows': len(layers)},
            interaction_handlers={layer.name: 'show_layer_components' for layer in layers}
        )
        
        return Visualization(
            diagram_type='layer_diagram',
            mermaid=mermaid,
            d3_json=d3_json,
            cytoscape_json=cytoscape_json,
            metadata=metadata
        )
    
    def _generate_mermaid_layers(self, layers: List[Layer]) -> str:
        """Create Mermaid syntax for layer diagram."""
        lines = ['graph TB']
        
        for i, layer in enumerate(layers):
            node_id = f"LAYER{i}"
            label = f"{layer.name.upper()}<br/>{len(layer.components)} components"
            lines.append(f"    {node_id}[\"{label}\"]")
        
        # Stack layers vertically
        for i in range(len(layers) - 1):
            lines.append(f"    LAYER{i} -.-> LAYER{i+1}")
        
        return '\n'.join(lines)
    
    def _generate_d3_layers(self, layers: List[Layer]) -> Dict[str, Any]:
        """Create D3.js compatible JSON for layer diagram."""
        nodes = []
        
        for i, layer in enumerate(layers):
            nodes.append({
                'id': f"layer_{i}",
                'label': layer.name.upper(),
                'component_count': len(layer.components),
                'level': i
            })
        
        return {'nodes': nodes, 'links': []}
    
    def _generate_cytoscape_layers(self, layers: List[Layer]) -> Dict[str, Any]:
        """Create Cytoscape.js compatible JSON for layer diagram."""
        elements = {'nodes': [], 'edges': []}
        
        for i, layer in enumerate(layers):
            elements['nodes'].append({
                'data': {
                    'id': f"layer_{i}",
                    'label': layer.name.upper(),
                    'component_count': len(layer.components),
                    'level': i
                }
            })
        
        return {'elements': elements}
    
    def _empty_visualization(self, diagram_type: str) -> Visualization:
        """Create empty visualization."""
        return Visualization(
            diagram_type=diagram_type,
            mermaid='graph TD\n    A[No data available]',
            d3_json={'nodes': [], 'links': []},
            cytoscape_json={'elements': {'nodes': [], 'edges': []}},
            metadata=VisualizationMetadata(
                node_count=0,
                edge_count=0,
                layout_hints={},
                interaction_handlers={}
            )
        )
    
    def _add_interaction_metadata(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Include click handler data."""
        # This would add interaction metadata in production
        return visualization
    
    def _calculate_layout_hints(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Provide positioning suggestions."""
        # This would calculate layout hints in production
        return visualization
