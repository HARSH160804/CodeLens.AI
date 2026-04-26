"""
Lambda handler for documentation status.
GET /repos/{id}/docs/status

Returns the current generation state and metadata for documentation.
"""

import json
import os
import sys
import logging
from typing import Dict, Any

# Lambda-compatible imports
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from lib.documentation.store import DocumentationStore

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy initialization - create these only when needed
_doc_store = None

def get_doc_store():
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentationStore()
    return _doc_store

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'
}


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create error response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message})
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle documentation status request.
    
    Path parameters:
        id: Repository ID
    
    Returns:
        200 OK:
        {
            "state": "not_generated|generating|generated|failed",
            "created_at": "2024-01-15T10:30:00Z" or null,
            "error_message": "..." or null
        }
        
        500 Internal Server Error:
        {
            "error": "Failed to retrieve status"
        }
    """
    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    try:
        # Extract repo_id
        repo_id = event.get('pathParameters', {}).get('id')
        
        if not repo_id:
            return _error_response(400, 'Repository ID is required')
        
        logger.info(f"Status check for {repo_id}")
        
        # Get documentation record
        import asyncio
        doc_store = get_doc_store()
        doc_record = asyncio.run(doc_store.get(repo_id))
        
        if doc_record is None:
            # No documentation exists
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'state': 'not_generated',
                    'created_at': None,
                    'error_message': None
                })
            }
        
        # Return status with metadata
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'state': doc_record.get('generation_state', 'not_generated'),
                'created_at': doc_record.get('created_at'),
                'error_message': doc_record.get('error_message')
            })
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return _error_response(500, 'Failed to retrieve status')
