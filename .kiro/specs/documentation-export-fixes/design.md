# Documentation Export Fixes - Bugfix Design

## Overview

This bugfix addresses two critical issues in the documentation export functionality: (1) PDF export fails due to weasyprint requiring system dependencies (Cairo, Pango, GDK-PixBuf) that are not available in AWS Lambda, and (2) Markdown downloads deliver base64-encoded content instead of plain text. The fix will replace weasyprint with a Lambda-compatible PDF generation approach and correct the Markdown response encoding to ensure proper text delivery.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bugs - PDF export attempts using weasyprint in Lambda, or Markdown export with base64 encoding flag
- **Property (P)**: The desired behavior - PDF exports succeed using Lambda-compatible methods, Markdown exports deliver plain text
- **Preservation**: Existing documentation generation, storage, and retrieval functionality that must remain unchanged
- **weasyprint**: Python library for HTML-to-PDF conversion that requires system dependencies (Cairo, Pango, GDK-PixBuf)
- **ExportService**: The class in `backend/lib/documentation/exporter.py` that handles format conversion
- **docs_export handler**: The Lambda function in `backend/handlers/docs_export.py` that processes export requests
- **isBase64Encoded**: API Gateway response flag that indicates whether the body is base64-encoded

## Bug Details

### Fault Condition

The bugs manifest in two distinct scenarios:

**Bug 1 - PDF Export Failure:**
The bug occurs when a user requests PDF export and the `ExportService._html_to_pdf()` method attempts to import and use weasyprint. The Lambda environment lacks the required system libraries (Cairo, Pango, GDK-PixBuf), causing an ImportError or runtime error that propagates as a 500 error to the user.

**Bug 2 - Markdown Base64 Encoding:**
The bug occurs when a user requests Markdown export and the handler returns the content with `isBase64Encoded: True`. This causes API Gateway or the frontend to treat the already-base64-encoded body as if it needs further processing, resulting in the user downloading base64 text instead of readable markdown.

**Formal Specification:**
```
FUNCTION isBugCondition_PDF(input)
  INPUT: input of type ExportRequest
  OUTPUT: boolean
  
  RETURN input.format == 'pdf'
         AND input.repo_id EXISTS in documentation store
         AND Lambda environment lacks weasyprint system dependencies
END FUNCTION

FUNCTION isBugCondition_Markdown(input)
  INPUT: input of type ExportRequest
  OUTPUT: boolean
  
  RETURN input.format == 'md'
         AND input.repo_id EXISTS in documentation store
         AND response.isBase64Encoded == True
END FUNCTION
```

### Examples

**PDF Export Bug:**
- User clicks "Export as PDF" for repository "my-repo"
- Backend retrieves documentation successfully
- `_html_to_pdf()` attempts `from weasyprint import HTML`
- ImportError or runtime error occurs: "Cairo library not found"
- User receives: "Failed to export documentation. Please try again. Export failed: 500"
- Expected: User receives a downloadable PDF file

**Markdown Export Bug:**
- User clicks "Export as Markdown" for repository "my-repo"
- Backend retrieves documentation successfully
- Handler encodes content as base64 and sets `isBase64Encoded: True`
- User downloads file containing: "IyBNeSBSZXBvIERvY3VtZW50YXRpb24KCiMjIE92ZXJ2aWV3..."
- Expected: User downloads file containing: "# My Repo Documentation\n\n## Overview..."

**Edge Cases:**
- Very large documentation (>10MB) - should still export successfully
- Documentation with special characters or unicode - should preserve encoding
- Concurrent export requests - should not interfere with each other

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Documentation generation must continue to work exactly as before
- Documentation storage and retrieval must remain unchanged
- Export API authentication and authorization must remain unchanged
- Export request validation (format parameter, repo_id) must remain unchanged
- Markdown-to-HTML conversion logic must remain unchanged (used for future HTML export)
- PDF caching mechanism must remain functional with new PDF generation method

**Scope:**
All inputs that do NOT involve PDF or Markdown export should be completely unaffected by this fix. This includes:
- Documentation generation requests (`/repos/{id}/docs/generate`)
- Documentation status checks (`/repos/{id}/docs/status`)
- Any other API endpoints
- Frontend documentation display functionality

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **PDF - System Dependency Issue**: weasyprint requires Cairo, Pango, and GDK-PixBuf system libraries
   - AWS Lambda provides a minimal Linux environment without these graphics libraries
   - Installing these libraries would require custom Lambda layers (>50MB) and complex configuration
   - weasyprint is designed for server environments with full system access, not serverless

