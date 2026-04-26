"""
Lambda handler for repository ingestion.
Implements FR-1.1, FR-1.2, FR-1.3 from requirements.
"""
import json
import os
import uuid
import shutil
import zipfile
import tempfile
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from bedrock_client import BedrockClient
from code_processor import RepositoryProcessor
from vector_store import DynamoDBVectorStore


# Initialize shared resources (reused across warm Lambda invocations)
bedrock_client = BedrockClient()
vector_store = DynamoDBVectorStore()
dynamodb = boto3.resource('dynamodb')
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))
sessions_table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'BloomWay-Sessions'))

# Constants
MAX_FILES = 500
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Ingest a GitHub repository: clone, parse, chunk, and embed code.
    
    Request body (JSON):
        {
            "source_type": "github",
            "source": "https://github.com/user/repo",
            "auth_token": "optional_github_token"
        }
    
    OR multipart/form-data with:
        - source_type: "zip"
        - file: ZIP file
    
    Returns:
        {
            "repo_id": "uuid",
            "status": "processing" | "completed" | "failed",
            "file_count": int,
            "chunk_count": int,
            "message": str
        }
    """
    repo_path = None
    zip_path = None
    
    try:
        headers = event.get('headers', {})
        content_type = (headers.get('content-type') or headers.get('Content-Type') or '').lower()
        
        if 'multipart/form-data' in content_type:
            import base64
            
            # Handle both base64-encoded and raw body
            body = event.get('body', '')
            is_base64 = event.get('isBase64Encoded', False)
            
            if is_base64:
                try:
                    body_bytes = base64.b64decode(body)
                except Exception as e:
                    return _error_response(400, f"Failed to decode base64 body: {str(e)}")
            else:
                # Body is already bytes or string
                if isinstance(body, str):
                    body_bytes = body.encode('latin-1')  # Preserve binary data
                else:
                    body_bytes = body
            
            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                return _error_response(400, "Missing boundary in multipart/form-data")
            
            # The boundary in the body might have different casing than in the header
            # Look for the actual boundary in the body
            if b'--' in body_bytes[:100]:
                # Extract actual boundary from body
                first_line = body_bytes.split(b'\r\n')[0]
                if first_line.startswith(b'--'):
                    boundary_bytes = first_line[2:]  # Remove leading --
                else:
                    boundary_bytes = boundary_match.group(1).strip().encode()
            else:
                boundary_bytes = boundary_match.group(1).strip().encode()
            
            parts = body_bytes.split(b'--' + boundary_bytes)
            
            source_type = 'zip'
            file_data = None
            
            for part in parts:
                if b'name="source_type"' in part:
                    try:
                        source_type = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0].decode().strip()
                    except Exception:
                        pass
                elif b'name="file"' in part and b'filename=' in part:
                    try:
                        file_data = part.split(b'\r\n\r\n', 1)[1].rsplit(b'\r\n', 1)[0]
                    except Exception:
                        pass
            
            if not file_data:
                return _error_response(400, "No file uploaded")
            
            repo_id = str(uuid.uuid4())
            print(f"Starting ZIP ingestion for repo_id: {repo_id}")
            
            zip_path = f"/tmp/{repo_id}.zip"
            try:
                with open(zip_path, 'wb') as f:
                    f.write(file_data)
                print(f"Saved uploaded ZIP to {zip_path} ({len(file_data)} bytes)")
            except Exception as e:
                return _error_response(500, f"Failed to save uploaded file: {str(e)}")
            
            extract_path = f"/tmp/{repo_id}"
            os.makedirs(extract_path, exist_ok=True)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                extracted_items = os.listdir(extract_path)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_path, extracted_items[0])):
                    repo_path = os.path.join(extract_path, extracted_items[0])
                else:
                    repo_path = extract_path
                
                print(f"Extracted ZIP to {repo_path}")
                
            except zipfile.BadZipFile:
                return _error_response(400, "Uploaded file is not a valid ZIP archive")
            except Exception as e:
                return _error_response(500, f"Failed to extract ZIP: {str(e)}")
            
            source = "uploaded_zip"
            auth_token = None
            
        elif 'application/json' in content_type or not content_type:
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError:
                return _error_response(400, "Invalid JSON in request body")
            
            source_type = body.get('source_type', 'github')
            source = body.get('source')
            auth_token = body.get('auth_token')
            
            if not source:
                return _error_response(400, "Missing required field: 'source'")
            
            if source_type not in ['github', 'zip']:
                return _error_response(400, f"Invalid source_type: {source_type}. Must be 'github' or 'zip'")
            
            repo_id = str(uuid.uuid4())
            print(f"Starting ingestion for repo_id: {repo_id}")
            
            # Store early 'processing' status so frontend can poll even if API Gateway times out
            timestamp = datetime.utcnow().isoformat() + 'Z'
            try:
                repos_table.put_item(Item={
                    'repo_id': repo_id,
                    'source': source,
                    'source_type': source_type,
                    'status': 'processing',
                    'file_count': 0,
                    'chunk_count': 0,
                    'created_at': timestamp,
                    'updated_at': timestamp
                })
            except Exception as e:
                print(f"Warning: Failed to store early processing status: {str(e)}")
            
            try:
                if source_type == 'github':
                    repo_path = _download_github_repo(source, repo_id)
                else:
                    return _error_response(400, "ZIP source_type requires file upload via multipart/form-data")
            except RuntimeError as e:
                if 'authentication' in str(e).lower() or 'permission' in str(e).lower():
                    return _error_response(401, f"Authentication failed: {str(e)}")
                return _error_response(400, f"Failed to access repository: {str(e)}")
            except HTTPError as e:
                if e.code == 404:
                    return _error_response(400, "Repository not found")
                return _error_response(502, f"Failed to download repository: HTTP {e.code}")
            except URLError as e:
                return _error_response(502, f"Failed to download repository: {str(e)}")
            except Exception as e:
                return _error_response(500, f"Failed to process repository: {str(e)}")
        
        else:
            return _error_response(400, f"Unsupported Content-Type: {content_type}. Use application/json or multipart/form-data")
        
        # Initialize processor with progress callback
        def progress_callback(message: str, percentage: int):
            print(f"[{percentage}%] {message}")
        
        processor = RepositoryProcessor(progress_callback=progress_callback)
        
        # Step 2: Discover files
        print("Discovering files...")
        files = processor.discover_files(repo_path)
        
        if len(files) > MAX_FILES:
            return _error_response(
                413,
                f"Repository too large: {len(files)} files found, maximum is {MAX_FILES}"
            )
        
        if len(files) == 0:
            return _error_response(400, "No supported source files found in repository")
        
        print(f"Discovered {len(files)} files")
        
        # Step 3: Process files and generate embeddings
        all_chunks = []
        
        for idx, file_info in enumerate(files):
            file_path = file_info['path']
            print(f"Processing file {idx + 1}/{len(files)}: {file_path}")
            
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
                
            except Exception as e:
                print(f"Warning: Failed to process {file_path}: {str(e)}")
                continue
        
        print(f"Generated {len(all_chunks)} chunks from {len(files)} files")
        
        # Step 4: Generate embeddings with throttling handling
        print("Generating embeddings...")
        chunks_with_embeddings = []
        
        for idx, chunk in enumerate(all_chunks):
            try:
                # Generate embedding for chunk content
                embedding = bedrock_client.generate_embedding(chunk['content'])
                chunk['embedding'] = embedding
                chunks_with_embeddings.append(chunk)
                
                if (idx + 1) % 10 == 0:
                    print(f"Generated {idx + 1}/{len(all_chunks)} embeddings")
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code == 'ThrottlingException':
                    return _error_response(
                        429,
                        "Bedrock API rate limit exceeded. Please try again later."
                    )
                
                print(f"Warning: Failed to generate embedding for chunk {idx}: {str(e)}")
                continue
        
        print(f"Successfully generated {len(chunks_with_embeddings)} embeddings")
        
        # Step 5: Store embeddings in vector store
        print("Storing embeddings in vector store...")
        print(f"DEBUG: repo_id={repo_id}, type={type(repo_id)}")
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
                
                # Log first chunk for verification
                if idx == 0:
                    print(f"✓ First chunk stored - repo_id: {chunk['repo_id']}, file: {chunk['file_path']}")
                    
            except ValueError as e:
                # Max chunks limit reached
                print(f"Warning: {str(e)}")
                break
            except Exception as e:
                print(f"Warning: Failed to store chunk {idx}: {str(e)}")
                continue
        
        print(f"✓ Stored {stored_count} chunks in vector store for repo_id: {repo_id}")
        
        # Step 5.5: Compute repo-level summary metrics
        print("Computing repo summary metrics...")
        total_lines = 0
        language_breakdown = {}
        largest_file_path = ''
        largest_file_lines = 0
        max_depth = 0
        
        for file_info in files:
            fpath = file_info['path']
            rel = os.path.relpath(fpath, repo_path)
            
            # Folder depth
            depth = rel.count(os.sep)
            if depth > max_depth:
                max_depth = depth
            
            # Language breakdown by extension
            _, ext = os.path.splitext(fpath)
            ext = ext.lower() if ext else 'no_ext'
            language_breakdown[ext] = language_breakdown.get(ext, 0) + 1
            
            # Line count
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
        indexed_at = datetime.utcnow().isoformat() + 'Z'
        
        repo_metrics = {
            'total_files': len(files),
            'total_lines_of_code': total_lines,
            'language_breakdown': language_breakdown,
            'primary_language': primary_language,
            'folder_depth': max_depth,
            'largest_file': {
                'path': largest_file_path,
                'lines': largest_file_lines
            },
            'indexed_at': indexed_at
        }
        print(f"Repo metrics: {json.dumps(repo_metrics, default=str)}")
        
        # Step 5.6: Build hierarchical file tree
        print("Building file tree...")
        file_tree = {'name': 'root', 'type': 'directory', 'children': []}
        
        for file_info in files:
            rel = os.path.relpath(file_info['path'], repo_path)
            parts = rel.split(os.sep)
            current = file_tree
            
            # Walk/create directory nodes for each segment except the last (the file)
            for part in parts[:-1]:
                # Find existing child directory
                found = None
                for child in current['children']:
                    if child['type'] == 'directory' and child['name'] == part:
                        found = child
                        break
                if found is None:
                    found = {'name': part, 'type': 'directory', 'children': []}
                    current['children'].append(found)
                current = found
            
            # Add the file leaf node
            current['children'].append({'name': parts[-1], 'type': 'file'})
        
        # Sort children alphabetically: directories first, then files
        def _sort_tree(node):
            if node.get('children'):
                node['children'].sort(key=lambda c: (0 if c['type'] == 'directory' else 1, c['name'].lower()))
                for child in node['children']:
                    _sort_tree(child)
        
        _sort_tree(file_tree)
        print(f"File tree built with {len(files)} entries")
        
        # Step 6: Detect tech stack
        print("Detecting tech stack...")
        tech_stack = processor.detect_tech_stack(files, repo_path=repo_path)
        
        # Step 6.5: Deep-scan manifest files for frameworks, databases, language
        print("Scanning manifest files...")
        detected_stack = _scan_manifest_files(repo_path)
        # Merge detected data into tech_stack
        for fw in detected_stack.get('frameworks', []):
            if fw not in tech_stack.get('frameworks', []):
                tech_stack.setdefault('frameworks', []).append(fw)
        for db in detected_stack.get('databases', []):
            tech_stack.setdefault('databases', []).append(db)
        for lang in detected_stack.get('languages', []):
            if lang not in tech_stack.get('languages', []):
                tech_stack.setdefault('languages', []).append(lang)
        # Store the raw detected_stack separately for richer metadata
        tech_stack['detected_stack'] = detected_stack
        print(f"Manifest scan complete: {json.dumps(detected_stack, default=str)}")
        
        # Step 6.6: Generate architecture summary
        print("Generating architecture summary...")
        
        # Build context for architecture analysis
        file_list = "\n".join([f"- {f['path']}" for f in files[:50]])  # Limit to first 50
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
        
        # Step 7: Store metadata in DynamoDB
        print("Storing metadata in DynamoDB...")
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        try:
            # Store in repos table
            repos_table.put_item(Item={
                'repo_id': repo_id,
                'source': source,
                'source_type': source_type,
                'file_count': len(files),
                'chunk_count': stored_count,
                'tech_stack': tech_stack,
                'architecture_summary': architecture_summary,
                'file_paths': [os.path.relpath(f['path'], repo_path) for f in files],
                'status': 'completed',
                'created_at': timestamp,
                'updated_at': timestamp,
                # Repo summary metrics
                'total_lines_of_code': total_lines,
                'language_breakdown': language_breakdown,
                'primary_language': primary_language,
                'folder_depth': max_depth,
                'largest_file': {
                    'path': largest_file_path,
                    'lines': largest_file_lines
                },
                'indexed_at': indexed_at,
                # Precomputed file tree
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
            
        except Exception as e:
            print(f"Warning: Failed to store metadata in DynamoDB: {str(e)}")
            # Continue anyway - vector store has the data
        
        # Success response
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'repo_id': repo_id,
                'session_id': session_id,
                'source': source,
                'status': 'completed',
                'file_count': len(files),
                'chunk_count': stored_count,
                'tech_stack': tech_stack,
                'message': 'Repository ingested successfully'
            })
        }
        
    except json.JSONDecodeError:
        return _error_response(400, "Invalid JSON in request body")
    
    except Exception as e:
        print(f"Unexpected error during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")
    
    finally:
        # Cleanup: Remove temporary files
        if repo_path and os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path)
                print(f"Cleaned up temporary directory: {repo_path}")
            except Exception as e:
                print(f"Warning: Failed to cleanup {repo_path}: {str(e)}")
        
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
                print(f"Cleaned up ZIP file: {zip_path}")
            except Exception as e:
                print(f"Warning: Failed to cleanup {zip_path}: {str(e)}")


def get_status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get repository ingestion status.
    
    Path parameters:
        id: Repository ID
    
    Returns:
        {
            "repo_id": "uuid",
            "status": "completed" | "processing" | "failed",
            "file_count": int,
            "chunk_count": int,
            "tech_stack": dict,
            "created_at": "ISO timestamp"
        }
    """
    try:
        # Extract repo_id from path parameters
        repo_id = event.get('pathParameters', {}).get('id')
        
        if not repo_id:
            return _error_response(400, "Repository ID is required")
        
        # Query DynamoDB for repo metadata
        try:
            response = repos_table.get_item(Key={'repo_id': repo_id})
            
            if 'Item' not in response:
                return _error_response(404, f"Repository {repo_id} not found")
            
            item = response['Item']
            
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'repo_id': item['repo_id'],
                    'status': item.get('status', 'unknown'),
                    'file_count': item.get('file_count', 0),
                    'chunk_count': item.get('chunk_count', 0),
                    'tech_stack': item.get('tech_stack', {}),
                    'file_paths': item.get('file_paths', []),
                    'source': item.get('source', ''),
                    'created_at': item.get('created_at', ''),
                    'updated_at': item.get('updated_at', ''),
                    # Repo summary metrics
                    'total_lines_of_code': item.get('total_lines_of_code', 0),
                    'language_breakdown': item.get('language_breakdown', {}),
                    'primary_language': item.get('primary_language', ''),
                    'folder_depth': item.get('folder_depth', 0),
                    'largest_file': item.get('largest_file', {}),
                    'indexed_at': item.get('indexed_at', ''),
                    'file_tree': item.get('file_tree', {})
                }, cls=_DecimalEncoder)
            }
            
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _error_response(500, "Failed to retrieve repository status")
    
    except Exception as e:
        print(f"Unexpected error in get_status_handler: {str(e)}")
        return _error_response(500, f"Internal server error: {str(e)}")


