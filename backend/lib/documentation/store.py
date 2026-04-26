"""
Documentation Store - Persistent storage for generated documentation

Manages documentation storage in DynamoDB with support for large documents
via S3 fallback and atomic state transitions.
"""

import os
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DocumentationStore:
    """
    Persistent storage layer for generated documentation.
    
    Uses DynamoDB for metadata and small documents (<400KB).
    Falls back to S3 for large documents (>400KB).
    """
    
    # DynamoDB item size limit is 400KB, use 350KB as safe threshold
    MAX_DYNAMODB_SIZE = 350 * 1024  # 350KB in bytes
    
    def __init__(self):
        """Initialize DocumentationStore with AWS clients."""
        self.dynamodb = boto3.resource('dynamodb')
        self.s3 = boto3.client('s3')
        self.table_name = os.environ.get('REPO_DOCUMENTATION_TABLE', 'BloomWay-RepoDocumentation')
        self.bucket_name = os.environ.get('CODE_BUCKET')
        self.table = self.dynamodb.Table(self.table_name)
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _should_use_s3(self, content: str) -> bool:
        """Determine if content should be stored in S3."""
        return len(content.encode('utf-8')) > self.MAX_DYNAMODB_SIZE
    
    async def save(self, repo_id: str, content: str) -> None:
        """
        Save generated documentation.
        
        Args:
            repo_id: Repository identifier
            content: Markdown documentation content
            
        Raises:
            Exception: If save operation fails
        """
        try:
            content_hash = self._calculate_hash(content)
            now = datetime.utcnow().isoformat() + 'Z'
            
            # Build update expression to preserve existing state
            update_expression = 'SET content_hash = :hash, updated_at = :now'
            expression_values = {
                ':hash': content_hash,
                ':now': now
            }
            
            # Check if content should go to S3
            if self._should_use_s3(content):
                # Store in S3
                s3_key = f'documentation/{repo_id}/docs.md'
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content.encode('utf-8'),
                    ContentType='text/markdown'
                )
                update_expression += ', content_s3_key = :s3_key'
                expression_values[':s3_key'] = s3_key
                # Remove inline content if it exists
                update_expression += ' REMOVE content'
                logger.info(f"Stored large documentation in S3: {s3_key}")
            else:
                # Store directly in DynamoDB
                update_expression += ', content = :content'
                expression_values[':content'] = content
                # Remove S3 key if it exists
                update_expression += ' REMOVE content_s3_key'
            
            # Update DynamoDB (preserves generation_state and created_at)
            self.table.update_item(
                Key={'repo_id': repo_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            logger.info(f"Saved documentation for repo {repo_id}")
            
        except ClientError as e:
            logger.error(f"Failed to save documentation for {repo_id}: {e}")
            raise Exception(f"Storage operation failed: {str(e)}")
    
    async def get(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve documentation with metadata.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Documentation record with content, or None if not found
        """
        try:
            response = self.table.get_item(Key={'repo_id': repo_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # If content is in S3, retrieve it
            if 'content_s3_key' in item and item['content_s3_key']:
                try:
                    s3_response = self.s3.get_object(
                        Bucket=self.bucket_name,
                        Key=item['content_s3_key']
                    )
                    item['content'] = s3_response['Body'].read().decode('utf-8')
                except ClientError as e:
                    logger.error(f"Failed to retrieve content from S3: {e}")
                    raise Exception("Failed to retrieve documentation content")
            
            return item
            
        except ClientError as e:
            logger.error(f"Failed to get documentation for {repo_id}: {e}")
            raise Exception(f"Retrieval operation failed: {str(e)}")
    
    async def get_state(self, repo_id: str) -> str:
        """
        Get current generation state.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Generation state (not_generated|generating|generated|failed)
        """
        try:
            response = self.table.get_item(
                Key={'repo_id': repo_id},
                ProjectionExpression='generation_state'
            )
            
            if 'Item' not in response:
                return 'not_generated'
            
            return response['Item'].get('generation_state', 'not_generated')
            
        except ClientError as e:
            logger.error(f"Failed to get state for {repo_id}: {e}")
            return 'not_generated'
    
    async def update_state(
        self, 
        repo_id: str, 
        state: str, 
        error: Optional[str] = None
    ) -> None:
        """
        Update generation state atomically.
        
        Args:
            repo_id: Repository identifier
            state: New state (generating|generated|failed)
            error: Optional error message (for failed state)
            
        Raises:
            Exception: If update fails
        """
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            update_expression = 'SET generation_state = :state, updated_at = :now'
            expression_values = {
                ':state': state,
                ':now': now
            }
            
            # Add error message if provided
            if error:
                update_expression += ', error_message = :error'
                expression_values[':error'] = error
            else:
                # Remove error message if state is not failed
                update_expression += ' REMOVE error_message'
            
            # For initial state, create the item if it doesn't exist
            if state == 'generating':
                self.table.put_item(
                    Item={
                        'repo_id': repo_id,
                        'generation_state': state,
                        'created_at': now,
                        'updated_at': now
                    }
                )
            else:
                # Update existing item
                self.table.update_item(
                    Key={'repo_id': repo_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values
                )
            
            logger.info(f"Updated state for {repo_id} to {state}")
            
        except ClientError as e:
            logger.error(f"Failed to update state for {repo_id}: {e}")
            raise Exception(f"State update failed: {str(e)}")
    
    async def delete(self, repo_id: str) -> None:
        """
        Delete documentation (for cleanup).
        
        Args:
            repo_id: Repository identifier
        """
        try:
            # Get item to check for S3 content
            item = await self.get(repo_id)
            
            if item and 'content_s3_key' in item:
                # Delete from S3
                try:
                    self.s3.delete_object(
                        Bucket=self.bucket_name,
                        Key=item['content_s3_key']
                    )
                except ClientError as e:
                    logger.warning(f"Failed to delete S3 content: {e}")
            
            # Delete from DynamoDB
            self.table.delete_item(Key={'repo_id': repo_id})
            logger.info(f"Deleted documentation for {repo_id}")
            
        except ClientError as e:
            logger.error(f"Failed to delete documentation for {repo_id}: {e}")
            raise Exception(f"Delete operation failed: {str(e)}")
