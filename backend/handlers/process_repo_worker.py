"""
Lambda handler for async repository processing worker.
Processes repositories from SQS queue with progress tracking.

Implements Requirements:
- 1.4: Process repository asynchronously
- 1.5: Generate embeddings and store in vector store
- 2.2, 3.1-3.5: Progress tracking
- 6.1-6.5: Stale job detection and timeout handling
- 7.1-7.5: Error handling and retries
- 8.1-8.5: Cleanup on failure
- 9.1-9.4: Backward compatibility with existing modules
- 12.1-12.5: Memory management
- 13.1-13.4: Structured logging
"""
import json
import os
import sys
import uuid
import shutil
import zipfile
import tempfile
import re
import gc
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from bedrock_client import BedrockClient
from code_processor import RepositoryProcessor
from vector_store import DynamoDBVectorStore
from progress_tracker import ProgressTracker

# Initialize shared resources
bedrock_client = BedrockClient()
vector_store = DynamoDBVectorStore()
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')

# Environment variables
INGESTION_JOBS_TABLE = os.environ.get('INGESTION_JOBS_TABLE', 'BloomWay-IngestionJobs')
REPOSITORIES_TABLE = os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories')
EMBEDDINGS_TABLE = os.environ.get('EMBEDDINGS_TABLE', 'BloomWay-Embeddings')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', 'BloomWay-Sessions')
CODE_BUCKET = os.environ.get('CODE_BUCKET', 'bloomway-code')

jobs_table = dynamodb.Table(INGESTION_JOBS_TABLE)
repos_table = dynamodb.Table(REPOSITORIES_TABLE)
sessions_table = dynamodb.Table(SESSIONS_TABLE)

