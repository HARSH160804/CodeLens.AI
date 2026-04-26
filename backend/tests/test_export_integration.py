"""
Integration Tests for Documentation Export Fixes

These tests verify the complete end-to-end export workflows:
- Full PDF export flow with various documentation sizes
- Full Markdown export flow with various content types
- Format switching between PDF and Markdown
- Concurrent exports from multiple repositories
- Export after documentation regeneration (cache invalidation)

All tests use real implementations with mocked storage.
"""

import pytest
import asyncio
import base64
import tempfile
import os
from unittest.mock import Mock, MagicMock, AsyncMock
from io import BytesIO
import sys

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from documentation.exporter import ExportService, NotFoundError, ConversionError
from documentation.store import DocumentationStore


class TestExportIntegration:
    """
    Integration tests for documentation export functionality.
    
    Tests the complete export workflows after bugfix implementation.
    """
    
    @pytest.fixture
    def mock_store(self):
        """Mock DocumentationStore with realistic data."""
        store = MagicMock()
        store.get = AsyncMock()
        return store
    
    @pytest.fixture
    def exporter(self, mock_store):
        """Create ExportService with mocked store."""
        return ExportService(mock_store)

    
    # =========================================================================
    # Task 4.1: Test full PDF export flow
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_full_pdf_export_flow_small_documentation(self, exporter, mock_store):
        """
        Test complete PDF export flow with small documentation.
        
        Validates: Requirements 2.1, 2.2
        """
        repo_id = "test-repo-small-pdf"
        small_content = """# Small Repository Documentation

## Overview
This is a small test repository with minimal content.

## Features
- Feature A: Basic functionality
- Feature B: Simple operations

## Code Example
```python
def hello():
    return "world"
```

## Conclusion
This is a small documentation example.
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': small_content,
            'content_hash': 'small-hash-123',
            'state': 'generated'
        }
        
        # Export as PDF
        pdf_bytes = await exporter.export_pdf(repo_id)
        
        # Verify PDF is valid
        assert pdf_bytes is not None, "PDF export should return bytes"
        assert isinstance(pdf_bytes, bytes), "PDF should be bytes"
        assert len(pdf_bytes) > 0, "PDF should have content"
        
        # Verify PDF magic number (starts with %PDF)
        assert pdf_bytes.startswith(b'%PDF'), "Should be valid PDF file"
        
        # Verify PDF can be "opened" (basic validation)
        # Try to write to temp file and verify it's readable
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            # Verify file exists and has content
            assert os.path.exists(tmp_path), "PDF file should be created"
            assert os.path.getsize(tmp_path) > 0, "PDF file should have content"
            
            # Verify it's a valid PDF by checking structure
            with open(tmp_path, 'rb') as f:
                content = f.read()
                assert b'%PDF' in content, "Should contain PDF header"
                assert b'%%EOF' in content or b'endobj' in content, "Should contain PDF structure"
        finally:
            os.unlink(tmp_path)
        
        print(f"✓ Small PDF export succeeded ({len(pdf_bytes)} bytes)")

    
    @pytest.mark.asyncio
    async def test_full_pdf_export_flow_medium_documentation(self, exporter, mock_store):
        """
        Test complete PDF export flow with medium-sized documentation.
        
        Validates: Requirements 2.1, 2.2
        """
        repo_id = "test-repo-medium-pdf"
        
        # Generate medium-sized content (reduced for faster testing)
        medium_content = "# Medium Repository Documentation\n\n"
        medium_content += "## Overview\n\nThis is a medium-sized repository.\n\n"
        
        for i in range(5):
            medium_content += f"## Section {i+1}\n\n"
            medium_content += f"This section covers topic {i+1}.\n\n"
            medium_content += "### Subsection A\n\n"
            medium_content += "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5
            medium_content += "\n\n### Subsection B\n\n"
            medium_content += "```python\n"
            medium_content += f"def function_{i}():\n"
            medium_content += f"    return 'result_{i}'\n"
            medium_content += "```\n\n"
        
        assert len(medium_content.encode('utf-8')) > 2000, "Should be >2KB"
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': medium_content,
            'content_hash': 'medium-hash-456',
            'state': 'generated'
        }
        
        # Export as PDF
        pdf_bytes = await exporter.export_pdf(repo_id)
        
        # Verify PDF is valid
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
        
        # Verify PDF contains expected content
        # Note: PDF content is compressed, so we just verify it's a valid PDF with content
        # The fact that it generated successfully and has substantial size is sufficient
        assert len(pdf_bytes) > 1000, "Medium PDF should have substantial content"
        
        print(f"✓ Medium PDF export succeeded ({len(pdf_bytes)} bytes)")

    
    @pytest.mark.asyncio
    async def test_full_pdf_export_flow_large_documentation(self, exporter, mock_store):
        """
        Test complete PDF export flow with large documentation.
        
        Validates: Requirements 2.1, 2.2
        """
        repo_id = "test-repo-large-pdf"
        
        # Generate large content (reduced for faster testing)
        large_content = "# Large Repository Documentation\n\n"
        large_content += "## Table of Contents\n\n"
        
        for i in range(10):
            large_content += f"{i+1}. Section {i+1}\n"
        
        large_content += "\n"
        
        for i in range(10):
            large_content += f"## Section {i+1}: Component Analysis\n\n"
            large_content += f"### Overview of Component {i+1}\n\n"
            large_content += "This component handles critical functionality. " * 10
            large_content += "\n\n### Architecture\n\n"
            large_content += "```python\n"
            large_content += f"class Component{i}:\n"
            large_content += f"    def __init__(self):\n"
            large_content += f"        self.name = 'Component{i}'\n"
            large_content += f"    \n"
            large_content += f"    def process(self, data):\n"
            large_content += f"        return data.transform()\n"
            large_content += "```\n\n"
            large_content += "### Dependencies\n\n"
            large_content += "- Dependency A\n- Dependency B\n- Dependency C\n\n"
        
        content_size = len(large_content.encode('utf-8'))
        assert content_size > 5000, f"Should be >5KB, got {content_size}"
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': large_content,
            'content_hash': 'large-hash-789',
            'state': 'generated'
        }
        
        # Export as PDF
        pdf_bytes = await exporter.export_pdf(repo_id)
        
        # Verify PDF is valid
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
        
        # Verify PDF has substantial content
        assert len(pdf_bytes) > 1000, "Large documentation should produce substantial PDF"
        
        print(f"✓ Large PDF export succeeded ({len(pdf_bytes)} bytes from {content_size} bytes markdown)")

    
    # =========================================================================
    # Task 4.2: Test full Markdown export flow
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_full_markdown_export_flow_plain_text(self, exporter, mock_store):
        """
        Test complete Markdown export flow returns plain text.
        
        Validates: Requirements 2.3, 2.4
        """
        repo_id = "test-repo-markdown-plain"
        markdown_content = """# Repository Documentation

