# Implementation Plan

- [x] 1. Write bug condition exploration tests
  - **Property 1: Fault Condition** - PDF Export Failure and Markdown Base64 Encoding
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: These tests encode the expected behavior - they will validate the fix when they pass after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bugs exist
  - **Scoped PBT Approach**: Scope properties to concrete failing cases to ensure reproducibility
  
  - [x] 1.1 Test PDF export with weasyprint dependency failure
    - Test that PDF export for any existing repository fails with ImportError or runtime error mentioning Cairo/Pango/weasyprint
    - Use concrete test case: export PDF for a test repository with valid documentation
    - Run test on UNFIXED code
    - **EXPECTED OUTCOME**: Test FAILS with system dependency error (this is correct - it proves the bug exists)
    - Document counterexample: specific error message and stack trace
    - _Requirements: 2.1_
  
  - [x] 1.2 Test Markdown export returns base64-encoded content
    - Test that Markdown export for any existing repository returns base64 string instead of plain text
    - Use concrete test case: export Markdown for a test repository, verify downloaded content starts with base64 characters (e.g., "IyB...") instead of markdown syntax (e.g., "# ")
    - Run test on UNFIXED code
    - **EXPECTED OUTCOME**: Test FAILS showing base64 content instead of plain text (this is correct - it proves the bug exists)
    - Document counterexample: actual base64 string received vs expected plain text
    - _Requirements: 2.3_
  
  - [x] 1.3 Test large documentation PDF export failure
    - Test that PDF export fails for large documentation (>5MB) with same weasyprint error
    - Use concrete test case: generate large documentation, attempt PDF export
    - Run test on UNFIXED code
    - **EXPECTED OUTCOME**: Test FAILS with same dependency error regardless of size (confirms issue is dependency, not size-related)
    - Document counterexample: error message for large documentation
    - _Requirements: 2.1_
  
  - [x] 1.4 Test special characters in Markdown export
    - Test that Markdown export with unicode and special characters returns base64-encoded content
    - Use concrete test case: export Markdown containing unicode characters (e.g., emoji, accented characters)
    - Run test on UNFIXED code
    - **EXPECTED OUTCOME**: Test FAILS showing base64 encoding obscures all content (confirms encoding issue affects all content types)
    - Document counterexample: base64 string vs expected unicode text
    - _Requirements: 2.3_
  
  - Mark task complete when all tests are written, run, and failures are documented
  - _Requirements: 2.1, 2.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Documentation Generation and Storage
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-export operations
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  
  - [x] 2.1 Test documentation generation preservation
    - Observe: Generate documentation for test repository on unfixed code, record content structure and format
    - Write property-based test: for all valid repository inputs, documentation generation produces same content structure
    - Verify test passes on UNFIXED code
    - _Requirements: 3.1, 3.2_
  
  - [x] 2.2 Test documentation storage and retrieval preservation
    - Observe: Store and retrieve documentation on unfixed code, verify correct data returned
    - Write property-based test: for all stored documentation, retrieval returns exact same content
    - Verify test passes on UNFIXED code
    - _Requirements: 3.3_
  
  - [x] 2.3 Test API validation preservation
    - Observe: Send invalid export requests (bad format, missing repo_id) on unfixed code, record error responses
    - Write property-based test: for all invalid requests, API returns appropriate 400/404 errors with same messages
    - Verify test passes on UNFIXED code
    - _Requirements: 3.4_
  
  - [x] 2.4 Test markdown-to-HTML conversion preservation
    - Observe: Convert markdown to HTML on unfixed code, record HTML structure and styling
    - Write property-based test: for all markdown inputs, HTML conversion produces same structure (used for future HTML export)
    - Verify test passes on UNFIXED code
    - _Requirements: 3.1_
  
  - Mark task complete when all tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for PDF export and Markdown encoding issues

  - [x] 3.1 Replace weasyprint with xhtml2pdf in ExportService
    - Update `backend/lib/documentation/exporter.py`
    - Remove weasyprint import: `from weasyprint import HTML`
    - Add xhtml2pdf imports: `from xhtml2pdf import pisa`
    - Modify `_html_to_pdf()` method to use xhtml2pdf API
    - Replace: `HTML(string=html_content).write_pdf(pdf_buffer)`
    - With: `pisa.CreatePDF(html_content, dest=pdf_buffer)`
    - Update error handling to reflect new library
    - Preserve caching logic in `_get_cached_pdf()` and `_cache_pdf()`
    - _Bug_Condition: isBugCondition_PDF(input) where input.format == 'pdf' AND Lambda lacks weasyprint dependencies_
    - _Expected_Behavior: PDF export succeeds using Lambda-compatible xhtml2pdf library_
    - _Preservation: Caching mechanism and HTML conversion logic remain unchanged_
    - _Requirements: 2.1, 2.2, 3.1_
  
  - [x] 3.2 Fix Markdown encoding in docs_export handler
    - Update `backend/handlers/docs_export.py`
    - Modify response creation to conditionally encode based on format
    - For Markdown format: return plain text body with `isBase64Encoded: False`
    - For PDF format: keep base64 encoding with `isBase64Encoded: True`
    - Update Content-Type headers: `text/markdown; charset=utf-8` for Markdown, `application/pdf` for PDF
    - Ensure Content-Disposition header includes correct file extension
    - _Bug_Condition: isBugCondition_Markdown(input) where input.format == 'md' AND response.isBase64Encoded == True_
    - _Expected_Behavior: Markdown export returns plain text without base64 encoding_
    - _Preservation: API authentication, validation, and error handling remain unchanged_
    - _Requirements: 2.3, 2.4, 3.4_
  
  - [x] 3.3 Update dependencies
    - Remove `weasyprint` from `backend/requirements.txt`
    - Add `xhtml2pdf` to `backend/requirements.txt`
    - Update Lambda layer configuration in `infrastructure/template.yaml` if needed
    - Verify no other code depends on weasyprint
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify bug condition exploration tests now pass
    - **Property 1: Expected Behavior** - PDF Export Success and Markdown Plain Text
    - **IMPORTANT**: Re-run the SAME tests from task 1 - do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run all bug condition exploration tests from step 1
    - **EXPECTED OUTCOME**: All tests PASS (confirms bugs are fixed)
    - Verify PDF export succeeds without dependency errors
    - Verify Markdown export returns plain text, not base64
    - Verify large documentation exports work correctly
    - Verify special characters are preserved in exports
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Documentation Generation and Storage
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run all preservation property tests from step 2
    - **EXPECTED OUTCOME**: All tests PASS (confirms no regressions)
    - Verify documentation generation produces same content structure
    - Verify storage and retrieval work identically
    - Verify API validation returns same error responses
    - Verify markdown-to-HTML conversion unchanged
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Integration testing

  - [x] 4.1 Test full PDF export flow
    - Generate documentation for test repository
    - Export as PDF using new xhtml2pdf implementation
    - Verify PDF file is valid and can be opened
    - Verify PDF contains expected documentation content
    - Test with various documentation sizes (small, medium, large)
    - _Requirements: 2.1, 2.2_
  
  - [x] 4.2 Test full Markdown export flow
    - Generate documentation for test repository
    - Export as Markdown using fixed encoding
    - Verify downloaded file opens in text editor
    - Verify content is plain text markdown, not base64
    - Test with various content types (unicode, special characters, code blocks)
    - _Requirements: 2.3, 2.4_
  
  - [x] 4.3 Test format switching
    - Generate documentation once
    - Export same documentation as both PDF and Markdown
    - Verify both exports succeed
    - Verify content consistency between formats
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 4.4 Test concurrent exports
    - Simulate multiple users exporting different repositories simultaneously
    - Verify no interference between concurrent requests
    - Verify all exports complete successfully
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.3_
  
  - [x] 4.5 Test export after documentation regeneration
    - Generate documentation for repository
    - Export as PDF (should be cached)
    - Regenerate documentation with changes
    - Export as PDF again
    - Verify cache invalidation works correctly
    - Verify new PDF reflects updated content
    - _Requirements: 2.1, 2.2, 3.1_

- [x] 5. Checkpoint - Ensure all tests pass
  - Run complete test suite (unit + property-based + integration)
  - Verify all bug condition tests pass (bugs are fixed)
  - Verify all preservation tests pass (no regressions)
  - Verify all integration tests pass (end-to-end flows work)
  - Ask user if any questions arise or if manual testing is needed