2. **PDF - No Fallback Mechanism**: The code has no alternative PDF generation method
   - `_html_to_pdf()` directly imports weasyprint without try/except for alternatives
   - No environment detection to choose appropriate PDF generation method
   - ConversionError is raised but doesn't trigger alternative approaches

3. **Markdown - Incorrect Encoding Flag**: The handler sets `isBase64Encoded: True` for all exports
   - Line 147 in `docs_export.py`: `'isBase64Encoded': True` is set for both PDF and Markdown
   - For binary content (PDF), this is correct - the body is base64-encoded bytes
   - For text content (Markdown), this is incorrect - API Gateway expects the body to be the actual base64 string, not to encode it again
   - The issue is that the body is already base64-encoded (line 145), and the flag tells API Gateway "this is base64", but API Gateway or the client may be double-encoding or not decoding properly

4. **Markdown - Content-Type Mismatch**: Setting `Content-Type: text/markdown` with base64 encoding creates ambiguity
   - Text content types typically expect plain text bodies
   - Binary content types expect base64-encoded bodies with the flag
   - The combination may cause API Gateway or browsers to mishandle the response

## Correctness Properties

Property 1: Fault Condition - PDF Export Success

_For any_ export request where format is 'pdf' and documentation exists for the repository, the fixed export function SHALL successfully generate and return a downloadable PDF file using a Lambda-compatible method (such as headless Chrome via AWS Lambda layer, HTML-to-PDF API service, or alternative Python library without system dependencies).

**Validates: Requirements 2.1, 2.2**

Property 2: Fault Condition - Markdown Plain Text Delivery

_For any_ export request where format is 'md' and documentation exists for the repository, the fixed export function SHALL return the markdown content as plain text that opens correctly in any text editor, without base64 encoding visible to the user.

**Validates: Requirements 2.3, 2.4**

Property 3: Preservation - Documentation Generation

