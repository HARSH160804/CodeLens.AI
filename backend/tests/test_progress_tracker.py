"""
Unit tests for ProgressTracker module.

Tests cover:
- Progress update frequency
- Timestamp updates
- Completion marking
- Failure marking
- Progress invariants
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

# Mock boto3 before importing
sys.modules['boto3'] = MagicMock()

from progress_tracker import ProgressTracker


class TestProgressTracker(unittest.TestCase):
    """Test ProgressTracker functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_table = Mock()
        
        # Patch the table initialization
        with patch('progress_tracker.boto3') as mock_boto3:
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = self.mock_table
            mock_boto3.resource.return_value = mock_dynamodb
            
            self.tracker = ProgressTracker('job-123', total_files=100)
    
    def test_initialization(self):
        """Test tracker initialization."""
        self.assertEqual(self.tracker.job_id, 'job-123')
        self.assertEqual(self.tracker.total_files, 100)
        self.assertEqual(self.tracker.last_update, 0)
    
    def test_update_every_10_files(self):
        """Test that updates occur every 10 files."""
        # Update at 5 files - should not write
        self.tracker.update(5)
        self.mock_table.update_item.assert_not_called()
        
        # Update at 10 files - should write
        self.tracker.update(10)
        self.mock_table.update_item.assert_called_once()
        
        # Reset mock
        self.mock_table.reset_mock()
        
        # Update at 15 files - should not write
        self.tracker.update(15)
        self.mock_table.update_item.assert_not_called()
        
        # Update at 20 files - should write
        self.tracker.update(20)
        self.mock_table.update_item.assert_called_once()
    
    def test_update_includes_timestamp(self):
        """Test that updates include current timestamp."""
        self.tracker.update(10)
        
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        
        # Verify timestamp is present and recent
        self.assertIn(':now', values)
        timestamp_str = values[':now']
        self.assertTrue(timestamp_str.endswith('Z'))
    
    def test_mark_completed_sets_status(self):
        """Test that mark_completed sets correct status."""
        self.tracker.mark_completed()
        
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        
        self.assertEqual(values[':status'], 'completed')
        self.assertEqual(values[':current'], 100)
        self.assertEqual(values[':total'], 100)
    
    def test_mark_failed_includes_error_message(self):
        """Test that mark_failed includes error message."""
        error_msg = "Processing failed due to network error"
        self.tracker.mark_failed(error_msg)
        
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        
        self.assertEqual(values[':status'], 'failed')
        self.assertEqual(values[':error_message'], error_msg)
    
    def test_progress_invariant_current_le_total(self):
        """Test that progress_current <= progress_total."""
        # Valid progress
        self.tracker.update(50)
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        self.assertLessEqual(values[':current'], values[':total'])
        
        # At limit
        self.tracker.update(100)
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        self.assertEqual(values[':current'], values[':total'])
    
    def test_progress_values_non_negative(self):
        """Test that progress values are non-negative."""
        self.tracker.update(10)
        
        call_args = self.mock_table.update_item.call_args
        values = call_args[1]['ExpressionAttributeValues']
        
        self.assertGreaterEqual(values[':current'], 0)
        self.assertGreaterEqual(values[':total'], 0)
    
    def test_update_handles_dynamodb_errors(self):
        """Test that update handles DynamoDB errors gracefully."""
        from botocore.exceptions import ClientError
        
        self.mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            'UpdateItem'
        )
        
        # Should not raise exception
        try:
            self.tracker.update(10)
        except ClientError:
            self.fail("update() raised ClientError unexpectedly")
    
    def test_multiple_updates_track_last_count(self):
        """Test that last_update is tracked correctly."""
        self.tracker.update(10)
        self.assertEqual(self.tracker.last_update, 10)
        
        self.tracker.update(20)
        self.assertEqual(self.tracker.last_update, 20)
        
        self.tracker.update(30)
        self.assertEqual(self.tracker.last_update, 30)


class TestProgressTrackerEdgeCases(unittest.TestCase):
    """Test edge cases for ProgressTracker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_table = Mock()
        
        with patch('progress_tracker.boto3') as mock_boto3:
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = self.mock_table
            mock_boto3.resource.return_value = mock_dynamodb
            
            self.tracker = ProgressTracker('job-123', total_files=100)
    
    def test_zero_total_files(self):
        """Test tracker with zero total files."""
        with patch('progress_tracker.boto3') as mock_boto3:
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = self.mock_table
            mock_boto3.resource.return_value = mock_dynamodb
            
            tracker = ProgressTracker('job-123', total_files=0)
            
            # Should handle gracefully
            tracker.mark_completed()
            self.mock_table.update_item.assert_called_once()
    
    def test_update_with_same_count_twice(self):
        """Test updating with same count twice."""
        self.tracker.update(10)
        self.mock_table.reset_mock()
        
        # Update with same count - should not write again
        self.tracker.update(10)
        self.mock_table.update_item.assert_not_called()
    
    def test_update_with_decreasing_count(self):
        """Test that decreasing counts are handled."""
        self.tracker.update(20)
        self.mock_table.reset_mock()
        
        # Update with lower count - should still write if at boundary
        self.tracker.update(10)
        # Since we already updated at 20, updating at 10 shouldn't trigger
        self.mock_table.update_item.assert_not_called()


if __name__ == '__main__':
    unittest.main()
