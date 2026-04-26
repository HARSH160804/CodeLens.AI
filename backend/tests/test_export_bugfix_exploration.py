"""
Bug Condition Exploration Tests for Documentation Export Fixes

These tests are designed to FAIL on unfixed code to demonstrate the bugs exist.
They encode the expected behavior and will pass once the fixes are implemented.

CRITICAL: Do NOT modify these tests or the code when they fail initially.
The failures are expected and prove the bugs exist.
"""

import pytest
import asyncio
import base64
from unittest.mock import Mock, MagicMock, AsyncMock
import sys
import os

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from documentation.exporter import ExportService, NotFoundError, ConversionError


class TestBugConditionExploration:
    """
    Bug condition exploration tests.
    
    These tests demonstrate the bugs on unfixed code:
    1. PDF export fails due to missing weasyprint dependencies in Lambda
    2. Markdown export returns base64-encoded content instead of plain text
    """
    
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
    # Task 1.1: Test PDF export with weasyprint dependency failure
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_pdf_export_weasyprint_dependency_failure(self, exporter, mock_store):
        """
        Test that PDF export fails with weasyprint dependency error.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with ImportError or runtime
        error mentioning Cairo/Pango/weasyprint system dependencies.
        
        This failure proves the bug exists.
        
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES - PDF export succeeds using
        Lambda-compatible xhtml2pdf library.
        """
        repo_id = "test-repo-pdf-bug"
        content = """# Test Repository Documentation

## Overview
This is a test repository for PDF export.

## Architecture
- Component A
- Component B

## Code Example
```python
def test():
    return "test"
```
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'test-hash-123'
        }
        
        # Attempt PDF export - this should fail on unfixed code with weasyprint error
        # On fixed code, this should succeed with xhtml2pdf
        try:
            result = await exporter.export_pdf(repo_id)
            
            # If we get here, the fix is working
            assert result is not None, "PDF export should return bytes"
            assert isinstance(result, bytes), "PDF export should return bytes"
            assert len(result) > 0, "PDF should have content"
            
            # Verify it's actually PDF content (starts with PDF magic number)
            assert result.startswith(b'%PDF'), "Result should be valid PDF"
            
            print("✓ PDF export succeeded - bug is FIXED")
            
        except (ImportError, ConversionError, Exception) as e:
            error_msg = str(e).lower()
            
            # Check if it's the expected weasyprint dependency error
            if any(keyword in error_msg for keyword in ['cairo', 'pango', 'weasyprint', 'gdk']):
                pytest.fail(
                    f"EXPECTED FAILURE (Bug Confirmed): PDF export failed with weasyprint "
                    f"dependency error: {e}\n\n"
                    f"This proves the bug exists. The fix should replace weasyprint with "
                    f"xhtml2pdf to make this test pass."
                )
            else:
                # Unexpected error - re-raise
                raise
    
    # =========================================================================
    # Task 1.2: Test Markdown export returns base64-encoded content
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_markdown_export_base64_encoding_bug(self, exporter, mock_store):
        """
        Test that Markdown export returns plain text, not base64-encoded content.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS because the export returns
        base64-encoded content instead of plain text.
        
        This failure proves the bug exists.
        
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES - Markdown export returns
        plain text without base64 encoding.
        """
        repo_id = "test-repo-markdown-bug"
        markdown_content = """# My Repository Documentation

## Overview
This is a test with **bold** and *italic* text.

