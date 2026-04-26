# Implementation Plan: Async Repository Ingestion

## Overview

This implementation plan converts the async repository ingestion design into actionable coding tasks. The system decouples repository upload from processing using an SQS queue, enabling immediate API responses while processing continues asynchronously with real-time progress updates.

The implementation follows a phased approach: infrastructure setup, core async components, progress tracking, error handling, and frontend integration. Each task builds incrementally with checkpoints to validate functionality.

## Tasks

- [x] 1. Set up infrastructure and data models
  - Create DynamoDB table schema for ingestion jobs with TTL and GSI
  - Create SQS queue configuration with dead letter queue
  - Update SAM template with new Lambda function definitions
  - Add CloudWatch alarms for error rates and DLQ messages
  - _Requirements: 2.5, 5.5, 10.1, 10.2, 10.3, 10.4, 13.5_

- [x] 2. Implement core utility modules
  - [x] 2.1 Create IdempotencyManager module
    - Implement `generate_key()` for SHA-256 hash generation from content
    - Implement `check_existing_job()` to query DynamoDB by idempotency_key
    - Implement `should_create_new_job()` decision logic based on job status
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 2.2 Write property test for IdempotencyManager
    - **Property 11: Idempotency Key Determinism**
    - **Validates: Requirements 5.1**
    - Test that same content always produces same key
    - Test key format is valid SHA-256 (64 hex characters)
  
  - [ ]* 2.3 Write unit tests for IdempotencyManager
    - Test key generation with various content types
    - Test duplicate detection for processing/completed/failed jobs
    - Test decision logic for creating new jobs
    - _Requirements: 15.5_
  
  - [x] 2.4 Create ProgressTracker module
    - Implement `__init__()` to initialize with job_id and total_files
    - Implement `update()` to write progress to DynamoDB with batching
    - Implement `mark_completed()` to set final status
    - Implement `mark_failed()` to set error status with message
    - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 2.5 Write property test for ProgressTracker
    - **Property 7: Progress Invariant**
    - **Validates: Requirements 3.1, 3.3, 3.4**
    - Test progress_current always <= progress_total
    - Test both values are non-negative
  
  - [ ]* 2.6 Write unit tests for ProgressTracker
    - Test update frequency (every 10 files)
    - Test timestamp updates on each write
    - Test completion marking sets correct status
    - Test failure marking includes error message
    - _Requirements: 15.7_

- [x] 3. Checkpoint - Verify utility modules
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Ingestion Service Lambda
  - [x] 4.1 Create ingest_async.py handler
    - Implement request parsing for GitHub URL and ZIP upload
    - Implement job_id generation (UUID v4)
    - Implement idempotency check using IdempotencyManager
    - Implement DynamoDB job record creation
    - Implement SQS message enqueuing
    - Implement response formatting with job_id and status
    - Add error handling for validation failures
    - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.2, 5.3, 11.1_
  
  - [ ]* 4.2 Write property test for job enqueue
    - **Property 1: Job Enqueue Before Response**
    - **Validates: Requirements 1.2**
    - Test SQS contains message before HTTP response
  
  - [ ]* 4.3 Write property test for initial job record
    - **Property 2: Initial Job Record Creation**
    - **Validates: Requirements 1.3, 2.1**
    - Test job record exists immediately after request
    - Test initial status is "processing"
  
  - [ ]* 4.4 Write unit tests for Ingestion Service
    - Test request validation (invalid JSON, missing fields)
    - Test duplicate request handling (processing/completed/failed)
    - Test SQS message format
    - Test DynamoDB record structure
    - Test error responses (400, 413, 500)
    - Test response time < 5 seconds
    - _Requirements: 15.1_
  
  - [x] 4.5 Create get_status_handler in ingest_async.py
    - Implement job_id extraction from path parameters
    - Implement DynamoDB query by job_id
    - Implement response formatting with all status fields
    - Implement 404 handling for non-existent jobs
    - Add response time optimization (< 1 second)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ]* 4.6 Write property test for status endpoint
    - **Property 22: Status Endpoint Response Accuracy**
    - **Validates: Requirements 11.2**
    - Test response matches DynamoDB state exactly
  
  - [ ]* 4.7 Write unit tests for status endpoint
    - Test valid job_id returns correct data
    - Test non-existent job_id returns 404
    - Test response includes all required fields
    - Test response time < 1 second
    - _Requirements: 15.1_