## Overview
This is a test repository with standard markdown content.

## Features
- Feature A
- Feature B
- Feature C

## Code Example
```python
def example():
    return "test"
```
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': markdown_content,
            'content_hash': 'md-hash-123',
            'state': 'generated'
        }
        
        # Export as Markdown
        md_bytes = await exporter.export_markdown(repo_id)
        
        # Verify it's bytes
        assert md_bytes is not None
        assert isinstance(md_bytes, bytes)
        
        # Decode to text
        md_text = md_bytes.decode('utf-8')
        
        # Verify it's plain text markdown, NOT base64
        assert md_text.startswith('# Repository Documentation'), \
            "Should start with markdown header, not base64"
        assert '## Overview' in md_text, "Should contain markdown headers"
        assert 'Feature A' in md_text, "Should contain list items"
        assert '```python' in md_text, "Should contain code blocks"
        
        # Verify it's NOT base64 encoded
        assert not md_text.startswith('IyB'), "Should NOT be base64 (IyB is base64 for '# ')"
        assert '==' not in md_text[-10:], "Should NOT have base64 padding"
        
        # Verify file can be opened in text editor (is valid UTF-8)
        try:
            md_text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            pytest.fail("Markdown should be valid UTF-8 text")
        
        print(f"✓ Markdown export returns plain text ({len(md_bytes)} bytes)")

    
    @pytest.mark.asyncio
    async def test_full_markdown_export_flow_unicode_characters(self, exporter, mock_store):
        """
        Test Markdown export with unicode characters.
        
        Validates: Requirements 2.3, 2.4
        """
        repo_id = "test-repo-markdown-unicode"
        markdown_with_unicode = """# Documentation with Unicode ✨

## International Content
- Café ☕
- Naïve approach
- Japanese: 日本語 🇯🇵
- Chinese: 中文 🇨🇳
- Arabic: العربية
- Emoji: 🚀 💻 🎉 ✅

## Math Symbols
- Sum: ∑
- Integral: ∫
- Partial: ∂
- Square root: √
- Infinity: ∞

## Arrows and Symbols
→ ← ↑ ↓ ⇒ ⇐ ⇑ ⇓
★ ☆ ♠ ♣ ♥ ♦

## Code with Unicode
```python
def greet():
    return "Hello, 世界! 🌍"
```
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': markdown_with_unicode,
            'content_hash': 'md-unicode-456',
            'state': 'generated'
        }
        
        # Export as Markdown
        md_bytes = await exporter.export_markdown(repo_id)
        md_text = md_bytes.decode('utf-8')
        
        # Verify unicode characters are preserved
        assert '✨' in md_text, "Should preserve emoji"
        assert '☕' in md_text, "Should preserve coffee emoji"
        assert '日本語' in md_text, "Should preserve Japanese characters"
        assert '中文' in md_text, "Should preserve Chinese characters"
        assert 'العربية' in md_text, "Should preserve Arabic characters"
        assert '🚀' in md_text, "Should preserve rocket emoji"
        assert '∑' in md_text, "Should preserve math symbols"
        assert '→' in md_text, "Should preserve arrows"
        
        # Verify it's NOT base64 encoded
        assert not md_text.startswith('IyB'), "Should NOT be base64"
        
        print(f"✓ Unicode characters preserved in Markdown export")

    
    @pytest.mark.asyncio
    async def test_full_markdown_export_flow_special_characters(self, exporter, mock_store):
        """
        Test Markdown export with special characters and code blocks.
        
        Validates: Requirements 2.3, 2.4
        """
        repo_id = "test-repo-markdown-special"
        markdown_with_special = """# Special Characters Test