# ── Known-keyword lookup tables for manifest scanning ────────────
_JS_FRAMEWORKS = {
    'react': 'React', 'next': 'Next.js', 'vue': 'Vue.js', 'nuxt': 'Nuxt.js',
    'angular': 'Angular', 'svelte': 'Svelte', 'express': 'Express',
    'fastify': 'Fastify', 'nestjs': 'NestJS', 'koa': 'Koa',
    'gatsby': 'Gatsby', 'remix': 'Remix', 'electron': 'Electron',
    'tailwindcss': 'TailwindCSS', 'vite': 'Vite',
}
_PY_FRAMEWORKS = {
    'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
    'tornado': 'Tornado', 'celery': 'Celery', 'scrapy': 'Scrapy',
    'pytest': 'pytest', 'pandas': 'Pandas', 'numpy': 'NumPy',
    'boto3': 'AWS SDK (boto3)', 'tensorflow': 'TensorFlow',
    'torch': 'PyTorch', 'langchain': 'LangChain',
    'streamlit': 'Streamlit', 'sqlalchemy': 'SQLAlchemy',
}
_DB_KEYWORDS = {
    'mongoose': 'MongoDB', 'mongodb': 'MongoDB', 'pymongo': 'MongoDB',
    'pg': 'PostgreSQL', 'psycopg2': 'PostgreSQL', 'postgres': 'PostgreSQL',
    'mysql': 'MySQL', 'mysql2': 'MySQL',
    'redis': 'Redis', 'ioredis': 'Redis',
    'sqlite3': 'SQLite', 'sqlite': 'SQLite',
    'dynamodb': 'DynamoDB', 'boto3': 'DynamoDB',
    'sequelize': 'SQL (Sequelize)', 'prisma': 'Prisma ORM',
    'typeorm': 'TypeORM', 'knex': 'Knex.js',
    'elasticsearch': 'Elasticsearch', 'cassandra': 'Cassandra',
}


