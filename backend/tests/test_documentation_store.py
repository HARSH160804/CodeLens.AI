"""
Unit tests for DocumentationStore class.

Tests storage operations, state management, and S3 fallback.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from documentation.store import DocumentationStore


class TestDocumentationStore:
    """Test suite for DocumentationStore."""
    
    @pytest.fixture
    def mock_dynamodb(self):
        """Mock DynamoDB resource."""
        with patch('boto3.resource') as mock_resource:
            mock_table = MagicMock()
            mock_resource.return_value.Table.return_value = mock_table
            yield mock_table
    
    @pytest.fixture
    def mock_s3(self):
        """Mock S3 client."""
        with patch('boto3.client') as mock_client:
            yield mock_client.return_value
    
    @pytest.fixture
    def store(self, mock_dynamodb, mock_s3):
        """Create DocumentationStore instance with mocked AWS clients."""
        with patch.dict(os.environ, {
            'DOCS_TABLE': 'test-docs-table',
            'CODE_BUCKET': 'test-bucket'
        }):
            return DocumentationStore()
    
    def test_calculate_hash(self, store):
        """Test content hash calculation."""
        content = "# Test Documentation\n\nThis is a test."
        hash1 = store._calculate_hash(content)
        hash2 = store._calculate_hash(content)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
        
        # Different content should produce different hash
        different_content = "# Different Documentation"
        hash3 = store._calculate_hash(different_content)
        assert hash1 != hash3
    
    def test_should_use_s3_small_content(self, store):
        """Test that small content doesn't use S3."""
        small_content = "# Small Doc\n\n" + ("x" * 1000)  # ~1KB
        assert not store._should_use_s3(small_content)
    
    def test_should_use_s3_large_content(self, store):
        """Test that large content uses S3."""
        large_content = "# Large Doc\n\n" + ("x" * 400000)  # ~400KB
        assert store._should_use_s3(large_content)
    
    @pytest.mark.asyncio
    async def test_save_small_document(self, store, mock_dynamodb):
        """Test saving small document to DynamoDB."""
        repo_id = "test-repo-123"
        content = "# Test Documentation\n\nSmall content."
        
        await store.save(repo_id, content)
        
        # Verify DynamoDB put_item was called
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['repo_id'] == repo_id
        assert item['content'] == content
        assert item['generation_state'] == 'generated'
        assert 'content_hash' in item
        assert 'created_at' in item
        assert 'updated_at' in item
    
    @pytest.mark.asyncio
    async def test_save_large_document(self, store, mock_dynamodb, mock_s3):
        """Test saving large document to S3."""
        repo_id = "test-repo-456"
        content = "# Large Documentation\n\n" + ("x" * 400000)
        
        await store.save(repo_id, content)
        
        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        s3_call_args = mock_s3.put_object.call_args[1]
        assert s3_call_args['Bucket'] == 'test-bucket'
        assert 'documentation/' in s3_call_args['Key']
        
        # Verify DynamoDB has S3 reference
        mock_dynamodb.put_item.assert_called_once()
        item = mock_dynamodb.put_item.call_args[1]['Item']
        assert 'content_s3_key' in item
        assert 'content' not in item  # Content should not be in DynamoDB
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self, store, mock_dynamodb):
        """Test getting non-existent document."""
        mock_dynamodb.get_item.return_value = {}
        
        result = await store.get("non-existent-repo")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_document_from_dynamodb(self, store, mock_dynamodb):
        """Test getting document from DynamoDB."""
        repo_id = "test-repo-789"
        content = "# Test Doc"
        
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'repo_id': repo_id,
                'content': content,
                'content_hash': 'abc123',
                'generation_state': 'generated',
                'created_at': '2024-01-01T00:00:00Z'
            }
        }
        
        result = await store.get(repo_id)
        
        assert result is not None
        assert result['repo_id'] == repo_id
        assert result['content'] == content
        assert result['generation_state'] == 'generated'
    
    @pytest.mark.asyncio
    async def test_get_document_from_s3(self, store, mock_dynamodb, mock_s3):
        """Test getting document from S3."""
        repo_id = "test-repo-s3"
        content = "# Large Doc from S3"
        s3_key = f"documentation/{repo_id}/docs.md"
        
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'repo_id': repo_id,
                'content_s3_key': s3_key,
                'content_hash': 'def456',
                'generation_state': 'generated'
            }
        }
        
        # Mock S3 response
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = content.encode('utf-8')
        mock_s3.get_object.return_value = mock_s3_response
        
        result = await store.get(repo_id)
        
        assert result is not None
        assert result['content'] == content
        mock_s3.get_object.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_state_not_generated(self, store, mock_dynamodb):
        """Test getting state for non-existent document."""
        mock_dynamodb.get_item.return_value = {}
        
        state = await store.get_state("new-repo")
        
        assert state == 'not_generated'
    
    @pytest.mark.asyncio
    async def test_get_state_generated(self, store, mock_dynamodb):
        """Test getting state for generated document."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'generation_state': 'generated'}
        }
        
        state = await store.get_state("test-repo")
        
        assert state == 'generated'
    
    @pytest.mark.asyncio
    async def test_update_state_to_generating(self, store, mock_dynamodb):
        """Test updating state to generating."""
        repo_id = "test-repo"
        
        await store.update_state(repo_id, 'generating')
        
        # Should create new item
        mock_dynamodb.put_item.assert_called_once()
        item = mock_dynamodb.put_item.call_args[1]['Item']
        assert item['repo_id'] == repo_id
        assert item['generation_state'] == 'generating'
    
    @pytest.mark.asyncio
    async def test_update_state_to_generated(self, store, mock_dynamodb):
        """Test updating state to generated."""
        repo_id = "test-repo"
        
        await store.update_state(repo_id, 'generated')
        
        # Should update existing item
        mock_dynamodb.update_item.assert_called_once()
        call_args = mock_dynamodb.update_item.call_args[1]
        assert call_args['Key']['repo_id'] == repo_id
        assert ':state' in call_args['ExpressionAttributeValues']
        assert call_args['ExpressionAttributeValues'][':state'] == 'generated'
    
    @pytest.mark.asyncio
    async def test_update_state_to_failed_with_error(self, store, mock_dynamodb):
        """Test updating state to failed with error message."""
        repo_id = "test-repo"
        error_msg = "Generation failed due to AI error"
        
        await store.update_state(repo_id, 'failed', error_msg)
        
        mock_dynamodb.update_item.assert_called_once()
        call_args = mock_dynamodb.update_item.call_args[1]
        assert ':error' in call_args['ExpressionAttributeValues']
        assert call_args['ExpressionAttributeValues'][':error'] == error_msg
    
    @pytest.mark.asyncio
    async def test_delete_document_dynamodb_only(self, store, mock_dynamodb):
        """Test deleting document from DynamoDB only."""
        repo_id = "test-repo"
        
        # Mock get to return document without S3 key
        with patch.object(store, 'get', return_value={'repo_id': repo_id, 'content': 'test'}):
            await store.delete(repo_id)
        
        mock_dynamodb.delete_item.assert_called_once()
        assert mock_dynamodb.delete_item.call_args[1]['Key']['repo_id'] == repo_id
    
    @pytest.mark.asyncio
    async def test_delete_document_with_s3(self, store, mock_dynamodb, mock_s3):
        """Test deleting document from both S3 and DynamoDB."""
        repo_id = "test-repo"
        s3_key = f"documentation/{repo_id}/docs.md"
        
        # Mock get to return document with S3 key
        with patch.object(store, 'get', return_value={
            'repo_id': repo_id,
            'content_s3_key': s3_key
        }):
            await store.delete(repo_id)
        
        # Verify S3 delete was called
        mock_s3.delete_object.assert_called_once()
        assert mock_s3.delete_object.call_args[1]['Key'] == s3_key
        
        # Verify DynamoDB delete was called
        mock_dynamodb.delete_item.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
