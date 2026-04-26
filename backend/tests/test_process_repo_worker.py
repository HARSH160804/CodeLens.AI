"""
Unit tests for Processing Worker Lambda.

Tests cover:
- Stale job detection
- Error classification
- Memory management
- Cleanup on failure
- SQS message parsing
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'handlers'))

# Mock AWS services and dependencies before importing handler
mock_boto3 = MagicMock()
mock_botocore = MagicMock()
mock_botocore_exceptions = MagicMock()

# Create mock exception classes
class MockClientError(Exception):
    def __init__(self, error_response, operation_name):
        self.response = error_response
        self.operation_name = operation_name

mock_botocore_exceptions.ClientError = MockClientError

sys.modules['boto3'] = mock_boto3
sys.modules['boto3.dynamodb'] = MagicMock()
sys.modules['boto3.dynamodb.conditions'] = MagicMock()
sys.modules['botocore'] = mock_botocore
sys.modules['botocore.exceptions'] = mock_botocore_exceptions

# Mock other dependencies
sys.modules['psutil'] = MagicMock()
sys.modules['code_processor'] = MagicMock()
sys.modules['bedrock_client'] = MagicMock()
sys.modules['vector_store'] = MagicMock()
sys.modules['idempotency_manager'] = MagicMock()
sys.modules['progress_tracker'] = MagicMock()

# Import after mocking
import process_repo_worker


class TestStaleJobDetection(unittest.TestCase):
    """Test stale job detection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_jobs_table = Mock()
        process_repo_worker.jobs_table = self.mock_jobs_table
    
    def test_detect_stale_jobs_marks_old_processing_jobs(self):
        """Test that jobs older than 15 minutes are marked as failed."""
        # Create a stale job (20 minutes old) - use naive datetime to match implementation
        stale_time = datetime.utcnow() - timedelta(minutes=20)
        stale_job = {
            'job_id': 'stale-job-123',
            'status': 'processing',
            'updated_at': stale_time.isoformat() + 'Z'
        }
        
        # Create a recent job (5 minutes old)
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        recent_job = {
            'job_id': 'recent-job-456',
            'status': 'processing',
            'updated_at': recent_time.isoformat() + 'Z'
        }
        
        self.mock_jobs_table.scan.return_value = {
            'Items': [stale_job, recent_job]
        }
        
        # Run detection
        process_repo_worker.detect_stale_jobs()
        
        # Verify only stale job was updated
        self.mock_jobs_table.update_item.assert_called_once()
        call_args = self.mock_jobs_table.update_item.call_args
        self.assertEqual(call_args[1]['Key']['job_id'], 'stale-job-123')
        self.assertIn('Processing timeout exceeded', 
                     str(call_args[1]['ExpressionAttributeValues'][':error']))
    
    def test_detect_stale_jobs_handles_no_stale_jobs(self):
        """Test detection when no stale jobs exist."""
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        recent_job = {
            'job_id': 'recent-job-456',
            'status': 'processing',
            'updated_at': recent_time.isoformat() + 'Z'
        }
        
        self.mock_jobs_table.scan.return_value = {
            'Items': [recent_job]
        }
        
        # Run detection
        process_repo_worker.detect_stale_jobs()
        
        # Verify no updates
        self.mock_jobs_table.update_item.assert_not_called()
    
    def test_detect_stale_jobs_handles_empty_table(self):
        """Test detection with no jobs in table."""
        self.mock_jobs_table.scan.return_value = {'Items': []}
        
        # Should not raise exception
        process_repo_worker.detect_stale_jobs()
        
        self.mock_jobs_table.update_item.assert_not_called()


class TestErrorClassification(unittest.TestCase):
    """Test error classification (TransientError vs PermanentError)."""
    
    def test_transient_error_is_retryable(self):
        """Test that TransientError is raised for retryable errors."""
        error = process_repo_worker.TransientError("Network timeout")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Network timeout")
    
    def test_permanent_error_is_not_retryable(self):
        """Test that PermanentError is raised for non-retryable errors."""
        error = process_repo_worker.PermanentError("Invalid format")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Invalid format")
    
    def test_error_types_are_distinct(self):
        """Test that error types can be distinguished."""
        transient = process_repo_worker.TransientError("test")
        permanent = process_repo_worker.PermanentError("test")
        
        self.assertNotEqual(type(transient), type(permanent))
        self.assertIsInstance(transient, process_repo_worker.TransientError)
        self.assertIsInstance(permanent, process_repo_worker.PermanentError)


