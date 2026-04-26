"""
Layer Analyzer for Architecture Analysis

Identifies and categorizes architectural layers and components.
"""

import json
import logging
from typing import List, Dict, Any

from bedrock_client import BedrockClient
from models.architecture_models import Layer, Component, LayerConnection

logger = logging.getLogger(__name__)


class LayerAnalyzer:
    """Identifies and categorizes architectural layers and components."""
    
    LAYER_TYPES = ['presentation', 'api', 'business', 'data', 'infrastructure']
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize layer analyzer.
        
        Args:
            bedrock_client: Optional Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def analyze_layers(
        self,
        context: Dict[str, Any]
    ) -> List[Layer]:
        """
        Analyze architectural layers and components.
        
        Args:
            context: Analysis context
            
        Returns:
            List of detected layers with components
        """
        try:
            # Build prompt for layer analysis
            prompt = self._build_layer_prompt(context)
            
            # Get AI analysis
            response = self.bedrock_client.invoke_claude(prompt)
            
            # Parse response
            layers = self._parse_layer_response(response)
            
            # Add uncategorized layer if needed
            layers = self._add_uncategorized_layer(layers, context)
            
            logger.info(f"Analyzed {len(layers)} layers")
            return layers
            
        except Exception as e:
            logger.error(f"Error analyzing layers: {str(e)}")
            # Return fallback heuristic-based analysis
            return self._fallback_layer_analysis(context)
    
    def _build_layer_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Bedrock AI layer analysis."""
        file_summaries = context.get('file_summaries', [])
        
        # Extract file information
        file_info = []
        for f in file_summaries[:50]:  # Limit to 50 files
            file_info.append({
                'path': f.get('file_path', ''),
                'summary': f.get('summary', '')[:200]  # Truncate summary
            })
        
        prompt = f"""Analyze this codebase and identify architectural layers and components.

Total Files: {len(file_summaries)}

File Information (sample):
{json.dumps(file_info, indent=2)}

Layer Types:
- presentation: UI components, views, templates
- api: API handlers, controllers, routes
- business: Business logic, services, use cases
- data: Repositories, DAOs, database access
- infrastructure: Configuration, utilities, external integrations

For each layer, provide:
1. Layer name (must be from layer types above)
2. Description
3. Components (list of components in this layer)
4. Technologies used
5. Entry points (main files)
6. Connections to other layers

For each component, provide:
1. Name
2. Type (e.g., "Controller", "Service", "Repository")
3. File path
4. Line count (estimate)
5. Complexity score (0-100 estimate)
6. Dependencies (other component names)
7. Health score (0-100 estimate)
8. Responsibilities (list of what it does)

Return ONLY a JSON array of layers in this exact format:
[
  {{
    "name": "api",
    "description": "API layer description",
    "components": [
      {{
        "name": "UserController",
        "type": "Controller",
        "file_path": "src/controllers/user.py",
        "line_count": 150,
        "complexity_score": 12.5,
        "dependencies": ["UserService"],
        "health_score": 85.0,
        "responsibilities": ["Handle user requests", "Validate input"]
      }}
    ],
    "technologies": ["Flask", "Python"],
    "entry_points": ["src/app.py"],
    "connections": [
      {{
        "from_layer": "api",
        "to_layer": "business",
        "connection_type": "Function call",
        "file_paths": ["src/controllers/user.py"]
      }}
    ]
  }}
]

