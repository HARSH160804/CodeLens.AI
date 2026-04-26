# Async Ingestion - Safety Analysis

## Will It Break Anything?

**Short answer: NO, it's actually safer than the current implementation.**

## What We're Changing

### Current Implementation (Synchronous)
```
API Request → Lambda processes everything → Return result
              ↓
              - Download/extract repo
              - Process all files
              - Generate embeddings
              - Store in DynamoDB
              - Return response
```

### New Implementation (Asynchronous)
```
API Request → Lambda returns immediately with "processing" status
              ↓
              Background Lambda does:
              - Download/extract repo
              - Process all files
              - Generate embeddings
              - Store in DynamoDB
              - Update status to "completed"
```

## What Stays EXACTLY The Same

### 1. File Processing Logic
**No changes** to:
- `RepositoryProcessor.discover_files()` - Same
- `RepositoryProcessor.semantic_chunking()` - Same
- File reading and parsing - Same

### 2. Embedding Generation
**No changes** to:
- `bedrock_client.generate_embedding()` - Same
- Chunking algorithm - Same
- Embedding storage - Same

### 3. Vector Store
**No changes** to:
- `vector_store.add_chunk()` - Same
- DynamoDB storage - Same
- Data structure - Same

### 4. All Other Features
**No changes** to:
- Architecture analysis
- Chat functionality
- File exploration
- Documentation generation
- Everything else

## What Changes

### Only 2 Things Change:

#### 1. API Response Timing
**Before**:
```python
# Wait for everything to complete
process_repository()  # Takes 5 minutes
return {"status": "completed", "file_count": 500}
```

**After**:
```python
# Return immediately
store_status("processing")
invoke_background_processor()  # Runs separately
return {"status": "processing", "message": "Poll for updates"}
```

#### 2. Frontend Polling
**Before**:
```typescript
// Wait for single response
const response = await ingestRepository(data)
// response.status === "completed"
```

**After**:
```typescript
// Get immediate response
const response = await ingestRepository(data)
// response.status === "processing"

// Poll for updates
while (status === "processing") {
  await sleep(2000)
  status = await getRepoStatus(repoId)
}
// status === "completed"
```

## Why It's Actually SAFER

### 1. Better Error Handling
**Current**: If Lambda times out, everything is lost
**Async**: Can retry failed steps, resume from where it stopped

### 2. Progress Tracking
**Current**: No visibility into what's happening
**Async**: Can update status at each step:
- "Downloading repository..."
- "Processing files (50/500)..."
- "Generating embeddings (200/500)..."
- "Completed"

### 3. No Partial State
**Current**: Timeout can leave partial data in database
**Async**: Can properly handle failures and clean up

### 4. Better Resource Management
**Current**: API Gateway connection held open for 5 minutes
**Async**: Connection released immediately, Lambda runs independently

## Implementation Details

### Backend Changes (Minimal)

#### Step 1: Split the handler into two functions
```python
# handlers/ingest_repo.py

def lambda_handler(event, context):
    """API endpoint - returns immediately"""
    # Validate request
    # Create repo_id
    # Store initial "processing" status
    # Invoke background processor (async)
    return {
        'statusCode': 202,
        'body': json.dumps({
            'repo_id': repo_id,
            'status': 'processing'
        })
    }

def process_repository_async(event, context):
    """Background processor - does the actual work"""
    # This is the SAME code that's currently in lambda_handler
    # Just moved to a separate function
    # No logic changes!
    
    repo_id = event['repo_id']
    repo_path = event['repo_path']
    
    # All the existing code:
    processor = RepositoryProcessor()
    files = processor.discover_files(repo_path)
    # ... rest of the existing logic ...
    
    # Update status when done
    repos_table.update_item(
        Key={'repo_id': repo_id},
        UpdateExpression='SET #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'completed'}
    )
```

#### Step 2: Add invocation mechanism
```python
# Option A: Direct Lambda invocation
lambda_client = boto3.client('lambda')
lambda_client.invoke(
    FunctionName='ProcessRepositoryFunction',
    InvocationType='Event',  # Async
    Payload=json.dumps({
        'repo_id': repo_id,
        'repo_path': repo_path
    })
)

# Option B: SQS queue (more robust)
sqs = boto3.client('sqs')
sqs.send_message(
    QueueUrl=PROCESSING_QUEUE_URL,
    MessageBody=json.dumps({
        'repo_id': repo_id,
        'repo_path': repo_path
    })
)
```

