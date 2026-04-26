# Implementation Plan: Documentation Generation and Export Workflow

## Overview

This implementation plan establishes a stateful documentation generation and export workflow that separates documentation creation from format conversion. The system will generate comprehensive technical documentation from architecture analysis data, store it persistently in DynamoDB, and enable on-demand export in Markdown and PDF formats.

## Tasks

- [x] 1. Set up DynamoDB table and data models
  - Create DynamoDB table schema in SAM template with repo_id as partition key
  - Implement DocumentationRecord dataclass in backend/lib/models/documentation_models.py
  - Add table name to environment variables in SAM template
  - _Requirements: 2.1, 2.2, 2.5_

- [ ] 2. Implement DocumentationStore class
  - [x] 2.1 Create DocumentationStore class with DynamoDB operations
    - Implement save(), get(), get_state(), update_state(), delete() methods
    - Add atomic state updates using conditional writes
    - Handle large documents (>400KB) with S3 fallback
    - Calculate and store content_hash (SHA256)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 2.2 Write property test for storage round-trip
    - **Property 4: Storage Round-Trip**
    - **Validates: Requirements 2.1, 2.2, 2.3**
  
  - [ ]* 2.3 Write property test for state persistence
    - **Property 5: State Persistence**
    - **Validates: Requirements 2.3, 2.5**
  
  - [ ]* 2.4 Write property test for latest version retrieval
    - **Property 6: Latest Version Retrieval**
    - **Validates: Requirements 2.4**
  
  - [ ]* 2.5 Write unit tests for DocumentationStore
    - Test concurrent state updates
    - Test large document handling
    - Test DynamoDB error handling
    - _Requirements: 2.1, 2.2, 2.5_

- [ ] 3. Implement DocumentationGenerator class
  - [x] 3.1 Create DocumentationGenerator with AI-powered generation
    - Implement generate() method using BedrockClient
    - Build structured prompt with ArchitectureAnalysis data
    - Generate all required sections (Overview, Patterns, Layers, Tech Stack, Data Flows, Dependencies, Metrics, Recommendations)
    - Include Mermaid diagrams from visualizations
    - Validate markdown output structure
    - _Requirements: 1.1, 1.2, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [ ]* 3.2 Write property test for complete documentation structure
    - **Property 1: Complete Documentation Structure**
    - **Validates: Requirements 1.1, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**
  
  - [ ]* 3.3 Write property test for data fidelity
    - **Property 2: Data Fidelity**
    - **Validates: Requirements 1.2**
  
  - [ ]* 3.4 Write property test for valid markdown output
    - **Property 3: Valid Markdown Output**
    - **Validates: Requirements 7.8**
  
  - [ ]* 3.5 Write unit tests for DocumentationGenerator
    - Test with minimal analysis data
    - Test with complete analysis data
    - Test with missing optional fields
    - Test error handling for invalid data
    - _Requirements: 1.1, 1.2, 7.8_

- [ ] 4. Checkpoint - Ensure core generation and storage tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement ExportService class
  - [x] 5.1 Create ExportService with format conversion
    - Implement export_markdown() method (passthrough from store)
    - Implement export_pdf() method with markdown→HTML→PDF pipeline
    - Use markdown library with extensions (tables, fenced_code, toc)
    - Use weasyprint for HTML to PDF conversion
    - Apply CSS styling for readable PDFs
    - Implement in-memory PDF caching with 1-hour TTL
    - _Requirements: 3.1, 3.2, 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ]* 5.2 Write property test for export content consistency
    - **Property 7: Export Content Consistency**
    - **Validates: Requirements 3.1**
  
  - [ ]* 5.3 Write property test for markdown to HTML preservation
    - **Property 8: Markdown to HTML Preservation**
    - **Validates: Requirements 9.1**
  
  - [ ]* 5.4 Write property test for PDF validity
    - **Property 9: PDF Validity**
    - **Validates: Requirements 3.2, 9.2**
  
  - [ ]* 5.5 Write property test for PDF table of contents
    - **Property 10: PDF Table of Contents**
    - **Validates: Requirements 9.3**
  
  - [ ]* 5.6 Write property test for PDF code block preservation
    - **Property 11: PDF Code Block Preservation**
    - **Validates: Requirements 9.5**
  
  - [ ]* 5.7 Write unit tests for ExportService
    - Test markdown export
    - Test PDF conversion pipeline
    - Test cache behavior
    - Test error handling for conversion failures
    - _Requirements: 3.1, 3.2, 9.1, 9.2_

