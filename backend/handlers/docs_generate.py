"""
Lambda handler for documentation generation.
POST /repos/{id}/docs/generate

Triggers documentation generation from architecture analysis data.
"""

import json
import os
import sys
import logging
from typing import Dict, Any
import boto3

# Lambda-compatible imports
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from lib.bedrock_client import BedrockClient
from lib.documentation.store import DocumentationStore
from lib.documentation.generator import DocumentationGenerator, GenerationError, ValidationError
from lib.analysis.engine import AnalysisEngine
from lib.analysis.cache_manager import CacheManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}

# Lazy initialization - create these only when needed
_bedrock_client = None
_doc_store = None
_doc_generator = None
_analysis_engine = None
_cache_manager = None

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client

def get_doc_store():
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentationStore()
    return _doc_store

def get_doc_generator():
    global _doc_generator
    if _doc_generator is None:
        _doc_generator = DocumentationGenerator(get_bedrock_client())
    return _doc_generator

def get_analysis_engine():
    global _analysis_engine
    if _analysis_engine is None:
        _analysis_engine = AnalysisEngine(get_bedrock_client())
    return _analysis_engine

def get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


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


async def _get_architecture_analysis(repo_id: str) -> Dict[str, Any]:
    """
    Retrieve architecture analysis data for a repository.
    
    Args:
        repo_id: Repository identifier
        
    Returns:
        Architecture analysis data dictionary
        
    Raises:
        Exception: If analysis data cannot be retrieved
    """
    try:
        # Get instances
        cache_manager = get_cache_manager()
        analysis_engine = get_analysis_engine()
        
        # Check cache first (using 'intermediate' as the level)
        cached_analysis = cache_manager.get_cached_analysis(repo_id, 'intermediate')
        if cached_analysis:
            logger.info(f"Using cached analysis for {repo_id}")
            return cached_analysis
        
        # Get repository metadata
        dynamodb = boto3.resource('dynamodb')
        repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))
        embeddings_table = dynamodb.Table(os.environ.get('EMBEDDINGS_TABLE', 'BloomWay-Embeddings'))
        
        response = repos_table.get_item(Key={'repo_id': repo_id})
        if 'Item' not in response:
            raise Exception("Repository not found")
        
        repo_metadata = response['Item']
        
        # Get file summaries from embeddings table
        embeddings_response = embeddings_table.query(
            KeyConditionExpression='repo_id = :repo_id',
            ExpressionAttributeValues={':repo_id': repo_id}
        )
        
        file_summaries = []
        for item in embeddings_response.get('Items', []):
            file_summaries.append({
                'file_path': item.get('file_path', ''),
                'content': item.get('content', ''),
                'language': item.get('language', ''),
                'summary': item.get('summary', '')
            })
        
        if not file_summaries:
            raise Exception("No file data found for repository")
        
        # Run analysis
        logger.info(f"Running architecture analysis for {repo_id}")
        analysis_result = analysis_engine.analyze(
            repo_id=repo_id,
            repo_metadata=repo_metadata,
            file_summaries=file_summaries,
            level='intermediate'
        )
        
        # Cache the result
        cache_manager.cache_analysis(repo_id, 'intermediate', analysis_result)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Failed to get architecture analysis: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle documentation generation request.
    
    Path parameters:
        id: Repository ID
    
    Returns:
        202 Accepted:
        {
            "status": "generating",
            "message": "Documentation generation started"
        }
        
        409 Conflict (if already generating):
        {
            "error": {
                "code": "GENERATION_IN_PROGRESS",
                "message": "Documentation generation already in progress"
            }
        }
        
        500 Internal Server Error:
        {
            "error": {
                "code": "GENERATION_FAILED",
                "message": "Documentation generation failed",
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
        logger.info(f"Received event: {json.dumps(event)}")
        # Extract repo_id
        repo_id = event.get('pathParameters', {}).get('id')
        
        if not repo_id:
            return _error_response(
                400,
                'INVALID_REQUEST',
                'Repository ID is required'
            )
        
        logger.info(f"Documentation generation requested for {repo_id}")
        
        # Check current state
        import asyncio
        doc_store = get_doc_store()
        current_state = asyncio.run(doc_store.get_state(repo_id))
        
        if current_state == 'generating':
            return _error_response(
                409,
                'GENERATION_IN_PROGRESS',
                'Documentation generation already in progress'
            )
        
        # Update state to generating
        asyncio.run(doc_store.update_state(repo_id, 'generating'))
        
        try:
            # Get architecture analysis data
            analysis_data = asyncio.run(_get_architecture_analysis(repo_id))
            
            if not analysis_data:
                raise Exception("Architecture analysis data not available")
            
            # Generate documentation
            logger.info(f"Generating documentation for {repo_id}")
            doc_generator = get_doc_generator()
            markdown = asyncio.run(doc_generator.generate(analysis_data))
            
            logger.info(f"Documentation generated, length: {len(markdown)} chars")
            
            # Store documentation
            logger.info(f"Saving documentation to store...")
            asyncio.run(doc_store.save(repo_id, markdown))
            logger.info(f"Documentation saved successfully")
            
            # Update state to generated - THIS IS CRITICAL
            logger.info(f"Updating state to 'generated'...")
            asyncio.run(doc_store.update_state(repo_id, 'generated'))
            logger.info(f"State updated to 'generated' successfully")
            
            logger.info(f"Documentation generation completed for {repo_id}")
            
            return {
                'statusCode': 202,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'status': 'generated',
                    'message': 'Documentation generation completed successfully'
                })
            }
            
        except ValidationError as e:
            # Update state to failed
            asyncio.run(doc_store.update_state(repo_id, 'failed', str(e)))
            
            return _error_response(
                400,
                'MISSING_ANALYSIS',
                'Architecture analysis data is incomplete',
                'Please run architecture analysis first'
            )
            
        except GenerationError as e:
            # Update state to failed
            asyncio.run(doc_store.update_state(repo_id, 'failed', str(e)))
            
            return _error_response(
                500,
                'GENERATION_FAILED',
                'Documentation generation failed',
                'The AI service encountered an error. Please try again.'
            )
            
        except Exception as e:
            # Update state to failed
            asyncio.run(doc_store.update_state(repo_id, 'failed', str(e)))
            
            logger.error(f"Documentation generation failed: {e}", exc_info=True)
            
            return _error_response(
                500,
                'GENERATION_FAILED',
                'Documentation generation failed',
                str(e)
            )
    
    except Exception as e:
        logger.error(f"Request handling failed: {e}", exc_info=True)
        
        return _error_response(
            500,
            'INTERNAL_ERROR',
            'An unexpected error occurred',
            str(e)
        )
