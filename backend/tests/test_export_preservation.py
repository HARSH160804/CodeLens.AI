"""
Preservation Property Tests for Documentation Export Fixes

These tests verify that non-export operations continue to work exactly as before.
They should PASS on both unfixed and fixed code to ensure no regressions.

IMPORTANT: Run these tests on UNFIXED code first to establish baseline behavior.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock
import sys
import os

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from documentation.store import DocumentationStore
from documentation.exporter import ExportService


class TestPreservation:
    """
    Preservation property tests.
    
    These tests verify that the bugfix does NOT affect:
    1. Documentation generation
    2. Documentation storage and retrieval
    3. API validation
    4. Markdown-to-HTML conversion
    """
    
    @pytest.fixture
    def mock_dynamodb(self):
        """Mock DynamoDB resource."""
        dynamodb = MagicMock()
        table = MagicMock()
        dynamodb.Table.return_value = table
        return dynamodb, table
    
    @pytest.fixture
    def mock_store(self):
        """Mock DocumentationStore."""
        store = MagicMock()
        store.get = AsyncMock()
        return store
    
    @pytest.fixture
    def exporter(self, mock_store):
        """Create ExportService with mocked store."""
        return ExportService(mock_store)
    
    # =========================================================================
    # Task 2.1: Test documentation generation preservation
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_documentation_storage_and_retrieval_preservation(self, mock_dynamodb):
        """
        Test that documentation storage and retrieval work identically.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        This confirms that storage/retrieval operations are not affected by the fix.
        """
        dynamodb, table = mock_dynamodb
        
        # Mock boto3.resource to return our mock
        import boto3
        original_resource = boto3.resource
        boto3.resource = lambda *args, **kwargs: dynamodb
        
        try:
            store = DocumentationStore()
            
            # Test data
            repo_id = "test-repo-preservation"
            content = "# Test Documentation\n\nThis is test content."
            
            # Mock successful storage
            table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
            
            # Mock successful retrieval
            table.get_item.return_value = {
                'Item': {
                    'repo_id': repo_id,
                    'content': content,
                    'state': 'generated',
                    'content_hash': 'test-hash',
                    'created_at': '2024-01-01T00:00:00Z'
                }
            }
            
            # Store documentation
            await store.save(repo_id, content)
            
            # Retrieve documentation
            result = await store.get(repo_id)
            
            # Verify storage and retrieval work correctly
            assert result is not None, "Should retrieve stored documentation"
            assert result['repo_id'] == repo_id, "Should return correct repo_id"
            assert result['content'] == content, "Should return exact same content"
            assert result['state'] == 'generated', "Should return correct state"
            
            # Verify DynamoDB operations were called
            table.put_item.assert_called_once()
            table.get_item.assert_called_once()
            
            print("✓ Documentation storage and retrieval preserved")
        finally:
            # Restore original boto3.resource
            boto3.resource = original_resource
    
    # =========================================================================
    # Task 2.2: Test documentation storage and retrieval preservation
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_state_management_preservation(self, mock_dynamodb):
        """
        Test that state management operations work identically.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        """
        dynamodb, table = mock_dynamodb
        
        # Mock boto3.resource to return our mock
        import boto3
        original_resource = boto3.resource
        boto3.resource = lambda *args, **kwargs: dynamodb
        
        try:
            store = DocumentationStore()
            
            repo_id = "test-repo-state"
            
            # Mock state retrieval - returns 'not_generated' by default
            table.get_item.return_value = {}
            
            # Get state (should return 'not_generated' when no item exists)
            state = await store.get_state(repo_id)
            
            # Verify state retrieval works
            assert state == 'not_generated', "Should return 'not_generated' for non-existent repo"
            
            # Now mock an existing item with 'generating' state
            table.get_item.return_value = {
                'Item': {
                    'repo_id': repo_id,
                    'generation_state': 'generating',
                    'created_at': '2024-01-01T00:00:00Z'
                }
            }
            
            # Get state again
            state = await store.get_state(repo_id)
            
            # Verify state retrieval works
            assert state == 'generating', "Should return correct state"
            
            # Mock state update (for 'generating' state, it uses put_item)
            table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
            
            # Update state to 'generating'
            await store.update_state(repo_id, 'generating')
            
            # Verify put_item was called (for 'generating' state)
            assert table.put_item.call_count >= 1, "Should call put_item for 'generating' state"
            
            print("✓ State management preserved")
        finally:
            # Restore original boto3.resource
            boto3.resource = original_resource
    
    # =========================================================================
    # Task 2.3: Test API validation preservation
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_api_validation_preservation(self, exporter, mock_store):
        """
        Test that API validation returns same error responses.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        """
        from documentation.exporter import NotFoundError
        
        # Test 1: Missing documentation returns NotFoundError
        mock_store.get.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            await exporter.export_markdown("non-existent-repo")
        
        assert 'not found' in str(exc_info.value).lower(), "Should return 'not found' error"
        
        # Test 2: Documentation without content returns NotFoundError
        mock_store.get.return_value = {'repo_id': 'test', 'state': 'generated'}
        
        with pytest.raises(NotFoundError):
            await exporter.export_markdown("test-repo")
        
        print("✓ API validation preserved")
    
    # =========================================================================
    # Task 2.4: Test markdown-to-HTML conversion preservation
    # =========================================================================
    
    def test_markdown_to_html_conversion_preservation(self, exporter):
        """
        Test that markdown-to-HTML conversion produces same structure.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        This is important because HTML conversion is used for future HTML export.
        """
        # Test basic markdown
        markdown = "# Test Heading\n\nThis is **bold** text."
        html = exporter._markdown_to_html(markdown)
        
        assert html is not None, "Should return HTML"
        assert '<h1' in html, "Should contain h1 tag"
        assert '<strong>' in html or '<b>' in html, "Should contain bold tag"
        assert '<style>' in html, "Should include CSS styling"
        
        # Test code blocks
        markdown_with_code = """# Code Example