- [ ] 6. Implement API handlers
  - [x] 6.1 Create POST /repos/{id}/docs/generate handler
    - Check current generation state
    - Update state to 'generating' with atomic write
    - Retrieve architecture analysis data
    - Call DocumentationGenerator
    - Store generated documentation
    - Update state to 'generated' or 'failed'
    - Return 202 Accepted response
    - Handle errors with proper error codes
    - _Requirements: 1.3, 1.4, 1.5, 4.2, 4.3, 4.4, 4.5, 6.1, 6.4, 11.1, 11.2, 11.4_
  
  - [x] 6.2 Create GET /repos/{id}/docs/export handler
    - Validate format parameter (md or pdf)
    - Call ExportService with requested format
    - Return file with appropriate Content-Type and Content-Disposition headers
    - Return 404 if documentation doesn't exist
    - Handle conversion errors
    - _Requirements: 3.1, 3.2, 3.5, 6.2, 6.5, 11.3_
  
  - [x] 6.3 Create GET /repos/{id}/docs/status handler
    - Retrieve documentation record from store
    - Return generation state, creation timestamp, and error message
    - Return 'not_generated' if no documentation exists
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.3, 6.6_
  
  - [ ]* 6.4 Write property test for atomic state transitions
    - **Property 12: Atomic State Transitions**
    - **Validates: Requirements 4.6**
  
  - [ ]* 6.5 Write property test for generation idempotency
    - **Property 13: Generation Idempotency**
    - **Validates: Requirements 1.5**
  
  - [ ]* 6.6 Write property test for regeneration updates
    - **Property 14: Regeneration Updates**
    - **Validates: Requirements 10.2, 10.3**
  
  - [ ]* 6.7 Write property test for regeneration atomicity
    - **Property 15: Regeneration Atomicity**
    - **Validates: Requirements 10.4, 10.5**
  
  - [ ]* 6.8 Write unit tests for API handlers
    - Test generate endpoint (202 response)
    - Test export endpoint (200 with file)
    - Test status endpoint (200 with state)
    - Test error responses (400, 404, 500)
    - Test state conflict handling (409)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 7. Checkpoint - Ensure backend implementation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Update SAM template with infrastructure
  - [ ] 8.1 Add DynamoDB table resource
    - Define RepoDocumentation table with PAY_PER_REQUEST billing
    - Enable point-in-time recovery
    - Enable encryption at rest
    - _Requirements: 2.1, 2.5_
  
  - [ ] 8.2 Add Lambda function resources
    - Create GenerateDocsFunction with 1024MB memory, 60s timeout
    - Create ExportDocsFunction with 2048MB memory, 30s timeout
    - Create DocsStatusFunction with 256MB memory, 10s timeout
    - Add DynamoDB permissions to each function
    - Add Bedrock permissions to GenerateDocsFunction
    - Add API Gateway events for each endpoint
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ] 8.3 Update requirements.txt with dependencies
    - Add markdown>=3.5.0
    - Add weasyprint>=60.0
    - Add hypothesis>=6.90.0 (for property tests)
    - _Requirements: 3.2, 9.1, 9.2_

