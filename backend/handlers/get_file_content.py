"""
Lambda handler for retrieving file content from vector store.
"""
import json
import os
from typing import Dict, Any
from urllib.parse import unquote
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from vector_store import DynamoDBVectorStore

# Initialize shared resources
vector_store = DynamoDBVectorStore()
dynamodb = boto3.resource('dynamodb')
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /repos/{id}/file?path=<file_path>
    
    Retrieves file content from vector store chunks.
    
    Query parameters:
        path: File path (URL encoded)
    
    Returns:
        {
            "repo_id": "uuid",
            "file_path": "src/core/api.js",
            "content": "file content...",
            "language": "javascript",
            "lines": 150
        }
    """
    try:
        # Extract parameters
        repo_id = event.get('pathParameters', {}).get('id')
        query_params = event.get('queryStringParameters') or {}
        encoded_path = query_params.get('path', '')
        file_path = unquote(encoded_path) if encoded_path else None
        
        if not repo_id:
            return _error_response(400, "Repository ID is required")
        
        if not file_path:
            return _error_response(400, "File path is required")
        
        print(f"Fetching file content: {file_path} for repo_id: {repo_id}")
        
        # Verify repository exists
        try:
            response = repos_table.get_item(Key={'repo_id': repo_id})
            if 'Item' not in response:
                return _error_response(404, f"Repository {repo_id} not found")
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve repository metadata")
        
        # Retrieve file chunks from vector store
        print(f"Retrieving chunks for file: {file_path}")
        file_chunks = vector_store.get_file_chunks(repo_id, file_path)
        
        if not file_chunks:
            return _error_response(404, f"File {file_path} not found in repository")
        
        # Reconstruct file content from chunks
        content = _reconstruct_file_content(file_chunks)
        
        # Detect language from file extension
        extension = file_path.split('.')[-1] if '.' in file_path else ''
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'java': 'java',
            'go': 'go',
            'rb': 'ruby',
            'php': 'php',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'rs': 'rust',
            'html': 'html',
            'css': 'css',
            'scss': 'scss',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'shell',
            'bash': 'shell',
            'sql': 'sql'
        }
        language = language_map.get(extension.lower(), 'plaintext')
        
        # Count lines
        lines = len(content.split('\n'))
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'repo_id': repo_id,
                'file_path': file_path,
                'content': content,
                'language': language,
                'lines': lines
            })
        }
        
    except Exception as e:
        print(f"Unexpected error in get_file_content handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


def _reconstruct_file_content(chunks: list) -> str:
    """Reconstruct file content from chunks."""
    # Sort chunks by start_line if available
    sorted_chunks = sorted(chunks, key=lambda c: c.get('metadata', {}).get('start_line', 0))
    
    # Combine content
    content_parts = [chunk['content'] for chunk in sorted_chunks]
    return '\n'.join(content_parts)


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
