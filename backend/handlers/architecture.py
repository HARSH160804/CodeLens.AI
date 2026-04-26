"""
Lambda handler for architecture summary generation.
Implements FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-3.5, FR-3.6 from requirements.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

# Import from lib directory (Lambda-compatible paths)
from lib.bedrock_client import BedrockClient
from lib.vector_store import DynamoDBVectorStore
from lib.analysis.engine import AnalysisEngine
from lib.analysis.cache_manager import CacheManager


# Initialize shared resources
bedrock_client = BedrockClient()
vector_store = DynamoDBVectorStore()
analysis_engine = AnalysisEngine(bedrock_client)
cache_manager = CacheManager()
dynamodb = boto3.resource('dynamodb')
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))
cache_table = dynamodb.Table(os.environ.get('CACHE_TABLE', 'BloomWay-Cache'))

# Constants
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}
CACHE_TTL_HOURS = 24


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate architecture summary and Mermaid diagram for a repository.
    
    Path parameters:
        id: Repository ID
    
    Query parameters:
        level: Analysis level (basic/intermediate/advanced), default: intermediate
        view: Response view filter (all/summary/visualizations/patterns/layers/metrics/recommendations), default: all
        format: Visualization format filter (all/mermaid/interactive/d3/cytoscape), default: all
    
    Returns:
        Full response (view=all):
        {
            "repo_id": "uuid",
            "schema_version": "2.0",
            "generated_at": "timestamp",
            "execution_duration_ms": 1234,
            "analysis_level": "intermediate",
            "statistics": {...},
            "patterns": [...],
            "layers": [...],
            "tech_stack": [...],
            "data_flows": [...],
            "dependencies": {...},
            "metrics": {...},
            "recommendations": [...],
            "visualizations": {...},
            "architecture": {...},
            "diagram": "flowchart TD..."
        }
        
        Filtered response examples:
        - view=visualizations: Only visualizations section
        - view=patterns: Only patterns section
        - format=mermaid: Only mermaid diagrams in visualizations
    """
    try:
        # Extract parameters
        repo_id = event.get('pathParameters', {}).get('id')
        query_params = event.get('queryStringParameters') or {}
        level = query_params.get('level', 'intermediate')
        view = query_params.get('view', 'all')
        format_type = query_params.get('format', 'all')
        
        if not repo_id:
            return _error_response(400, "Repository ID is required")
        
        if level not in ['basic', 'intermediate', 'advanced']:
            return _error_response(400, f"Invalid level: {level}. Must be 'basic', 'intermediate', or 'advanced'")
        
        valid_views = ['all', 'summary', 'visualizations', 'patterns', 'layers', 'metrics', 'recommendations', 'tech_stack', 'dependencies', 'data_flows']
        if view not in valid_views:
            return _error_response(400, f"Invalid view: {view}. Must be one of {', '.join(valid_views)}")
        
        valid_formats = ['all', 'mermaid', 'interactive', 'd3', 'cytoscape']
        if format_type not in valid_formats:
            return _error_response(400, f"Invalid format: {format_type}. Must be one of {', '.join(valid_formats)}")
        
        print(f"Generating architecture for repo_id: {repo_id}, level: {level}, view: {view}, format: {format_type}")
        
        # Step 1: Check cache first using new Cache Manager
        cached_result = cache_manager.get_cached_analysis(repo_id, level)
        if cached_result:
            print("Returning cached architecture (v2.0)")
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps(cached_result)
            }
        
        # Step 2: Fetch repo metadata from DynamoDB
        try:
            response = repos_table.get_item(Key={'repo_id': repo_id})
            
            if 'Item' not in response:
                return _error_response(404, f"Repository {repo_id} not found")
            
            repo_metadata = response['Item']
            
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve repository metadata")
        
        # Step 3: Retrieve file summaries from vector store
        print("Retrieving file chunks from vector store...")
        file_summaries = _get_file_summaries(repo_id)
        
        # Step 4: Generate comprehensive architecture analysis using new Analysis Engine
        print("Generating comprehensive architecture analysis with Analysis Engine v2.0...")
        try:
            result = analysis_engine.analyze(
                repo_id=repo_id,
                repo_metadata=repo_metadata,
                file_summaries=file_summaries,
                level=level
            )
            
            # Apply view and format filters
            result = _apply_response_filters(result, view, format_type)
            
            # Cache the result using new Cache Manager
            cache_manager.cache_analysis(repo_id, level, result)
            
        except Exception as e:
            print(f"Failed to generate architecture analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback to legacy analysis
            print("Falling back to legacy analysis...")
            context = _build_architecture_context(repo_metadata, file_summaries, level)
            architecture_json = _generate_fallback_architecture(repo_metadata, file_summaries)
            timestamp = datetime.utcnow().isoformat() + 'Z'
            result = {
                'repo_id': repo_id,
                'architecture': architecture_json,
                'diagram': architecture_json.get('mermaidDiagram', _generate_fallback_diagram(repo_metadata)),
                'generated_at': timestamp,
                'schema_version': '1.0',
                'error': str(e)
            }
            _cache_architecture(repo_id, level, result)
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Unexpected error in architecture handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


def _get_cached_architecture(repo_id: str, level: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached architecture from DynamoDB.
    
    Args:
        repo_id: Repository identifier
        level: Analysis level
        
    Returns:
        Cached result or None if not found/expired
    """
    try:
        cache_key = f"{repo_id}#{level}"
        response = cache_table.get_item(Key={'cache_key': cache_key})
        
        if 'Item' in response:
            item = response['Item']
            # Check if cache is still valid (TTL not expired)
            if 'ttl' in item and item['ttl'] > int(datetime.utcnow().timestamp()):
                return item.get('data')
        
        return None
        
    except Exception as e:
        print(f"Cache retrieval error: {str(e)}")
        return None


def _cache_architecture(repo_id: str, level: str, data: Dict[str, Any]) -> None:
    """
    Cache architecture result in DynamoDB.
    
    Args:
        repo_id: Repository identifier
        level: Analysis level
        data: Architecture data to cache
    """
    try:
        cache_key = f"{repo_id}#{level}"
        ttl = int((datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)).timestamp())
        
        cache_table.put_item(Item={
            'cache_key': cache_key,
            'repo_id': repo_id,
            'level': level,
            'data': data,
            'ttl': ttl,
            'created_at': datetime.utcnow().isoformat() + 'Z'
        })
        
        print(f"Cached architecture for {cache_key}")
        
    except Exception as e:
        print(f"Cache storage error: {str(e)}")
        # Non-critical, continue without caching


def _get_file_summaries(repo_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve top-level file summaries from vector store.
    
    Args:
        repo_id: Repository identifier
        
    Returns:
        List of file summaries with paths and content snippets
    """
    file_summaries = []
    
    try:
        # Get all chunks for the repo (limited by vector store max)
        # Group by file_path and take first chunk of each file
        seen_files = set()
        
        # Use a dummy query to get all chunks (not ideal, but works for MVP)
        # In production, vector store should have a get_all_files method
        dummy_embedding = [0.0] * 1024  # Titan v2 dimension
        all_chunks = vector_store.search(repo_id, dummy_embedding, top_k=100)
        
        for chunk in all_chunks:
            file_path = chunk['file_path']
            if file_path not in seen_files:
                seen_files.add(file_path)
                file_summaries.append({
                    'file_path': file_path,
                    'content_preview': chunk['content'][:500],  # First 500 chars
                    'metadata': chunk.get('metadata', {})
                })
        
        print(f"Retrieved {len(file_summaries)} file summaries")
        
    except Exception as e:
        print(f"Error retrieving file summaries: {str(e)}")
    
    return file_summaries


def _build_architecture_context(
    repo_metadata: Dict[str, Any],
    file_summaries: List[Dict[str, Any]],
    level: str
) -> str:
    """
    Build context string for architecture analysis.
    
    Args:
        repo_metadata: Repository metadata from DynamoDB
        file_summaries: List of file summaries
        level: Analysis level
        
    Returns:
        Context string for Bedrock prompt
    """
    tech_stack = repo_metadata.get('tech_stack', {})
    file_count = repo_metadata.get('file_count', 0)
    
    # Repo summary metrics (stored during ingestion)
    total_lines = repo_metadata.get('total_lines_of_code', 0)
    lang_breakdown = repo_metadata.get('language_breakdown', {})
    primary_lang = repo_metadata.get('primary_language', 'unknown')
    folder_depth = repo_metadata.get('folder_depth', 0)
    largest_file = repo_metadata.get('largest_file', {})
    
    # Folder structure (from precomputed file_tree or file_paths)
    file_tree = repo_metadata.get('file_tree', {})
    if file_tree:
        folder_structure = json.dumps(file_tree, indent=2)[:2000]
    else:
        file_paths = repo_metadata.get('file_paths', [])
        folder_structure = '\n'.join([f"  {p}" for p in file_paths[:40]])
    
    # File previews
    file_list = '\n'.join([
        f"- {f['file_path']}: {f['content_preview'][:150]}..."
        for f in file_summaries[:25]
    ])
    
    # Language breakdown formatted
    lang_str = ', '.join([f"{ext}: {cnt} files" for ext, cnt in sorted(
        lang_breakdown.items(), key=lambda x: x[1], reverse=True
    )[:8]]) if lang_breakdown else 'unknown'
    
    context = f"""=== REPOSITORY METRICS ===
Total Files: {file_count}
Total Lines of Code: {total_lines}
Primary Language: {primary_lang}
Language Breakdown: {lang_str}
Max Folder Depth: {folder_depth}
Largest File: {largest_file.get('path', 'N/A')} ({largest_file.get('lines', 0)} lines)
Tech Stack: {json.dumps(tech_stack, indent=2)}

=== FOLDER STRUCTURE ===
{folder_structure}

=== FILE PREVIEWS (top {min(len(file_summaries), 25)}) ===
{file_list}

Analysis Level: {level}"""
    
    return context


def _generate_architecture_analysis(context: str, level: str) -> Dict[str, Any]:
    """
    Generate architecture analysis using Bedrock.
    
    Args:
        context: Context string with repo information
        level: Analysis level
        
    Returns:
        Architecture JSON structure
    """
    # Adjust system prompt based on level
    if level == 'basic':
        level_hint = 'Provide a high-level overview suitable for beginners. Focus on main components and simple relationships.'
    elif level == 'advanced':
        level_hint = 'Provide an in-depth analysis including design patterns, architectural trade-offs, scalability considerations, and technical debt.'
    else:
        level_hint = 'Provide a balanced analysis covering components, patterns, and data flow.'
    
    system_prompt = bedrock_client.ARCHITECTURE_SYSTEM_PROMPT + f"\n\n{level_hint}"
    
    prompt = f"""{context}

You are a senior software architect. Analyze the repository above and respond with ONLY a valid JSON object matching this EXACT schema (no markdown, no commentary):

{{
  "overview": "2-3 sentence high-level summary of what this codebase does",
  "architectureStyle": "e.g. Monolithic MVC, Microservices, Serverless, Layered, etc.",
  "components": [
    {{
      "name": "Component Name",
      "description": "What this component does",
      "files": ["file1.py", "file2.js"],
      "role": "e.g. API Layer, Data Access, Business Logic"
    }}
  ],
  "dataFlowSteps": [
    "Step 1: User sends request to API Gateway",
    "Step 2: Lambda handler validates input"
  ],
  "mermaidDiagram": "flowchart TD\n    A[Client] --> B[API]\n    B --> C[Service]\n    C --> D[(Database)]",
  "confidence": 0.85
}}

IMPORTANT:
- The mermaidDiagram must be valid Mermaid flowchart TD syntax on a single JSON string (use \n for newlines).
- confidence is 0.0-1.0 reflecting how confident you are in this analysis.
- Respond with ONLY the JSON object."""
    
    response = bedrock_client.invoke_claude(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=3000,
        temperature=0.2
    )
    
    return _parse_and_validate_architecture(response, repo_metadata_hint=None)


def _parse_and_validate_architecture(
    response: str,
    repo_metadata_hint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Parse LLM response as JSON, validate required fields, handle malformation."""
    json_str = response.strip()
    if '```json' in json_str:
        start = json_str.find('```json') + 7
        end = json_str.find('```', start)
        json_str = json_str[start:end].strip()
    elif '```' in json_str:
        start = json_str.find('```') + 3
        end = json_str.find('```', start)
        json_str = json_str[start:end].strip()
    
    try:
        arch = json.loads(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse architecture JSON: {str(e)}")
        print(f"Raw response (first 500 chars): {response[:500]}")
        # Attempt brace extraction
        brace_start = json_str.find('{')
        brace_end = json_str.rfind('}')
        if brace_start != -1 and brace_end > brace_start:
            try:
                arch = json.loads(json_str[brace_start:brace_end + 1])
            except (json.JSONDecodeError, ValueError):
                raise
        else:
            raise
    
    # Schema enforcement — fill missing fields
    defaults = {
        'overview': 'Architecture overview unavailable.',
        'architectureStyle': 'Unknown',
        'components': [],
        'dataFlowSteps': [],
        'mermaidDiagram': 'flowchart TD\n    A[Application] --> B[Components]\n    B --> C[(Data)]',
        'confidence': 0.5
    }
    for key, default_val in defaults.items():
        if key not in arch:
            arch[key] = default_val
    
    # Clamp confidence
    try:
        arch['confidence'] = max(0.0, min(1.0, float(arch['confidence'])))
    except (TypeError, ValueError):
        arch['confidence'] = 0.5
    
    # Validate mermaid starts correctly
    diagram = arch.get('mermaidDiagram', '')
    if diagram and not diagram.strip().startswith('flowchart') and not diagram.strip().startswith('graph'):
        arch['mermaidDiagram'] = 'flowchart TD\n' + diagram
    
    return arch


def _generate_fallback_architecture(
    repo_metadata: Dict[str, Any],
    file_summaries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate deterministic fallback architecture when LLM fails."""
    tech_stack = repo_metadata.get('tech_stack', {})
    languages = tech_stack.get('languages', [])
    frameworks = tech_stack.get('frameworks', [])
    primary_lang = repo_metadata.get('primary_language', 'unknown')
    total_lines = repo_metadata.get('total_lines_of_code', 0)
    
    # Identify entry points
    entry_files = []
    for f in file_summaries:
        path = f['file_path']
        if any(name in path.lower() for name in ['main', 'app', 'index', 'server', 'handler', 'lambda']):
            entry_files.append(path)
    
    return {
        'overview': f"Repository with {repo_metadata.get('file_count', 0)} files, "
                    f"{total_lines} lines of code. "
                    f"Primary language: {primary_lang}. "
                    f"Uses {', '.join(frameworks) if frameworks else 'standard libraries'}.",
        'architectureStyle': 'Unknown (LLM analysis unavailable)',
        'components': [
            {
                'name': 'Core Application',
                'description': 'Main application logic',
                'files': [f['file_path'] for f in file_summaries[:5]],
                'role': 'Application'
            }
        ],
        'dataFlowSteps': ['Data flow analysis unavailable. Please review the codebase manually.'],
        'mermaidDiagram': _generate_fallback_diagram(repo_metadata),
        'confidence': 0.0
    }


def _generate_fallback_diagram(repo_metadata: Dict[str, Any]) -> str:
    """Generate basic Mermaid diagram as fallback."""
    tech_stack = repo_metadata.get('tech_stack', {})
    languages = tech_stack.get('languages', [])
    frameworks = tech_stack.get('frameworks', [])
    
    diagram = 'flowchart TD\n'
    diagram += '    A[Application Entry Point]\n'
    
    if languages:
        for i, lang in enumerate(languages[:3]):
            diagram += f'    A --> B{i}[{lang} Components]\n'
    
    if frameworks:
        for i, fw in enumerate(frameworks[:3]):
            diagram += f'    A --> C{i}[{fw} Layer]\n'
    
    diagram += '    A --> D[Data Layer]\n'
    diagram += '    D --> E[(Storage)]\n'
    
    return diagram


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        API Gateway response dict
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message,
            'status_code': status_code
        })
    }


