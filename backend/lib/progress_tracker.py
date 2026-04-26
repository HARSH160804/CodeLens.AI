"""
Progress Tracker for Async Repository Ingestion.

Tracks and updates job progress in DynamoDB during processing.
Implements Requirements 2.2, 3.1, 3.2, 3.3, 3.4, 3.5 from async-repository-ingestion spec.
"""
import os
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError


class ProgressTracker:
    """Track and update job progress in DynamoDB."""
    
    def __init__(self, job_id: str, total_files: int):
        """
        Initialize tracker with job ID and total file count.
        
        Args:
            job_id: Unique identifier for the ingestion job
            total_files: Total number of files to process
            
        Validates: Requirements 3.1, 3.3, 3.4 (Progress Initialization)
        """
        self.job_id = job_id
        self.total_files = total_files
        self.last_update = 0
        self.update_interval = 10  # Update every 10 files
        
        self.dynamodb = boto3.resource('dynamodb')
        self.jobs_table = self.dynamodb.Table(
            os.environ.get('INGESTION_JOBS_TABLE', 'BloomWay-IngestionJobs')
        )
    
    def update(self, files_processed: int, message: str = ""):
        """
        Update progress in DynamoDB if threshold reached.
        
        Updates are batched to avoid excessive DynamoDB writes.
        Progress is updated every 10 files or at completion.
        
        Args:
            files_processed: Number of files processed so far
            message: Optional status message
            
        Validates: Requirements 3.2 (Update Frequency), 3.3, 3.4 (Progress Values)
        Property 7: Progress Invariant (current <= total, non-negative)
        Property 8: Progress Update Frequency
        """
        # Validate progress invariant
        if files_processed < 0:
            print(f"Warning: Negative files_processed value: {files_processed}")
            files_processed = 0
        
        if files_processed > self.total_files:
            print(f"Warning: files_processed ({files_processed}) > total_files ({self.total_files})")
            files_processed = self.total_files
        
        # Check if update threshold reached
        if files_processed - self.last_update >= self.update_interval or files_processed == self.total_files:
            self._write_to_dynamodb(files_processed, message)
            self.last_update = files_processed
    
    def _write_to_dynamodb(self, files_processed: int, message: str = ""):
        """
        Write progress to DynamoDB with timestamp update.
        
        Uses conditional write to prevent conflicts from concurrent updates.
        
        Args:
            files_processed: Number of files processed
            message: Optional status message
            
        Validates: Requirements 2.2 (Status Updates), 6.3 (Timestamp Updates)
        Property 15: Timestamp Update on Status Change
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        try:
            update_expression = 'SET progress_current = :current, progress_total = :total, updated_at = :now'
            expression_values = {
                ':current': files_processed,
                ':total': self.total_files,
                ':now': timestamp
            }
            
            if message:
                update_expression += ', progress_message = :message'
                expression_values[':message'] = message
            
            self.jobs_table.update_item(
                Key={'job_id': self.job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                # Conditional: only update if timestamp is older (prevent race conditions)
                ConditionExpression='attribute_not_exists(updated_at) OR updated_at < :now'
            )
            
            print(f"Progress updated: {files_processed}/{self.total_files} files")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Another process updated more recently, skip this update
                print(f"Skipped progress update due to concurrent modification")
            else:
                print(f"Error updating progress: {str(e)}")
                # Don't raise - progress updates are non-critical
    
    def mark_completed(self, repo_id: Optional[str] = None):
        """
        Mark job as completed with final status.
        
        Sets status to "completed", progress to 100%, and includes repo_id.
        
        Args:
            repo_id: Generated repository ID (optional)
            
        Validates: Requirements 2.3 (Completion Status), 3.5 (Final Progress)
        Property 4: Status Transition to Completed
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        try:
            update_expression = ('SET #status = :status, progress_current = :current, '
                               'progress_total = :total, updated_at = :now, completed_at = :now')
            expression_values = {
                ':status': 'completed',
                ':current': self.total_files,
                ':total': self.total_files,
                ':now': timestamp
            }
            expression_names = {
                '#status': 'status'  # 'status' is a reserved word in DynamoDB
            }
            
            if repo_id:
                update_expression += ', repo_id = :repo_id'
                expression_values[':repo_id'] = repo_id
            
            self.jobs_table.update_item(
                Key={'job_id': self.job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            print(f"Job {self.job_id} marked as completed")
            
        except ClientError as e:
            print(f"Error marking job as completed: {str(e)}")
            raise
    
    def mark_failed(self, error_message: str, error_code: str = "UNKNOWN_ERROR"):
        """
        Mark job as failed with error details.
        
        Sets status to "failed" and includes error message for user display.
        
        Args:
            error_message: User-friendly error message
            error_code: Error code for categorization
            
        Validates: Requirements 2.4 (Failure Status), 14.1-14.5 (Error Messages)
        Property 5: Status Transition to Failed
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        try:
            self.jobs_table.update_item(
                Key={'job_id': self.job_id},
                UpdateExpression=('SET #status = :status, error_message = :error_message, '
                                'error_code = :error_code, updated_at = :now, failed_at = :now'),
                ExpressionAttributeNames={
                    '#status': 'status'  # 'status' is a reserved word
                },
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error_message': error_message,
                    ':error_code': error_code,
                    ':now': timestamp
                }
            )
            
            print(f"Job {self.job_id} marked as failed: {error_message}")
            
        except ClientError as e:
            print(f"Error marking job as failed: {str(e)}")
            # Don't raise - we want to ensure failure is recorded even if update fails
    
    def update_status_message(self, message: str):
        """
        Update status message without changing progress.
        
        Useful for providing detailed status updates during processing.
        
        Args:
            message: Status message to display
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        try:
            self.jobs_table.update_item(
                Key={'job_id': self.job_id},
                UpdateExpression='SET progress_message = :message, updated_at = :now',
                ExpressionAttributeValues={
                    ':message': message,
                    ':now': timestamp
                }
            )
        except ClientError as e:
            print(f"Error updating status message: {str(e)}")
            # Non-critical, don't raise