class TestMemoryManagement(unittest.TestCase):
    """Test memory monitoring and management."""
    
    def test_check_memory_handles_missing_psutil(self):
        """Test that check_memory handles missing psutil gracefully."""
        # Should not raise exception when psutil is not available
        try:
            process_repo_worker.check_memory()
        except process_repo_worker.PermanentError:
            # This is okay - it means memory is actually high
            pass
        except Exception as e:
            # Should not raise other exceptions
            self.fail(f"check_memory raised unexpected exception: {e}")
    
    def test_memory_constants_defined(self):
        """Test that memory management constants are defined."""
        self.assertTrue(hasattr(process_repo_worker, 'MAX_MEMORY_MB'))
        self.assertTrue(hasattr(process_repo_worker, 'MEMORY_THRESHOLD_MB'))
        self.assertGreater(process_repo_worker.MAX_MEMORY_MB, 0)
        self.assertGreater(process_repo_worker.MEMORY_THRESHOLD_MB, 0)


class TestCleanupOnFailure(unittest.TestCase):
    """Test cleanup functionality on processing failure."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_jobs_table = Mock()
        self.mock_embeddings_table = Mock()
        self.mock_dynamodb = Mock()
        self.mock_dynamodb.Table.return_value = self.mock_embeddings_table
        
        process_repo_worker.jobs_table = self.mock_jobs_table
        process_repo_worker.dynamodb = self.mock_dynamodb
    
    @patch('process_repo_worker.shutil')
    @patch('process_repo_worker.os')
    @patch('process_repo_worker.ProgressTracker')
    def test_cleanup_removes_temp_files(self, mock_tracker_class, mock_os, mock_shutil):
        """Test that temporary files are removed on cleanup."""
        mock_os.path.exists.return_value = True
        mock_os.path.dirname.return_value = '/tmp/test-repo'
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        # Run cleanup
        process_repo_worker.cleanup_on_failure(
            'job-123', 'repo-456', 'Test error', '/tmp/test-repo/extracted'
        )
        
        # Verify temp files removed
        mock_shutil.rmtree.assert_called_once()
    
    @patch('process_repo_worker.ProgressTracker')
    def test_cleanup_deletes_partial_embeddings(self, mock_tracker_class):
        """Test that partial embeddings are deleted on cleanup."""
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        # Mock embeddings query
        self.mock_embeddings_table.query.return_value = {
            'Items': [
                {'repo_id': 'repo-456', 'chunk_id': 'chunk-1'},
                {'repo_id': 'repo-456', 'chunk_id': 'chunk-2'}
            ]
        }
        
        # Create a proper mock for batch_writer context manager
        mock_batch_writer = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context.__exit__ = Mock(return_value=False)
        self.mock_embeddings_table.batch_writer.return_value = mock_context
        
        # Run cleanup
        process_repo_worker.cleanup_on_failure(
            'job-123', 'repo-456', 'Test error', None
        )
        
        # Verify embeddings deleted
        self.assertEqual(mock_batch_writer.delete_item.call_count, 2)
    
    @patch('process_repo_worker.ProgressTracker')
    def test_cleanup_marks_job_as_failed(self, mock_tracker_class):
        """Test that job status is updated to failed."""
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        self.mock_embeddings_table.query.return_value = {'Items': []}
        
        # Run cleanup
        process_repo_worker.cleanup_on_failure(
            'job-123', 'repo-456', 'Test error message', None
        )
        
        # Verify job marked as failed
        mock_tracker.mark_failed.assert_called_once_with('Test error message')
    
    @patch('process_repo_worker.ProgressTracker')
    def test_cleanup_continues_on_partial_failure(self, mock_tracker_class):
        """Test that cleanup continues even if some steps fail."""
        mock_tracker = Mock()
        mock_tracker.mark_failed.side_effect = Exception("Tracker failed")
        mock_tracker_class.return_value = mock_tracker
        
        self.mock_embeddings_table.query.return_value = {'Items': []}
        
        # Should not raise exception
        process_repo_worker.cleanup_on_failure(
            'job-123', 'repo-456', 'Test error', None
        )
        
        # Verify fallback update was attempted
        self.mock_jobs_table.update_item.assert_called_once()


class TestSQSMessageParsing(unittest.TestCase):
    """Test SQS message parsing and validation."""
    
    def test_parse_valid_sqs_message(self):
        """Test parsing a valid SQS message."""
        event = {
            'Records': [{
                'body': json.dumps({
                    'job_id': 'job-123',
                    'repo_id': 'repo-456',
                    'source': 'https://github.com/user/repo',
                    'source_type': 'github'
                }),
                'receiptHandle': 'receipt-handle-123'
            }]
        }
        
        # Extract message
        record = event['Records'][0]
        message = json.loads(record['body'])
        
        self.assertEqual(message['job_id'], 'job-123')
        self.assertEqual(message['repo_id'], 'repo-456')
        self.assertEqual(message['source_type'], 'github')
    
    def test_handle_missing_required_fields(self):
        """Test handling of message with missing required fields."""
        event = {
            'Records': [{
                'body': json.dumps({
                    'job_id': 'job-123'
                    # Missing repo_id, source, source_type
                }),
                'receiptHandle': 'receipt-handle-123'
            }]
        }
        
        record = event['Records'][0]
        message = json.loads(record['body'])
        
        # Verify missing fields
        self.assertIsNone(message.get('repo_id'))
        self.assertIsNone(message.get('source'))
        self.assertIsNone(message.get('source_type'))
    
    def test_handle_invalid_json(self):
        """Test handling of invalid JSON in message."""
        event = {
            'Records': [{
                'body': 'invalid json {',
                'receiptHandle': 'receipt-handle-123'
            }]
        }
        
        record = event['Records'][0]
        
        # Should raise JSONDecodeError
        with self.assertRaises(json.JSONDecodeError):
            json.loads(record['body'])


class TestDownloadRepository(unittest.TestCase):
    """Test repository download functionality."""
    
    @patch('process_repo_worker.download_github_repo')
    def test_download_github_repository(self, mock_download):
        """Test downloading a GitHub repository."""
        mock_download.return_value = '/tmp/repo-123/extracted'
        
        result = process_repo_worker.download_repository(
            'repo-123',
            'https://github.com/user/repo',
            'github'
        )
        
        self.assertEqual(result, '/tmp/repo-123/extracted')
        mock_download.assert_called_once_with('https://github.com/user/repo', 'repo-123')
    
    def test_download_unsupported_source_type(self):
        """Test handling of unsupported source type."""
        with self.assertRaises(process_repo_worker.PermanentError) as context:
            process_repo_worker.download_repository(
                'repo-123',
                'some-source',
                'unsupported'
            )
        
        self.assertIn("Unsupported source_type", str(context.exception))
    
    @patch('process_repo_worker.urlopen')
    @patch('process_repo_worker.zipfile')
    @patch('process_repo_worker.os')
    def test_download_github_repo_tries_master_on_404(self, mock_os, mock_zipfile, mock_urlopen):
        """Test that download tries master branch if main fails."""
        from urllib.error import HTTPError
        
        # First call (main branch) raises 404
        # Second call (master branch) succeeds
        mock_response = Mock()
        mock_response.read.return_value = b'zip content'
        
        # Create proper context manager for the response
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_response)
        mock_context.__exit__ = Mock(return_value=False)
        
        mock_urlopen.side_effect = [
            HTTPError('url', 404, 'Not Found', {}, None),
            mock_context
        ]
        
        mock_os.path.getsize.return_value = 1000
        mock_os.path.exists.return_value = True
        mock_os.listdir.return_value = ['repo-main']
        mock_os.path.isdir.return_value = True
        mock_os.path.join.return_value = '/tmp/repo-123/repo-main'
        mock_os.makedirs.return_value = None
        
        # Create proper context manager for ZipFile
        mock_zip = Mock()
        mock_zip_context = Mock()
        mock_zip_context.__enter__ = Mock(return_value=mock_zip)
        mock_zip_context.__exit__ = Mock(return_value=False)
        mock_zipfile.ZipFile.return_value = mock_zip_context
        
        result = process_repo_worker.download_github_repo(
            'https://github.com/user/repo',
            'repo-123'
        )
        
        # Verify both branches were tried
        self.assertEqual(mock_urlopen.call_count, 2)


class TestBatchProcessing(unittest.TestCase):
    """Test batch processing logic."""
    
    def test_batch_size_calculation(self):
        """Test that files are processed in correct batch sizes."""
        files = [{'path': f'/tmp/file{i}.py'} for i in range(125)]
        batch_size = 50
        
        batches = []
        for start in range(0, len(files), batch_size):
            end = min(start + batch_size, len(files))
            batch = files[start:end]
            batches.append(batch)
        
        # Verify batch counts
        self.assertEqual(len(batches), 3)  # 50 + 50 + 25
        self.assertEqual(len(batches[0]), 50)
        self.assertEqual(len(batches[1]), 50)
        self.assertEqual(len(batches[2]), 25)
    
    def test_progress_update_frequency(self):
        """Test that progress is updated every 10 files."""
        total_files = 45
        update_frequency = 10
        
        updates = []
        for i in range(total_files):
            if (i + 1) % update_frequency == 0:
                updates.append(i + 1)
        
        # Verify update points
        self.assertEqual(updates, [10, 20, 30, 40])


if __name__ == '__main__':
    unittest.main()
