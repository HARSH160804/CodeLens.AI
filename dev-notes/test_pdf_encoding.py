#!/usr/bin/env python3
"""
Test PDF encoding to debug the production issue.
This simulates what the Lambda handler does.
"""

import sys
import base64

sys.path.insert(0, 'backend/lib')
sys.path.insert(0, 'backend')

from documentation.exporter import ExportService

# Test markdown
test_markdown = '''# Test Documentation

## Overview
This is a test document with some content.

## Features
- Feature 1: Authentication
- Feature 2: Data processing
- Feature 3: Export functionality

## Code Example
```python
def hello():
    print("Hello, World!")
```

## Conclusion
This is the end of the test document.
'''

# Create a mock store
class MockStore:
    async def get(self, repo_id):
        return {
            'content': test_markdown,
            'content_hash': 'test123'
        }

# Generate PDF
service = ExportService(MockStore())
html = service._markdown_to_html(test_markdown)
pdf_bytes = service._html_to_pdf(html)

print(f"PDF size: {len(pdf_bytes)} bytes")
print(f"PDF header: {pdf_bytes[:20]}")
print(f"Valid PDF: {pdf_bytes[:4] == b'%PDF'}")

# Simulate what Lambda handler does
base64_encoded = base64.b64encode(pdf_bytes).decode('utf-8')
print(f"\nBase64 encoded size: {len(base64_encoded)} chars")
print(f"Base64 preview: {base64_encoded[:100]}...")

# Save both versions
with open('/tmp/direct.pdf', 'wb') as f:
    f.write(pdf_bytes)
print("\nSaved direct PDF to /tmp/direct.pdf")

# Simulate what browser receives (decode base64)
decoded_bytes = base64.b64decode(base64_encoded)
with open('/tmp/decoded.pdf', 'wb') as f:
    f.write(decoded_bytes)
print("Saved decoded PDF to /tmp/decoded.pdf")

# Verify they're identical
if pdf_bytes == decoded_bytes:
    print("✓ Encoding/decoding works correctly")
else:
    print("✗ Encoding/decoding mismatch!")