# Constants
MAX_FILES = 500
BATCH_SIZE = 50  # Process files in batches
STALE_JOB_TIMEOUT_MINUTES = 15
MEMORY_THRESHOLD_MB = 512  # Trigger GC when less than this available
MAX_MEMORY_MB = 2500  # Fail if memory exceeds this (Lambda has 3008MB)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process repository from SQS message.
    
    SQS Event structure:
        {
            "Records": [{
                "body": "{\"job_id\": \"...\", \"source\": \"...\", \"source_type\": \"...\", ...}"
            }]
        }
    
    Returns:
        Success/failure status
    """
    print(f"Worker invoked with event: {json.dumps(event)}")
    
    # Detect and mark stale jobs before processing
    try:
        detect_stale_jobs()
    except Exception as e:
        print(f"Warning: Stale job detection failed: {str(e)}")
    
    # Parse SQS message
    if 'Records' not in event or len(event['Records']) == 0:
        print("ERROR: No SQS records in event")
        return {'statusCode': 400, 'body': 'No SQS records'}
    
    record = event['Records'][0]
    try:
        message_body = json.loads(record['body'])
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in SQS message: {str(e)}")
        return {'statusCode': 400, 'body': 'Invalid message format'}
    
    job_id = message_body.get('job_id')
    source = message_body.get('source')
    source_type = message_body.get('source_type')
    repo_id = message_body.get('repo_id')
    
    if not all([job_id, source, source_type, repo_id]):
        print(f"ERROR: Missing required fields in message: {message_body}")
        return {'statusCode': 400, 'body': 'Missing required fields'}
    
    print(f"Processing job_id={job_id}, repo_id={repo_id}, source_type={source_type}")
    
    # Retrieve job record
    try:
        job_response = jobs_table.get_item(Key={'job_id': job_id})
        if 'Item' not in job_response:
            print(f"ERROR: Job {job_id} not found in DynamoDB")
            return {'statusCode': 404, 'body': 'Job not found'}
        
        job = job_response['Item']
        print(f"Job status: {job.get('status')}")
        
    except ClientError as e:
        print(f"ERROR: Failed to retrieve job: {str(e)}")
        return {'statusCode': 500, 'body': 'Database error'}
    
    # Process the repository
    repo_path = None
    try:
        repo_path = process_repository(job_id, repo_id, source, source_type)
        print(f"✓ Repository processing completed successfully for job_id={job_id}")
        return {'statusCode': 200, 'body': 'Success'}
        
    except TransientError as e:
        # Transient errors should be retried by SQS
        print(f"TRANSIENT ERROR: {str(e)}")
        print("Re-raising for SQS retry...")
        raise  # SQS will retry
        
    except PermanentError as e:
        # Permanent errors should not be retried
        print(f"PERMANENT ERROR: {str(e)}")
        cleanup_on_failure(job_id, repo_id, str(e), repo_path)
        
        # Delete message from queue to prevent retries
        try:
            receipt_handle = record['receiptHandle']
            queue_url = os.environ.get('PROCESSING_QUEUE_URL')
            if queue_url:
                sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                print("Deleted message from queue (permanent failure)")
        except Exception as del_err:
            print(f"Warning: Failed to delete SQS message: {str(del_err)}")
        
        return {'statusCode': 200, 'body': 'Permanent failure handled'}
        
    except Exception as e:
        # Unknown errors - treat as transient for safety
        print(f"UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to cleanup
        try:
            cleanup_on_failure(job_id, repo_id, f"Unexpected error: {str(e)}", repo_path)
        except Exception as cleanup_err:
            print(f"Warning: Cleanup failed: {str(cleanup_err)}")
        
        # Re-raise for SQS retry
        raise
    
    finally:
        # Always cleanup temp files
        if repo_path and os.path.exists(repo_path):
            try:
                parent_dir = os.path.dirname(repo_path)
                if parent_dir.startswith('/tmp/'):
                    shutil.rmtree(parent_dir, ignore_errors=True)
                    print(f"Cleaned up temp directory: {parent_dir}")
            except Exception as e:
                print(f"Warning: Failed to cleanup temp files: {str(e)}")


def detect_stale_jobs() -> None:
    """
    Detect and mark stale processing jobs as failed.
    
    Scans for jobs with status='processing' and updated_at > 15 minutes ago.
    Marks them as failed with timeout error message.
    
    Implements Requirements 6.1-6.5: Stale job detection
    """
    print("Scanning for stale jobs...")
    
    try:
        # Scan for processing jobs
        response = jobs_table.scan(
            FilterExpression='#status = :processing',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':processing': 'processing'}
        )
        
        stale_count = 0
        cutoff_time = datetime.utcnow() - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)
        
        for job in response.get('Items', []):
            updated_at_str = job.get('updated_at', '')
            try:
                # Parse ISO timestamp - remove timezone info to make it naive for comparison
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', ''))
                
                if updated_at < cutoff_time:
                    job_id = job['job_id']
                    print(f"Found stale job: {job_id} (last updated: {updated_at_str})")
                    
                    # Mark as failed
                    jobs_table.update_item(
                        Key={'job_id': job_id},
                        UpdateExpression='SET #status = :failed, error_message = :error, updated_at = :now',
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={
                            ':failed': 'failed',
                            ':error': 'Processing timeout exceeded (15 minutes)',
                            ':now': datetime.utcnow().isoformat() + 'Z'
                        }
                    )
                    stale_count += 1
                    
            except (ValueError, AttributeError) as e:
                print(f"Warning: Failed to parse timestamp for job {job.get('job_id')}: {str(e)}")
                continue
        
        if stale_count > 0:
            print(f"Marked {stale_count} stale jobs as failed")
        else:
            print("No stale jobs found")
            
    except ClientError as e:
        print(f"ERROR: Failed to scan for stale jobs: {str(e)}")
        raise


def process_repository(job_id: str, repo_id: str, source: str, source_type: str) -> str:
    """
    Main repository processing logic.
    
    Steps:
    1. Download/extract repository
    2. Discover files
    3. Process files in batches with progress tracking
    4. Generate embeddings
    5. Store in vector store
    6. Store metadata
    7. Mark job as completed
    
    Args:
        job_id: Ingestion job ID
        repo_id: Repository ID
        source: Repository source (URL or "uploaded_zip")
        source_type: "github" or "zip"
    
    Returns:
        Path to extracted repository
    
    Raises:
        TransientError: For retryable errors
        PermanentError: For non-retryable errors
    """
    print(f"Starting repository processing: job_id={job_id}, repo_id={repo_id}")
    
    # Step 1: Download/extract repository
    repo_path = download_repository(repo_id, source, source_type)
    print(f"Repository extracted to: {repo_path}")
    
    # Step 2: Discover files
    processor = RepositoryProcessor()
    files = processor.discover_files(repo_path)
    
    if len(files) > MAX_FILES:
        raise PermanentError(
            f"Repository too large: {len(files)} files found, maximum is {MAX_FILES}"
        )
    
    if len(files) == 0:
        raise PermanentError("No supported source files found in repository")
    
    print(f"Discovered {len(files)} files")
    
    # Initialize progress tracker
    tracker = ProgressTracker(job_id, total_files=len(files))
    
    # Step 3: Process files in batches
    all_chunks = []
    
    for batch_start in range(0, len(files), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(files))
        batch = files[batch_start:batch_end]
        
        print(f"Processing batch {batch_start//BATCH_SIZE + 1}: files {batch_start+1}-{batch_end}")
        
        # Check memory before processing batch
        check_memory()
        
        # Process files in batch
        for idx, file_info in enumerate(batch):
            file_path = file_info['path']
            global_idx = batch_start + idx
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Chunk the file
                chunks = processor.semantic_chunking(file_path, content)
                
                # Create relative path for storage
                rel_path = os.path.relpath(file_path, repo_path)
                
                for chunk in chunks:
                    chunk['file_path'] = rel_path
                    chunk['repo_id'] = repo_id
                    all_chunks.append(chunk)
                
                # Update progress every 10 files
                if (global_idx + 1) % 10 == 0:
                    tracker.update(global_idx + 1)
                    print(f"Progress: {global_idx + 1}/{len(files)} files processed")
                
            except Exception as e:
                print(f"Warning: Failed to process {file_path}: {str(e)}")
                continue
        
        # Garbage collection between batches
        gc.collect()
        print(f"Batch complete. Total chunks so far: {len(all_chunks)}")
    
    print(f"Generated {len(all_chunks)} chunks from {len(files)} files")
    
    # Step 4: Generate embeddings
    print("Generating embeddings...")
    chunks_with_embeddings = []
    
    for idx, chunk in enumerate(all_chunks):
        try:
            embedding = bedrock_client.generate_embedding(chunk['content'])
            chunk['embedding'] = embedding
            chunks_with_embeddings.append(chunk)
            
            if (idx + 1) % 50 == 0:
                print(f"Generated {idx + 1}/{len(all_chunks)} embeddings")
                check_memory()
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ThrottlingException':
                raise TransientError("Bedrock API rate limit exceeded")
            
            print(f"Warning: Failed to generate embedding for chunk {idx}: {str(e)}")
            continue
    
    print(f"Successfully generated {len(chunks_with_embeddings)} embeddings")
    
    # Step 5: Store embeddings in vector store
    print("Storing embeddings in vector store...")
    stored_count = 0
    
    for idx, chunk in enumerate(chunks_with_embeddings):
        try:
            vector_store.add_chunk(
                repo_id=chunk['repo_id'],
                file_path=chunk['file_path'],
                content=chunk['content'],
                embedding=chunk['embedding'],
                metadata=chunk.get('metadata', {})
            )
            stored_count += 1
            
        except ValueError as e:
            print(f"Warning: {str(e)}")
            break
        except Exception as e:
            print(f"Warning: Failed to store chunk {idx}: {str(e)}")
            continue
    
    print(f"Stored {stored_count} chunks in vector store")
    
    # Step 6: Store repository metadata
    store_repository_metadata(repo_id, source, source_type, files, repo_path, stored_count)
    
    # Step 7: Mark job as completed
    tracker.mark_completed()
    print(f"✓ Job {job_id} marked as completed")
    
    return repo_path


def download_repository(repo_id: str, source: str, source_type: str) -> str:
    """
    Download and extract repository based on source type.
    
    Args:
        repo_id: Repository ID
        source: Repository source (URL or "uploaded_zip")
        source_type: "github" or "zip"
    
    Returns:
        Path to extracted repository
    
    Raises:
        TransientError: For network errors
        PermanentError: For invalid format or not found
    """
    if source_type == 'github':
        return download_github_repo(source, repo_id)
    elif source_type == 'zip':
        # For ZIP uploads, the file should be in S3
        return download_from_s3(repo_id)
    else:
        raise PermanentError(f"Unsupported source_type: {source_type}")


def download_github_repo(github_url: str, repo_id: str) -> str:
    """
    Download GitHub repository as ZIP and extract.
    
    Reuses logic from ingest_repo.py for consistency.
    """
    github_pattern = r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
    match = re.match(github_pattern, github_url)
    
    if not match:
        raise PermanentError("Invalid GitHub URL format")
    
    owner, repo = match.groups()
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    zip_path = f"/tmp/{repo_id}.zip"
    
    try:
        print(f"Downloading repository from {zip_url}")
        request = Request(zip_url, headers={'User-Agent': 'BloomWay-AI/1.0'})
        
        with urlopen(request, timeout=60) as response:
            with open(zip_path, 'wb') as f:
                f.write(response.read())
        
        print(f"Downloaded {os.path.getsize(zip_path)} bytes")
        
    except HTTPError as e:
        if e.code == 404:
            # Try master branch
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
            print(f"Trying master branch: {zip_url}")
            
            try:
                request = Request(zip_url, headers={'User-Agent': 'BloomWay-AI/1.0'})
                with urlopen(request, timeout=60) as response:
                    with open(zip_path, 'wb') as f:
                        f.write(response.read())
                print(f"Downloaded {os.path.getsize(zip_path)} bytes")
            except HTTPError:
                raise PermanentError("Repository not found (tried main and master branches)")
            except URLError as e:
                raise TransientError(f"Network error downloading repository: {str(e)}")
        else:
            raise TransientError(f"HTTP error {e.code} downloading repository")
    
    except URLError as e:
        raise TransientError(f"Network error downloading repository: {str(e)}")
    
    # Extract ZIP
    extract_path = f"/tmp/{repo_id}"
    
    try:
        print(f"Extracting to {extract_path}")
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # GitHub ZIPs contain a single root directory
        extracted_items = os.listdir(extract_path)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_path, extracted_items[0])):
            actual_repo_path = os.path.join(extract_path, extracted_items[0])
            print(f"Repository extracted to {actual_repo_path}")
            return actual_repo_path
        
        print(f"Repository extracted to {extract_path}")
        return extract_path
        
    except zipfile.BadZipFile:
        raise PermanentError("Downloaded file is not a valid ZIP archive")
    except Exception as e:
        raise PermanentError(f"Failed to extract repository: {str(e)}")
    finally:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass


def download_from_s3(repo_id: str) -> str:
    """
    Download ZIP file from S3 and extract.
    
    For ZIP uploads, the async ingestion service should upload to S3 first.
    """
    # TODO: Implement S3 download logic when ZIP upload support is added
    raise PermanentError("S3 ZIP download not yet implemented")


def store_repository_metadata(
    repo_id: str,
    source: str,
    source_type: str,
    files: List[Dict[str, Any]],
    repo_path: str,
    chunk_count: int
) -> None:
    """
    Store repository metadata in DynamoDB.
    
    Reuses logic from ingest_repo.py for consistency.
    """
    print("Computing repository metadata...")
    
    # Compute metrics
    total_lines = 0
    language_breakdown = {}
    largest_file_path = ''
    largest_file_lines = 0
    max_depth = 0
    
    for file_info in files:
        fpath = file_info['path']
        rel = os.path.relpath(fpath, repo_path)
        
        depth = rel.count(os.sep)
        if depth > max_depth:
            max_depth = depth
        
        _, ext = os.path.splitext(fpath)
        ext = ext.lower() if ext else 'no_ext'
        language_breakdown[ext] = language_breakdown.get(ext, 0) + 1
        
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            total_lines += line_count
            if line_count > largest_file_lines:
                largest_file_lines = line_count
                largest_file_path = rel
        except Exception:
            pass
    
    primary_language = max(language_breakdown, key=language_breakdown.get) if language_breakdown else 'unknown'
    
    # Build file tree
    file_tree = {'name': 'root', 'type': 'directory', 'children': []}
    
    for file_info in files:
        rel = os.path.relpath(file_info['path'], repo_path)
        parts = rel.split(os.sep)
        current = file_tree
        
        for part in parts[:-1]:
            found = None
            for child in current['children']:
                if child['type'] == 'directory' and child['name'] == part:
                    found = child
                    break
            if found is None:
                found = {'name': part, 'type': 'directory', 'children': []}
                current['children'].append(found)
            current = found
        
        current['children'].append({'name': parts[-1], 'type': 'file'})
    
    def sort_tree(node):
        if node.get('children'):
            node['children'].sort(key=lambda c: (0 if c['type'] == 'directory' else 1, c['name'].lower()))
            for child in node['children']:
                sort_tree(child)
    
    sort_tree(file_tree)
    
    # Detect tech stack
    processor = RepositoryProcessor()
    tech_stack = processor.detect_tech_stack(files, repo_path=repo_path)
    
    # Generate architecture summary
    file_list = "\n".join([f"- {os.path.relpath(f['path'], repo_path)}" for f in files[:50]])
    context = f"Repository contains {len(files)} files.\n\nTech Stack: {json.dumps(tech_stack)}\n\nKey Files:\n{file_list}"
    
    try:
        architecture_summary = bedrock_client.invoke_claude(
            prompt=context,
            system_prompt=bedrock_client.ARCHITECTURE_SYSTEM_PROMPT,
            max_tokens=2048
        )
    except Exception as e:
        print(f"Warning: Failed to generate architecture summary: {str(e)}")
        architecture_summary = f"Architecture analysis unavailable. Tech stack: {json.dumps(tech_stack)}"
    
    # Store in DynamoDB
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    try:
        repos_table.put_item(Item={
            'repo_id': repo_id,
            'source': source,
            'source_type': source_type,
            'file_count': len(files),
            'chunk_count': chunk_count,
            'tech_stack': tech_stack,
            'architecture_summary': architecture_summary,
            'file_paths': [os.path.relpath(f['path'], repo_path) for f in files],
            'status': 'completed',
            'created_at': timestamp,
            'updated_at': timestamp,
            'total_lines_of_code': total_lines,
            'language_breakdown': language_breakdown,
            'primary_language': primary_language,
            'folder_depth': max_depth,
            'largest_file': {
                'path': largest_file_path,
                'lines': largest_file_lines
            },
            'indexed_at': timestamp,
            'file_tree': file_tree
        })
        
        # Create initial session
        session_id = str(uuid.uuid4())
        ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        
        sessions_table.put_item(Item={
            'session_id': session_id,
            'repo_id': repo_id,
            'created_at': timestamp,
            'ttl': ttl
        })
        
        print(f"Metadata stored successfully. Session ID: {session_id}")
        
    except ClientError as e:
        print(f"Warning: Failed to store metadata: {str(e)}")
        raise TransientError(f"Failed to store metadata: {str(e)}")


def check_memory() -> None:
    """
    Check memory usage and trigger garbage collection if needed.
    
    Implements Requirements 12.3-12.5: Memory management
    
    Raises:
        PermanentError: If memory cannot be freed
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"Memory usage: {memory_mb:.2f} MB")
        
        # Check if we're approaching the limit
        if memory_mb > MAX_MEMORY_MB:
            print(f"ERROR: Memory usage ({memory_mb:.2f} MB) exceeds maximum ({MAX_MEMORY_MB} MB)")
            raise PermanentError(f"Out of memory: {memory_mb:.2f} MB used")
        
        # Trigger GC if memory is getting high
        available_mb = MAX_MEMORY_MB - memory_mb
        if available_mb < MEMORY_THRESHOLD_MB:
            print(f"Low memory ({available_mb:.2f} MB available), triggering garbage collection...")
            gc.collect()
            
            # Check again after GC
            memory_info = process.memory_info()
            memory_mb_after = memory_info.rss / 1024 / 1024
            freed_mb = memory_mb - memory_mb_after
            print(f"GC freed {freed_mb:.2f} MB, now using {memory_mb_after:.2f} MB")
            
            # If still too high after GC, fail
            if memory_mb_after > MAX_MEMORY_MB:
                raise PermanentError(f"Out of memory even after GC: {memory_mb_after:.2f} MB used")
    
    except ImportError:
        # psutil not available, skip memory check
        print("Warning: psutil not available, skipping memory check")
    except PermanentError:
        raise
    except Exception as e:
        print(f"Warning: Memory check failed: {str(e)}")