- [x] 5. Checkpoint - Verify Ingestion Service
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Processing Worker Lambda
  - [x] 6.1 Create process_repo_worker.py handler skeleton
    - Implement SQS message parsing
    - Implement job record retrieval from DynamoDB
    - Implement basic error handling structure
    - Add logging for job start/completion
    - _Requirements: 1.4, 13.2_
  
  - [x] 6.2 Implement stale job detection
    - Implement `detect_stale_jobs()` to scan for old processing jobs
    - Mark jobs with updated_at > 15 minutes as failed
    - Add timeout error message
    - Run detection at worker start
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 6.3 Write property test for stale job detection
    - **Property 14: Stale Job Detection**
    - **Validates: Requirements 6.1, 6.5**
    - Test jobs older than 15 minutes are marked failed
    - Test error message is "Processing timeout exceeded"
  
  - [ ]* 6.4 Write unit tests for stale job detection
    - Test detection with various timestamps
    - Test only processing jobs are affected
    - Test completed/failed jobs are not changed
    - _Requirements: 15.2_
  
  - [x] 6.5 Implement repository download and extraction
    - Implement GitHub repository cloning
    - Implement ZIP file extraction from S3
    - Implement file discovery and filtering
    - Add temporary file management in /tmp
    - _Requirements: 1.5, 9.1_
  
  - [x] 6.6 Implement batch processing logic
    - Implement file batching (50 files per batch)
    - Implement batch iteration with progress tracking
    - Integrate ProgressTracker for updates every 10 files
    - Add memory monitoring between batches
    - Add garbage collection between batches
    - _Requirements: 3.2, 12.1, 12.2, 12.4_
  
  - [ ]* 6.7 Write property test for batch processing
    - **Property 24: Batch Processing**
    - **Validates: Requirements 12.1**
    - Test repos with >50 files are processed in batches
    - Test each batch contains at most 50 files
  
  - [ ]* 6.8 Write unit tests for batch processing
    - Test batch size calculation
    - Test progress updates during batching
    - Test memory monitoring between batches
    - _Requirements: 15.2_
  
  - [x] 6.9 Implement file processing and embedding generation
    - Integrate existing code_processor module for file parsing
    - Integrate existing bedrock_client for embeddings
    - Implement chunk generation and storage
    - Use existing Vector_Store interface
    - Maintain backward-compatible data schema
    - _Requirements: 1.5, 9.1, 9.2, 9.3, 9.4_
  
  - [ ]* 6.10 Write property test for processing completeness
    - **Property 3: Processing Completeness**
    - **Validates: Requirements 1.5**
    - Test all processable files have embeddings in Vector_Store
  
  - [ ]* 6.11 Write unit tests for file processing
    - Test integration with code_processor
    - Test integration with bedrock_client
    - Test Vector_Store data schema compatibility
    - _Requirements: 15.2_

- [x] 7. Checkpoint - Verify core processing logic
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement error handling and retries
  - [x] 8.1 Create error classification module
    - Define TransientError exception class
    - Define PermanentError exception class
    - Implement error classification logic
    - Map AWS exceptions to error types
    - _Requirements: 7.4, 7.5_
  
  - [ ]* 8.2 Write property test for error classification
    - **Property 17: Error Classification**
    - **Validates: Requirements 7.4, 7.5**
    - Test transient errors are retryable
    - Test permanent errors are not retryable
  
  - [ ]* 8.3 Write unit tests for error classification
    - Test network timeout → TransientError
    - Test throttling → TransientError
    - Test invalid format → PermanentError
    - Test out of memory → PermanentError
    - _Requirements: 15.4_
  
  - [x] 8.4 Implement retry logic in worker
    - Add try-catch for transient vs permanent errors
    - Re-raise transient errors for SQS retry
    - Mark permanent errors as failed immediately
    - Delete SQS message on permanent failure
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  
  - [ ]* 8.5 Write property test for retry behavior
    - **Property 16: Transient Error Retry**
    - **Validates: Requirements 7.1, 7.3**
    - Test transient errors are retried up to 3 times
  
  - [ ]* 8.6 Write integration test for retry workflow
    - Test SQS retry with exponential backoff
    - Test DLQ routing after 3 failures
    - Test permanent error immediate failure
    - _Requirements: 15.4_
  
  - [x] 8.7 Implement cleanup on failure
    - Implement `cleanup_on_failure()` function
    - Remove temporary files from /tmp
    - Delete partial embeddings from Vector_Store
    - Update job status to failed with error message
    - Add error logging for cleanup failures
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ]* 8.8 Write property test for cleanup
    - **Property 18: Cleanup on Termination**
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - Test temp files removed on success and failure
    - Test partial data removed from Vector_Store on failure
  
  - [ ]* 8.9 Write unit tests for cleanup
    - Test cleanup on successful completion
    - Test cleanup on processing failure
    - Test job status updated even if cleanup fails
    - _Requirements: 15.8_