def _apply_response_filters(result: Dict[str, Any], view: str, format_type: str) -> Dict[str, Any]:
    """
    Apply view and format filters to the analysis result.
    
    Args:
        result: Full analysis result from Analysis Engine
        view: View filter (all/summary/visualizations/patterns/layers/metrics/recommendations/tech_stack/dependencies/data_flows)
        format_type: Format filter for visualizations (all/mermaid/interactive/d3/cytoscape)
        
    Returns:
        Filtered result based on view and format parameters
    """
    # If view is 'all' and format is 'all', return full result
    if view == 'all' and format_type == 'all':
        return result
    
    # Apply view filter
    if view != 'all':
        filtered_result = {
            'repo_id': result.get('repo_id'),
            'schema_version': result.get('schema_version'),
            'generated_at': result.get('generated_at'),
            'analysis_level': result.get('analysis_level')
        }
        
        if view == 'summary':
            # Summary includes statistics, execution time, and basic metadata
            filtered_result['statistics'] = result.get('statistics', {})
            filtered_result['execution_duration_ms'] = result.get('execution_duration_ms', 0)
            filtered_result['architecture'] = result.get('architecture', {})
            
        elif view == 'visualizations':
            filtered_result['visualizations'] = result.get('visualizations', {})
            filtered_result['diagram'] = result.get('diagram', '')
            
        elif view == 'patterns':
            filtered_result['patterns'] = result.get('patterns', [])
            
        elif view == 'layers':
            filtered_result['layers'] = result.get('layers', [])
            
        elif view == 'metrics':
            filtered_result['metrics'] = result.get('metrics', {})
            filtered_result['statistics'] = result.get('statistics', {})
            
        elif view == 'recommendations':
            filtered_result['recommendations'] = result.get('recommendations', [])
            
        elif view == 'tech_stack':
            filtered_result['tech_stack'] = result.get('tech_stack', [])
            # Include tech stack cards from visualizations if available
            visualizations = result.get('visualizations', {})
            if 'tech_stack_cards' in visualizations:
                filtered_result['tech_stack_cards'] = visualizations['tech_stack_cards']
            
        elif view == 'dependencies':
            filtered_result['dependencies'] = result.get('dependencies', {})
            
        elif view == 'data_flows':
            filtered_result['data_flows'] = result.get('data_flows', [])
            # Include data flow scenarios from visualizations if available
            visualizations = result.get('visualizations', {})
            if 'data_flow_scenarios' in visualizations:
                filtered_result['data_flow_scenarios'] = visualizations['data_flow_scenarios']
        
        result = filtered_result
    
    # Apply format filter to visualizations
    if format_type != 'all' and 'visualizations' in result:
        filtered_visualizations = {}
        
        for viz_key, viz_data in result['visualizations'].items():
            # Skip non-visualization data (like data_flow_scenarios, tech_stack_cards)
            if not isinstance(viz_data, dict) or 'diagram_type' not in viz_data:
                filtered_visualizations[viz_key] = viz_data
                continue
            
            filtered_viz = {
                'diagram_type': viz_data.get('diagram_type')
            }
            
            if format_type == 'mermaid':
                filtered_viz['mermaid'] = viz_data.get('mermaid', '')
                
            elif format_type == 'interactive':
                # Interactive includes the full interactive JSON
                if 'd3_json' in viz_data:
                    filtered_viz['interactive'] = viz_data['d3_json']
                filtered_viz['metadata'] = viz_data.get('metadata', {})
                
            elif format_type == 'd3':
                filtered_viz['d3_json'] = viz_data.get('d3_json', {})
                filtered_viz['metadata'] = viz_data.get('metadata', {})
                
            elif format_type == 'cytoscape':
                filtered_viz['cytoscape_json'] = viz_data.get('cytoscape_json', {})
                filtered_viz['metadata'] = viz_data.get('metadata', {})
            
            filtered_visualizations[viz_key] = filtered_viz
        
        result['visualizations'] = filtered_visualizations
        
        # Also filter the top-level diagram field if present
        if format_type == 'mermaid' and 'diagram' in result:
            # Keep diagram as-is (it's already mermaid)
            pass
        elif format_type != 'mermaid' and 'diagram' in result:
            # Remove diagram for non-mermaid formats
            result.pop('diagram', None)
    
    return result