### Frontend Changes (Minimal)

#### Update the ingestion hook
```typescript
// frontend/src/hooks/useIngestion.ts

export function useIngestion() {
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(0)
  
  const ingest = async (data) => {
    // 1. Start ingestion (returns immediately)
    const response = await ingestRepository(data)
    const repoId = response.data.repo_id
    
    setStatus('processing')
    
    // 2. Poll for status
    const pollInterval = setInterval(async () => {
      const statusResponse = await getRepoStatus(repoId)
      
      if (statusResponse.data.status === 'completed') {
        clearInterval(pollInterval)
        setStatus('completed')
        // Navigate to repo page
      } else if (statusResponse.data.status === 'failed') {
        clearInterval(pollInterval)
        setStatus('failed')
      } else {
        // Update progress if available
        setProgress(statusResponse.data.progress || 0)
      }
    }, 2000)
  }
  
  return { ingest, status, progress }
}
```

## What Could Go Wrong? (And How We Handle It)

### Scenario 1: Background Lambda Fails
**Problem**: Processing fails halfway through
**Solution**: 
- Status remains "processing"
- Frontend shows error after timeout (e.g., 15 minutes)
- User can retry
- We can add automatic retry logic

### Scenario 2: Status Not Updating
**Problem**: Lambda completes but status not updated
**Solution**:
- Add heartbeat updates during processing
- Frontend can detect stale "processing" status
- Add manual "check status" button

### Scenario 3: Duplicate Invocations
**Problem**: User clicks "upload" multiple times
**Solution**:
- Check if repo_id already exists
- Return existing status if already processing
- Idempotent operations

## Testing Strategy

### Phase 1: Test with Small Repos
1. Upload small repo (<100 files)
2. Verify async processing works
3. Verify status updates correctly
4. Verify final result is identical to current implementation

### Phase 2: Test with Medium Repos
1. Upload medium repo (300-500 files)
2. Verify no timeout errors
3. Verify progress updates
4. Verify embeddings are correct

### Phase 3: Test with Large Repos
1. Upload large repo (>500 files)
2. Verify it completes successfully
3. Verify all files are processed
4. Verify chat/search works correctly

### Phase 4: Test Error Scenarios
1. Invalid ZIP file
2. Network interruption
3. Bedrock throttling
4. Out of memory

## Rollback Plan

If something goes wrong, we can rollback in 2 minutes:

```bash
# Revert to previous deployment
cd infrastructure
git checkout HEAD~1 template.yaml
./deploy.sh
```

All data is preserved because we're not changing the data structure.

## Comparison to Documentation Generation

This is **exactly the same pattern** we already use for documentation generation:

### Documentation Generation (Already Async)
```python
# POST /repos/{id}/docs/generate
def lambda_handler(event, context):
    # Store "generating" status
    doc_store.update_state(repo_id, 'generating')
    
    # Generate in background
    markdown = doc_generator.generate(analysis_data)
    
    # Update status when done
    doc_store.update_state(repo_id, 'generated')
```

### Repository Ingestion (Will Be Async)
```python
# POST /repos/ingest
def lambda_handler(event, context):
    # Store "processing" status
    repos_table.put_item({'status': 'processing'})
    
    # Process in background
    process_repository(repo_path)
    
    # Update status when done
    repos_table.update_item({'status': 'completed'})
```

**It's the same pattern!** We're just applying what already works for documentation generation to repository ingestion.

## Conclusion

### Will it break things?
**No.** The core logic (file processing, embedding generation, storage) remains unchanged.

### What's the risk?
**Very low.** We're only changing:
1. When the API returns (immediately vs. after completion)
2. How the frontend polls for status (already does this for docs)

### What's the benefit?
**Huge:**
- No timeout errors
- Works for any repository size
- Better user experience
- More reliable
- Easier to debug

### Should we do it?
**Yes.** It's a standard pattern, low risk, high reward, and we already use it elsewhere in the codebase.
