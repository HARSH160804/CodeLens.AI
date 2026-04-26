# Requirements Document

## Introduction

This document specifies requirements for asynchronous repository ingestion to solve network timeout issues when processing large repositories. The current synchronous implementation causes API Gateway timeouts (30s) and Lambda timeouts (300s) for repositories with more than 300 files, resulting in "Network Error" messages for users even though processing may continue in the background.

The async ingestion system will decouple the upload request from the processing workflow, allowing immediate response to users while processing continues asynchronously with real-time progress updates.

## Glossary

- **Ingestion_Service**: The Lambda function that receives repository upload requests
- **Processing_Queue**: The SQS queue that holds repository processing jobs
- **Processing_Worker**: The Lambda function that processes repositories from the queue
- **Status_Store**: The DynamoDB table that stores ingestion status and progress
- **Progress_Tracker**: The component that updates processing progress in the Status_Store
- **Status_Poller**: The frontend component that polls for status updates
- **Vector_Store**: The storage system for code embeddings and chunks
- **Repository**: A collection of code files uploaded by a user
- **Ingestion_Job**: A single repository processing task
- **Job_ID**: A unique identifier for an Ingestion_Job
- **Processing_Status**: The current state of an Ingestion_Job (processing, completed, failed)
- **Idempotency_Key**: A unique identifier to prevent duplicate processing of the same repository

## Requirements

### Requirement 1: Async Processing Pattern

**User Story:** As a user, I want to upload large repositories without timeout errors, so that I can analyze repositories of any size.

#### Acceptance Criteria

1. WHEN a repository upload request is received, THE Ingestion_Service SHALL return a response within 5 seconds
2. THE Ingestion_Service SHALL enqueue the Ingestion_Job to the Processing_Queue before returning the response
3. THE Ingestion_Service SHALL return a Job_ID and initial Processing_Status of "processing" to the client
4. THE Processing_Worker SHALL process Ingestion_Jobs from the Processing_Queue asynchronously
5. THE Processing_Worker SHALL complete all existing ingestion operations (embeddings, chunking, vector storage)

### Requirement 2: Status Management

**User Story:** As a user, I want to know the current status of my repository processing, so that I understand when analysis is complete.

#### Acceptance Criteria

1. WHEN an Ingestion_Job is created, THE Ingestion_Service SHALL store the initial status in the Status_Store
2. WHILE processing an Ingestion_Job, THE Processing_Worker SHALL update the Processing_Status in the Status_Store
3. WHEN processing completes successfully, THE Processing_Worker SHALL set the Processing_Status to "completed"
4. IF processing fails, THEN THE Processing_Worker SHALL set the Processing_Status to "failed" with an error message
5. THE Status_Store SHALL maintain the following fields: Job_ID, Processing_Status, progress_current, progress_total, error_message, created_at, updated_at

### Requirement 3: Progress Tracking

**User Story:** As a user, I want to see real-time progress updates during repository processing, so that I know how much work remains.

#### Acceptance Criteria

1. WHILE processing files, THE Progress_Tracker SHALL update progress_current and progress_total in the Status_Store
2. THE Progress_Tracker SHALL update progress at least every 10 files processed
3. THE progress_current field SHALL represent the number of files processed
4. THE progress_total field SHALL represent the total number of files to process
5. WHEN all files are processed, THE Progress_Tracker SHALL set progress_current equal to progress_total

### Requirement 4: Status Polling

**User Story:** As a user, I want the interface to automatically update with processing progress, so that I don't need to manually refresh.

#### Acceptance Criteria

1. WHEN an Ingestion_Job is initiated, THE Status_Poller SHALL begin polling for status updates
2. THE Status_Poller SHALL poll the status endpoint every 2 seconds
3. WHEN the Processing_Status is "completed" or "failed", THE Status_Poller SHALL stop polling
4. THE Status_Poller SHALL display the current progress as "Processing X/Y files"
5. IF polling fails, THEN THE Status_Poller SHALL retry up to 3 times with exponential backoff

### Requirement 5: Idempotency

**User Story:** As a user, I want duplicate upload requests to be handled gracefully, so that I don't accidentally process the same repository multiple times.

#### Acceptance Criteria

1. WHEN a repository upload request is received, THE Ingestion_Service SHALL generate an Idempotency_Key from the repository content hash
2. IF an Ingestion_Job with the same Idempotency_Key exists with Processing_Status "processing", THEN THE Ingestion_Service SHALL return the existing Job_ID
3. IF an Ingestion_Job with the same Idempotency_Key exists with Processing_Status "completed", THEN THE Ingestion_Service SHALL return the existing Job_ID with status "completed"
4. IF an Ingestion_Job with the same Idempotency_Key exists with Processing_Status "failed", THEN THE Ingestion_Service SHALL create a new Ingestion_Job
5. THE Idempotency_Key SHALL be stored in the Status_Store

### Requirement 6: Timeout Detection

**User Story:** As a developer, I want stale processing jobs to be detected and marked as failed, so that the system doesn't show perpetual "processing" status.

#### Acceptance Criteria

1. WHEN an Ingestion_Job has Processing_Status "processing" for more than 15 minutes, THE Processing_Worker SHALL mark it as "failed"
2. THE Processing_Worker SHALL set the error_message to "Processing timeout exceeded"
3. THE Status_Store SHALL record the updated_at timestamp on every status update
4. THE timeout detection SHALL run before processing each new Ingestion_Job
5. THE timeout detection SHALL check all jobs with Processing_Status "processing" and updated_at older than 15 minutes

### Requirement 7: Error Handling and Retries

**User Story:** As a user, I want transient failures to be retried automatically, so that temporary issues don't cause permanent failures.

#### Acceptance Criteria

