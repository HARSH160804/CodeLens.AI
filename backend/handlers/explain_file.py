"""
Lambda handler for file explanation generation.
Implements FR-2.1, FR-2.2, FR-2.3, FR-2.4 from requirements.
"""
import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from urllib.parse import unquote
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from bedrock_client import BedrockClient
from vector_store import DynamoDBVectorStore
from code_processor import RepositoryProcessor
from complexity_analyzer import compute_complexity
from static_analysis import analyze_file_metadata


# Initialize shared resources
bedrock_client = BedrockClient()
vector_store = DynamoDBVectorStore()
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
    Generate multi-level explanation for a code file.
    
    Path parameters:
        id: Repository ID
        path: File path (URL encoded)
    
    Query parameters:
        level: Explanation level (beginner/intermediate/advanced), default: intermediate
    
    Returns:
        {
            "repo_id": "uuid",
            "file_path": "src/core/api.js",
            "explanation": {
                "purpose": "string",
                "key_functions": [{"name": "string", "description": "string", "line": int}],
                "patterns": ["pattern1", "pattern2"],
                "dependencies": ["dep1", "dep2"],
                "complexity": {"lines": int, "functions": int}
            },
            "related_files": ["file1.py", "file2.py"],
            "level": "intermediate",
            "generated_at": "timestamp"
        }
    """
    try:
        # Extract parameters
        repo_id = event.get('pathParameters', {}).get('id')
        encoded_path = event.get('pathParameters', {}).get('path', '')
        file_path = unquote(encoded_path) if encoded_path else None
        
        query_params = event.get('queryStringParameters') or {}
        level = query_params.get('level', 'intermediate')
        
        if not repo_id:
            return _error_response(400, "Repository ID is required")
        
        if not file_path:
            return _error_response(400, "File path is required")
        
        if level not in ['beginner', 'intermediate', 'advanced']:
            return _error_response(400, f"Invalid level: {level}. Must be 'beginner', 'intermediate', or 'advanced'")
        
        print(f"Explaining file: {file_path} for repo_id: {repo_id}, level: {level}")
        
        # Step 1: Check cache
        cached_result = _get_cached_explanation(repo_id, file_path, level)
        if cached_result:
            print("Returning cached explanation")
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps(cached_result, default=_decimal_default)
            }
        
        # Step 2: Verify repository exists
        try:
            response = repos_table.get_item(Key={'repo_id': repo_id})
            if 'Item' not in response:
                return _error_response(404, f"Repository {repo_id} not found")
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve repository metadata")
        
        # Step 3: Retrieve file chunks from vector store
        print(f"Retrieving chunks for file: {file_path}")
        file_chunks = vector_store.get_file_chunks(repo_id, file_path)
        
        if not file_chunks:
            return _error_response(404, f"File {file_path} not found in repository")
        
        # Step 4: Reconstruct file content from chunks
        file_content = _reconstruct_file_content(file_chunks)
        
        # Step 5: Extract file metadata + static analysis + complexity
        file_metadata = _extract_file_metadata(file_content, file_path)
        static_analysis = analyze_file_metadata(file_content)
        complexity_result = compute_complexity(file_content)
        
        # Step 5.5: Retrieve top-3 related chunks for repo context
        related_context_chunks = []
        similarity_scores = []
        try:
            sample_embedding = bedrock_client.generate_embedding(file_content[:500])
            related_results = vector_store.search(repo_id, sample_embedding, top_k=5)
            for rc in related_results:
                if rc['file_path'] != file_path:
                    related_context_chunks.append({
                        'file_path': rc['file_path'],
                        'snippet': rc['content'][:300]
                    })
                    # Capture similarity score if available
                    score = rc.get('score', rc.get('similarity', 0))
                    similarity_scores.append(float(score))
                if len(related_context_chunks) >= 3:
                    break
        except Exception as e:
            print(f"Warning: Failed to retrieve related context: {str(e)}")
        
        # Step 6: Generate explanation with Bedrock (no streaming)
        print(f"Generating {level} explanation with Bedrock...")
        try:
            explanation = _generate_explanation(
                file_path, file_content, file_metadata,
                static_analysis, complexity_result,
                related_context_chunks, level
            )
        except Exception as e:
            print(f"Failed to generate explanation: {str(e)}")
            explanation = _generate_fallback_explanation(
                file_path, file_content, file_metadata,
                static_analysis, complexity_result
            )
        
        # Step 6.5: Override confidence with deterministic computation
        explanation['confidence'] = _compute_deterministic_confidence(
            similarity_scores, len(related_context_chunks), len(file_content)
        )
        
        # Step 7: Identify related files
        related_files = _identify_related_files(file_path, file_content, repo_id)
        
        # Step 8: Build response
        timestamp = datetime.utcnow().isoformat() + 'Z'
        result = {
            'repo_id': repo_id,
            'file_path': file_path,
            'explanation': explanation,
            'related_files': related_files,
            'level': level,
            'generated_at': timestamp
        }
        
        # Step 9: Cache result
        _cache_explanation(repo_id, file_path, level, result)
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Unexpected error in explain_file handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


def _get_cached_explanation(repo_id: str, file_path: str, level: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached explanation from DynamoDB.
    
    Key schema:
        Partition key (repo_id): Repository ID
        Sort key (sort_key):     file_path#level
    """
    try:
        sort_key = f"{file_path}#{level}"
        response = cache_table.get_item(Key={
            'repo_id': repo_id,
            'sort_key': sort_key
        })
        
        if 'Item' in response:
            item = response['Item']
            # Check TTL — skip expired entries
            if 'ttl' in item and item['ttl'] > int(datetime.utcnow().timestamp()):
                return item.get('data')
        
        return None
    except Exception as e:
        print(f"Cache retrieval error: {str(e)}")
        return None