## HTML-like Content
- Tags: <div>, <span>, <script>
- Entities: &nbsp; &lt; &gt; &amp;

## Code Blocks with Special Chars
```javascript
const regex = /[<>'"&]/g;
const html = '<div class="test">Hello & goodbye</div>';
const escaped = html.replace(regex, (m) => {
    return {'<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '&': '&amp;'}[m];
});
```

## Markdown Special Characters
- Asterisks: * ** ***
- Underscores: _ __ ___
- Backticks: ` `` ```
- Brackets: [ ] ( )
- Pipes: | || |||

## Quotes and Apostrophes
"Double quotes" and 'single quotes'
It's a test with apostrophes

## Backslashes
Path: C:\\Users\\Test\\file.txt
Escape: \\n \\t \\r
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': markdown_with_special,
            'content_hash': 'md-special-789',
            'state': 'generated'
        }
        
        # Export as Markdown
        md_bytes = await exporter.export_markdown(repo_id)
        md_text = md_bytes.decode('utf-8')
        
        # Verify special characters are preserved
        assert '<div>' in md_text, "Should preserve HTML-like tags"
        assert '&nbsp;' in md_text, "Should preserve HTML entities"
        assert '/[<>\'"&]/g' in md_text, "Should preserve regex patterns"
        assert 'C:\\Users\\Test' in md_text or 'C:\\\\Users\\\\Test' in md_text, \
            "Should preserve backslashes"
        assert '"Double quotes"' in md_text, "Should preserve quotes"
        assert "It's" in md_text, "Should preserve apostrophes"
        
        # Verify it's plain text, not base64
        assert md_text.startswith('# Special Characters Test'), \
            "Should start with markdown header"
        
        print(f"✓ Special characters preserved in Markdown export")

    
    # =========================================================================
    # Task 4.3: Test format switching
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_format_switching_same_documentation(self, exporter, mock_store):
        """
        Test exporting same documentation as both PDF and Markdown.
        
        Validates: Requirements 2.1, 2.2, 2.3, 2.4
        """
        repo_id = "test-repo-format-switch"
        content = """# Multi-Format Documentation

## Overview
This documentation will be exported in both PDF and Markdown formats.

## Section 1: Introduction
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 2: Code Example
```python
def multi_format():
    return "works in both formats"
```

## Section 3: Lists
- Item A
- Item B
- Item C

## Section 4: Tables
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

## Conclusion
Both formats should work correctly.
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'switch-hash-123',
            'state': 'generated'
        }
        
        # Export as Markdown first
        md_bytes = await exporter.export_markdown(repo_id)
        md_text = md_bytes.decode('utf-8')
        
        # Verify Markdown export succeeded
        assert md_text.startswith('# Multi-Format Documentation')
        assert 'Section 1: Introduction' in md_text
        assert '```python' in md_text
        assert 'Item A' in md_text
        
        # Export same documentation as PDF
        pdf_bytes = await exporter.export_pdf(repo_id)
        
        # Verify PDF export succeeded
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 0
        
        # Verify content consistency between formats
        # Markdown should contain the main content in plain text
        assert 'Multi-Format' in md_text, "Markdown should contain title"
        assert 'Introduction' in md_text, "Markdown should contain section headers"
        
        # PDF should be valid and have substantial content
        # (PDF content is compressed, so we can't easily verify text)
        assert len(pdf_bytes) > 1000, "PDF should have substantial content"
        
        print(f"✓ Format switching succeeded: MD={len(md_bytes)} bytes, PDF={len(pdf_bytes)} bytes")

    
    @pytest.mark.asyncio
    async def test_format_switching_multiple_times(self, exporter, mock_store):
        """
        Test switching between formats multiple times.
        
        Validates: Requirements 2.1, 2.2, 2.3, 2.4
        """
        repo_id = "test-repo-multi-switch"
        content = "# Test\n\nContent for multiple format switches."
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'multi-switch-456',
            'state': 'generated'
        }
        
        # Switch between formats multiple times
        for i in range(3):
            # Export as PDF
            pdf_bytes = await exporter.export_pdf(repo_id)
            assert pdf_bytes.startswith(b'%PDF'), f"PDF export {i+1} failed"
            
            # Export as Markdown
            md_bytes = await exporter.export_markdown(repo_id)
            md_text = md_bytes.decode('utf-8')
            assert md_text.startswith('# Test'), f"Markdown export {i+1} failed"
        
        print(f"✓ Multiple format switches succeeded (3 iterations)")

    
    # =========================================================================
    # Task 4.4: Test concurrent exports
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_concurrent_exports_different_repositories(self, mock_store):
        """
        Test multiple users exporting different repositories simultaneously.
        
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.3
        """
        # Create multiple exporters (reduced for faster testing)
        exporters = [ExportService(mock_store) for _ in range(3)]
        
        # Prepare different repository data
        repos = []
        for i in range(3):
            repo_id = f"concurrent-repo-{i}"
            content = f"# Repository {i}\n\n## Content\nThis is repository {i} documentation.\n\n" + \
                     f"Content specific to repo {i}. " * 5
            repos.append({
                'repo_id': repo_id,
                'content': content,
                'content_hash': f'concurrent-hash-{i}'
            })
        
        # Mock store to return appropriate data based on repo_id
        async def mock_get(repo_id):
            for repo in repos:
                if repo['repo_id'] == repo_id:
                    return repo
            return None
        
        mock_store.get = mock_get
        
        # Create concurrent export tasks
        tasks = []
        
        # Mix of PDF and Markdown exports
        for i, exporter in enumerate(exporters):
            repo_id = f"concurrent-repo-{i}"
            if i % 2 == 0:
                # PDF export
                tasks.append(exporter.export_pdf(repo_id))
            else:
                # Markdown export
                tasks.append(exporter.export_markdown(repo_id))
        
        # Execute all exports concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all exports succeeded
        assert len(results) == 3, "Should have 3 results"
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Export {i} failed: {result}"
            assert isinstance(result, bytes), f"Export {i} should return bytes"
            assert len(result) > 0, f"Export {i} should have content"
            
            # Verify correct format
            if i % 2 == 0:
                # PDF
                assert result.startswith(b'%PDF'), f"Export {i} should be PDF"
            else:
                # Markdown
                text = result.decode('utf-8')
                assert text.startswith(f'# Repository {i}'), \
                    f"Export {i} should be Markdown for repo {i}"
        
        print(f"✓ Concurrent exports succeeded (3 simultaneous exports)")

    
    @pytest.mark.asyncio
    async def test_concurrent_exports_same_repository(self, mock_store):
        """
        Test multiple concurrent exports of the same repository.
        
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.3
        """
        # Create multiple exporters (reduced for faster testing)
        exporters = [ExportService(mock_store) for _ in range(5)]
        
        repo_id = "concurrent-same-repo"
        content = "# Shared Repository\n\n## Content\nThis repository is accessed concurrently.\n\n" + \
                 "Shared content. " * 10
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': 'shared-hash-123'
        }
        
        # Create concurrent export tasks (mix of PDF and Markdown)
        tasks = []
        for i, exporter in enumerate(exporters):
            if i % 3 == 0:
                tasks.append(exporter.export_pdf(repo_id))
            else:
                tasks.append(exporter.export_markdown(repo_id))
        
        # Execute all exports concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all exports succeeded
        assert len(results) == 5, "Should have 5 results"
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent export {i} failed: {result}"
            assert isinstance(result, bytes), f"Export {i} should return bytes"
            assert len(result) > 0, f"Export {i} should have content"
        
        # Verify no interference - all PDF exports should be identical
        pdf_results = [results[i] for i in range(len(results)) if i % 3 == 0]
        if len(pdf_results) > 1:
            first_pdf = pdf_results[0]
            for pdf in pdf_results[1:]:
                assert pdf == first_pdf, "All PDF exports of same repo should be identical"
        
        # Verify all Markdown exports are identical
        md_results = [results[i] for i in range(len(results)) if i % 3 != 0]
        if len(md_results) > 1:
            first_md = md_results[0]
            for md in md_results[1:]:
                assert md == first_md, "All Markdown exports of same repo should be identical"
        
        print(f"✓ Concurrent exports of same repository succeeded (5 simultaneous exports)")

    
    # =========================================================================
    # Task 4.5: Test export after documentation regeneration
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_export_after_documentation_regeneration(self, exporter, mock_store):
        """
        Test cache invalidation when documentation is regenerated.
        
        Validates: Requirements 2.1, 2.2, 3.1
        """
        repo_id = "test-repo-regeneration"
        
        # Initial documentation
        initial_content = """# Initial Documentation

