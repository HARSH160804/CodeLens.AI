"""
Idempotency Manager for Async Repository Ingestion.

Handles duplicate request detection using content-based hashing.
Implements Requirements 5.1, 5.2, 5.3, 5.4, 5.5 from async-repository-ingestion spec.
"""
import hashlib
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


class IdempotencyManager:
    """Manage idempotency for repository ingestion requests."""
    
    def __init__(self):
        """Initialize the idempotency manager with DynamoDB client."""
        self.dynamodb = boto3.resource('dynamodb')
        self.jobs_table = self.dynamodb.Table(
            os.environ.get('INGESTION_JOBS_TABLE', 'BloomWay-IngestionJobs')
        )
    
    @staticmethod
    def generate_key(content: bytes, source: str = "") -> str:
        """
        Generate idempotency key from content hash.
        
        Uses SHA-256 to create a deterministic hash from the repository content.
        For the same content, this will always produce the same key.
        
        Args:
            content: File content bytes (e.g., ZIP file data)
            source: Source URL or identifier (optional, for additional uniqueness)
            
        Returns:
            SHA-256 hash as 64-character hex string
            
        Validates: Requirements 5.1 (Idempotency Key Generation)
        Property 11: Idempotency Key Determinism
        """
        hasher = hashlib.sha256()
        hasher.update(content)
        
        # Include source for additional uniqueness if provided
        if source:
            hasher.update(source.encode('utf-8'))
        
        return hasher.hexdigest()
    
    def check_existing_job(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Check for existing job with same idempotency key.
        
        Queries the idempotency-index GSI to find jobs with matching key.
        Returns the most recent job if found.
        
        Args:
            idempotency_key: SHA-256 hash of repository content
            
        Returns:
            Job record dict if exists, None otherwise
            
        Validates: Requirements 5.2, 5.3, 5.4 (Duplicate Detection)
        """
        try:
            response = self.jobs_table.query(
                IndexName='idempotency-index',
                KeyConditionExpression='idempotency_key = :key',
                ExpressionAttributeValues={':key': idempotency_key},
                ScanIndexForward=False,  # Most recent first
                Limit=1
            )
            
            if response.get('Items'):
                return response['Items'][0]
            
            return None
            
        except ClientError as e:
            print(f"Error querying idempotency index: {str(e)}")
            # On error, assume no existing job (fail open)
            return None
    
    def should_create_new_job(self, existing_job: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if new job should be created based on existing job status.
        
        Decision logic:
        - No existing job: Create new job
        - Existing job with status "processing": Return existing (don't create)
        - Existing job with status "completed": Return existing (don't create)
        - Existing job with status "failed": Create new job (allow retry)
        
        Args:
            existing_job: Existing job record or None
            
        Returns:
            True if new job should be created, False if existing job should be returned
            
        Validates: Requirements 5.2, 5.3, 5.4 (Status-based Decision Logic)
        """
        if existing_job is None:
            # No existing job, create new one
            return True
        
        status = existing_job.get('status', '')
        
        if status in ['processing', 'completed']:
            # Job is in progress or already done, return existing
            return False
        
        if status == 'failed':
            # Job failed, allow retry with new job
            return True
        
        # Unknown status, create new job to be safe
        return True
    
    def get_existing_job_response(self, existing_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format response for existing job.
        
        Args:
            existing_job: Existing job record from DynamoDB
            
        Returns:
            Response dict with job_id, status, and progress information
        """
        from decimal import Decimal
        
        response = {
            'job_id': existing_job['job_id'],
            'status': existing_job.get('status', 'unknown'),
            'message': 'Job already exists'
        }
        
        # Include progress if available (convert Decimal to int)
        if 'progress_current' in existing_job:
            val = existing_job['progress_current']
            response['progress_current'] = int(val) if isinstance(val, Decimal) else val
        if 'progress_total' in existing_job:
            val = existing_job['progress_total']
            response['progress_total'] = int(val) if isinstance(val, Decimal) else val
        
        # Include repo_id if completed
        if existing_job.get('status') == 'completed' and 'repo_id' in existing_job:
            response['repo_id'] = existing_job['repo_id']
        
        # Include error message if failed
        if existing_job.get('status') == 'failed' and 'error_message' in existing_job:
            response['error_message'] = existing_job['error_message']
        
        return response