_For any_ documentation generation request, the fixed code SHALL produce exactly the same behavior as the original code, preserving all generation, storage, and status checking functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/lib/documentation/exporter.py`

**Function**: `_html_to_pdf()`

**Specific Changes**:
1. **Replace weasyprint with Lambda-compatible solution**: Remove weasyprint dependency
   - Option A: Use AWS Lambda layer with headless Chromium (e.g., `chrome-aws-lambda` + `pyppeteer`)
   - Option B: Use alternative Python library without system dependencies (e.g., `xhtml2pdf`, `reportlab`)
   - Option C: Call external HTML-to-PDF API service (e.g., AWS API Gateway → headless Chrome in container)
   - Recommended: Option B (`xhtml2pdf`) for simplicity - pure Python, no system dependencies, good enough quality

2. **Update import statements**: Replace `from weasyprint import HTML` with chosen alternative

3. **Modify PDF generation logic**: Adapt HTML-to-PDF conversion to new library's API
   - `xhtml2pdf` uses: `pisa.CreatePDF(html_string, dest=pdf_buffer)`
   - Maintain same input (HTML string) and output (PDF bytes) interface

4. **Update error handling**: Ensure ConversionError messages reflect new library

5. **Preserve caching logic**: No changes needed to `_get_cached_pdf()` or `_cache_pdf()`

**File**: `backend/handlers/docs_export.py`

**Function**: `lambda_handler()`

**Specific Changes**:
1. **Fix Markdown encoding**: Modify response for Markdown format
   - Remove base64 encoding for Markdown: return plain text body
   - Keep `isBase64Encoded: False` for Markdown
   - Keep base64 encoding only for PDF (binary content)

2. **Conditional encoding logic**: Split response creation by format
   ```python
   if format_param == 'md':
       return {
           'statusCode': 200,
           'headers': {...},
           'body': content_bytes.decode('utf-8'),  # Plain text
           'isBase64Encoded': False
       }
   else:  # pdf
       return {
           'statusCode': 200,
           'headers': {...},
           'body': base64.b64encode(content_bytes).decode('utf-8'),
           'isBase64Encoded': True
       }
   ```

3. **Update Content-Type headers**: Ensure correct MIME types
   - Markdown: `text/markdown; charset=utf-8`
   - PDF: `application/pdf`

**File**: `backend/requirements.txt` or `infrastructure/template.yaml`

**Dependency Changes**:
1. **Remove**: `weasyprint` and its dependencies
2. **Add**: `xhtml2pdf` (or chosen alternative)
3. **Update Lambda layer configuration** if using external dependencies

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that attempt PDF and Markdown exports on the UNFIXED code to observe the exact failure modes and validate our root cause hypotheses.

**Test Cases**:
1. **PDF Export Failure Test**: Request PDF export for existing documentation (will fail on unfixed code)
   - Expected failure: ImportError or runtime error mentioning Cairo/Pango/weasyprint
   - Confirms: System dependency issue

2. **Markdown Base64 Test**: Request Markdown export and inspect downloaded file content (will fail on unfixed code)
   - Expected failure: File contains base64 string instead of plain text
   - Confirms: Encoding flag issue

3. **Large Documentation PDF Test**: Generate large documentation (>5MB) and attempt PDF export (will fail on unfixed code)
   - Expected failure: Same weasyprint error regardless of size
   - Confirms: Issue is dependency, not size-related

4. **Special Characters Markdown Test**: Export markdown with unicode and special characters (may fail on unfixed code)
   - Expected failure: Base64 encoding obscures all content
   - Confirms: Encoding issue affects all content types

**Expected Counterexamples**:
- PDF: `ImportError: Cairo library not found` or similar weasyprint dependency error
- Markdown: Downloaded file opens in text editor showing base64 string starting with "IyB..." instead of "# ..."

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed functions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition_PDF(input) DO
  result := export_pdf_fixed(input.repo_id)
  ASSERT result is valid PDF bytes
  ASSERT result can be opened by PDF reader
  ASSERT result contains expected documentation content
END FOR

FOR ALL input WHERE isBugCondition_Markdown(input) DO
  result := export_markdown_fixed(input.repo_id)
  ASSERT result is plain text string
  ASSERT result starts with markdown syntax (e.g., "# ")
  ASSERT result does NOT contain base64 encoding
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed functions produce the same result as the original functions.

**Pseudocode:**
```
FOR ALL input WHERE NOT (isBugCondition_PDF(input) OR isBugCondition_Markdown(input)) DO
  ASSERT documentation_generation_original(input) = documentation_generation_fixed(input)
  ASSERT documentation_storage_original(input) = documentation_storage_fixed(input)
  ASSERT api_authentication_original(input) = api_authentication_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-export operations

**Test Plan**: Observe behavior on UNFIXED code first for documentation generation and storage, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Documentation Generation Preservation**: Verify generating documentation continues to work
   - Observe: Generation creates documentation with same content structure
   - Test: Generate docs before and after fix, compare content

2. **Storage Retrieval Preservation**: Verify retrieving documentation continues to work
   - Observe: Store retrieves correct documentation for repo_id
   - Test: Retrieve docs before and after fix, compare results

3. **API Validation Preservation**: Verify request validation continues to work
   - Observe: Invalid format parameters return 400 errors
   - Test: Send invalid requests before and after fix, compare error responses

4. **HTML Conversion Preservation**: Verify markdown-to-HTML conversion unchanged
   - Observe: HTML output has same structure and styling
   - Test: Convert same markdown before and after fix, compare HTML (used for future HTML export feature)

### Unit Tests

- Test PDF export with xhtml2pdf for various documentation sizes
- Test Markdown export returns plain text without base64 encoding
- Test edge cases: empty documentation, very large documentation, special characters
- Test error handling: missing documentation, invalid repo_id
- Test Content-Type and Content-Disposition headers are correct
- Test PDF caching still works with new PDF generation method

### Property-Based Tests

- Generate random markdown content and verify PDF generation succeeds
- Generate random markdown content and verify Markdown export returns plain text
- Generate random repo_ids and verify appropriate error handling (404 for missing docs)
- Test that all documentation generation operations continue to work across many scenarios

### Integration Tests

- Test full export flow: generate documentation → export as PDF → verify PDF is valid
- Test full export flow: generate documentation → export as Markdown → verify text is readable
- Test switching between formats: export same documentation as both PDF and Markdown
- Test concurrent exports: multiple users exporting different repositories simultaneously
- Test export after documentation regeneration: ensure cache invalidation works correctly