def cleanup_on_failure(job_id: str, repo_id: str, error_message: str, repo_path: Optional[str] = None) -> None:
    """
    Cleanup resources on processing failure.
    
    Steps:
    1. Remove temporary files
    2. Delete partial embeddings from vector store
    3. Update job status to failed
    
    Implements Requirements 8.1-8.5: Cleanup on failure
    """
    print(f"Cleaning up after failure for job_id={job_id}, repo_id={repo_id}")
    
    # Step 1: Remove temporary files
    if repo_path and os.path.exists(repo_path):
        try:
            parent_dir = os.path.dirname(repo_path)
            if parent_dir.startswith('/tmp/'):
                shutil.rmtree(parent_dir, ignore_errors=True)
                print(f"Removed temp directory: {parent_dir}")
        except Exception as e:
            print(f"Warning: Failed to remove temp files: {str(e)}")
    
    # Step 2: Delete partial embeddings from vector store
    try:
        # Query all chunks for this repo_id
        embeddings_table = dynamodb.Table(EMBEDDINGS_TABLE)
        response = embeddings_table.query(
            KeyConditionExpression='repo_id = :repo_id',
            ExpressionAttributeValues={':repo_id': repo_id}
        )
        
        chunks = response.get('Items', [])
        if chunks:
            print(f"Deleting {len(chunks)} partial embeddings...")
            
            # Delete in batches
            with embeddings_table.batch_writer() as batch:
                for chunk in chunks:
                    batch.delete_item(Key={
                        'repo_id': chunk['repo_id'],
                        'chunk_id': chunk['chunk_id']
                    })
            
            print(f"Deleted {len(chunks)} partial embeddings")
    
    except Exception as e:
        print(f"Warning: Failed to delete partial embeddings: {str(e)}")
    
    # Step 3: Update job status to failed (always do this, even if cleanup fails)
    try:
        tracker = ProgressTracker(job_id, total_files=0)
        tracker.mark_failed(error_message)
        print(f"Job {job_id} marked as failed")
    
    except Exception as e:
        print(f"ERROR: Failed to mark job as failed: {str(e)}")
        # Try direct DynamoDB update as fallback
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :failed, error_message = :error, updated_at = :now',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':failed': 'failed',
                    ':error': error_message,
                    ':now': datetime.utcnow().isoformat() + 'Z'
                }
            )
            print(f"Job {job_id} marked as failed (fallback)")
        except Exception as fallback_err:
            print(f"CRITICAL: Failed to mark job as failed even with fallback: {str(fallback_err)}")


# Custom exception classes for error classification
class TransientError(Exception):
    """
    Transient error that should be retried.
    
    Examples:
    - Network timeouts
    - API throttling
    - Temporary service unavailability
    
    Implements Requirements 7.4-7.5: Error classification
    """
    pass


class PermanentError(Exception):
    """
    Permanent error that should not be retried.
    
    Examples:
    - Invalid file format
    - Repository not found
    - Out of memory
    - Repository too large
    
    Implements Requirements 7.4-7.5: Error classification
    """
    pass
