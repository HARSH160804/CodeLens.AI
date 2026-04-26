"""
Lambda handler for retrieving stored repository metadata.
Returns precomputed metrics from DynamoDB — no dynamic computation.
"""
import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal


# Initialize shared resources
dynamodb = boto3.resource('dynamodb')
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}


class _DecimalEncoder(json.JSONEncoder):
    """Convert DynamoDB Decimal types to int/float."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj == int(obj) else float(obj)
        return super().default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /repo/{repoId}/metadata

    Returns precomputed repo-level metadata stored during ingestion.

    Response:
        {
            "repoName": "owner/repo",
            "totalFiles": 42,
            "totalLines": 8500,
            "languageBreakdown": {".py": 15, ".js": 10},
            "primaryLanguage": ".py",
            "techStack": {...},
            "architectureType": "Serverless",
            "indexedAt": "2026-03-03T12:00:00Z"
        }
    """
    try:
        repo_id = (event.get('pathParameters') or {}).get('id')

        if not repo_id:
            return _error_response(400, "Repository ID is required")

        # Read stored metadata item — no dynamic computation
        try:
            response = repos_table.get_item(Key={'repo_id': repo_id})
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve repository metadata")

        if 'Item' not in response:
            return _error_response(404, f"Repository {repo_id} not found")

        item = response['Item']

        # Extract the source to derive a human-readable repo name
        source = item.get('source', '')
        if 'github.com' in source:
            # e.g. https://github.com/owner/repo -> owner/repo
            parts = source.rstrip('/').split('github.com/')
            repo_name = parts[-1] if len(parts) > 1 else source
        elif source == 'uploaded_zip':
            repo_name = 'Uploaded ZIP'
        else:
            repo_name = source or repo_id

        result = {
            'repoName': repo_name,
            'totalFiles': item.get('file_count', 0),
            'totalLines': item.get('total_lines_of_code', 0),
            'languageBreakdown': item.get('language_breakdown', {}),
            'primaryLanguage': item.get('primary_language', ''),
            'techStack': item.get('tech_stack', {}),
            'architectureType': item.get('architecture_summary', '')[:200] if isinstance(item.get('architecture_summary'), str) else '',
            'indexedAt': item.get('indexed_at', item.get('created_at', ''))
        }

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result, cls=_DecimalEncoder)
        }

    except Exception as e:
        print(f"Unexpected error in get_repo_metadata: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


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
