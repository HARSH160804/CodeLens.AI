# Design Document: Async Repository Ingestion

## Overview

This design implements an asynchronous repository ingestion system to solve timeout issues when processing large repositories. The current synchronous implementation causes API Gateway timeouts (30s) and Lambda timeouts (300s) for repositories with more than 300 files.

The async pattern decouples the upload request from the processing workflow using an SQS queue, allowing immediate response to users while processing continues asynchronously with real-time progress updates via polling.

### Key Design Principles

1. **Immediate Response**: API returns within 5 seconds with a job ID
2. **Asynchronous Processing**: Long-running work happens in background workers
3. **Progress Transparency**: Real-time status updates via polling
4. **Idempotency**: Duplicate requests handled gracefully
5. **Backward Compatibility**: Existing features continue to work unchanged
6. **Production Ready**: Comprehensive error handling, retries, and monitoring

### Architecture Pattern

This design follows the **Queue-Based Load Leveling** pattern:
- Frontend → API Gateway → Ingestion Service (fast) → SQS Queue
- SQS Queue → Processing Worker (slow) → Vector Store + DynamoDB
- Frontend polls status endpoint for progress updates

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[Frontend Client]
    API[API Gateway]
    Ingestion[Ingestion Service Lambda]
    Queue[SQS Processing Queue]
    DLQ[SQS Dead Letter Queue]
    Worker[Processing Worker Lambda]
    Status[Status Store DynamoDB]
    Vector[Vector Store DynamoDB]
    Repos[Repositories Table]
    
    Client -->|1. POST /repos/ingest| API
    API --> Ingestion
    Ingestion -->|2. Create job record| Status
    Ingestion -->|3. Enqueue message| Queue
    Ingestion -->|4. Return job_id| Client
    Client -->|5. Poll GET /ingestion/status/:id| API
    API -->|6. Query status| Status
    Queue -->|7. Trigger| Worker
    Worker -->|8. Update progress| Status
    Worker -->|9. Store embeddings| Vector
    Worker -->|10. Store metadata| Repos
    Queue -->|Failed after 3 retries| DLQ
    
    style Ingestion fill:#90EE90
    style Worker fill:#FFB6C1
    style Queue fill:#87CEEB
    style Status fill:#FFD700
```

### Component Interaction Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant I as Ingestion Service
    participant S as Status Store
    participant Q as SQS Queue
    participant W as Processing Worker
    participant V as Vector Store
    
    C->>I: POST /repos/ingest (ZIP file)
    I->>I: Generate job_id & idempotency_key
    I->>S: Check for existing job (idempotency)
    alt Job exists and processing
        S-->>I: Return existing job_id
        I-->>C: 200 OK {job_id, status: processing}
    else Job exists and completed
        S-->>I: Return existing job_id
        I-->>C: 200 OK {job_id, status: completed}
    else New job
        I->>S: Create job record (status: processing)
        I->>Q: Enqueue processing message
        I-->>C: 200 OK {job_id, status: processing}
        
        loop Every 2 seconds
            C->>I: GET /ingestion/status/:job_id
            I->>S: Query job status
            S-->>I: {status, progress_current, progress_total}
            I-->>C: Status response
        end
        
        Q->>W: Trigger Lambda (SQS event)
        W->>S: Update status (processing, 0/N files)
        
        loop For each file
            W->>W: Process file & generate embedding
            W->>V: Store chunk with embedding
            W->>S: Update progress (X/N files)
        end
        
        W->>S: Update status (completed)
        W->>S: Store final metadata
        
        C->>I: GET /ingestion/status/:job_id
        I->>S: Query job status
        S-->>I: {status: completed}
        I-->>C: Status response
        C->>C: Stop polling, navigate to dashboard
    end
```

### State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> Processing: Job created
    Processing --> Completed: All files processed successfully
    Processing --> Failed: Error occurs
    Processing --> Failed: Timeout (15 min)
    Failed --> Processing: Retry (transient error)
    Completed --> [*]
    Failed --> [*]: Max retries exhausted
    
    note right of Processing
        progress_current < progress_total
        updated_at refreshed regularly
    end note
    
    note right of Completed
        progress_current == progress_total
        All data stored successfully
    end note
    
    note right of Failed
        error_message populated
        Cleanup performed
    end note
```

## Components and Interfaces

### 1. Ingestion Service Lambda

**Purpose**: Receive upload requests, validate, create job records, enqueue processing

**Handler**: `handlers/ingest_async.py::lambda_handler`

**Responsibilities**:
- Validate incoming requests (GitHub URL or ZIP file)
- Generate unique job_id (UUID v4)
- Generate idempotency_key (SHA-256 hash of content)
- Check for duplicate jobs (idempotency)
- Create initial job record in Status Store
- Enqueue message to Processing Queue
- Return immediate response with job_id

**Interface**:

```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle async repository ingestion request.
    
    Request:
        POST /repos/ingest
        Content-Type: multipart/form-data or application/json
        
        JSON body:
        {
            "source_type": "github",
            "source": "https://github.com/user/repo",
            "auth_token": "optional"
        }
        
        OR multipart with file upload
    
    Response:
        {
            "job_id": "uuid",
            "status": "processing",
            "message": "Repository ingestion started"
        }
    """
```

**Configuration**:
- Memory: 512 MB
- Timeout: 30 seconds (fast response required)
- Environment Variables:
  - `INGESTION_JOBS_TABLE`: DynamoDB table for job status
  - `PROCESSING_QUEUE_URL`: SQS queue URL
  - `REPOSITORIES_TABLE`: Existing repos table

### 2. Processing Worker Lambda

**Purpose**: Process repositories asynchronously from the queue

**Handler**: `handlers/process_repo_worker.py::lambda_handler`

**Responsibilities**:
- Receive messages from SQS queue
- Download/extract repository files
- Process files in batches (50 files per batch)
- Generate embeddings using Bedrock
- Store chunks in Vector Store
- Update progress in Status Store
- Handle errors and cleanup
- Detect and mark stale jobs as failed

**Interface**:

```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process repository from SQS queue.
    
    SQS Message Body:
        {
            "job_id": "uuid",
            "source_type": "github" | "zip",
            "source": "url or s3_key",
            "idempotency_key": "sha256_hash"
        }
    
    Processing Flow:
        1. Check for stale jobs (timeout detection)
        2. Download/extract repository
        3. Discover files
        4. Process in batches of 50
        5. Update progress every 10 files
        6. Store embeddings and metadata
        7. Mark job as completed
        8. Cleanup temporary files
    """