- [x] 9. Implement frontend useDocumentation hook
  - [x] 9.1 Create useDocumentation hook with React Query
    - Implement status query with polling during 'generating' state
    - Implement generate mutation
    - Implement exportMarkdown and exportPdf functions with proper blob download handling
    - Return status, createdAt, errorMessage, isLoading, generate, isGenerating
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.3_
  
  - [ ]* 9.2 Write unit tests for useDocumentation hook
    - Test status polling behavior
    - Test generate mutation
    - Test export functions
    - _Requirements: 4.1, 5.3_

- [x] 10. Implement frontend UI components
  - [x] 10.1 Create GenerateButton component
    - Display "Generate Documentation" or "Regenerate Documentation" based on status
    - Show loading spinner during generation
    - Disable button while generating
    - _Requirements: 5.1, 5.4, 10.1_
  
  - [x] 10.2 Create ExportDropdown component
    - Display "Export Documentation" button with dropdown
    - Provide "Export as Markdown" and "Export as PDF" options
    - Trigger download on selection
    - _Requirements: 5.2, 5.5_
  
  - [x] 10.3 Update ArchitectureView with documentation controls
    - Conditionally render GenerateButton or ExportDropdown based on generation state
    - Show loading indicator during 'generating' state
    - Display error messages for 'failed' state
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ]* 10.4 Write unit tests for UI components
    - Test GenerateButton rendering and behavior
    - Test ExportDropdown rendering and behavior
    - Test ArchitectureView state-based rendering
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 11. Implement API client functions
  - [x] 11.1 Create documentation API client in frontend/src/services/api.ts
    - Implement getStatus(repoId) function
    - Implement generate(repoId) function
    - Implement getExportUrl(repoId, format) function
    - Handle error responses with proper error messages
    - _Requirements: 6.1, 6.2, 6.3, 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 12. Checkpoint - Ensure frontend implementation works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Write property-based tests for performance
  - [ ]* 13.1 Write property test for markdown export performance
    - **Property 18: Markdown Export Performance**
    - **Validates: Requirements 3.3, 12.2**
  
  - [ ]* 13.2 Write property test for PDF export performance
    - **Property 19: PDF Export Performance**
    - **Validates: Requirements 3.4, 12.3**
  
  - [ ]* 13.3 Write property test for generation performance
    - **Property 20: Generation Performance**
    - **Validates: Requirements 12.1**
  
  - [ ]* 13.4 Write property test for status endpoint performance
    - **Property 21: Status Endpoint Performance**
    - **Validates: Requirements 12.5**
  
  - [ ]* 13.5 Write property test for PDF cache effectiveness
    - **Property 22: PDF Cache Effectiveness**
    - **Validates: Requirements 12.4**

- [ ] 14. Write property-based tests for error handling
  - [ ]* 14.1 Write property test for error state transition
    - **Property 16: Error State Transition**
    - **Validates: Requirements 1.4**
  
  - [ ]* 14.2 Write property test for error logging completeness
    - **Property 17: Error Logging Completeness**
    - **Validates: Requirements 11.5**

- [ ] 15. Integration testing and end-to-end verification
  - [ ]* 15.1 Write integration test for complete workflow
    - Test generate → poll status → export markdown → export PDF
    - Test regeneration workflow
    - Test error scenarios (missing analysis, AI failures)
    - _Requirements: 1.1, 1.3, 2.1, 3.1, 3.2, 4.1, 10.2, 10.3_
  
  - [ ]* 15.2 Write integration test for concurrent operations
    - Test concurrent generation requests
    - Test concurrent export requests
    - Verify atomic state updates
    - _Requirements: 4.6_

- [ ] 16. Final checkpoint - Deploy and verify
  - Deploy SAM template to AWS
  - Verify DynamoDB table creation
  - Verify Lambda functions are deployed
  - Test API endpoints manually
  - Verify frontend integration
  - Monitor CloudWatch logs for errors
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation uses Python for backend and TypeScript/React for frontend
- PDF conversion requires weasyprint library with system dependencies (Lambda Layer)
- DynamoDB table uses PAY_PER_REQUEST billing for variable workload
- Generation is synchronous in Lambda (consider Step Functions for very large repos)