def _scan_manifest_files(repo_path: str) -> Dict[str, Any]:
    """
    Scan common manifest/config files for frameworks, databases, and language.

    Scans:
        package.json, requirements.txt, Dockerfile, go.mod, pom.xml

    Returns:
        {
            "frameworks": [...],
            "databases": [...],
            "languages": [...],
            "manifests_found": [...]
        }
    """
    frameworks = set()
    databases = set()
    languages = set()
    manifests_found = []

    for dirpath, _dirs, filenames in os.walk(repo_path):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)

            try:
                if fname == 'package.json':
                    manifests_found.append('package.json')
                    languages.add('JavaScript')
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        pkg = json.loads(f.read())
                    all_deps = {}
                    all_deps.update(pkg.get('dependencies', {}))
                    all_deps.update(pkg.get('devDependencies', {}))
                    for dep_name in all_deps:
                        dep_lower = dep_name.lower().replace('@', '').split('/')[0]
                        if dep_lower in _JS_FRAMEWORKS:
                            frameworks.add(_JS_FRAMEWORKS[dep_lower])
                        if dep_lower in _DB_KEYWORDS:
                            databases.add(_DB_KEYWORDS[dep_lower])
                    if 'typescript' in all_deps or 'ts-node' in all_deps:
                        languages.add('TypeScript')

                elif fname == 'requirements.txt':
                    manifests_found.append('requirements.txt')
                    languages.add('Python')
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            dep = re.split(r'[>=<!\[\]]', line.strip().lower())[0].strip()
                            if dep in _PY_FRAMEWORKS:
                                frameworks.add(_PY_FRAMEWORKS[dep])
                            if dep in _DB_KEYWORDS:
                                databases.add(_DB_KEYWORDS[dep])

                elif fname == 'Dockerfile':
                    manifests_found.append('Dockerfile')
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                    if 'python' in content:
                        languages.add('Python')
                    if 'node' in content:
                        languages.add('JavaScript')
                    if 'golang' in content or 'FROM go' in content:
                        languages.add('Go')
                    if 'java' in content:
                        languages.add('Java')
                    if 'postgres' in content:
                        databases.add('PostgreSQL')
                    if 'mysql' in content:
                        databases.add('MySQL')
                    if 'redis' in content:
                        databases.add('Redis')
                    if 'mongo' in content:
                        databases.add('MongoDB')

                elif fname == 'go.mod':
                    manifests_found.append('go.mod')
                    languages.add('Go')
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                    if 'gin-gonic' in content:
                        frameworks.add('Gin')
                    if 'echo' in content:
                        frameworks.add('Echo')
                    if 'fiber' in content:
                        frameworks.add('Fiber')
                    if 'gorm' in content:
                        frameworks.add('GORM')
                    if 'mongo-driver' in content:
                        databases.add('MongoDB')
                    if 'pgx' in content or 'pq' in content:
                        databases.add('PostgreSQL')
                    if 'go-redis' in content:
                        databases.add('Redis')

                elif fname == 'pom.xml':
                    manifests_found.append('pom.xml')
                    languages.add('Java')
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                    if 'spring-boot' in content:
                        frameworks.add('Spring Boot')
                    if 'spring-web' in content or 'spring-mvc' in content:
                        frameworks.add('Spring MVC')
                    if 'hibernate' in content:
                        frameworks.add('Hibernate')
                    if 'mysql' in content:
                        databases.add('MySQL')
                    if 'postgresql' in content:
                        databases.add('PostgreSQL')
                    if 'mongodb' in content or 'mongo' in content:
                        databases.add('MongoDB')
                    if 'redis' in content:
                        databases.add('Redis')

            except Exception as e:
                print(f"Warning: Failed to scan {fpath}: {str(e)}")
                continue

    return {
        'frameworks': sorted(list(frameworks)),
        'databases': sorted(list(databases)),
        'languages': sorted(list(languages)),
        'manifests_found': manifests_found
    }


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        API Gateway response dict
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message,
            'status_code': status_code
        })
    }


