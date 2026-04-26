# Big Repository Ingestion - Limitations & Solutions

## Current Limitations

### 1. Lambda Timeout (300 seconds = 5 minutes)
**Location**: `infrastructure/template.yaml` line 45
```yaml
IngestRepoFunction:
  Timeout: 300  # 5 minutes maximum
```

**Problem**: For large repositories, the ingestion process includes:
- Downloading/extracting the ZIP
- Processing all files (reading, chunking)
- Generating embeddings for each chunk (calls to Bedrock API)
- Storing embeddings in DynamoDB

If this takes longer than 5 minutes, Lambda times out and returns a network error to the frontend.

**What happens**:
- Frontend shows "Network Error"
- Repository is partially ingested (some files processed, some not)
- Database is left in inconsistent state

### 2. File Count Limit (500 files)
**Location**: `backend/handlers/ingest_repo.py` line 32
```python
MAX_FILES = 500
```

**Problem**: Repositories with more than 500 files are rejected immediately.

**What happens**:
```json
{
  "error": "Repository too large: 750 files found, maximum is 500",
  "status_code": 413
}
```

### 3. Memory Limit (512 MB)
**Location**: `infrastructure/template.yaml` line 44
```yaml
IngestRepoFunction:
  MemorySize: 512  # 512 MB
```

**Problem**: Large files or many files in memory can cause out-of-memory errors.

### 4. API Gateway Timeout (30 seconds)
**Problem**: API Gateway has a hard limit of 30 seconds for synchronous requests. Even though Lambda can run for 5 minutes, API Gateway will timeout after 30 seconds.

**What happens**:
- Frontend receives 504 Gateway Timeout
- Lambda continues running in the background
- User sees "Network Error" but ingestion might still complete

### 5. Bedrock API Rate Limits
**Problem**: Generating embeddings for thousands of chunks can hit Bedrock throttling limits.

**What happens**:
```json
{
  "error": "Bedrock API rate limit exceeded. Please try again later.",
  "status_code": 429
}
```

## Current Workarounds in Code

### 1. Early Status Storage
The code stores a "processing" status early:
```python
# Store early 'processing' status so frontend can poll even if API Gateway times out
repos_table.put_item(Item={
    'repo_id': repo_id,
    'status': 'processing',
    ...
})
```

This allows the frontend to poll for status even if the initial request times out.

### 2. Throttling Detection
The code detects Bedrock throttling:
```python
if error_code == 'ThrottlingException':
    return _error_response(429, "Bedrock API rate limit exceeded. Please try again later.")
```

## Solutions

### Solution 1: Asynchronous Processing (RECOMMENDED)
**Complexity**: Medium
**Effectiveness**: High
**Implementation Time**: 2-3 hours

**How it works**:
1. Change ingestion to be fully asynchronous
2. Return immediately with `status: "processing"`
3. Process repository in the background
4. Frontend polls for status updates

**Changes needed**:

1. **Modify ingestion handler** to return immediately:
```python
def lambda_handler(event, context):
    # Validate request
    # Store initial "processing" status
    # Invoke async processing (SQS or Step Functions)
    # Return immediately
    return {
        'statusCode': 202,  # Accepted
        'body': json.dumps({
            'repo_id': repo_id,
            'status': 'processing',
            'message': 'Repository ingestion started. Poll /repos/{id}/status for updates.'
        })
    }
```

2. **Create async processor** (separate Lambda or Step Function)
3. **Update frontend** to poll immediately instead of waiting for response

**Pros**:
- No timeout issues
- Can process repositories of any size
- Better user experience (progress updates)

**Cons**:
- More complex architecture
- Requires frontend changes

### Solution 2: Increase Limits (PARTIAL FIX)
**Complexity**: Low
**Effectiveness**: Medium
**Implementation Time**: 10 minutes

**Changes**:
```yaml
IngestRepoFunction:
  MemorySize: 3008  # Increase to 3 GB
  Timeout: 900      # Increase to 15 minutes (Lambda max)
```