Return empty array [] if no layers detected."""
        
        return prompt
    
    def _parse_layer_response(self, response: str) -> List[Layer]:
        """Parse AI response into Layer objects."""
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON array found in response")
                return []
            
            json_str = response[json_start:json_end]
            layers_data = json.loads(json_str)
            
            layers = []
            for data in layers_data:
                # Parse components
                components = []
                for comp_data in data.get('components', []):
                    component = Component(
                        name=comp_data.get('name', 'Unknown'),
                        type=comp_data.get('type', 'Unknown'),
                        file_path=comp_data.get('file_path', ''),
                        line_count=int(comp_data.get('line_count', 0)),
                        complexity_score=float(comp_data.get('complexity_score', 0)),
                        dependencies=comp_data.get('dependencies', []),
                        health_score=float(comp_data.get('health_score', 75)),
                        responsibilities=comp_data.get('responsibilities', [])
                    )
                    components.append(component)
                
                # Parse connections
                connections = []
                for conn_data in data.get('connections', []):
                    connection = LayerConnection(
                        from_layer=conn_data.get('from_layer', ''),
                        to_layer=conn_data.get('to_layer', ''),
                        connection_type=conn_data.get('connection_type', ''),
                        file_paths=conn_data.get('file_paths', [])
                    )
                    connections.append(connection)
                
                layer = Layer(
                    name=data.get('name', 'unknown'),
                    description=data.get('description', ''),
                    components=components,
                    technologies=data.get('technologies', []),
                    entry_points=data.get('entry_points', []),
                    connections=connections
                )
                layers.append(layer)
            
            return layers
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing layer response: {str(e)}")
            return []
    
    def _add_uncategorized_layer(
        self,
        layers: List[Layer],
        context: Dict[str, Any]
    ) -> List[Layer]:
        """
        Add uncategorized layer for files that don't fit into other layers.
        
        Args:
            layers: Existing layers
            context: Analysis context
            
        Returns:
            Updated list of layers with uncategorized layer if needed
        """
        # Get all categorized file paths
        categorized_paths = set()
        for layer in layers:
            for component in layer.components:
                categorized_paths.add(component.file_path)
        
        # Find uncategorized files
        file_summaries = context.get('file_summaries', [])
        uncategorized_files = [
            f for f in file_summaries
            if f.get('file_path', '') not in categorized_paths
        ]
        
        if uncategorized_files:
            # Create components for uncategorized files
            components = []
            for f in uncategorized_files[:20]:  # Limit to 20
                component = Component(
                    name=f.get('file_path', '').split('/')[-1],
                    type='Uncategorized',
                    file_path=f.get('file_path', ''),
                    line_count=f.get('line_count', 0),
                    complexity_score=0.0,
                    dependencies=[],
                    health_score=50.0,
                    responsibilities=['Uncategorized functionality']
                )
                components.append(component)
            
            uncategorized_layer = Layer(
                name='uncategorized',
                description='Files that could not be categorized into standard layers',
                components=components,
                technologies=[],
                entry_points=[],
                connections=[]
            )
            layers.append(uncategorized_layer)
        
        return layers
    
    def _fallback_layer_analysis(self, context: Dict[str, Any]) -> List[Layer]:
        """
        Fallback heuristic-based layer analysis when AI fails.
        
        Uses simple file path analysis to categorize layers.
        """
        file_summaries = context.get('file_summaries', [])
        
        # Initialize layers
        layer_map = {
            'presentation': [],
            'api': [],
            'business': [],
            'data': [],
            'infrastructure': []
        }
        
        # Categorize files
        for f in file_summaries:
            path = f.get('file_path', '').lower()
            
            # Simple heuristic categorization
            if any(x in path for x in ['view', 'template', 'component', 'ui']):
                layer_map['presentation'].append(f)
            elif any(x in path for x in ['handler', 'controller', 'route', 'api']):
                layer_map['api'].append(f)
            elif any(x in path for x in ['service', 'business', 'usecase', 'domain']):
                layer_map['business'].append(f)
            elif any(x in path for x in ['repository', 'dao', 'model', 'database']):
                layer_map['data'].append(f)
            elif any(x in path for x in ['config', 'util', 'helper', 'lib']):
                layer_map['infrastructure'].append(f)
        
        # Build layers
        layers = []
        for layer_name, files in layer_map.items():
            if not files:
                continue
            
            components = []
            for f in files[:10]:  # Limit to 10 per layer
                component = Component(
                    name=f.get('file_path', '').split('/')[-1],
                    type=layer_name.capitalize(),
                    file_path=f.get('file_path', ''),
                    line_count=f.get('line_count', 0),
                    complexity_score=10.0,
                    dependencies=[],
                    health_score=70.0,
                    responsibilities=[f'Handles {layer_name} logic']
                )
                components.append(component)
            
            layer = Layer(
                name=layer_name,
                description=f'{layer_name.capitalize()} layer',
                components=components,
                technologies=[],
                entry_points=[],
                connections=[]
            )
            layers.append(layer)
        
        logger.info(f"Fallback analysis found {len(layers)} layers")
        return layers
    
    def _categorize_component(self, file_path: str) -> str:
        """
        Assign component to layer based on file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Layer name
        """
        path_lower = file_path.lower()
        
        if any(x in path_lower for x in ['view', 'template', 'component', 'ui']):
            return 'presentation'
        elif any(x in path_lower for x in ['handler', 'controller', 'route', 'api']):
            return 'api'
        elif any(x in path_lower for x in ['service', 'business', 'usecase', 'domain']):
            return 'business'
        elif any(x in path_lower for x in ['repository', 'dao', 'model', 'database']):
            return 'data'
        elif any(x in path_lower for x in ['config', 'util', 'helper', 'lib']):
            return 'infrastructure'
        else:
            return 'uncategorized'
    
    def _analyze_component(self, file_data: Dict[str, Any]) -> Component:
        """
        Extract component details from file data.
        
        Args:
            file_data: File information
            
        Returns:
            Component object
        """
        return Component(
            name=file_data.get('file_path', '').split('/')[-1],
            type='Component',
            file_path=file_data.get('file_path', ''),
            line_count=file_data.get('line_count', 0),
            complexity_score=0.0,
            dependencies=[],
            health_score=75.0,
            responsibilities=[]
        )
    
    def _identify_connections(self, layers: List[Layer]) -> List[Layer]:
        """
        Find inter-layer connections.
        
        Args:
            layers: List of layers
            
        Returns:
            Updated layers with connections
        """
        # This is a placeholder - actual implementation would analyze imports/dependencies
        return layers