1. IF the Processing_Worker encounters a transient error (network timeout, throttling), THEN THE Processing_Queue SHALL retry the Ingestion_Job up to 3 times
2. WHEN the Processing_Queue retries an Ingestion_Job, THE retry SHALL use exponential backoff (30s, 60s, 120s)
3. IF all retries are exhausted, THEN THE Processing_Worker SHALL mark the Ingestion_Job as "failed"
4. THE Processing_Worker SHALL distinguish between transient errors (retryable) and permanent errors (not retryable)
5. IF a permanent error occurs (invalid file format, out of memory), THEN THE Processing_Worker SHALL immediately mark the job as "failed" without retrying

### Requirement 8: Resource Cleanup

**User Story:** As a developer, I want proper resource cleanup on success and failure, so that the system doesn't leak resources.

#### Acceptance Criteria

1. WHEN processing completes successfully, THE Processing_Worker SHALL remove temporary files from local storage
2. WHEN processing fails, THE Processing_Worker SHALL remove temporary files from local storage
3. WHEN processing fails, THE Processing_Worker SHALL remove partial data from the Vector_Store
4. THE Processing_Worker SHALL log all cleanup operations
5. IF cleanup fails, THEN THE Processing_Worker SHALL log the error but still mark the job status appropriately

### Requirement 9: Backward Compatibility

**User Story:** As a developer, I want existing functionality to remain unchanged, so that current features continue to work.

#### Acceptance Criteria

1. THE Processing_Worker SHALL use the existing code_processor module for file processing
2. THE Processing_Worker SHALL use the existing bedrock_client for generating embeddings
3. THE Processing_Worker SHALL use the existing Vector_Store interface for storing embeddings
4. THE Processing_Worker SHALL maintain the same data schema in the Vector_Store
5. THE existing architecture analysis, chat, and documentation features SHALL function without modification

### Requirement 10: Queue Configuration

**User Story:** As a developer, I want the processing queue properly configured, so that jobs are processed reliably.

#### Acceptance Criteria

1. THE Processing_Queue SHALL have a visibility timeout of 900 seconds (15 minutes)
2. THE Processing_Queue SHALL have a message retention period of 4 days
3. THE Processing_Queue SHALL have a dead letter queue for failed messages after 3 retries
4. THE Processing_Queue SHALL trigger the Processing_Worker Lambda function
5. THE Processing_Worker Lambda SHALL have a timeout of 900 seconds (15 minutes)

### Requirement 11: Status API Endpoint

**User Story:** As a frontend developer, I want a status endpoint to query job progress, so that I can display updates to users.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL provide a GET endpoint at /api/ingestion/status/{job_id}
2. WHEN the status endpoint is called, THE Ingestion_Service SHALL return the current Processing_Status from the Status_Store
3. THE status response SHALL include: Job_ID, Processing_Status, progress_current, progress_total, error_message, created_at, updated_at
4. IF the Job_ID does not exist, THEN THE Ingestion_Service SHALL return a 404 error
5. THE status endpoint SHALL respond within 1 second

### Requirement 12: Memory Management

**User Story:** As a developer, I want memory usage controlled during processing, so that Lambda functions don't run out of memory.

#### Acceptance Criteria

1. THE Processing_Worker SHALL process files in batches of 50 files maximum
2. WHEN a batch is completed, THE Processing_Worker SHALL release memory before processing the next batch
3. IF available memory drops below 512MB, THEN THE Processing_Worker SHALL pause processing and trigger garbage collection
4. THE Processing_Worker SHALL log memory usage at the start and end of each batch
5. IF memory cannot be freed, THEN THE Processing_Worker SHALL mark the job as "failed" with error "Out of memory"

### Requirement 13: Monitoring and Logging

**User Story:** As a developer, I want comprehensive logging and monitoring, so that I can troubleshoot issues.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL log all incoming requests with Job_ID and Idempotency_Key
2. THE Processing_Worker SHALL log the start and completion of each Ingestion_Job
3. THE Processing_Worker SHALL log progress updates every 50 files
4. THE Processing_Worker SHALL log all errors with full stack traces
5. THE Processing_Worker SHALL emit CloudWatch metrics for: jobs_started, jobs_completed, jobs_failed, processing_duration, files_processed

### Requirement 14: Graceful Degradation

**User Story:** As a user, I want meaningful error messages when processing fails, so that I understand what went wrong.

#### Acceptance Criteria

1. WHEN processing fails due to invalid file format, THE Processing_Worker SHALL set error_message to "Invalid file format: {details}"
2. WHEN processing fails due to timeout, THE Processing_Worker SHALL set error_message to "Processing timeout exceeded"
3. WHEN processing fails due to memory limits, THE Processing_Worker SHALL set error_message to "Repository too large: out of memory"
4. WHEN processing fails due to API throttling, THE Processing_Worker SHALL set error_message to "Service temporarily unavailable: rate limit exceeded"
5. THE error_message SHALL be displayed to the user in the frontend

### Requirement 15: Testing Requirements

**User Story:** As a developer, I want comprehensive test coverage, so that I can verify the system works correctly.

#### Acceptance Criteria

1. THE test suite SHALL include unit tests for the Ingestion_Service with 90% code coverage
2. THE test suite SHALL include unit tests for the Processing_Worker with 90% code coverage
3. THE test suite SHALL include integration tests for the complete async workflow
4. THE test suite SHALL include tests for all error scenarios (timeout, retry, failure, duplicate)
5. THE test suite SHALL include tests for idempotency with duplicate requests
6. THE test suite SHALL include tests for status transitions (processing → completed, processing → failed)
7. THE test suite SHALL include tests for progress tracking accuracy
8. THE test suite SHALL include tests for resource cleanup on success and failure