- [x] 9. Checkpoint - Verify error handling
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement memory management
  - [x] 10.1 Create memory monitoring utilities
    - Implement `get_memory_usage_mb()` using psutil
    - Implement `check_memory_threshold()` with 2.5GB threshold
    - Add memory logging at batch boundaries
    - _Requirements: 12.3, 12.4_
  
  - [x] 10.2 Integrate memory checks in worker
    - Add memory check before processing each file
    - Trigger garbage collection if threshold exceeded
    - Fail job if memory cannot be freed
    - Set appropriate error message for OOM
    - _Requirements: 12.3, 12.5_
  
  - [ ]* 10.3 Write property test for memory threshold
    - **Property 25: Memory Threshold Handling**
    - **Validates: Requirements 12.3**
    - Test GC triggered when memory < 512MB
  
  - [ ]* 10.4 Write property test for OOM failure
    - **Property 26: Out of Memory Failure**
    - **Validates: Requirements 12.5**
    - Test job marked failed when memory cannot be freed
    - Test error message contains "out of memory"
  
  - [ ]* 10.5 Write unit tests for memory management
    - Test memory monitoring accuracy
    - Test GC triggering logic
    - Test OOM error handling
    - _Requirements: 15.2_

- [x] 11. Implement status transitions and completion
  - [x] 11.1 Implement completion logic in worker
    - Mark job as completed after all files processed
    - Store final repository metadata
    - Update progress to 100%
    - Add completion timestamp
    - _Requirements: 2.3, 3.5_
  
  - [ ]* 11.2 Write property test for completion status
    - **Property 4: Status Transition to Completed**
    - **Validates: Requirements 2.3, 3.5**
    - Test successful jobs have status "completed"
    - Test progress_current equals progress_total
  
  - [ ]* 11.3 Write property test for failure status
    - **Property 5: Status Transition to Failed**
    - **Validates: Requirements 2.4**
    - Test failed jobs have status "failed"
    - Test error_message is non-empty
  
  - [ ]* 11.4 Write property test for status schema
    - **Property 6: Status Schema Completeness**
    - **Validates: Requirements 2.5, 5.5, 11.3**
    - Test all required fields present in job records
  
  - [ ]* 11.5 Write property test for timestamp updates
    - **Property 15: Timestamp Update on Status Change**
    - **Validates: Requirements 6.3**
    - Test updated_at increases on each update
  
  - [ ]* 11.6 Write integration tests for status transitions
    - Test processing → completed workflow
    - Test processing → failed workflow
    - Test status persistence across retries
    - _Requirements: 15.6_

- [x] 12. Checkpoint - Verify status management
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement user-friendly error messages
  - [ ] 13.1 Create error message formatter
    - Map error codes to user-friendly messages
    - Implement message templates for common errors
    - Add technical details for debugging
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ]* 13.2 Write property test for error message format
    - **Property 27: Error Message Format**
    - **Validates: Requirements 14.1**
    - Test invalid format errors match pattern
  
  - [ ]* 13.3 Write unit tests for error messages
    - Test all error code mappings
    - Test message template formatting
    - Test error message display in frontend
    - _Requirements: 15.4_

- [ ] 14. Implement monitoring and logging
  - [ ] 14.1 Add structured logging to all components
    - Log all incoming requests with job_id
    - Log job start/completion in worker
    - Log progress updates every 50 files
    - Log all errors with stack traces
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [ ] 14.2 Add CloudWatch metrics emission
    - Emit jobs_started metric
    - Emit jobs_completed metric
    - Emit jobs_failed metric
    - Emit processing_duration metric
    - Emit files_processed metric
    - _Requirements: 13.5_
  
  - [ ]* 14.3 Write unit tests for logging
    - Test log format and structure
    - Test all log points are reached
    - Test error logs include stack traces
    - _Requirements: 15.2_

