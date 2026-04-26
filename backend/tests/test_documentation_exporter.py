"""
Unit tests for ExportService class.

Tests markdown and PDF export functionality with caching.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import sys
import os

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from documentation.exporter import ExportService, NotFoundError, ConversionError


class TestExportService:
    """Test suite for ExportService."""
    
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
    
    @staticmethod
    def _get_sample_markdown():
        """Get sample markdown content."""
        return """# Repository Documentation

## Overview
This is a test repository.

## Architecture Patterns
- MVC Pattern (85% confidence)

## Technology Stack
- Python 3.9
- Flask 2.0

## Code Example
```python
def hello():
    return "Hello, World!"
```

## Table Example
| Metric | Value |
|--------|-------|
| Health | 75.5  |
| Complexity | 3.2 |
"""
    
    @pytest.mark.asyncio
    async def test_export_markdown_success(self, exporter, mock_store):
        """Test successful markdown export."""
        repo_id = "test-repo-123"
        content = self._get_sample_markdown()
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'abc123'
        }
        
        result = await exporter.export_markdown(repo_id)
        
        assert result is not None
        assert isinstance(result, bytes)
        assert result.decode('utf-8') == content
        mock_store.get.assert_called_once_with(repo_id)
    
    @pytest.mark.asyncio
    async def test_export_markdown_not_found(self, exporter, mock_store):
        """Test markdown export when documentation doesn't exist."""
        mock_store.get.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            await exporter.export_markdown("non-existent-repo")
        
        assert 'not found' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_export_markdown_no_content(self, exporter, mock_store):
        """Test markdown export when record has no content."""
        mock_store.get.return_value = {'repo_id': 'test', 'content_hash': 'abc'}
        
        with pytest.raises(NotFoundError):
            await exporter.export_markdown("test-repo")
    
    def test_markdown_to_html_basic(self, exporter):
        """Test markdown to HTML conversion."""
        markdown = "# Test\n\nThis is a **test**."
        
        html = exporter._markdown_to_html(markdown)
        
        assert html is not None
        assert '<h1>Test</h1>' in html or '<h1 id="test">Test</h1>' in html
        assert '<strong>test</strong>' in html or '<b>test</b>' in html
        assert '<style>' in html  # CSS should be included
    
    def test_markdown_to_html_with_code_blocks(self, exporter):
        """Test markdown to HTML with code blocks."""
        markdown = """# Code Example

```python
def hello():
    return "Hello"
```
"""
        
        html = exporter._markdown_to_html(markdown)
        
        assert '<pre>' in html or '<code>' in html
        # The code might be wrapped in HTML entities or spans
        assert 'hello' in html.lower()
    
    def test_markdown_to_html_with_tables(self, exporter):
        """Test markdown to HTML with tables."""
        markdown = """# Table

| Name | Value |
|------|-------|
| Test | 123   |
"""
        
        html = exporter._markdown_to_html(markdown)
        
        assert '<table>' in html
        assert '<th>' in html or '<td>' in html
    
    @patch('documentation.exporter.SimpleDocTemplate')
    @patch('documentation.exporter.Paragraph')
    def test_html_to_pdf_success(self, mock_paragraph, mock_doc_template, exporter):
        """Test HTML to PDF conversion with reportlab."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        pdf_bytes = b'%PDF-1.4 fake pdf content'
        
        # Mock reportlab components
        mock_doc_instance = MagicMock()
        mock_doc_template.return_value = mock_doc_instance
        
        # Mock the build method to write PDF bytes
        def build_mock(story):
            # Simulate PDF generation
            pass
        
        mock_doc_instance.build.side_effect = build_mock
        
        # We need to mock BytesIO to return our fake PDF
        with patch('documentation.exporter.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = pdf_bytes
            mock_bytesio.return_value = mock_buffer
            
            result = exporter._html_to_pdf(html_content)
            
            assert result is not None
            assert isinstance(result, bytes)
            assert result == pdf_bytes
    
    @patch('documentation.exporter.SimpleDocTemplate')
    def test_html_to_pdf_error(self, mock_doc_template, exporter):
        """Test HTML to PDF conversion error with reportlab."""
        # Mock SimpleDocTemplate to raise an exception
        mock_doc_template.side_effect = Exception("PDF generation failed")
        
        with pytest.raises(ConversionError) as exc_info:
            exporter._html_to_pdf("<html></html>")
        
        assert 'failed to convert' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @patch('documentation.exporter.SimpleDocTemplate')
    async def test_export_pdf_success(self, mock_doc_template, exporter, mock_store):
        """Test successful PDF export with reportlab."""
        repo_id = "test-repo-pdf"
        content = self._get_sample_markdown()
        pdf_bytes = b'%PDF-1.4 fake pdf'
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'def456'
        }
        
        # Mock reportlab components
        mock_doc_instance = MagicMock()
        mock_doc_template.return_value = mock_doc_instance
        
        with patch('documentation.exporter.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = pdf_bytes
            mock_bytesio.return_value = mock_buffer
            
            result = await exporter.export_pdf(repo_id)
            
            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_export_pdf_not_found(self, exporter, mock_store):
        """Test PDF export when documentation doesn't exist."""
        mock_store.get.return_value = None
        
        with pytest.raises(NotFoundError):
            await exporter.export_pdf("non-existent-repo")
    
    @pytest.mark.asyncio
    @patch('documentation.exporter.SimpleDocTemplate')
    async def test_pdf_caching(self, mock_doc_template, exporter, mock_store):
        """Test PDF caching functionality with reportlab."""
        repo_id = "test-repo-cache"
        content = "# Test Doc"
        content_hash = "cache123"
        pdf_bytes = b'%PDF-1.4 cached pdf'
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': content_hash
        }
        
        # Mock reportlab components
        mock_doc_instance = MagicMock()
        mock_doc_template.return_value = mock_doc_instance
        
        with patch('documentation.exporter.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = pdf_bytes
            mock_bytesio.return_value = mock_buffer
            
            # First export - should generate PDF
            result1 = await exporter.export_pdf(repo_id)
            assert mock_doc_template.call_count == 1
            
            # Second export - should use cache
            result2 = await exporter.export_pdf(repo_id)
            assert mock_doc_template.call_count == 1  # Should not call again
            
            # Results should be identical
            assert result1 == result2
    
    def test_get_cached_pdf_hit(self, exporter):
        """Test cache hit."""
        repo_id = "test-repo"
        content_hash = "hash123"
        pdf_bytes = b'cached pdf'
        
        # Manually add to cache
        exporter._cache_pdf(repo_id, content_hash, pdf_bytes)
        
        # Retrieve from cache
        cached = exporter._get_cached_pdf(repo_id, content_hash)
        
        assert cached == pdf_bytes
    
    def test_get_cached_pdf_miss(self, exporter):
        """Test cache miss."""
        cached = exporter._get_cached_pdf("non-cached-repo", "hash")
        
        assert cached is None
    
    def test_get_cached_pdf_expired(self, exporter):
        """Test expired cache entry."""
        repo_id = "test-repo"
        content_hash = "hash456"
        pdf_bytes = b'old pdf'
        
        # Add to cache with old timestamp
        cache_key = f"{repo_id}:{content_hash}"
        old_timestamp = datetime.utcnow() - timedelta(hours=2)
        exporter._pdf_cache[cache_key] = (pdf_bytes, old_timestamp)
        
        # Should return None for expired cache
        cached = exporter._get_cached_pdf(repo_id, content_hash)
        
        assert cached is None
        # Cache entry should be removed
        assert cache_key not in exporter._pdf_cache
    
    def test_cache_pdf(self, exporter):
        """Test caching PDF."""
        repo_id = "test-repo"
        content_hash = "hash789"
        pdf_bytes = b'new pdf'
        
        exporter._cache_pdf(repo_id, content_hash, pdf_bytes)
        
        cache_key = f"{repo_id}:{content_hash}"
        assert cache_key in exporter._pdf_cache
        cached_pdf, timestamp = exporter._pdf_cache[cache_key]
        assert cached_pdf == pdf_bytes
        assert isinstance(timestamp, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