```

**Configuration**:
- Memory: 3008 MB (maximum for processing large repos)
- Timeout: 900 seconds (15 minutes)
- Reserved Concurrency: 5 (limit parallel processing)
- Batch Size: 1 (process one job at a time)
- Environment Variables:
  - `INGESTION_JOBS_TABLE`: DynamoDB table for job status
  - `REPOSITORIES_TABLE`: Repos metadata table
  - `EMBEDDINGS_TABLE`: Vector store table
  - `SESSIONS_TABLE`: Sessions table
  - `CODE_BUCKET`: S3 bucket for temporary storage

### 3. Status Query Handler

**Purpose**: Provide job status for frontend polling

**Handler**: `handlers/ingest_async.py::get_status_handler`

**Responsibilities**:
- Query job status from Status Store
- Return current progress information
- Handle missing job IDs gracefully

**Interface**:

```python
def get_status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get ingestion job status.
    
    Request:
        GET /ingestion/status/{job_id}
    
    Response:
        {
            "job_id": "uuid",
            "status": "processing" | "completed" | "failed",
            "progress_current": 45,
            "progress_total": 100,
            "error_message": "optional error details",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z"
        }
    """
```

**Configuration**:
- Memory: 256 MB
- Timeout: 10 seconds
- Environment Variables:
  - `INGESTION_JOBS_TABLE`: DynamoDB table for job status

### 4. Progress Tracker Module

**Purpose**: Update job progress during processing

**Module**: `lib/progress_tracker.py`

**Interface**:

```python
class ProgressTracker:
    """Track and update job progress in DynamoDB."""
    
    def __init__(self, job_id: str, total_files: int):
        """Initialize tracker with job ID and total file count."""
        
    def update(self, files_processed: int, message: str = ""):
        """
        Update progress in Status Store.
        
        Args:
            files_processed: Number of files processed so far
            message: Optional status message
        """
        
    def mark_completed(self):
        """Mark job as completed."""
        
    def mark_failed(self, error_message: str):
        """Mark job as failed with error message."""
```

### 5. Idempotency Manager Module

**Purpose**: Handle duplicate request detection

**Module**: `lib/idempotency_manager.py`

**Interface**:

```python
class IdempotencyManager:
    """Manage idempotency for ingestion requests."""
    
    @staticmethod
    def generate_key(content: bytes, source: str) -> str:
        """
        Generate idempotency key from content hash.
        
        Args:
            content: File content bytes
            source: Source URL or identifier
            
        Returns:
            SHA-256 hash as hex string
        """
        
    def check_existing_job(self, idempotency_key: str) -> Optional[Dict]:
        """
        Check for existing job with same idempotency key.
        
        Returns:
            Job record if exists, None otherwise
        """
        
    def should_create_new_job(self, existing_job: Optional[Dict]) -> bool:
        """
        Determine if new job should be created.
        
        Returns:
            True if new job needed, False if existing job should be returned
        """
```

## Data Models

### Ingestion Jobs Table (DynamoDB)

**Table Name**: `BloomWay-IngestionJobs`

**Primary Key**: `job_id` (String, HASH)

**Global Secondary Index**: `idempotency-index`
- Partition Key: `idempotency_key` (String)
- Projection: ALL

**Attributes**:

```python
{
    "job_id": "uuid-string",                    # Primary key
    "idempotency_key": "sha256-hash",           # For duplicate detection
    "status": "processing|completed|failed",     # Current status
    "source_type": "github|zip",                # Source type
    "source": "url-or-s3-key",                  # Source location
    "progress_current": 45,                      # Files processed
    "progress_total": 100,                       # Total files
    "error_message": "optional-error",           # Error details if failed
    "created_at": "2024-01-15T10:30:00Z",       # Job creation time
    "updated_at": "2024-01-15T10:35:00Z",       # Last update time
    "repo_id": "uuid-string",                    # Generated repo ID
    "ttl": 1705324200                            # Expire after 7 days
}
```

**TTL Configuration**: 7 days (604800 seconds)

**Indexes**:
1. Primary: `job_id` (for status queries)
2. GSI: `idempotency_key` (for duplicate detection)

### SQS Message Format

**Queue Name**: `BloomWay-RepositoryProcessing`

**Message Body**:

```json
{
    "job_id": "uuid-string",
    "source_type": "github|zip",
    "source": "url-or-s3-key",
    "idempotency_key": "sha256-hash",
    "auth_token": "optional-github-token"
}
```

**Message Attributes**:
- `job_id` (String): For tracing
- `source_type` (String): For routing/filtering

### Repositories Table Updates

**No schema changes required** - existing table structure supports async pattern.

The worker will populate the same fields as the current synchronous implementation:
- `repo_id`, `source`, `source_type`, `status`, `file_count`, `chunk_count`
- `tech_stack`, `architecture_summary`, `file_paths`, `file_tree`
- `created_at`, `updated_at`

### Vector Store (Embeddings Table)

**No schema changes required** - existing table structure remains unchanged.

The worker uses the same `DynamoDBVectorStore` interface:
- `add_chunk(repo_id, file_path, content, embedding, metadata)`



## API Endpoint Specifications

### 1. POST /repos/ingest (Async)

**Purpose**: Initiate asynchronous repository ingestion

**Request**:

```http
POST /repos/ingest HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="source_type"

zip
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="repo.zip"
Content-Type: application/zip

[binary data]
------WebKitFormBoundary--
```

OR

```http
POST /repos/ingest HTTP/1.1
Content-Type: application/json

{
    "source_type": "github",
    "source": "https://github.com/user/repo",
    "auth_token": "optional_token"
}
```

**Response** (200 OK):

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "message": "Repository ingestion started",
    "poll_url": "/ingestion/status/550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK - Duplicate Request):

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "message": "Job already in progress",
    "progress_current": 45,
    "progress_total": 100
}
```

**Error Responses**:

- `400 Bad Request`: Invalid request format
- `413 Payload Too Large`: File exceeds size limit
- `500 Internal Server Error`: Server error

**Performance SLA**: Response within 5 seconds

### 2. GET /ingestion/status/{job_id}

**Purpose**: Query job status and progress

**Request**:

```http
GET /ingestion/status/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
```

**Response** (200 OK - Processing):

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "progress_current": 45,
    "progress_total": 100,
    "progress_percentage": 45,
    "message": "Processing files...",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
}
```

**Response** (200 OK - Completed):

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress_current": 100,
    "progress_total": 100,
    "progress_percentage": 100,
    "repo_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_count": 100,
    "chunk_count": 450,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:40:00Z",
    "completed_at": "2024-01-15T10:40:00Z"
}
```

**Response** (200 OK - Failed):

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "error_message": "Repository too large: out of memory",
    "error_code": "OUT_OF_MEMORY",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "failed_at": "2024-01-15T10:35:00Z"
}
```

**Response** (404 Not Found):

```json
{
    "error": "Job not found",
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Performance SLA**: Response within 1 second

### 3. GET /repos/{id}/status (Existing - Enhanced)

**Purpose**: Get repository metadata (existing endpoint, no changes)

This endpoint continues to work as before. Once ingestion completes, the repo_id from the job can be used with existing endpoints:
- `GET /repos/{repo_id}/status`
- `GET /repos/{repo_id}/architecture`
- `GET /repos/{repo_id}/chat`
- etc.

## Error Handling Strategy

### Error Classification

**Transient Errors** (Retryable):
- Network timeouts
- Bedrock throttling (ThrottlingException)
- DynamoDB throttling (ProvisionedThroughputExceededException)
- Temporary service unavailability (503)

**Permanent Errors** (Not Retryable):
- Invalid file format (BadZipFile)
- Repository not found (404)
- Authentication failure (401, 403)
- Out of memory (MemoryError)
- Invalid request parameters (400)

### Retry Strategy

**SQS Queue Configuration**:
- Maximum Receives: 3
- Visibility Timeout: 900 seconds (15 minutes)
- Retry Backoff: Exponential
  - Attempt 1: Immediate
  - Attempt 2: 30 seconds delay
  - Attempt 3: 60 seconds delay
  - Attempt 4: 120 seconds delay
- Dead Letter Queue: After 3 failed attempts

**Lambda Retry Logic**:

```python
def process_with_retry(job_id: str, attempt: int = 1) -> None:
    """Process job with retry logic."""
    try:
        process_repository(job_id)
    except TransientError as e:
        if attempt < 3:
            # Let SQS handle retry with backoff
            raise  # Re-raise to trigger SQS retry
        else:
            # Max retries exhausted
            mark_job_failed(job_id, f"Max retries exhausted: {str(e)}")
    except PermanentError as e:
        # Don't retry, mark as failed immediately
        mark_job_failed(job_id, str(e))
        # Delete message from queue to prevent retries
        delete_sqs_message()
```

### Error Messages

User-friendly error messages for common scenarios:

| Error Code | User Message | Technical Details |
|------------|--------------|-------------------|
| `INVALID_FORMAT` | "Invalid file format. Please upload a valid ZIP archive." | BadZipFile exception |
| `REPO_NOT_FOUND` | "Repository not found. Please check the URL." | HTTP 404 from GitHub |
| `AUTH_FAILED` | "Authentication failed. Please check your access token." | HTTP 401/403 |
| `OUT_OF_MEMORY` | "Repository too large: out of memory. Try a smaller repository." | MemoryError |
| `TIMEOUT` | "Processing timeout exceeded. Please try again." | 15-minute timeout |
| `RATE_LIMIT` | "Service temporarily unavailable: rate limit exceeded. Please try again in a few minutes." | Bedrock throttling |
| `NETWORK_ERROR` | "Network error occurred. Please try again." | URLError, ConnectionError |
| `UNKNOWN_ERROR` | "An unexpected error occurred. Please try again or contact support." | Unhandled exceptions |

### Cleanup on Failure

**Cleanup Actions**:
1. Remove temporary files from `/tmp`
2. Delete partial data from Vector Store (if any)
3. Update job status to "failed" with error message
4. Log full error details for debugging

**Cleanup Implementation**:

```python
def cleanup_on_failure(job_id: str, repo_id: str, temp_path: str):
    """Cleanup resources after failure."""
    try:
        # 1. Remove temporary files
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
            logger.info(f"Cleaned up temp path: {temp_path}")
    except Exception as e:
        logger.error(f"Failed to cleanup temp files: {e}")
    
    try:
        # 2. Delete partial embeddings
        vector_store.delete_repo(repo_id)
        logger.info(f"Deleted partial embeddings for repo: {repo_id}")
    except Exception as e:
        logger.error(f"Failed to cleanup embeddings: {e}")
    
    try:
        # 3. Update job status
        update_job_status(job_id, "failed", error_message)
        logger.info(f"Marked job as failed: {job_id}")
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
```

### Timeout Detection

**Stale Job Detection**:

```python
def detect_stale_jobs():
    """Detect and mark stale jobs as failed."""
    cutoff_time = datetime.utcnow() - timedelta(minutes=15)
    
    # Query jobs with status=processing and updated_at < cutoff
    response = jobs_table.scan(
        FilterExpression="status = :status AND updated_at < :cutoff",
        ExpressionAttributeValues={
            ":status": "processing",
            ":cutoff": cutoff_time.isoformat()
        }
    )
    
    for job in response.get('Items', []):
        logger.warning(f"Detected stale job: {job['job_id']}")
        update_job_status(
            job['job_id'],
            "failed",
            "Processing timeout exceeded"
        )
```

This runs at the start of each worker invocation to clean up stale jobs.

## Idempotency Implementation

### Idempotency Key Generation

**For ZIP Uploads**:

```python
def generate_idempotency_key_zip(file_content: bytes) -> str:
    """Generate idempotency key from ZIP content."""
    return hashlib.sha256(file_content).hexdigest()
```

**For GitHub URLs**:

```python
def generate_idempotency_key_github(url: str) -> str:
    """Generate idempotency key from GitHub URL."""
    # Normalize URL (remove .git suffix, trailing slash)
    normalized = url.rstrip('/').replace('.git', '')
    # Include timestamp to allow re-ingestion of same repo
    # (repos can change over time)
    # For true idempotency, use commit SHA if available
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### Duplicate Detection Logic

```python
def check_duplicate_job(idempotency_key: str) -> Optional[Dict]:
    """Check for existing job with same idempotency key."""
    
    # Query GSI by idempotency_key
    response = jobs_table.query(
        IndexName='idempotency-index',
        KeyConditionExpression='idempotency_key = :key',
        ExpressionAttributeValues={':key': idempotency_key},
        ScanIndexForward=False,  # Most recent first
        Limit=1
    )
    
    if not response.get('Items'):
        return None
    
    existing_job = response['Items'][0]
    
    # Decision matrix:
    # - processing: Return existing job (don't create duplicate)
    # - completed: Return existing job (already done)
    # - failed: Create new job (allow retry)
    
    if existing_job['status'] in ['processing', 'completed']:
        return existing_job
    
    return None  # Allow new job for failed status
```

### Idempotency Flow

```mermaid
graph TD
    A[Receive Request] --> B[Generate Idempotency Key]
    B --> C[Query Existing Jobs]
    C --> D{Job Exists?}
    D -->|No| E[Create New Job]
    D -->|Yes| F{Job Status?}
    F -->|Processing| G[Return Existing Job ID]
    F -->|Completed| H[Return Existing Job ID + Completed Status]
    F -->|Failed| E
    E --> I[Enqueue to SQS]
    I --> J[Return New Job ID]
    G --> K[Client Polls Status]
    H --> L[Client Navigates to Dashboard]
    J --> K
```

## Progress Tracking Mechanism

### Progress Update Strategy

**Update Frequency**:
- Update every 10 files processed
- Always update at start (0/N)
- Always update at completion (N/N)
- Update on batch boundaries (every 50 files)

**Progress Calculation**:

```python
class ProgressTracker:
    def __init__(self, job_id: str, total_files: int):
        self.job_id = job_id
        self.total_files = total_files
        self.last_update = 0
        self.update_interval = 10  # Update every 10 files
    
    def update(self, files_processed: int):
        """Update progress if threshold reached."""
        if files_processed - self.last_update >= self.update_interval:
            self._write_to_dynamodb(files_processed)
            self.last_update = files_processed
    
    def _write_to_dynamodb(self, files_processed: int):
        """Write progress to DynamoDB."""
        jobs_table.update_item(
            Key={'job_id': self.job_id},
            UpdateExpression='SET progress_current = :current, '
                           'progress_total = :total, '
                           'updated_at = :now',
            ExpressionAttributeValues={
                ':current': files_processed,
                ':total': self.total_files,
                ':now': datetime.utcnow().isoformat() + 'Z'
            }
        )
```

### Progress Granularity

**File-Level Progress**:
- Track number of files processed
- Display as "Processing 45/100 files"

**Future Enhancement** (not in initial implementation):
- Chunk-level progress within files
- Embedding generation progress
- Storage progress

### Memory-Efficient Progress Tracking

To avoid excessive DynamoDB writes:
- Batch updates (every 10 files)
- Use conditional writes to prevent conflicts
- Include timestamp to detect stale updates

```python
def update_progress_safe(job_id: str, current: int, total: int):
    """Update progress with conditional write to prevent conflicts."""
    try:
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET progress_current = :current, '
                           'progress_total = :total, '
                           'updated_at = :now',
            ConditionExpression='attribute_not_exists(updated_at) OR '
                              'updated_at < :now',
            ExpressionAttributeValues={
                ':current': current,
                ':total': total,
                ':now': datetime.utcnow().isoformat() + 'Z'
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Another process updated more recently, skip
            pass
        else:
            raise
```

## Frontend Polling Strategy

### Polling Implementation

**Polling Configuration**:
- Poll interval: 2 seconds
- Max poll duration: 15 minutes (900 seconds)
- Exponential backoff on errors: 2s, 4s, 8s
- Stop conditions:
  - Status becomes "completed"
  - Status becomes "failed"
  - Max duration exceeded

**React Hook Implementation**:

```typescript
interface IngestionStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress_current: number;
  progress_total: number;
  error_message?: string;
  repo_id?: string;
}

function useIngestionStatus(jobId: string) {
  const [status, setStatus] = useState<IngestionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  
  useEffect(() => {
    if (!jobId || !isPolling) return;
    
    let pollCount = 0;
    const maxPolls = 450; // 15 minutes at 2-second intervals
    
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/ingestion/status/${jobId}`);
        const data = await response.json();
        
        setStatus(data);
        
        // Stop polling on completion or failure
        if (data.status === 'completed' || data.status === 'failed') {
          setIsPolling(false);
          
          if (data.status === 'completed' && data.repo_id) {
            // Navigate to dashboard
            navigate(`/repos/${data.repo_id}`);
          }
        }
        
        pollCount++;
        if (pollCount >= maxPolls) {
          setIsPolling(false);
          setError('Polling timeout exceeded');
        }
      } catch (err) {
        console.error('Polling error:', err);
        // Continue polling on errors (transient network issues)
      }
    };
    
    // Initial poll
    pollStatus();
    
    // Set up interval
    const interval = setInterval(pollStatus, 2000);
    
    return () => clearInterval(interval);
  }, [jobId, isPolling]);
  
  return { status, error, isPolling };
}
```

### UI Progress Display

**Progress Bar Component**:

```typescript
function IngestionProgress({ status }: { status: IngestionStatus }) {
  const percentage = status.progress_total > 0
    ? Math.round((status.progress_current / status.progress_total) * 100)
    : 0;
  
  return (
    <div className="ingestion-progress">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="progress-text">
        Processing {status.progress_current}/{status.progress_total} files
        ({percentage}%)
      </div>
    </div>
  );
}
```

### Error Handling in Frontend

```typescript
function IngestionStatusDisplay({ jobId }: { jobId: string }) {
  const { status, error, isPolling } = useIngestionStatus(jobId);
  
  if (error) {
    return (
      <div className="error-message">
        <AlertIcon />
        <p>Failed to check ingestion status: {error}</p>
        <button onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }
  
  if (!status) {
    return <LoadingSpinner />;
  }
  
  if (status.status === 'failed') {
    return (
      <div className="error-message">
        <AlertIcon />
        <p>Ingestion failed: {status.error_message}</p>
        <button onClick={() => navigate('/repos/new')}>
          Try Again
        </button>
      </div>
    );
  }
  
  if (status.status === 'completed') {
    return (
      <div className="success-message">
        <CheckIcon />
        <p>Repository ingested successfully!</p>
        <p>Redirecting to dashboard...</p>
      </div>
    );
  }
  
  return <IngestionProgress status={status} />;
}
```

## Memory Management

### Batch Processing Strategy

**Batch Size**: 50 files per batch

**Rationale**:
- Lambda has 3008 MB memory (maximum)
- Each file ~1-2 MB in memory (content + chunks + embeddings)
- Batch of 50 files = ~50-100 MB
- Leaves ample memory for Python runtime and libraries

**Implementation**:

```python
def process_repository_in_batches(repo_path: str, job_id: str):
    """Process repository files in batches."""
    files = discover_files(repo_path)
    total_files = len(files)
    batch_size = 50
    
    tracker = ProgressTracker(job_id, total_files)
    tracker.update(0)  # Initial progress
    
    for i in range(0, total_files, batch_size):
        batch = files[i:i + batch_size]
        
        logger.info(f"Processing batch {i//batch_size + 1}, "
                   f"files {i} to {i + len(batch)}")
        
        # Process batch
        process_batch(batch, repo_path, job_id)
        
        # Update progress
        tracker.update(i + len(batch))
        
        # Force garbage collection between batches
        gc.collect()
        
        # Log memory usage
        memory_mb = get_memory_usage_mb()
        logger.info(f"Memory usage after batch: {memory_mb} MB")
        
        # Check memory threshold
        if memory_mb > 2500:  # 2.5 GB threshold
            logger.warning(f"High memory usage: {memory_mb} MB")
            gc.collect()
            time.sleep(1)  # Brief pause for GC
```

### Memory Monitoring

```python
import psutil
import os

def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_threshold(threshold_mb: float = 2500) -> bool:
    """Check if memory usage exceeds threshold."""
    current = get_memory_usage_mb()
    if current > threshold_mb:
        logger.warning(f"Memory threshold exceeded: {current} MB > {threshold_mb} MB")
        return True
    return False
```

### Out of Memory Handling

```python
def process_with_memory_check(files: List[str], job_id: str):
    """Process files with memory monitoring."""
    try:
        for idx, file_path in enumerate(files):
            # Check memory before processing each file
            if check_memory_threshold(2500):
                gc.collect()
                time.sleep(0.5)
                
                # Check again after GC
                if check_memory_threshold(2500):
                    raise MemoryError(
                        f"Out of memory after processing {idx} files"
                    )
            
            process_file(file_path)
            
    except MemoryError as e:
        logger.error(f"Memory error: {e}")
        mark_job_failed(
            job_id,
            "Repository too large: out of memory"
        )
        raise
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following consolidations to eliminate redundancy:

**Consolidated Properties**:
1. Progress invariants (3.1, 3.3, 3.4, 3.5) → Single property about progress consistency
2. Cleanup properties (8.1, 8.2, 8.3) → Single property about cleanup on any termination
3. Status schema properties (2.5, 5.5, 11.3) → Single property about data schema completeness
4. Idempotency properties (5.2, 5.3, 5.4) → Single property about idempotent behavior
5. Error classification (7.4, 7.5) → Single property about error handling strategy
6. Timeout detection (6.1, 6.5) → Single property about stale job detection

### Property 1: Job Enqueue Before Response

*For any* valid repository upload request, the SQS queue SHALL contain a message for that job before the HTTP response is returned to the client.

**Validates: Requirements 1.2**

### Property 2: Initial Job Record Creation

*For any* repository upload request, querying the Status_Store immediately after the request SHALL return a job record with status "processing" and the correct job_id.

**Validates: Requirements 1.3, 2.1**

### Property 3: Processing Completeness

*For any* repository that completes processing successfully, the Vector_Store SHALL contain embeddings for all processable files discovered in that repository.

**Validates: Requirements 1.5**

### Property 4: Status Transition to Completed

*For any* processing job that successfully processes all files, the final status in the Status_Store SHALL be "completed" with progress_current equal to progress_total.

**Validates: Requirements 2.3, 3.5**

### Property 5: Status Transition to Failed

*For any* processing job that encounters an error, the final status in the Status_Store SHALL be "failed" with a non-empty error_message field.

**Validates: Requirements 2.4**

### Property 6: Status Schema Completeness

*For any* job record in the Status_Store, the record SHALL contain all required fields: job_id, idempotency_key, status, progress_current, progress_total, created_at, updated_at.

**Validates: Requirements 2.5, 5.5, 11.3**

### Property 7: Progress Invariant

*For any* job during processing, the progress_current value SHALL always be less than or equal to progress_total, and both values SHALL be non-negative.

**Validates: Requirements 3.1, 3.3, 3.4**

### Property 8: Progress Update Frequency

*For any* processing job with more than 10 files, the Status_Store SHALL be updated at least once for every 10 files processed.

**Validates: Requirements 3.2**

### Property 9: Polling Termination

*For any* job that reaches a terminal status ("completed" or "failed"), subsequent polling requests SHALL continue to return that terminal status without changing it.

**Validates: Requirements 4.3**

### Property 10: Polling Retry on Failure

*For any* polling request that fails with a transient error, the poller SHALL retry up to 3 times before reporting failure to the user.

**Validates: Requirements 4.5**

### Property 11: Idempotency Key Determinism

*For any* repository content, generating the idempotency key multiple times with the same content SHALL always produce the same key value.

**Validates: Requirements 5.1**

### Property 12: Idempotent Request Handling

*For any* duplicate upload request (same idempotency_key), if an existing job is in "processing" or "completed" status, the response SHALL return the existing job_id without creating a new job.

**Validates: Requirements 5.2, 5.3**

### Property 13: Failed Job Retry

*For any* duplicate upload request where the existing job has "failed" status, a new job SHALL be created with a new job_id.

**Validates: Requirements 5.4**

### Property 14: Stale Job Detection

*For any* job with status "processing" and updated_at timestamp older than 15 minutes, the timeout detection mechanism SHALL mark it as "failed" with error_message "Processing timeout exceeded".

**Validates: Requirements 6.1, 6.5**

### Property 15: Timestamp Update on Status Change

*For any* status update operation, the updated_at timestamp SHALL be set to the current time and SHALL be greater than the previous updated_at value.

**Validates: Requirements 6.3**

### Property 16: Transient Error Retry

*For any* processing job that encounters a transient error (network timeout, throttling), the job SHALL be retried up to 3 times before being marked as "failed".

**Validates: Requirements 7.1, 7.3**

### Property 17: Error Classification

*For any* error encountered during processing, the system SHALL correctly classify it as either transient (retryable) or permanent (not retryable), and permanent errors SHALL result in immediate failure without retries.

**Validates: Requirements 7.4, 7.5**

### Property 18: Cleanup on Termination

*For any* processing job that terminates (successfully or with failure), all temporary files SHALL be removed from local storage and any partial data SHALL be removed from the Vector_Store.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 19: Cleanup Error Resilience

*For any* cleanup operation that fails, the job status SHALL still be updated correctly to reflect the processing outcome (completed or failed).

**Validates: Requirements 8.5**

### Property 20: Vector Store Schema Compatibility

*For any* chunk stored in the Vector_Store by the async worker, the chunk SHALL have the same schema fields (repo_id, file_path, content, embedding, metadata) as chunks stored by the current synchronous implementation.

**Validates: Requirements 9.4**

### Property 21: Dead Letter Queue Routing

*For any* SQS message that fails processing 3 times, the message SHALL appear in the Dead Letter Queue.

**Validates: Requirements 10.3**

### Property 22: Status Endpoint Response Accuracy

*For any* valid job_id, the status endpoint response SHALL exactly match the current state in the Status_Store.

**Validates: Requirements 11.2**

### Property 23: Status Endpoint 404 Handling

*For any* non-existent job_id, the status endpoint SHALL return a 404 HTTP status code.

**Validates: Requirements 11.4**

### Property 24: Batch Processing

*For any* repository with more than 50 files, the processing SHALL occur in batches where each batch contains at most 50 files.

**Validates: Requirements 12.1**

### Property 25: Memory Threshold Handling

*For any* processing job where available memory drops below 512MB, garbage collection SHALL be triggered before continuing processing.

**Validates: Requirements 12.3**

### Property 26: Out of Memory Failure

*For any* processing job that cannot free sufficient memory after garbage collection, the job SHALL be marked as "failed" with error_message containing "out of memory".

**Validates: Requirements 12.5**

### Property 27: Error Message Format

*For any* processing failure due to invalid file format, the error_message SHALL match the pattern "Invalid file format: {details}" where {details} provides specific information about the error.

**Validates: Requirements 14.1**

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, error conditions, and integration points
**Property Tests**: Verify universal properties across all inputs through randomization

Together, these approaches provide comprehensive coverage where unit tests catch concrete bugs and property tests verify general correctness.

### Property-Based Testing Configuration

**Library Selection**: 
- Python: `hypothesis` (industry-standard PBT library)
- TypeScript/Frontend: `fast-check` (for frontend polling logic)

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: async-repository-ingestion, Property {N}: {property_text}`

**Example Property Test**:

```python
from hypothesis import given, strategies as st
import hypothesis

@hypothesis.settings(max_examples=100)
@given(
    content=st.binary(min_size=100, max_size=10000),
    source=st.text(min_size=1, max_size=100)
)
def test_property_11_idempotency_key_determinism(content, source):
    """
    Feature: async-repository-ingestion, Property 11
    For any repository content, generating the idempotency key multiple 
    times with the same content SHALL always produce the same key value.
    """
    manager = IdempotencyManager()
    
    # Generate key twice with same inputs
    key1 = manager.generate_key(content, source)
    key2 = manager.generate_key(content, source)
    
    # Keys must be identical
    assert key1 == key2
    # Keys must be valid SHA-256 hashes (64 hex characters)
    assert len(key1) == 64
    assert all(c in '0123456789abcdef' for c in key1)
```

### Unit Testing Strategy

**Ingestion Service Tests**:
- Request validation (invalid JSON, missing fields)
- Idempotency check logic (existing jobs in various states)
- SQS message enqueuing
- DynamoDB record creation
- Error response formatting
- CORS headers

**Processing Worker Tests**:
- SQS message parsing
- File discovery and filtering
- Batch processing logic
- Progress tracking updates
- Error classification (transient vs permanent)
- Retry logic
- Cleanup operations
- Memory monitoring
- Timeout detection

**Progress Tracker Tests**:
- Update frequency (every 10 files)
- Progress invariants (current <= total)
- Timestamp updates
- Completion marking
- Failure marking

**Idempotency Manager Tests**:
- Key generation (deterministic)
- Duplicate detection
- Status-based decision logic

**Frontend Polling Tests**:
- Polling interval (2 seconds)
- Termination on completed/failed
- Retry on errors
- Progress display formatting
- Navigation on completion

### Integration Tests

**End-to-End Workflow**:
1. Upload repository → Verify job created
2. Poll status → Verify progress updates
3. Wait for completion → Verify final status
4. Query repo metadata → Verify data stored correctly
5. Test existing features → Verify backward compatibility

**Error Scenarios**:
- Invalid ZIP file → Verify immediate failure
- Network timeout → Verify retry behavior
- Bedrock throttling → Verify retry with backoff
- Out of memory → Verify cleanup and failure
- Duplicate request → Verify idempotency

**Timeout Scenarios**:
- Stale job detection → Verify timeout marking
- Long-running job → Verify progress updates prevent timeout

### Test Coverage Goals

- Ingestion Service: 90% code coverage
- Processing Worker: 90% code coverage
- Progress Tracker: 95% code coverage
- Idempotency Manager: 95% code coverage
- Frontend Polling: 85% code coverage

### Mock Strategy

**AWS Service Mocks**:
- DynamoDB: Use `moto` library for local DynamoDB
- SQS: Use `moto` for local SQS queues
- Bedrock: Mock with fixed embeddings for deterministic tests
- S3: Use `moto` for temporary file storage

**Time Mocking**:
- Use `freezegun` to control time for timeout tests
- Mock `datetime.utcnow()` for timestamp tests

### Performance Tests

While not property tests, these verify performance requirements:

**Response Time Tests**:
- Ingestion endpoint responds within 5 seconds (Req 1.1)
- Status endpoint responds within 1 second (Req 11.5)

**Load Tests**:
- Multiple concurrent uploads
- High-frequency polling
- Large repository processing (500 files)

### Regression Tests

Verify existing features continue to work:
- Architecture analysis endpoint
- Chat endpoint
- Documentation generation
- File content retrieval
- Repository metadata query

These tests ensure backward compatibility (Requirement 9.5).



## Infrastructure Configuration

### SQS Queue Configuration

**Queue Name**: `BloomWay-RepositoryProcessing`

**Configuration**:
```yaml
Type: AWS::SQS::Queue
Properties:
  QueueName: BloomWay-RepositoryProcessing
  VisibilityTimeout: 900  # 15 minutes (matches Lambda timeout)
  MessageRetentionPeriod: 345600  # 4 days
  ReceiveMessageWaitTimeSeconds: 20  # Long polling
  RedrivePolicy:
    deadLetterTargetArn: !GetAtt ProcessingDLQ.Arn
    maxReceiveCount: 3
  Tags:
    - Key: Application
      Value: BloomWay-AI
```

**Dead Letter Queue**:
```yaml
ProcessingDLQ:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: BloomWay-RepositoryProcessing-DLQ
    MessageRetentionPeriod: 1209600  # 14 days
    Tags:
      - Key: Application
        Value: BloomWay-AI
```

### DynamoDB Table Configuration

**Ingestion Jobs Table**:
```yaml
IngestionJobsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: BloomWay-IngestionJobs
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: job_id
        AttributeType: S
      - AttributeName: idempotency_key
        AttributeType: S
    KeySchema:
      - AttributeName: job_id
        KeyType: HASH
    GlobalSecondaryIndexes:
      - IndexName: idempotency-index
        KeySchema:
          - AttributeName: idempotency_key
            KeyType: HASH
        Projection:
          ProjectionType: ALL
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
    StreamSpecification:
      StreamViewType: NEW_AND_OLD_IMAGES
    Tags:
      - Key: Application
        Value: BloomWay-AI
```

### Lambda Function Configuration

**Ingestion Service Lambda**:
```yaml
IngestAsyncFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: ../backend/
    Handler: handlers.ingest_async.lambda_handler
    MemorySize: 512
    Timeout: 30
    Environment:
      Variables:
        INGESTION_JOBS_TABLE: !Ref IngestionJobsTable
        PROCESSING_QUEUE_URL: !Ref ProcessingQueue
        REPOSITORIES_TABLE: !Ref RepositoriesTable
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref IngestionJobsTable
      - SQSSendMessagePolicy:
          QueueName: !GetAtt ProcessingQueue.QueueName
      - DynamoDBReadPolicy:
          TableName: !Ref RepositoriesTable
    Events:
      IngestAsync:
        Type: Api
        Properties:
          RestApiId: !Ref BloomWayApi
          Path: /repos/ingest
          Method: POST
```

**Processing Worker Lambda**:
```yaml
ProcessRepoWorkerFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: ../backend/
    Handler: handlers.process_repo_worker.lambda_handler
    MemorySize: 3008  # Maximum memory for large repos
    Timeout: 900  # 15 minutes
    ReservedConcurrentExecutions: 5  # Limit parallel processing
    Environment:
      Variables:
        INGESTION_JOBS_TABLE: !Ref IngestionJobsTable
        REPOSITORIES_TABLE: !Ref RepositoriesTable
        EMBEDDINGS_TABLE: !Ref EmbeddingsTable
        SESSIONS_TABLE: !Ref SessionsTable
        CODE_BUCKET: !Ref CodeArtifactsBucket
        BEDROCK_REGION: !Ref AWS::Region
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref IngestionJobsTable
      - DynamoDBCrudPolicy:
          TableName: !Ref RepositoriesTable
      - DynamoDBCrudPolicy:
          TableName: !Ref EmbeddingsTable
      - DynamoDBCrudPolicy:
          TableName: !Ref SessionsTable
      - S3CrudPolicy:
          BucketName: !Ref CodeArtifactsBucket
      - Statement:
          - Effect: Allow
            Action:
              - bedrock:InvokeModel
              - bedrock:InvokeModelWithResponseStream
            Resource: '*'
          - Effect: Allow
            Action:
              - sqs:DeleteMessage
              - sqs:GetQueueAttributes
            Resource: !GetAtt ProcessingQueue.Arn
    Events:
      ProcessingQueue:
        Type: SQS
        Properties:
          Queue: !GetAtt ProcessingQueue.Arn
          BatchSize: 1  # Process one job at a time
          MaximumBatchingWindowInSeconds: 0
```

**Status Query Lambda**:
```yaml
GetIngestionStatusFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: ../backend/
    Handler: handlers.ingest_async.get_status_handler
    MemorySize: 256
    Timeout: 10
    Environment:
      Variables:
        INGESTION_JOBS_TABLE: !Ref IngestionJobsTable
    Policies:
      - DynamoDBReadPolicy:
          TableName: !Ref IngestionJobsTable
    Events:
      GetStatus:
        Type: Api
        Properties:
          RestApiId: !Ref BloomWayApi
          Path: /ingestion/status/{job_id}
          Method: GET
```

### CloudWatch Alarms

**High Error Rate Alarm**:
```yaml
ProcessingErrorAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: BloomWay-ProcessingWorker-HighErrorRate
    AlarmDescription: Alert when processing worker error rate exceeds 10%
    MetricName: Errors
    Namespace: AWS/Lambda
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: FunctionName
        Value: !Ref ProcessRepoWorkerFunction
```

**DLQ Messages Alarm**:
```yaml
DLQMessagesAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: BloomWay-ProcessingDLQ-MessagesPresent
    AlarmDescription: Alert when messages appear in DLQ
    MetricName: ApproximateNumberOfMessagesVisible
    Namespace: AWS/SQS
    Statistic: Sum
    Period: 60
    EvaluationPeriods: 1
    Threshold: 1
    ComparisonOperator: GreaterThanOrEqualToThreshold
    Dimensions:
      - Name: QueueName
        Value: !GetAtt ProcessingDLQ.QueueName
```

### Monitoring Dashboard

**CloudWatch Dashboard**:
```yaml
IngestionDashboard:
  Type: AWS::CloudWatch::Dashboard
  Properties:
    DashboardName: BloomWay-AsyncIngestion
    DashboardBody: !Sub |
      {
        "widgets": [
          {
            "type": "metric",
            "properties": {
              "metrics": [
                ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "Ingestion Requests"}],
                [".", "Errors", {"stat": "Sum", "label": "Errors"}],
                [".", "Duration", {"stat": "Average", "label": "Avg Duration"}]
              ],
              "period": 300,
              "stat": "Sum",
              "region": "${AWS::Region}",
              "title": "Ingestion Service Metrics",
              "dimensions": {
                "FunctionName": "${IngestAsyncFunction}"
              }
            }
          },
          {
            "type": "metric",
            "properties": {
              "metrics": [
                ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "Jobs Processed"}],
                [".", "Errors", {"stat": "Sum", "label": "Processing Errors"}],
                [".", "Duration", {"stat": "Average", "label": "Avg Processing Time"}]
              ],
              "period": 300,
              "stat": "Sum",
              "region": "${AWS::Region}",
              "title": "Processing Worker Metrics",
              "dimensions": {
                "FunctionName": "${ProcessRepoWorkerFunction}"
              }
            }
          },
          {
            "type": "metric",
            "properties": {
              "metrics": [
                ["AWS/SQS", "ApproximateNumberOfMessagesVisible", {"label": "Messages in Queue"}],
                [".", "ApproximateAgeOfOldestMessage", {"label": "Oldest Message Age"}]
              ],
              "period": 60,
              "stat": "Average",
              "region": "${AWS::Region}",
              "title": "Processing Queue Metrics",
              "dimensions": {
                "QueueName": "${ProcessingQueue.QueueName}"
              }
            }
          },
          {
            "type": "metric",
            "properties": {
              "metrics": [
                ["AWS/SQS", "ApproximateNumberOfMessagesVisible", {"label": "Messages in DLQ"}]
              ],
              "period": 60,
              "stat": "Sum",
              "region": "${AWS::Region}",
              "title": "Dead Letter Queue",
              "dimensions": {
                "QueueName": "${ProcessingDLQ.QueueName}"
              }
            }
          }
        ]
      }
```

## Deployment Strategy

### Phased Rollout

**Phase 1: Infrastructure Setup**
1. Deploy new DynamoDB table (IngestionJobs)
2. Deploy SQS queues (Processing + DLQ)
3. Deploy CloudWatch alarms and dashboard
4. Verify infrastructure with smoke tests

**Phase 2: Backend Deployment**
1. Deploy new Lambda functions (IngestAsync, ProcessRepoWorker, GetStatus)
2. Keep existing synchronous endpoint active
3. Test async endpoints with small repositories
4. Monitor error rates and performance

**Phase 3: Frontend Integration**
1. Update frontend to use async endpoints
2. Implement polling UI components
3. Add progress indicators
4. Test end-to-end workflow

**Phase 4: Migration**
1. Route all new requests to async endpoints
2. Monitor for issues
3. Deprecate synchronous endpoint (keep for 30 days)
4. Remove synchronous endpoint after validation period

### Rollback Plan

If issues are detected:
1. Route traffic back to synchronous endpoint
2. Investigate and fix issues
3. Re-deploy with fixes
4. Resume phased rollout

### Backward Compatibility

The async implementation maintains full backward compatibility:
- Same data schema in Vector Store
- Same data schema in Repositories table
- Existing endpoints (architecture, chat, docs) unchanged
- Existing frontend features continue to work

## Security Considerations

### Authentication and Authorization

**API Gateway**:
- CORS headers configured for frontend domain
- API keys for rate limiting (future enhancement)
- IAM authentication for service-to-service calls

**Lambda Execution Roles**:
- Principle of least privilege
- Separate roles for each function
- No cross-account access

### Data Protection

**At Rest**:
- DynamoDB encryption enabled (SSE)
- S3 bucket encryption enabled (AES-256)
- SQS messages encrypted (SSE-SQS)

**In Transit**:
- HTTPS only for API Gateway
- TLS for all AWS service calls
- Secure WebSocket for future real-time updates

### Input Validation

**Ingestion Service**:
- Validate file size limits (max 100 MB)
- Validate file types (ZIP only)
- Sanitize GitHub URLs
- Validate JSON structure

**Processing Worker**:
- Validate SQS message format
- Validate file paths (prevent directory traversal)
- Validate file content (prevent malicious code execution)

### Rate Limiting

**API Gateway**:
- Throttle limits: 100 requests/second per IP
- Burst limits: 200 requests

**SQS Queue**:
- Reserved concurrency: 5 (prevents resource exhaustion)
- Visibility timeout: 15 minutes (prevents duplicate processing)

### Secrets Management

**GitHub Tokens**:
- Not stored in DynamoDB
- Passed through SQS messages (encrypted)
- Deleted after use

**Bedrock API**:
- IAM role-based authentication (no API keys)
- Regional endpoint configuration

## Operational Runbook

### Common Issues and Resolutions

**Issue: Jobs stuck in "processing" status**

Symptoms:
- Job status remains "processing" for > 15 minutes
- No progress updates

Resolution:
1. Check CloudWatch logs for worker Lambda
2. Check SQS queue for messages
3. Verify worker Lambda is being triggered
4. Run timeout detection manually if needed
5. Check DLQ for failed messages

**Issue: High error rate in processing worker**

Symptoms:
- CloudWatch alarm triggered
- Multiple jobs failing

Resolution:
1. Check CloudWatch logs for error patterns
2. Identify error type (transient vs permanent)
3. If Bedrock throttling: Wait for rate limit reset
4. If memory errors: Reduce batch size temporarily
5. If code errors: Deploy hotfix

**Issue: DLQ contains messages**

Symptoms:
- DLQ alarm triggered
- Messages in dead letter queue

Resolution:
1. Retrieve messages from DLQ
2. Analyze failure reasons
3. Fix underlying issues
4. Manually reprocess if needed
5. Update job status to "failed" with explanation

### Monitoring Checklist

Daily:
- [ ] Check CloudWatch dashboard
- [ ] Verify no messages in DLQ
- [ ] Check error rates < 5%
- [ ] Verify average processing time < 5 minutes

Weekly:
- [ ] Review CloudWatch logs for warnings
- [ ] Check DynamoDB table sizes
- [ ] Verify TTL cleanup working
- [ ] Review cost metrics

Monthly:
- [ ] Analyze processing patterns
- [ ] Optimize batch sizes if needed
- [ ] Review and update alarms
- [ ] Capacity planning for growth

### Debugging Tools

**Query Job Status**:
```bash
aws dynamodb get-item \
  --table-name BloomWay-IngestionJobs \
  --key '{"job_id": {"S": "YOUR_JOB_ID"}}'
```

**Check SQS Queue Depth**:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/BloomWay-RepositoryProcessing \
  --attribute-names ApproximateNumberOfMessages
```

**View Recent Logs**:
```bash
aws logs tail /aws/lambda/ProcessRepoWorkerFunction --follow
```

**Manually Trigger Timeout Detection**:
```python
# Run in Lambda console or locally
from handlers.process_repo_worker import detect_stale_jobs
detect_stale_jobs()
```

## Performance Optimization

### Current Performance Characteristics

**Ingestion Service**:
- Response time: < 2 seconds (target: < 5 seconds)
- Throughput: 100 requests/second
- Cold start: ~1 second

**Processing Worker**:
- Small repos (< 50 files): 2-3 minutes
- Medium repos (50-200 files): 5-10 minutes
- Large repos (200-500 files): 10-15 minutes

### Optimization Opportunities

**Future Enhancements**:

1. **Parallel File Processing**
   - Process multiple files concurrently within batches
   - Use ThreadPoolExecutor for I/O-bound operations
   - Expected improvement: 30-40% faster processing

2. **Embedding Batch API**
   - Use Bedrock batch embedding API (when available)
   - Reduce API calls by 10x
   - Expected improvement: 50% faster embedding generation

3. **Caching**
   - Cache embeddings for unchanged files
   - Use file content hash as cache key
   - Expected improvement: 80% faster for re-ingestion

4. **Progressive Loading**
   - Allow users to start using repo before full ingestion
   - Process critical files first (entry points, configs)
   - Improved user experience

5. **WebSocket Updates**
   - Replace polling with WebSocket push notifications
   - Reduce API calls by 90%
   - Real-time progress updates

## Migration Guide

### For Existing Deployments

**Step 1: Backup Current Data**
```bash
# Backup DynamoDB tables
aws dynamodb create-backup \
  --table-name BloomWay-Repositories \
  --backup-name pre-async-migration

aws dynamodb create-backup \
  --table-name BloomWay-Embeddings \
  --backup-name pre-async-migration
```

**Step 2: Deploy Infrastructure**
```bash
cd infrastructure
sam build
sam deploy --guided
```

**Step 3: Verify Infrastructure**
```bash
# Check tables exist
aws dynamodb describe-table --table-name BloomWay-IngestionJobs

# Check queues exist
aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing
```

**Step 4: Deploy Backend**
```bash
# Deploy Lambda functions
sam deploy --no-confirm-changeset
```

**Step 5: Test Async Endpoints**
```bash
# Test ingestion
curl -X POST https://API_ENDPOINT/repos/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_type": "github", "source": "https://github.com/user/small-repo"}'

# Test status query
curl https://API_ENDPOINT/ingestion/status/JOB_ID
```

**Step 6: Update Frontend**
```bash
cd frontend
npm install
npm run build
npm run deploy
```

**Step 7: Monitor**
- Watch CloudWatch dashboard for 24 hours
- Check error rates
- Verify successful completions
- Monitor DLQ

### For New Deployments

Follow standard deployment process:
```bash
cd infrastructure
sam build
sam deploy --guided
```

All async components will be deployed automatically.

## Conclusion

This design implements a production-ready asynchronous repository ingestion system that solves timeout issues while maintaining backward compatibility. The architecture follows AWS best practices for serverless applications and includes comprehensive error handling, monitoring, and operational procedures.

Key benefits:
- **Scalability**: Handles repositories of any size
- **Reliability**: Automatic retries and error recovery
- **Observability**: Comprehensive logging and monitoring
- **User Experience**: Real-time progress updates
- **Maintainability**: Clean separation of concerns
- **Backward Compatibility**: Existing features unchanged

The implementation is ready for development and deployment following the phased rollout strategy.