class _DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts Decimal to int/float for DynamoDB compatibility."""
    def default(self, obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def _download_github_repo(github_url: str, repo_id: str) -> str:
    """
    Download GitHub repository as ZIP and extract.
    
    Args:
        github_url: GitHub repository URL (e.g., https://github.com/owner/repo)
        repo_id: Unique repository identifier
        
    Returns:
        Path to extracted repository
        
    Raises:
        ValueError: If URL is not a valid GitHub URL
        HTTPError: If download fails
        RuntimeError: If extraction fails
    """
    # Parse GitHub URL
    github_pattern = r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
    match = re.match(github_pattern, github_url)
    
    if not match:
        raise ValueError("Invalid GitHub URL format")
    
    owner, repo = match.groups()
    
    # Construct ZIP download URL (try main branch first, then master)
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    
    # Download ZIP to /tmp
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
            except Exception:
                raise HTTPError(zip_url, 404, "Repository not found (tried main and master branches)", None, None)
        else:
            raise
    
    # Extract ZIP
    extract_path = f"/tmp/{repo_id}"
    
    try:
        print(f"Extracting to {extract_path}")
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # GitHub ZIPs contain a single root directory (repo-branch/)
        # Find and return the actual repo directory
        extracted_items = os.listdir(extract_path)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_path, extracted_items[0])):
            actual_repo_path = os.path.join(extract_path, extracted_items[0])
            print(f"Repository extracted to {actual_repo_path}")
            return actual_repo_path
        
        print(f"Repository extracted to {extract_path}")
        return extract_path
        
    except zipfile.BadZipFile:
        raise RuntimeError("Downloaded file is not a valid ZIP archive")
    except Exception as e:
        raise RuntimeError(f"Failed to extract repository: {str(e)}")
    finally:
        # Clean up ZIP file
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