## Version 1
This is the first version of the documentation.

## Features
- Feature A (v1)
- Feature B (v1)
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': initial_content,
            'content_hash': 'initial-hash-v1',
            'state': 'generated'
        }
        
        # First export - should generate and cache PDF
        pdf_v1 = await exporter.export_pdf(repo_id)
        
        assert pdf_v1.startswith(b'%PDF')
        pdf_v1_text = pdf_v1.decode('latin-1', errors='ignore')
        
        # Verify cache was populated
        cached_pdf = exporter._get_cached_pdf(repo_id, 'initial-hash-v1')
        assert cached_pdf is not None, "PDF should be cached"
        assert cached_pdf == pdf_v1, "Cached PDF should match original"
        
        # Second export with same content - should use cache
        pdf_v1_cached = await exporter.export_pdf(repo_id)
        assert pdf_v1_cached == pdf_v1, "Should return cached PDF"
        
        # Now simulate documentation regeneration with changes
        updated_content = """# Updated Documentation

## Version 2
This is the UPDATED version of the documentation.

## Features
- Feature A (v2) - UPDATED
- Feature B (v2) - UPDATED
- Feature C (NEW)

## New Section
This section was added in version 2.
"""
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': updated_content,
            'content_hash': 'updated-hash-v2',  # Different hash
            'state': 'generated'
        }
        
        # Export after regeneration - should NOT use old cache
        pdf_v2 = await exporter.export_pdf(repo_id)
        
        assert pdf_v2.startswith(b'%PDF')
        pdf_v2_text = pdf_v2.decode('latin-1', errors='ignore')
        
        # Verify new PDF is different from old PDF
        assert pdf_v2 != pdf_v1, "Updated PDF should be different from original"
        
        # Verify cache invalidation worked
        # Old cache should still exist (different hash)
        old_cached = exporter._get_cached_pdf(repo_id, 'initial-hash-v1')
        assert old_cached == pdf_v1, "Old cache should still exist with old hash"
        
        # New cache should exist with new hash
        new_cached = exporter._get_cached_pdf(repo_id, 'updated-hash-v2')
        assert new_cached is not None, "New PDF should be cached"
        assert new_cached == pdf_v2, "New cached PDF should match updated PDF"
        
        # Verify content reflects updates by checking PDF is different
        # (PDF content is compressed, so we verify by comparing bytes)
        assert pdf_v2 != pdf_v1, "Updated PDF should be different from original"
        assert len(pdf_v2) != len(pdf_v1), "Updated PDF should have different size"
        
        print(f"✓ Cache invalidation works correctly after regeneration")

    
    @pytest.mark.asyncio
    async def test_cache_expiration_after_ttl(self, exporter, mock_store):
        """
        Test that PDF cache expires after TTL.
        
        Validates: Requirements 2.1, 2.2, 3.1
        """
        from datetime import datetime, timedelta
        
        repo_id = "test-repo-cache-expiry"
        content = "# Cache Expiry Test\n\nThis tests cache TTL."
        content_hash = "cache-expiry-hash"
        
        mock_store.get.return_value = {
            'repo_id': repo_id,
            'content': content,
            'content_hash': content_hash,
            'state': 'generated'
        }
        
        # Generate PDF and cache it
        pdf_bytes = await exporter.export_pdf(repo_id)
        
        # Verify cache exists
        cached = exporter._get_cached_pdf(repo_id, content_hash)
        assert cached is not None, "PDF should be cached"
        
        # Manually expire the cache by modifying timestamp
        cache_key = f"{repo_id}:{content_hash}"
        if cache_key in exporter._pdf_cache:
            pdf_data, timestamp = exporter._pdf_cache[cache_key]
            # Set timestamp to 2 hours ago (beyond 1 hour TTL)
            expired_timestamp = datetime.utcnow() - timedelta(hours=2)
            exporter._pdf_cache[cache_key] = (pdf_data, expired_timestamp)
        
        # Try to get cached PDF - should return None (expired)
        cached_after_expiry = exporter._get_cached_pdf(repo_id, content_hash)
        assert cached_after_expiry is None, "Expired cache should return None"
        
        # Verify cache entry was removed
        assert cache_key not in exporter._pdf_cache, "Expired cache should be removed"
        
        print(f"✓ Cache expiration works correctly after TTL")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