def _decimal_default(obj):
    """JSON serializer for Decimal types from DynamoDB."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _convert_floats(obj):
    """Recursively convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def _cache_explanation(repo_id: str, file_path: str, level: str, data: Dict[str, Any]) -> None:
    """Cache explanation result in DynamoDB.
    
    Key schema:
        Partition key (repo_id): Repository ID
        Sort key (sort_key):     file_path#level
    """
    try:
        sort_key = f"{file_path}#{level}"
        ttl = int((datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)).timestamp())
        
        cache_table.put_item(Item=_convert_floats({
            'repo_id': repo_id,
            'sort_key': sort_key,
            'file_path': file_path,
            'level': level,
            'data': data,
            'ttl': ttl,
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }))
        
        print(f"Cached explanation for repo={repo_id} key={sort_key}")
    except Exception as e:
        print(f"Cache storage error: {str(e)}")


def _reconstruct_file_content(chunks: List[Dict[str, Any]]) -> str:
    """Reconstruct file content from chunks."""
    # Sort chunks by start_line if available
    sorted_chunks = sorted(chunks, key=lambda c: c.get('metadata', {}).get('start_line', 0))
    
    # Combine content
    content_parts = [chunk['content'] for chunk in sorted_chunks]
    return '\n'.join(content_parts)


def _extract_file_metadata(content: str, file_path: str) -> Dict[str, Any]:
    """Extract metadata from file content."""
    lines = content.split('\n')
    
    # Count lines
    total_lines = len(lines)
    code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('//'))
    
    # Detect language
    extension = file_path.split('.')[-1] if '.' in file_path else ''
    language_map = {
        'py': 'Python',
        'js': 'JavaScript',
        'ts': 'TypeScript',
        'jsx': 'JavaScript',
        'tsx': 'TypeScript',
        'java': 'Java',
        'go': 'Go',
        'rb': 'Ruby',
        'php': 'PHP',
        'cpp': 'C++',
        'c': 'C',
        'cs': 'C#',
        'rs': 'Rust'
    }
    language = language_map.get(extension, 'Unknown')
    
    # Extract functions/methods
    functions = _extract_functions(content, language)
    
    # Extract imports/dependencies
    dependencies = _extract_dependencies(content, language)
    
    return {
        'lines': total_lines,
        'code_lines': code_lines,
        'functions': len(functions),
        'function_list': functions,
        'language': language,
        'dependencies': dependencies
    }


def _extract_functions(content: str, language: str) -> List[Dict[str, Any]]:
    """Extract function definitions from code."""
    functions = []
    lines = content.split('\n')
    
    patterns = {
        'Python': r'^\s*def\s+(\w+)\s*\(',
        'JavaScript': r'^\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
        'TypeScript': r'^\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
        'Java': r'^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(',
        'Go': r'^\s*func\s+(\w+)\s*\(',
    }
    
    pattern = patterns.get(language)
    if not pattern:
        return functions
    
    for i, line in enumerate(lines, 1):
        match = re.search(pattern, line)
        if match:
            func_name = match.group(1) or match.group(2) if match.lastindex >= 2 else match.group(1)
            if func_name:
                functions.append({
                    'name': func_name,
                    'line': i,
                    'description': ''  # Will be filled by AI
                })
    
    return functions[:10]  # Limit to first 10