```python
MAX_FILES = 1000  # Increase file limit
```

**Pros**:
- Easy to implement
- Handles medium-large repos

**Cons**:
- Still has hard limits
- API Gateway 30-second timeout remains
- More expensive (higher memory)
- Doesn't solve the fundamental problem

### Solution 3: Chunked Processing
**Complexity**: High
**Effectiveness**: High
**Implementation Time**: 4-6 hours

**How it works**:
1. Split repository into batches (e.g., 100 files per batch)
2. Process each batch separately
3. Update status after each batch
4. Frontend shows progress (e.g., "Processing 300/750 files")

**Pros**:
- Can handle unlimited repository size
- Provides progress feedback
- Resilient to failures (can retry individual batches)

**Cons**:
- Complex implementation
- Requires significant refactoring

### Solution 4: Stream Processing
**Complexity**: Very High
**Effectiveness**: Very High
**Implementation Time**: 1-2 days

**How it works**:
1. Upload files to S3 first
2. Trigger Lambda for each file (S3 event)
3. Process files in parallel
4. Aggregate results

**Pros**:
- Highly scalable
- Parallel processing
- No timeout issues

**Cons**:
- Very complex
- Requires major architecture changes
- Higher AWS costs

## Recommended Approach

### Phase 1: Quick Fix (10 minutes)
Increase limits to handle medium-large repos:

```yaml
# infrastructure/template.yaml
IngestRepoFunction:
  MemorySize: 1024  # 1 GB
  Timeout: 900      # 15 minutes (max)
```

```python
# backend/handlers/ingest_repo.py
MAX_FILES = 1000
```

This will handle repos up to ~1000 files that process in under 15 minutes.

### Phase 2: Async Processing (2-3 hours)
Implement fully asynchronous processing:

1. Return `202 Accepted` immediately
2. Process in background
3. Frontend polls for status
4. Show progress updates

This removes all timeout limitations.

### Phase 3: Optimization (optional)
- Batch processing for very large repos
- Parallel embedding generation
- Caching and deduplication

## Testing Different Repository Sizes

| Repo Size | Files | Expected Time | Current Limit | Will Work? |
|-----------|-------|---------------|---------------|------------|
| Small     | <100  | <1 min        | 5 min         | ✅ Yes     |
| Medium    | 100-300 | 1-3 min     | 5 min         | ✅ Yes     |
| Large     | 300-500 | 3-5 min     | 5 min         | ⚠️ Maybe   |
| Very Large| 500-1000| 5-10 min    | 5 min         | ❌ No      |
| Huge      | >1000 | >10 min       | 5 min         | ❌ No      |

## How to Know if Your Repo is Too Big

Before uploading, check:
1. **File count**: `find . -type f | wc -l`
2. **Total size**: `du -sh .`

**Current limits**:
- Max files: 500
- Max processing time: ~5 minutes
- Estimated: ~100 files per minute

**Rule of thumb**:
- <300 files: Should work fine
- 300-500 files: Might timeout
- >500 files: Will be rejected or timeout

## Immediate Action Items

### For You (User)
1. **Test with small repos first** (<100 files)
2. **If you need to ingest large repos**, let me know and I'll implement async processing
3. **Check file count** before uploading: `find . -type f | wc -l`

### For Me (Developer)
1. **Implement async processing** (Solution 1) - This is the proper fix
2. **Add progress indicators** to show processing status
3. **Add file count validation** before starting ingestion
4. **Add estimated time calculation** based on file count

## Can This Be Solved?

**YES**, this is 100% solvable. The solution is to make ingestion asynchronous:

1. User uploads repo
2. Backend returns immediately with "processing" status
3. Backend processes in background (no timeout)
4. Frontend polls for updates every 2 seconds
5. Shows progress: "Processing 450/750 files (60%)"
6. Completes when done (no matter how long it takes)

This is a standard pattern for long-running operations in serverless architectures.

**Do you want me to implement this now?** It will take about 2-3 hours to implement properly.
