"""
Unit tests for IdempotencyManager.

Tests Requirements 5.1-5.5 from async-repository-ingestion spec.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from idempotency_manager import IdempotencyManager


class TestIdempotencyManager(unittest.TestCase):
    """Test IdempotencyManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = IdempotencyManager()
    
    def test_generate_key_deterministic(self):
        """Test that same content produces same key (Property 11)."""
        content = b"test repository content"
        source = "test_source"
        
        key1 = IdempotencyManager.generate_key(content, source)
        key2 = IdempotencyManager.generate_key(content, source)
        
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 64)  # SHA-256 produces 64 hex characters
        self.assertTrue(all(c in '0123456789abcdef' for c in key1))
    
    def test_generate_key_different_content(self):
        """Test that different content produces different keys."""
        content1 = b"repository content 1"
        content2 = b"repository content 2"
        
        key1 = IdempotencyManager.generate_key(content1)
        key2 = IdempotencyManager.generate_key(content2)
        
        self.assertNotEqual(key1, key2)
    
    def test_generate_key_with_source(self):
        """Test that source affects key generation."""
        content = b"same content"
        
        key1 = IdempotencyManager.generate_key(content, "source1")
        key2 = IdempotencyManager.generate_key(content, "source2")
        
        self.assertNotEqual(key1, key2)
    
    @patch('idempotency_manager.boto3')
    def test_check_existing_job_found(self, mock_boto3):
        """Test checking for existing job that exists."""
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'job_id': 'test-job-123',
                'status': 'processing',
                'idempotency_key': 'test-key'
            }]
        }
        
        manager = IdempotencyManager()
        manager.jobs_table = mock_table
        
        result = manager.check_existing_job('test-key')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['job_id'], 'test-job-123')
        mock_table.query.assert_called_once()
    
    @patch('idempotency_manager.boto3')
    def test_check_existing_job_not_found(self, mock_boto3):
        """Test checking for existing job that doesn't exist."""
        mock_table = Mock()
        mock_table.query.return_value = {'Items': []}
        
        manager = IdempotencyManager()
        manager.jobs_table = mock_table
        
        result = manager.check_existing_job('nonexistent-key')
        
        self.assertIsNone(result)
    
    def test_should_create_new_job_no_existing(self):
        """Test decision when no existing job (Requirement 5.2)."""
        result = self.manager.should_create_new_job(None)
        self.assertTrue(result)
    
    def test_should_create_new_job_processing(self):
        """Test decision when existing job is processing (Requirement 5.2)."""
        existing_job = {'job_id': 'test-123', 'status': 'processing'}
        result = self.manager.should_create_new_job(existing_job)
        self.assertFalse(result)  # Should return existing
    
    def test_should_create_new_job_completed(self):
        """Test decision when existing job is completed (Requirement 5.3)."""
        existing_job = {'job_id': 'test-123', 'status': 'completed'}
        result = self.manager.should_create_new_job(existing_job)
        self.assertFalse(result)  # Should return existing
    
    def test_should_create_new_job_failed(self):
        """Test decision when existing job failed (Requirement 5.4)."""
        existing_job = {'job_id': 'test-123', 'status': 'failed'}
        result = self.manager.should_create_new_job(existing_job)
        self.assertTrue(result)  # Should create new (allow retry)
    
    def test_should_create_new_job_unknown_status(self):
        """Test decision when existing job has unknown status."""
        existing_job = {'job_id': 'test-123', 'status': 'unknown'}
        result = self.manager.should_create_new_job(existing_job)
        self.assertTrue(result)  # Should create new to be safe
    
    def test_get_existing_job_response_processing(self):
        """Test response formatting for processing job."""
        existing_job = {
            'job_id': 'test-123',
            'status': 'processing',
            'progress_current': 50,
            'progress_total': 100
        }
        
        response = self.manager.get_existing_job_response(existing_job)
        
        self.assertEqual(response['job_id'], 'test-123')
        self.assertEqual(response['status'], 'processing')
        self.assertEqual(response['progress_current'], 50)
        self.assertEqual(response['progress_total'], 100)
        self.assertIn('message', response)
    
    def test_get_existing_job_response_completed(self):
        """Test response formatting for completed job."""
        existing_job = {
            'job_id': 'test-123',
            'status': 'completed',
            'repo_id': 'repo-456'
        }
        
        response = self.manager.get_existing_job_response(existing_job)
        
        self.assertEqual(response['status'], 'completed')
        self.assertEqual(response['repo_id'], 'repo-456')
    
    def test_get_existing_job_response_failed(self):
        """Test response formatting for failed job."""
        existing_job = {
            'job_id': 'test-123',
            'status': 'failed',
            'error_message': 'Processing failed'
        }
        
        response = self.manager.get_existing_job_response(existing_job)
        
        self.assertEqual(response['status'], 'failed')
        self.assertEqual(response['error_message'], 'Processing failed')


if __name__ == '__main__':
    unittest.main()