def _extract_dependencies(content: str, language: str) -> List[str]:
    """Extract import statements and dependencies."""
    dependencies = []
    lines = content.split('\n')
    
    patterns = {
        'Python': [r'^\s*import\s+([\w.]+)', r'^\s*from\s+([\w.]+)\s+import'],
        'JavaScript': [r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', r'^\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'],
        'TypeScript': [r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', r'^\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'],
        'Java': [r'^\s*import\s+([\w.]+);'],
        'Go': [r'^\s*import\s+"([^"]+)"'],
    }
    
    pattern_list = patterns.get(language, [])
    
    for line in lines:
        for pattern in pattern_list:
            match = re.search(pattern, line)
            if match:
                dep = match.group(1)
                if dep and dep not in dependencies:
                    dependencies.append(dep)
    
    return dependencies[:20]  # Limit to first 20


def _generate_explanation(
    file_path: str,
    content: str,
    metadata: Dict[str, Any],
    static_analysis: Dict[str, Any],
    complexity_result: Dict[str, Any],
    related_context: List[Dict[str, str]],
    level: str
) -> Dict[str, Any]:
    """Generate explanation using Bedrock with strict JSON schema."""
    level_guidance = {
        'beginner': 'Use simple terminology. Avoid jargon. Explain like teaching a CS freshman.',
        'intermediate': 'Include implementation details, design patterns, and system context.',
        'advanced': 'Focus on trade-offs, performance, edge cases, and architectural critique.'
    }
    guidance = level_guidance.get(level, level_guidance['intermediate'])

    # Build context sections
    func_list = '\n'.join([f"  - {f['name']}() at line {f['line']}" for f in metadata['function_list'][:8]])
    dep_list = ', '.join(metadata['dependencies'][:15])
    sa_imports = ', '.join(static_analysis.get('imports', [])[:15])
    sa_funcs = ', '.join(static_analysis.get('function_names', [])[:10])
    sa_classes = ', '.join(static_analysis.get('class_names', [])[:5])
    sa_async = ', '.join(static_analysis.get('async_usage', []))
    sa_db = ', '.join(static_analysis.get('db_keywords', [])[:10])
    sa_api = ', '.join(static_analysis.get('api_patterns', [])[:10])
    cx = complexity_result.get('metrics', {})
    cx_score = complexity_result.get('score', 1)

    related_ctx_str = ''
    if related_context:
        parts = []
        for rc in related_context:
            parts.append(f"  [{rc['file_path']}]: {rc['snippet'][:200]}")
        related_ctx_str = '\n'.join(parts)
    else:
        related_ctx_str = '  (none available)'

    prompt = f"""You are a senior software engineer analyzing a codebase.
Analyze the following {metadata['language']} file at a {level} level.

{guidance}

=== FILE INFO ===
Path: {file_path}
Language: {metadata['language']}
Total lines: {metadata['lines']}  |  Code lines: {metadata['code_lines']}

=== STATIC ANALYSIS ===
Imports: {sa_imports or 'none'}
Functions: {sa_funcs or 'none'}
Classes: {sa_classes or 'none'}
Async usage: {sa_async or 'none'}
DB keywords: {sa_db or 'none'}
API patterns: {sa_api or 'none'}

=== COMPLEXITY METRICS (deterministic) ===
Score: {cx_score}/10
Function count: {cx.get('function_count', 0)}
Class count: {cx.get('class_count', 0)}
Async count: {cx.get('async_count', 0)}
Deep nesting lines: {cx.get('nesting_estimate', 0)}
Try/catch blocks: {cx.get('try_catch_count', 0)}

=== RELATED REPOSITORY CONTEXT (top 3 files) ===
{related_ctx_str}

=== SOURCE CODE ===
```
{content[:4000]}
```

Respond with ONLY a valid JSON object matching this EXACT schema (no markdown, no commentary):

{{
  "purpose": "One-sentence purpose of this file",
  "businessContext": "How this file fits into the overall system/product",
  "executionFlow": [
    "Step 1 description",
    "Step 2 description"
  ],
  "keyFunctions": [
    {{"name": "func_name", "description": "what it does", "line": 0}}
  ],
  "designPatterns": ["Pattern1"],
  "dependencies": ["dep1"],
  "complexity": {{
    "score": {cx_score},
    "reasoning": "Brief explanation of complexity score"
  }},
  "improvementSuggestions": ["suggestion1"],
  "securityRisks": ["risk1 or none"],
  "impactAssessment": "What would break if this file were modified",
  "confidence": 0.9
}}"""

    response = bedrock_client.invoke_claude(
        prompt=prompt,
        max_tokens=3000,
        temperature=0.2
    )

    return _parse_and_validate_json(response, metadata, complexity_result)


def _parse_and_validate_json(
    response: str,
    metadata: Dict[str, Any],
    complexity_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse LLM response as JSON, validate required fields, handle malformation."""
    # Strip markdown fences if present
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
        explanation = json.loads(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse explanation JSON: {str(e)}")
        print(f"Raw response (first 500 chars): {response[:500]}")
        # Attempt to extract JSON object from noisy output
        brace_start = json_str.find('{')
        brace_end = json_str.rfind('}')
        if brace_start != -1 and brace_end > brace_start:
            try:
                explanation = json.loads(json_str[brace_start:brace_end + 1])
            except (json.JSONDecodeError, ValueError):
                raise
        else:
            raise

    # Schema enforcement — fill missing fields with safe defaults
    cx = complexity_result.get('metrics', {})
    defaults = {
        'purpose': 'Purpose could not be determined',
        'businessContext': '',
        'executionFlow': [],
        'keyFunctions': [],
        'designPatterns': [],
        'dependencies': metadata.get('dependencies', []),
        'complexity': {
            'score': complexity_result.get('score', 1),
            'reasoning': 'Auto-computed from deterministic metrics'
        },
        'improvementSuggestions': [],
        'securityRisks': [],
        'impactAssessment': '',
        'confidence': 0.5
    }
    for key, default_val in defaults.items():
        if key not in explanation:
            explanation[key] = default_val

    # Clamp confidence to 0-1
    try:
        explanation['confidence'] = max(0.0, min(1.0, float(explanation['confidence'])))
    except (TypeError, ValueError):
        explanation['confidence'] = 0.5

    return explanation


def _generate_fallback_explanation(
    file_path: str,
    content: str,
    metadata: Dict[str, Any],
    static_analysis: Dict[str, Any],
    complexity_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate deterministic fallback explanation when LLM fails."""
    cx = complexity_result.get('metrics', {})
    return {
        'purpose': f"This {metadata['language']} file contains {metadata['functions']} functions across {metadata['lines']} lines.",
        'businessContext': '',
        'executionFlow': [],
        'keyFunctions': metadata['function_list'][:5],
        'designPatterns': [],
        'dependencies': metadata.get('dependencies', []),
        'complexity': {
            'score': complexity_result.get('score', 1),
            'reasoning': f"Deterministic: {cx.get('function_count', 0)} functions, "
                         f"{cx.get('nesting_estimate', 0)} deeply-nested lines, "
                         f"{cx.get('try_catch_count', 0)} try/catch blocks"
        },
        'improvementSuggestions': [],
        'securityRisks': [],
        'impactAssessment': '',
        'confidence': 0.0
    }


def _compute_deterministic_confidence(
    similarity_scores: List[float],
    chunk_count: int,
    file_size: int
) -> float:
    """
    Compute deterministic confidence that overrides LLM confidence.

    Rules:
        High  (0.9) — avg similarity > 0.8 AND chunks >= 2
        Medium(0.7) — avg similarity > 0.6
        Low   (0.4) — everything else

    A small bonus is added for larger files (more context available).
    """
    if not similarity_scores:
        return 0.3  # No related context at all

    avg_sim = sum(similarity_scores) / len(similarity_scores)

    if avg_sim > 0.8 and chunk_count >= 2:
        base = 0.9
    elif avg_sim > 0.6:
        base = 0.7
    else:
        base = 0.4

    # Small file-size bonus (caps at +0.05 for files > 2 KB)
    size_bonus = min(0.05, file_size / 40000)

    return round(min(1.0, base + size_bonus), 2)


def _identify_related_files(file_path: str, content: str, repo_id: str) -> List[str]:
    """Identify related files based on imports and directory."""
    related = []
    
    # Extract imported modules
    dependencies = _extract_dependencies(content, 'Python')  # Simplified
    
    # Get files in same directory
    directory = '/'.join(file_path.split('/')[:-1])
    
    # Query vector store for related files (simplified - would need better implementation)
    try:
        # Get a sample of chunks to find related files
        dummy_embedding = [0.0] * 1024
        chunks = vector_store.search(repo_id, dummy_embedding, top_k=50)
        
        seen_files = set()
        for chunk in chunks:
            chunk_file = chunk['file_path']
            if chunk_file != file_path and chunk_file not in seen_files:
                # Check if in same directory
                chunk_dir = '/'.join(chunk_file.split('/')[:-1])
                if chunk_dir == directory:
                    related.append(chunk_file)
                    seen_files.add(chunk_file)
                    if len(related) >= 5:
                        break
    except Exception as e:
        print(f"Error finding related files: {str(e)}")
    
    return related[:5]


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message,
            'status_code': status_code
        })
    }