```python
def hello():
    return "world"
```
"""
        html_with_code = exporter._markdown_to_html(markdown_with_code)
        
        assert '<pre>' in html_with_code or '<code>' in html_with_code, "Should contain code tags"
        # Code content is preserved, just with HTML tags around it
        assert 'hello' in html_with_code and 'return' in html_with_code, "Should preserve code content"
        
        # Test tables
        markdown_with_table = """# Table

| Name | Value |
|------|-------|
| Test | 123   |
"""
        html_with_table = exporter._markdown_to_html(markdown_with_table)
        
        assert '<table>' in html_with_table, "Should contain table tag"
        assert '<th>' in html_with_table or '<td>' in html_with_table, "Should contain table cells"
        
        # Test that HTML structure is consistent
        assert '<!DOCTYPE html>' in html, "Should be complete HTML document"
        assert '<html>' in html, "Should have html tag"
        assert '<body>' in html, "Should have body tag"
        
        print("✓ Markdown-to-HTML conversion preserved")
    
    def test_html_css_styling_preservation(self, exporter):
        """
        Test that HTML CSS styling remains unchanged.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        """
        markdown = "# Test"
        html = exporter._markdown_to_html(markdown)
        
        # Verify CSS includes expected styling
        assert 'font-family' in html, "Should include font-family styling"
        assert 'font-size' in html, "Should include font-size styling"
        assert '@page' in html, "Should include page styling for PDF"
        assert 'margin' in html, "Should include margin styling"
        
        # Verify styling for different elements
        assert 'h1 {' in html or 'h1{' in html, "Should style h1 elements"
        assert 'code {' in html or 'code{' in html, "Should style code elements"
        assert 'table {' in html or 'table{' in html, "Should style table elements"
        
        print("✓ HTML CSS styling preserved")
    
    @pytest.mark.asyncio
    async def test_cache_mechanism_preservation(self, exporter):
        """
        Test that PDF caching mechanism works identically.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        """
        repo_id = "test-repo-cache"
        content_hash = "cache-hash-123"
        pdf_bytes = b'%PDF-1.4 test pdf content'
        
        # Test cache miss
        cached = exporter._get_cached_pdf(repo_id, content_hash)
        assert cached is None, "Should return None for cache miss"
        
        # Test cache set
        exporter._cache_pdf(repo_id, content_hash, pdf_bytes)
        
        # Test cache hit
        cached = exporter._get_cached_pdf(repo_id, content_hash)
        assert cached == pdf_bytes, "Should return cached PDF"
        
        # Test cache with different hash (miss)
        cached_different = exporter._get_cached_pdf(repo_id, "different-hash")
        assert cached_different is None, "Should return None for different hash"
        
        print("✓ Cache mechanism preserved")
    
    def test_error_handling_preservation(self, exporter):
        """
        Test that error handling works identically.
        
        EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
        """
        from documentation.exporter import ConversionError
        
        # Test markdown-to-HTML error handling
        # Pass invalid input that should raise ConversionError
        try:
            # This should work fine - markdown library is forgiving
            result = exporter._markdown_to_html("")
            assert result is not None, "Should handle empty markdown"
        except ConversionError:
            # If it raises ConversionError, that's also acceptable
            pass
        
        print("✓ Error handling preserved")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