## Special Characters
- Unicode: café, naïve, 日本語
- Emoji: 🚀 ✨ 🎉
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': markdown_content,
            'content_hash': 'markdown-hash-123'
        }
        
        # Call the actual export function
        result = await exporter.export_markdown(repo_id)
        
        # Result should be bytes
        assert isinstance(result, bytes), "Export should return bytes"
        
        # Decode to string
        result_str = result.decode('utf-8')
        
        # Check if it's plain text or base64
        # Base64 of "# My" would start with "IyBN"
        if result_str.startswith('IyBN') or (not result_str.startswith('#')):
            # This is base64-encoded
            pytest.fail(
                f"EXPECTED FAILURE (Bug Confirmed): Markdown export returns base64-encoded "
                f"content instead of plain text.\n\n"
                f"Expected plain text starting with: '# My Repository Documentation'\n"
                f"Got content starting with: '{result_str[:50]}...'\n\n"
                f"The fix should return plain text with isBase64Encoded: False for Markdown."
            )
        else:
            # Plain text - bug is fixed
            assert result_str == markdown_content, "Should return plain markdown text"
            assert '# My Repository Documentation' in result_str, "Should have markdown header"
            print("✓ Markdown export returns plain text - bug is FIXED")
    
    # =========================================================================
    # Task 1.3: Test large documentation PDF export failure
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_large_documentation_pdf_export_failure(self, exporter, mock_store):
        """
        Test that PDF export fails for large documentation with same weasyprint error.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with same dependency error
        regardless of documentation size (confirms issue is dependency, not size-related).
        
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES - large PDF export succeeds.
        """
        repo_id = "test-repo-large-pdf"
        
        # Generate large markdown content (reduced for faster testing)
        large_content = "# Large Documentation\n\n"
        large_content += "## Section\n\n" * 100
        large_content += "Lorem ipsum dolor sit amet. " * 1000
        
        assert len(large_content.encode('utf-8')) > 25000, "Content should be >25KB"
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': large_content,
            'content_hash': 'large-hash-456'
        }
        
        try:
            result = await exporter.export_pdf(repo_id)
            
            # If we get here, the fix is working
            assert result is not None, "Large PDF export should return bytes"
            assert isinstance(result, bytes), "Large PDF export should return bytes"
            assert len(result) > 0, "Large PDF should have content"
            assert result.startswith(b'%PDF'), "Result should be valid PDF"
            
            print("✓ Large PDF export succeeded - bug is FIXED")
            
        except (ImportError, ConversionError, Exception) as e:
            error_msg = str(e).lower()
            
            if any(keyword in error_msg for keyword in ['cairo', 'pango', 'weasyprint', 'gdk']):
                pytest.fail(
                    f"EXPECTED FAILURE (Bug Confirmed): Large PDF export failed with same "
                    f"weasyprint dependency error: {e}\n\n"
                    f"This confirms the issue is dependency-related, not size-related."
                )
            else:
                raise
    
    # =========================================================================
    # Task 1.4: Test special characters in Markdown export
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_special_characters_markdown_export_base64_bug(self, exporter, mock_store):
        """
        Test that Markdown export with unicode and special characters returns
        plain text, not base64-encoded content.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS showing base64 encoding
        obscures all content including unicode characters.
        
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES - unicode characters are
        preserved in plain text export.
        """
        repo_id = "test-repo-unicode"
        markdown_with_unicode = """# Documentation with Special Characters

## Unicode Examples
- Café ☕
- Naïve approach
- Japanese: 日本語
- Emoji: 🚀 ✨ 🎉 💻
- Math: ∑ ∫ ∂ √
- Arrows: → ← ↑ ↓

## Code with Unicode
```python
def greet():
    return "Hello, 世界! 🌍"
```
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': markdown_with_unicode,
            'content_hash': 'unicode-hash-456'
        }
        
        # Call the actual export function
        result = await exporter.export_markdown(repo_id)
        
        # Result should be bytes
        assert isinstance(result, bytes), "Export should return bytes"
        
        # Decode to string
        result_str = result.decode('utf-8')
        
        # Check if content is base64-encoded or plain text
        if not result_str.startswith('# Documentation'):
            # Content is base64-encoded, not plain text
            pytest.fail(
                f"EXPECTED FAILURE (Bug Confirmed): Markdown with unicode characters "
                f"returns base64-encoded content.\n\n"
                f"Expected plain text starting with: '# Documentation with Special Characters'\n"
                f"Got content starting with: '{result_str[:50]}...'\n\n"
                f"Unicode characters like ☕, 🚀, 日本語 are obscured by base64 encoding.\n"
                f"The fix should return plain text to preserve these characters."
            )
        else:
            # Plain text - bug is fixed
            assert '☕' in result_str, "Should preserve emoji"
            assert '日本語' in result_str, "Should preserve Japanese characters"
            assert '🚀' in result_str, "Should preserve emoji"
            assert result_str == markdown_with_unicode, "Should match original content"
            print("✓ Unicode characters preserved in plain text - bug is FIXED")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