- [x] 15. Implement frontend polling components
  - [x] 15.1 Create useIngestionStatus React hook
    - Implement polling logic with 2-second interval
    - Implement stop conditions (completed/failed)
    - Implement exponential backoff on errors
    - Implement max poll duration (15 minutes)
    - Add error state management
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  
  - [ ]* 15.2 Write property test for polling termination
    - **Property 9: Polling Termination**
    - **Validates: Requirements 4.3**
    - Test polling stops on completed/failed status
    - Test terminal status remains unchanged
  
  - [ ]* 15.3 Write property test for polling retry
    - **Property 10: Polling Retry on Failure**
    - **Validates: Requirements 4.5**
    - Test polling retries up to 3 times on error
  
  - [ ]* 15.4 Write unit tests for polling hook
    - Test polling interval is 2 seconds
    - Test stop conditions work correctly
    - Test error handling and retry logic
    - Test max duration timeout
  
  - [x] 15.5 Create IngestionProgress UI component
    - Implement progress bar visualization
    - Display "Processing X/Y files" text
    - Calculate and display percentage
    - Add loading animation
    - _Requirements: 4.4_
  
  - [x] 15.6 Create IngestionStatusDisplay component
    - Integrate useIngestionStatus hook
    - Display progress during processing
    - Display success message on completion
    - Display error message on failure
    - Implement navigation to dashboard on completion
    - Add retry button on failure
    - _Requirements: 4.4, 14.5_
  
  - [ ]* 15.7 Write unit tests for UI components
    - Test progress bar rendering
    - Test percentage calculation
    - Test error display
    - Test navigation on completion

- [x] 16. Checkpoint - Verify frontend integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Update API Gateway and SAM template
  - [x] 17.1 Add new API endpoints to template
    - Add POST /repos/ingest route to IngestAsyncFunction
    - Add GET /ingestion/status/{job_id} route to GetStatusFunction
    - Configure CORS headers for both endpoints
    - Set appropriate timeouts and memory limits
    - _Requirements: 11.1_
  
  - [x] 17.2 Configure SQS event source for worker
    - Add SQS trigger to ProcessRepoWorkerFunction
    - Set batch size to 1
    - Configure visibility timeout to 900 seconds
    - Set reserved concurrency to 5
    - _Requirements: 10.4, 10.5_
  
  - [x] 17.3 Add IAM policies to Lambda roles
    - Grant Ingestion Service access to DynamoDB and SQS
    - Grant Worker access to DynamoDB, S3, Bedrock, SQS
    - Grant Status Handler access to DynamoDB
    - Follow principle of least privilege
  
  - [ ]* 17.4 Write infrastructure validation tests
    - Test all resources are created
    - Test IAM policies are correct
    - Test event source mappings work

- [x] 18. Implement backward compatibility verification
  - [ ]* 18.1 Write property test for Vector Store schema
    - **Property 20: Vector Store Schema Compatibility**
    - **Validates: Requirements 9.4**
    - Test async worker uses same schema as sync implementation
  
  - [ ]* 18.2 Write integration tests for existing features
    - Test architecture analysis endpoint still works
    - Test chat endpoint still works
    - Test documentation generation still works
    - Test file content retrieval still works
    - _Requirements: 9.5, 15.8_

- [ ] 19. Implement end-to-end integration tests
  - [ ]* 19.1 Write E2E test for successful ingestion
    - Upload small repository
    - Poll status until completed
    - Verify embeddings in Vector_Store
    - Verify repository metadata
    - Test existing features work with new repo
    - _Requirements: 15.3_
  
  - [ ]* 19.2 Write E2E test for duplicate requests
    - Upload same repository twice
    - Verify second request returns existing job_id
    - Verify no duplicate processing occurs
    - _Requirements: 15.5_
  
  - [ ]* 19.3 Write E2E test for error scenarios
    - Test invalid ZIP file handling
    - Test network timeout retry
    - Test out of memory handling
    - Test stale job detection
    - _Requirements: 15.4_
  
  - [ ]* 19.4 Write E2E test for large repository
    - Upload repository with 500 files
    - Verify batch processing works
    - Verify progress updates occur
    - Verify completion within 15 minutes
    - _Requirements: 15.3_

- [ ] 20. Final checkpoint - Complete system verification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 21. Create deployment documentation
  - Document infrastructure deployment steps
  - Document environment variable configuration
  - Document monitoring setup
  - Create operational runbook for common issues
  - Document rollback procedures

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and integration points
- The implementation maintains full backward compatibility with existing features
- All async components use existing modules (code_processor, bedrock_client, vector_store)
- Frontend polling provides real-time progress updates without WebSocket complexity
- Error handling distinguishes transient (retryable) from permanent (non-retryable) errors
- Memory management prevents Lambda OOM errors for large repositories
- Idempotency prevents duplicate processing of the same repository
- Comprehensive logging and monitoring enable production troubleshooting
