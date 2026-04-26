"""
Async Repository Ingestion Handler.

Receives repository upload requests, creates job records, and enqueues processing.
Returns immediately with job_id for status polling.

Implements Requirements 1.1, 1.2, 1.3, 5.1-5.5, 11.1-11.5 from async-repository-ingestion spec.
"""
import json
import os
import uuid
import re
import base64
from datetime import datetime, timedelta
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from idempotency_manager import IdempotencyManager


# Initialize shared resources
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
jobs_table = dynamodb.Table(os.environ.get('INGESTION_JOBS_TABLE', 'BloomWay-IngestionJobs'))
processing_queue_url = os.environ.get('PROCESSING_QUEUE_URL')

# Constants
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle async repository ingestion request.
    
    Creates job record, enqueues processing, and returns immediately.
    
    Request:
        POST /repos/ingest
        Content-Type: multipart/form-data or application/json
        
        JSON body:
        {
            "source_type": "github",
            "source": "https://github.com/user/repo",
            "auth_token": "optional"
        }
        
        OR multipart with file upload
    
    Response:
        {
            "job_id": "uuid",
            "status": "processing",
            "message": "Repository ingestion started",
            "poll_url": "/ingestion/status/{job_id}"
        }
    
    Validates: Requirements 1.1, 1.2, 1.3, 5.1-5.4, 11.1
    Property 1: Job Enqueue Before Response
    Property 2: Initial Job Record Creation
    """
    try:
        headers = event.get('headers', {})
        content_type = (headers.get('content-type') or headers.get('Content-Type') or '').lower()
        
        idempotency_mgr = IdempotencyManager()
        
        # Parse request based on content type
        if 'multipart/form-data' in content_type:
            result = _handle_multipart_upload(event, idempotency_mgr)
        elif 'application/json' in content_type or not content_type:
            result = _handle_json_request(event, idempotency_mgr)
        else:
            return _error_response(400, f"Unsupported Content-Type: {content_type}")
        
        return result
        
    except Exception as e:
        print(f"Unexpected error in ingestion handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


def _handle_multipart_upload(event: Dict[str, Any], idempotency_mgr: IdempotencyManager) -> Dict[str, Any]:
    """Handle multipart/form-data ZIP upload."""
    body = event.get('body', '')
    is_base64 = event.get('isBase64Encoded', False)
    
    # Decode body if base64 encoded
    if is_base64:
        try:
            body_bytes = base64.b64decode(body)
        except Exception as e:
            return _error_response(400, f"Failed to decode base64 body: {str(e)}")
    else:
        if isinstance(body, str):
            body_bytes = body.encode('latin-1')
        else:
            body_bytes = body
    
    # Extract boundary
    content_type = event.get('headers', {}).get('content-type', '')
    boundary_match = re.search(r'boundary=([^;]+)', content_type)
    if not boundary_match:
        return _error_response(400, "Missing boundary in multipart/form-data")
    
    # Parse multipart data
    if b'--' in body_bytes[:100]:
        first_line = body_bytes.split(b'\r\n')[0]
        if first_line.startswith(b'--'):
            boundary_bytes = first_line[2:]
        else:
            boundary_bytes = boundary_match.group(1).strip().encode()
    else:
        boundary_bytes = boundary_match.group(1).strip().encode()
    
    parts = body_bytes.split(b'--' + boundary_bytes)
    
    source_type = 'zip'
    file_data = None
    
    for part in parts:
        if b'name="source_type"' in part:
            try:
                source_type = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0].decode().strip()
            except Exception:
                pass
        elif b'name="file"' in part and b'filename=' in part:
            try:
                file_data = part.split(b'\r\n\r\n', 1)[1].rsplit(b'\r\n', 1)[0]
            except Exception:
                pass
    
    if not file_data:
        return _error_response(400, "No file uploaded")
    
    # Generate idempotency key from file content
    idempotency_key = idempotency_mgr.generate_key(file_data, source="zip_upload")
    
    # Check for existing job
    existing_job = idempotency_mgr.check_existing_job(idempotency_key)
    if existing_job and not idempotency_mgr.should_create_new_job(existing_job):
        # Return existing job
        response = idempotency_mgr.get_existing_job_response(existing_job)
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response)
        }
    
    # Create new job
    job_id = str(uuid.uuid4())
    repo_id = str(uuid.uuid4())  # Generate repo_id for the repository
    timestamp = datetime.utcnow().isoformat() + 'Z'
    ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())
    
    # Store initial job record
    try:
        jobs_table.put_item(Item={
            'job_id': job_id,
            'repo_id': repo_id,
            'idempotency_key': idempotency_key,
            'status': 'processing',
            'source_type': source_type,
            'source': 'uploaded_zip',
            'progress_current': 0,
            'progress_total': 0,
            'created_at': timestamp,
            'updated_at': timestamp,
            'ttl': ttl
        })
        print(f"Created job record: {job_id}, repo_id: {repo_id}")
    except Exception as e:
        print(f"Error creating job record: {str(e)}")
        return _error_response(500, "Failed to create job record")
    
    # Enqueue processing message
    try:
        # Store file data in message (for small files) or S3 (for large files)
        # For now, we'll use base64 encoding in the message
        # TODO: For files > 256KB, upload to S3 first
        file_data_b64 = base64.b64encode(file_data).decode('utf-8')
        
        message_body = json.dumps({
            'job_id': job_id,
            'repo_id': repo_id,
            'source_type': source_type,
            'source': 'uploaded_zip',
            'file_data': file_data_b64,
            'idempotency_key': idempotency_key
        })
        
        sqs.send_message(
            QueueUrl=processing_queue_url,
            MessageBody=message_body,
            MessageAttributes={
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'source_type': {'StringValue': source_type, 'DataType': 'String'}
            }
        )
        print(f"Enqueued job: {job_id}")
    except Exception as e:
        print(f"Error enqueuing job: {str(e)}")
        # Mark job as failed
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, error_message = :error',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': f"Failed to enqueue processing: {str(e)}"
                }
            )
        except:
            pass
        return _error_response(500, "Failed to enqueue processing")
    
    # Return success response
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'job_id': job_id,
            'status': 'processing',
            'message': 'Repository ingestion started',
            'poll_url': f'/ingestion/status/{job_id}'
        })
    }


def _handle_json_request(event: Dict[str, Any], idempotency_mgr: IdempotencyManager) -> Dict[str, Any]:
    """Handle JSON request (GitHub URL)."""
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return _error_response(400, "Invalid JSON in request body")
    
    source_type = body.get('source_type', 'github')
    source = body.get('source')
    auth_token = body.get('auth_token')
    
    if not source:
        return _error_response(400, "Missing required field: 'source'")
    
    if source_type not in ['github', 'zip']:
        return _error_response(400, f"Invalid source_type: {source_type}")
    
    # Generate idempotency key from source URL
    idempotency_key = idempotency_mgr.generate_key(source.encode('utf-8'), source=source_type)
    
    # Check for existing job
    existing_job = idempotency_mgr.check_existing_job(idempotency_key)
    if existing_job and not idempotency_mgr.should_create_new_job(existing_job):
        # Return existing job
        response = idempotency_mgr.get_existing_job_response(existing_job)
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response)
        }
    
    # Create new job
    job_id = str(uuid.uuid4())
    repo_id = str(uuid.uuid4())  # Generate repo_id for the repository
    timestamp = datetime.utcnow().isoformat() + 'Z'
    ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())
    
    # Store initial job record
    try:
        jobs_table.put_item(Item={
            'job_id': job_id,
            'repo_id': repo_id,
            'idempotency_key': idempotency_key,
            'status': 'processing',
            'source_type': source_type,
            'source': source,
            'progress_current': 0,
            'progress_total': 0,
            'created_at': timestamp,
            'updated_at': timestamp,
            'ttl': ttl
        })
        print(f"Created job record: {job_id}, repo_id: {repo_id}")
    except Exception as e:
        print(f"Error creating job record: {str(e)}")
        return _error_response(500, "Failed to create job record")
    
    # Enqueue processing message
    try:
        message_body = json.dumps({
            'job_id': job_id,
            'repo_id': repo_id,
            'source_type': source_type,
            'source': source,
            'auth_token': auth_token,
            'idempotency_key': idempotency_key
        })
        
        sqs.send_message(
            QueueUrl=processing_queue_url,
            MessageBody=message_body,
            MessageAttributes={
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'source_type': {'StringValue': source_type, 'DataType': 'String'}
            }
        )
        print(f"Enqueued job: {job_id}")
    except Exception as e:
        print(f"Error enqueuing job: {str(e)}")
        # Mark job as failed
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, error_message = :error',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': f"Failed to enqueue processing: {str(e)}"
                }
            )
        except:
            pass
        return _error_response(500, "Failed to enqueue processing")
    
    # Return success response
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'job_id': job_id,
            'status': 'processing',
            'message': 'Repository ingestion started',
            'poll_url': f'/ingestion/status/{job_id}'
        })
    }


def get_status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get ingestion job status.
    
    Request:
        GET /ingestion/status/{job_id}
    
    Response:
        {
            "job_id": "uuid",
            "status": "processing" | "completed" | "failed",
            "progress_current": 45,
            "progress_total": 100,
            "error_message": "optional error details",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z"
        }
    
    Validates: Requirements 11.1-11.5
    Property 22: Status Endpoint Response Accuracy
    Property 23: Status Endpoint 404 Handling
    """
    try:
        # Extract job_id from path parameters
        job_id = event.get('pathParameters', {}).get('job_id')
        
        if not job_id:
            return _error_response(400, "Job ID is required")
        
        # Query DynamoDB for job status
        try:
            response = jobs_table.get_item(Key={'job_id': job_id})
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'error': 'Job not found',
                        'job_id': job_id
                    })
                }
            
            item = response['Item']
            
            # Build response
            status_response = {
                'job_id': item['job_id'],
                'status': item.get('status', 'unknown'),
                'progress_current': item.get('progress_current', 0),
                'progress_total': item.get('progress_total', 0),
                'created_at': item.get('created_at', ''),
                'updated_at': item.get('updated_at', '')
            }
            
            # Calculate percentage
            if item.get('progress_total', 0) > 0:
                status_response['progress_percentage'] = int(
                    (item.get('progress_current', 0) / item['progress_total']) * 100
                )
            
            # Add optional fields
            if 'progress_message' in item:
                status_response['message'] = item['progress_message']
            
            if 'error_message' in item:
                status_response['error_message'] = item['error_message']
            
            if 'error_code' in item:
                status_response['error_code'] = item['error_code']
            
            if 'repo_id' in item:
                status_response['repo_id'] = item['repo_id']
            
            if 'completed_at' in item:
                status_response['completed_at'] = item['completed_at']
            
            if 'failed_at' in item:
                status_response['failed_at'] = item['failed_at']
            
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps(status_response, cls=_DecimalEncoder)
            }
            
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve job status")
    
    except Exception as e:
        print(f"Unexpected error in get_status_handler: {str(e)}")
        return _error_response(500, f"Internal server error: {str(e)}")


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create error response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message})
    }


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder for DynamoDB Decimal types."""
    def default(self, obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(_DecimalEncoder, self).default(obj)
