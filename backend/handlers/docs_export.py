"""
Lambda handler for documentation export.
GET /repos/{id}/docs/export?format=md|pdf

Exports generated documentation in requested format.
"""

import json
import os
import sys
import logging
import base64
from typing import Dict, Any

# Lambda-compatible imports
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from lib.documentation.store import DocumentationStore
from lib.documentation.exporter import ExportService, NotFoundError, ConversionError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy initialization - create these only when needed
_doc_store = None
_export_service = None

def get_doc_store():
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentationStore()
    return _doc_store

def get_export_service():
    global _export_service
    if _export_service is None:
        _export_service = ExportService(get_doc_store())
    return _export_service

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'
}


def _error_response(status_code: int, error_code: str, message: str, details: str = None) -> Dict[str, Any]:
    """Create error response."""
    error_body = {
        'error': {
            'code': error_code,
            'message': message
        }
    }
    if details:
        error_body['error']['details'] = details
    
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(error_body)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle documentation export request.
    
    Path parameters:
        id: Repository ID
    
    Query parameters:
        format: Export format (md or pdf), default: md
    
    Returns:
        200 OK with file download:
        Headers:
            Content-Type: text/markdown or application/pdf
            Content-Disposition: attachment; filename="repo-docs.{ext}"
        Body: Base64-encoded file content
        
        400 Bad Request (invalid format):
        {
            "error": {
                "code": "INVALID_FORMAT",
                "message": "Invalid format. Use md or pdf."
            }
        }
        
        404 Not Found (documentation doesn't exist):
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Documentation not found",
                "details": "Please generate documentation first."
            }
        }
        
        500 Internal Server Error:
        {
            "error": {
                "code": "EXPORT_FAILED",
                "message": "Export failed",
                "details": "..."
            }
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
        # Extract parameters
        repo_id = event.get('pathParameters', {}).get('id')
        query_params = event.get('queryStringParameters') or {}
        format_param = query_params.get('format', 'md').lower()
        
        if not repo_id:
            return _error_response(
                400,
                'INVALID_REQUEST',
                'Repository ID is required'
            )
        
        # Validate format
        if format_param not in ['md', 'pdf']:
            return _error_response(
                400,
                'INVALID_FORMAT',
                'Invalid format. Use md or pdf.'
            )
        
        logger.info(f"Export requested for {repo_id} in format {format_param}")
        
        # Export documentation
        import asyncio
        
        export_service = get_export_service()
        
        try:
            if format_param == 'md':
                content_bytes = asyncio.run(export_service.export_markdown(repo_id))
                content_type = 'text/markdown; charset=utf-8'
                filename = f'{repo_id}-docs.md'
                
                # Return Markdown as plain text (not base64-encoded)
                return {
                    'statusCode': 200,
                    'headers': {
                        **CORS_HEADERS,
                        'Content-Type': content_type,
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    },
                    'body': content_bytes.decode('utf-8'),
                    'isBase64Encoded': False
                }
            else:  # pdf
                content_bytes = asyncio.run(export_service.export_pdf(repo_id))
                content_type = 'application/pdf'
                filename = f'{repo_id}-docs.pdf'
                
                # Return PDF as base64-encoded binary
                return {
                    'statusCode': 200,
                    'headers': {
                        **CORS_HEADERS,
                        'Content-Type': content_type,
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    },
                    'body': base64.b64encode(content_bytes).decode('utf-8'),
                    'isBase64Encoded': True
                }
            
        except NotFoundError as e:
            return _error_response(
                404,
                'NOT_FOUND',
                'Documentation not found',
                'Please generate documentation first.'
            )
            
        except ConversionError as e:
            logger.error(f"Conversion error: {e}")
            
            # Suggest markdown export as fallback for PDF failures
            if format_param == 'pdf':
                return _error_response(
                    500,
                    'CONVERSION_FAILED',
                    'PDF conversion failed',
                    'Please try exporting as Markdown instead.'
                )
            else:
                return _error_response(
                    500,
                    'EXPORT_FAILED',
                    'Export failed',
                    str(e)
                )
        
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        
        return _error_response(
            500,
            'EXPORT_FAILED',
            'Export failed',
            str(e)
        )
