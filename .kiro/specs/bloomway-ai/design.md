# Design Document: CodeLens

## Overview

CodeLens is an AI-powered codebase understanding tool that enables developers to quickly comprehend unfamiliar codebases through intelligent analysis, visualization, and interactive chat. The system leverages Amazon Bedrock's Claude 3.5 Sonnet v2 for natural language generation and Titan Embeddings v2 for semantic code search, implementing a retrieval-augmented generation (RAG) architecture.

### System Goals

- Enable rapid codebase comprehension for developers joining new projects
- Provide multi-level explanations suitable for different expertise levels
- Generate accurate architecture visualizations automatically
- Support natural language queries about code functionality and structure
- Maintain session-based analysis with automatic cleanup

### Key Features

1. **Repository Ingestion**: Clone GitHub repositories, parse source code, generate embeddings, and store in vector database
2. **Architecture Analysis**: Generate high-level architecture summaries with interactive Mermaid diagrams
3. **Multi-Level File Explanation**: Provide beginner, intermediate, and advanced explanations for individual files
4. **Conversational Chat**: Answer natural language questions using RAG with code context
5. **Documentation Export**: Generate and export comprehensive documentation artifacts
6. **Session Management**: Automatic session lifecycle with 24-hour TTL

### Technology Stack

**Backend:**
- AWS Lambda (Python 3.11) for serverless compute
- Amazon Bedrock (Claude 3.5 Sonnet v2, Titan Embeddings v2) for AI capabilities
- DynamoDB for metadata and session storage
- S3 for artifact storage
- API Gateway for REST endpoints

**Frontend:**
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Mermaid.js for diagram rendering

**Infrastructure:**
- AWS SAM for infrastructure as code
- CloudFormation for resource provisioning

## Architecture

### High-Level Architecture

The system follows a serverless microservices architecture with clear separation between ingestion, analysis, and query services:

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼
┌────────┐ ┌────┐ ┌────────┐ ┌──────┐ ┌──────┐
│Ingest  │ │Arch│ │Explain │ │ Chat │ │ Docs │
│Lambda  │ │    │ │Lambda  │ │      │ │      │
└───┬────┘ └─┬──┘ └───┬────┘ └──┬───┘ └──┬───┘
    │        │        │          │        │
    └────────┴────────┴──────────┴────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌────────┐  ┌─────────┐  ┌────────┐
    │DynamoDB│  │ Bedrock │  │   S3   │
    │        │  │         │  │        │
    └────────┘  └─────────┘  └────────┘
         │            │            │
         └────────────┴────────────┘
                      │
              ┌───────▼────────┐
              │  Vector Store  │
              │  (In-Memory)   │
              └────────────────┘
```

### Component Architecture

#### 1. Ingestion Service
- **Responsibility**: Clone repositories, parse code, generate embeddings, store in vector database
- **Input**: GitHub URL or ZIP file
- **Output**: Repository metadata, embeddings stored in vector store
- **Key Operations**:
  - Download repository from GitHub
  - Discover source files (filter by extension, size, binary check)
  - Semantic chunking of code files
  - Batch embedding generation with Bedrock Titan
  - Vector store population
  - Metadata persistence to DynamoDB

#### 2. Architecture Service
- **Responsibility**: Generate architecture summaries and Mermaid diagrams
- **Input**: Repository ID, analysis level (basic/intermediate/advanced)
- **Output**: Architecture JSON with components, patterns, data flow, and Mermaid diagram
- **Key Operations**:
  - Retrieve file summaries from vector store
  - Build context with tech stack and file previews
  - Generate architecture analysis with Claude
  - Generate Mermaid diagram from architecture
  - Cache results in DynamoDB

#### 3. Explanation Service
- **Responsibility**: Generate multi-level file explanations
- **Input**: Repository ID, file path, level (beginner/intermediate/advanced)
- **Output**: Structured explanation with purpose, functions, patterns, dependencies
- **Key Operations**:
  - Retrieve file chunks from vector store
  - Reconstruct file content
  - Extract metadata (functions, imports, complexity)
  - Generate level-appropriate explanation with Claude
  - Identify related files
  - Cache results in DynamoDB

#### 4. Chat Service
- **Responsibility**: Answer natural language questions using RAG
- **Input**: User question, session ID, scope (all/file/directory), conversation history
- **Output**: Answer with citations, suggested questions, confidence score
- **Key Operations**:
  - Generate query embedding
  - Retrieve relevant code chunks from vector store
  - Build RAG prompt with context and history
  - Generate response with Claude
  - Extract citations from response
  - Generate suggested follow-up questions
  - Store conversation in session

#### 5. Documentation Service
- **Responsibility**: Export documentation artifacts
- **Input**: Session ID, export format (Markdown/PDF)
- **Output**: Download URL for documentation artifact
- **Key Operations**:
  - Compile architecture summaries
  - Include Mermaid diagrams
  - Format documentation structure
  - Store artifact in S3
  - Generate presigned download URL

### Data Flow

#### Ingestion Flow
1. User submits GitHub URL via frontend
2. API Gateway routes to Ingestion Lambda
3. Lambda downloads repository to /tmp
4. Code processor discovers and filters source files
5. Files are semantically chunked (functions, classes, blocks)
6. Bedrock Titan generates embeddings for each chunk
7. Embeddings stored in in-memory vector store
8. Metadata persisted to DynamoDB (Repositories, Sessions tables)
9. Response returned with repo_id and session_id

#### Query Flow (Chat)
1. User submits question via chat interface
2. API Gateway routes to Chat Lambda
3. Lambda generates embedding for question
4. Vector store performs similarity search
5. Top-k relevant chunks retrieved
6. RAG prompt constructed with chunks and history
7. Claude generates response with citations
8. Response parsed for file references
9. Suggested questions generated
10. Conversation stored in session
11. Response returned to frontend

### Architectural Patterns

1. **Serverless Microservices**: Each Lambda function handles a specific domain (ingestion, architecture, explanation, chat, docs)
2. **Retrieval-Augmented Generation (RAG)**: Semantic search retrieves relevant code context before LLM generation
3. **Caching Layer**: DynamoDB cache reduces Bedrock API calls and improves response times
4. **Session-Based State**: User sessions maintain conversation history and analyzed repositories
5. **Event-Driven**: Lambda functions triggered by API Gateway events
6. **Separation of Concerns**: Clear boundaries between transport (API Gateway), business logic (Lambda), and data (DynamoDB, S3, Vector Store)

## Components and Interfaces

### Backend Components

#### 1. Lambda Handlers

**IngestRepoHandler** (`backend/handlers/ingest_repo.py`)
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    POST /repos/ingest
    Body: {
        "source_type": "github" | "zip",
        "source": "https://github.com/user/repo",
        "auth_token": "optional"
    }
    Returns: {
        "repo_id": "uuid",
        "session_id": "uuid",
        "status": "completed",
        "file_count": int,
        "chunk_count": int,
        "tech_stack": {...}
    }
    """
```

**ArchitectureHandler** (`backend/handlers/architecture.py`)
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /repos/{id}/architecture?level=intermediate
    Returns: {
        "repo_id": "uuid",
        "architecture": {
            "overview": "string",
            "components": [...],
            "patterns": [...],
            "data_flow": "string",
            "entry_points": [...]
        },
        "diagram": "flowchart TD...",
        "generated_at": "timestamp"
    }
    """
```

**ExplainFileHandler** (`backend/handlers/explain_file.py`)
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /repos/{id}/files/{path}/explain?level=intermediate
    Returns: {
        "repo_id": "uuid",
        "file_path": "src/api.js",
        "explanation": {
            "purpose": "string",
            "key_functions": [...],
            "patterns": [...],
            "dependencies": [...],
            "complexity": {...}
        },
        "related_files": [...],
        "level": "intermediate"
    }
    """
```

**ChatHandler** (`backend/handlers/chat.py`)
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    POST /repos/{id}/chat
    Body: {
        "message": "string",
        "session_id": "uuid",
        "scope": {"type": "all"|"file"|"directory", "path": "..."},
        "history": [...]
    }
    Returns: {
        "repo_id": "uuid",
        "response": "string with [file:line] citations",
        "citations": [...],
        "suggested_questions": [...],
        "confidence": "high"|"medium"|"low",
        "session_id": "uuid"
    }
    """
```

**DocsHandler** (`backend/handlers/generate_docs.py`)
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    POST /sessions/{id}/export
    Body: {
        "format": "markdown" | "pdf"
    }
    Returns: {
        "session_id": "uuid",
        "download_url": "presigned S3 URL",
        "format": "markdown",
        "expires_at": "timestamp"
    }
    """
```

#### 2. Core Libraries

**BedrockClient** (`backend/lib/bedrock_client.py`)
- `generate_embedding(text: str) -> List[float]`: Generate 1024-dim embedding with Titan v2
- `invoke_claude(prompt: str, system_prompt: str, max_tokens: int, temperature: float) -> str`: Generate text with Claude 3.5 Sonnet
- `invoke_claude_streaming(...)`: Stream Claude responses for real-time chat
- Implements retry logic with exponential backoff for throttling

**RepositoryProcessor** (`backend/lib/code_processor.py`)
- `discover_files(repo_path: str) -> List[Dict]`: Find source files, filter by extension/size
- `semantic_chunking(file_path: str, content: str) -> List[Dict]`: Chunk code by functions/classes
- `detect_tech_stack(files: List[Dict]) -> Dict`: Identify languages, frameworks, libraries
- `extract_imports(file_path: str) -> List[str]`: Parse import statements
- `estimate_complexity(file_path: str) -> Dict`: Calculate LOC, functions, classes, comment ratio

**InMemoryVectorStore** (`backend/lib/vector_store.py`)
- `add_chunk(repo_id: str, file_path: str, content: str, embedding: List[float], metadata: Dict)`: Store chunk with embedding
- `search(repo_id: str, query_embedding: List[float], top_k: int) -> List[Dict]`: Cosine similarity search
- `get_file_chunks(repo_id: str, file_path: str) -> List[Dict]`: Retrieve all chunks for a file
- `delete_repo(repo_id: str)`: Remove all chunks for a repository
- **Known Limitation**: In-memory storage doesn't persist across Lambda cold starts

### Frontend Components

#### Existing Components

**Layout Components** (`frontend/src/components/layout/`)
- `SplitPane.tsx`: Resizable split pane for file tree and content view

**Explorer Components** (`frontend/src/components/explorer/`)
- `FileTree.tsx`: Hierarchical file browser
- `FileNode.tsx`: Individual file/folder node with expand/collapse
- `Breadcrumb.tsx`: Navigation breadcrumb trail

**Input Components** (`frontend/src/components/input/`)
- `UploadZone.tsx`: GitHub URL input and file upload zone

**Pages** (`frontend/src/pages/`)
- `RepoInputPage.tsx`: Landing page for repository input
- `RepoExplorerPage.tsx`: Main explorer with file tree
- `FileViewPage.tsx`: File content viewer
- `ArchitecturePage.tsx`: Architecture summary and diagram viewer

#### Components to Design (Not Yet Implemented)

**ExplanationPanel** (`frontend/src/components/code/ExplanationPanel.tsx`)
- Display multi-level file explanations
- Tab interface for beginner/intermediate/advanced levels
- Show purpose, key functions, patterns, dependencies
- Display related files with navigation links
- Syntax highlighting for code snippets

**ArchitectureView** (`frontend/src/components/architecture/ArchitectureView.tsx`)
- Render architecture summary text
- Display interactive Mermaid diagram
- Level selector (basic/intermediate/advanced)
- Component list with descriptions
- Pattern badges
- Entry point links

**ChatInterface** (`frontend/src/components/chat/ChatInterface.tsx`)
- Message list with user/assistant bubbles
- Input field with send button
- Citation display with file links
- Suggested questions as clickable chips
- Confidence indicator
- Scope selector (all/file/directory)
- Conversation history management

**DocGenerator** (`frontend/src/components/docs/DocGenerator.tsx`)
- Export format selector (Markdown/PDF)
- Export button with loading state
- Download link display
- Preview of documentation structure

### API Interfaces

**REST API Endpoints** (API Gateway)

```
POST   /repos/ingest                    # Ingest repository
GET    /repos/{id}/status               # Get ingestion status
GET    /repos/{id}/architecture         # Get architecture summary
GET    /repos/{id}/files/{path}/explain # Explain file
POST   /repos/{id}/chat                 # Chat query
POST   /sessions/{id}/export            # Export documentation
GET    /sessions/{id}                   # Get session info
```

**API Base URL**: `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod`

### External Interfaces

**Amazon Bedrock**
- Model: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Embedding Model: `amazon.titan-embed-text-v2:0`
- Region: `us-east-1`
- Authentication: IAM role-based

**GitHub API**
- Repository download via HTTPS (public repos)
- Archive download: `https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip`
- No authentication required for public repos

## Data Models

### DynamoDB Tables

#### Repositories Table
```
Table: BloomWay-Repositories
Partition Key: repo_id (String)

Attributes:
- repo_id: String (UUID)
- source: String (GitHub URL or S3 path)
- source_type: String ("github" | "zip")
- file_count: Number
- chunk_count: Number
- tech_stack: Map {
    languages: List<String>
    frameworks: List<String>
    libraries: List<String>
  }
- architecture_summary: String
- status: String ("processing" | "completed" | "failed")
- created_at: String (ISO 8601)
- updated_at: String (ISO 8601)
```

#### Sessions Table
```
Table: BloomWay-Sessions
Partition Key: session_id (String)

Attributes:
- session_id: String (UUID)
- repo_id: String (UUID)
- created_at: String (ISO 8601)
- last_message_at: String (ISO 8601)
- message_count: Number
- ttl: Number (Unix timestamp, 24 hours from creation)
```

#### Cache Table
```
Table: BloomWay-Cache
Partition Key: cache_key (String)

Attributes:
- cache_key: String (format: "{repo_id}#{resource_type}#{level}")
- repo_id: String (UUID)
- resource_type: String ("architecture" | "file_explanation")
- level: String ("basic" | "intermediate" | "advanced" | "beginner")
- data: Map (cached response data)
- ttl: Number (Unix timestamp, 24 hours from creation)
- created_at: String (ISO 8601)
```

### Vector Store Schema

**Chunk Document**
```python
{
    "id": "uuid",
    "repo_id": "uuid",
    "file_path": "src/api.js",
    "content": "function handleRequest(req, res) { ... }",
    "embedding": [0.123, -0.456, ...],  # 1024 dimensions
    "metadata": {
        "start_line": 45,
        "end_line": 78,
        "type": "function" | "class" | "block",
        "language": "javascript",
        "size": 1234
    }
}
```

### Frontend State Models

**Repository State**
```typescript
interface Repository {
  id: string;
  source: string;
  sourceType: 'github' | 'zip';
  fileCount: number;
  chunkCount: number;
  techStack: {
    languages: string[];
    frameworks: string[];
    libraries: string[];
  };
  status: 'processing' | 'completed' | 'failed';
  createdAt: string;
}
```

**Architecture State**
```typescript
interface Architecture {
  repoId: string;
  architecture: {
    overview: string;
    components: Array<{
      name: string;
      description: string;
      files: string[];
    }>;
    patterns: string[];
    dataFlow: string;
    entryPoints: string[];
  };
  diagram: string;  // Mermaid code
  generatedAt: string;
}
```

**File Explanation State**
```typescript
interface FileExplanation {
  repoId: string;
  filePath: string;
  explanation: {
    purpose: string;
    keyFunctions: Array<{
      name: string;
      description: string;
      line: number;
    }>;
    patterns: string[];
    dependencies: string[];
    complexity: {
      lines: number;
      functions: number;
    };
  };
  relatedFiles: string[];
  level: 'beginner' | 'intermediate' | 'advanced';
  generatedAt: string;
}
```

**Chat State**
```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    file: string;
    line?: number;
    snippet: string;
  }>;
  timestamp: string;
}

interface ChatSession {
  sessionId: string;
  repoId: string;
  messages: ChatMessage[];
  suggestedQuestions: string[];
  confidence: 'high' | 'medium' | 'low';
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies:
- Property 3.5 is redundant with 3.1 (both test that three explanation levels are returned)
- Property 12.3 is redundant with 9.7 (both test S3 server-side encryption)
- Several properties about endpoint existence (8.1-8.5) can be combined into examples rather than separate properties
- Properties about data structure validation (9.1-9.3) can be combined into a single comprehensive property

The following properties represent unique, testable behaviors that validate the system's correctness:

### Property 1: Embedding Round Trip

*For any* code chunk that is ingested, generating an embedding and storing it in the vector store should allow retrieval of that chunk with its embedding intact.

**Validates: Requirements 1.4, 1.5**

### Property 2: Repository File Limit Enforcement

*For any* repository with more than 500 files, the ingestion service should reject the repository with an appropriate error message.

**Validates: Requirements 1.6**

### Property 3: Metadata Persistence Round Trip

*For any* successfully ingested repository, the metadata stored in DynamoDB should be retrievable and match the ingestion results.

**Validates: Requirements 1.8**

### Property 4: Semantic Chunking Preserves Code Structure

*For any* source code file, semantic chunking should produce chunks that align with code boundaries (functions, classes, or logical blocks) and maintain proper line number ranges.

**Validates: Requirements 1.3**

### Property 5: Architecture Response Completeness

*For any* ingested repository, requesting architecture analysis should return a response containing both a textual summary with required fields (overview, components, patterns, data_flow, entry_points) and a valid Mermaid diagram.

**Validates: Requirements 2.2, 2.3, 2.4, 2.5**

### Property 6: Mermaid Diagram Component Consistency

*For any* architecture analysis, all components mentioned in the architecture summary should appear as nodes in the generated Mermaid diagram.

**Validates: Requirements 2.6**

### Property 7: Multi-Level Explanation Generation

*For any* file in an ingested repository, requesting an explanation should generate responses for all three complexity levels (beginner, intermediate, advanced) with required fields (purpose, key_functions, patterns, dependencies, complexity).

**Validates: Requirements 3.1, 3.5**

### Property 8: Vector Search Returns Ranked Results

*For any* chat query, the vector store search should return chunks ranked by semantic similarity in descending order.

**Validates: Requirements 4.1, 4.2**

### Property 9: Top-K Context Selection

*For any* chat query, exactly top-k chunks (where k is the configured limit) should be selected as context for the LLM prompt.

**Validates: Requirements 4.3**

### Property 10: RAG Prompt Contains Query and Context

*For any* chat query, the constructed RAG prompt should contain both the user's question and the retrieved code chunks.

**Validates: Requirements 4.4**

### Property 11: Chat Response Contains Citations

*For any* chat response, the answer should include references to source files in the format [filename:line] or [filename].

**Validates: Requirements 4.6**

### Property 12: Conversation History Preservation

*For any* session, sending multiple chat messages should preserve the conversation history, with each subsequent message having access to previous messages in the session.

**Validates: Requirements 4.7**

### Property 13: Documentation Export Completeness

*For any* documentation export request, the generated artifact should contain all architecture summaries and Mermaid diagrams for the session.

**Validates: Requirements 5.1, 5.2**

### Property 14: Export Artifact Accessibility

*For any* stored documentation artifact, the returned download URL should be valid and allow retrieval of the artifact from S3.

**Validates: Requirements 5.4, 5.5**

### Property 15: Session Creation with Unique ID

*For any* repository analysis initiation, a new session should be created in DynamoDB with a unique session ID and TTL set to 24 hours from creation.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 16: Session State Round Trip

*For any* active session, retrieving the session state should return all analyzed repositories and conversation history associated with that session.

**Validates: Requirements 6.7**

### Property 17: Session Cleanup Completeness

*For any* deleted session, all associated embeddings should be removed from the vector store and all artifacts should be removed from S3.

**Validates: Requirements 6.5, 6.6, 12.5**

### Property 18: API Routing Correctness

*For any* valid API request to a defined endpoint, the request should be routed to the appropriate Lambda handler and return a response with the correct HTTP status code.

**Validates: Requirements 8.6, 8.7**

### Property 19: Input Validation Error Handling

*For any* invalid request (malformed JSON, missing required fields, invalid values), the API should return a 400 status code with a descriptive error message.

**Validates: Requirements 8.8, 10.7**

### Property 20: DynamoDB Data Structure Validation

*For any* data written to DynamoDB tables (Sessions, Repositories, Cache), the stored item should contain all required fields with correct data types.

**Validates: Requirements 9.1, 9.2, 9.3**

### Property 21: S3 Artifact Organization

*For any* artifact stored in S3, the object key should follow the organizational structure (session_id/repo_id/artifact_type) and the object should have server-side encryption enabled.

**Validates: Requirements 9.4, 9.5, 9.7, 12.3**

### Property 22: AWS Service Error Handling

*For any* AWS service error (DynamoDB, S3, Bedrock), the system should catch the error, log it, and return a user-friendly error message to the client.

**Validates: Requirements 10.5**

### Property 23: Invalid Repository URL Handling

*For any* invalid or inaccessible GitHub URL, the ingestion service should return an error message indicating the repository cannot be accessed without crashing.

**Validates: Requirements 10.1**

### Property 24: Empty Vector Store Handling

*For any* chat query when the vector store contains no chunks for the repository, the chat service should return a message indicating no relevant code was found.

**Validates: Requirements 10.4**

### Property 25: Bedrock Retry with Exponential Backoff

*For any* transient Bedrock API error (throttling, temporary unavailability), the system should retry the request with exponential backoff up to the maximum retry limit.

**Validates: Requirements 10.6**

### Property 26: LLM Service Unavailability Handling

*For any* Bedrock service unavailability error, the system should return an error message indicating the AI service is temporarily unavailable.

**Validates: Requirements 10.3**

### Property 27: Concurrent Ingestion Independence

*For any* two concurrent ingestion requests, each should be processed independently in separate Lambda invocations without interfering with each other.

**Validates: Requirements 11.1**

### Property 28: Credential Non-Persistence

*For any* ingestion request with a GitHub token, the token should not be stored in DynamoDB, S3, or logs after the ingestion completes.

**Validates: Requirements 12.6**

## Error Handling

### Error Categories

#### 1. Input Validation Errors (4xx)
- **Invalid GitHub URL**: Return 400 with message "Invalid GitHub URL format"
- **Repository Not Found**: Return 404 with message "Repository not found"
- **Repository Too Large**: Return 413 with message "Repository exceeds 500 file limit"
- **Missing Required Fields**: Return 400 with message specifying missing field
- **Invalid Parameter Values**: Return 400 with message specifying invalid value

#### 2. Authentication/Authorization Errors (401, 403)
- **GitHub Authentication Failed**: Return 401 with message "Failed to access private repository"
- **CORS Violation**: Return 403 with message "Origin not allowed"

#### 3. Service Errors (5xx)
- **Lambda Timeout**: Return 504 with message "Operation timed out"
- **Bedrock Unavailable**: Return 503 with message "AI service temporarily unavailable"
- **DynamoDB Error**: Return 500 with message "Database operation failed"
- **S3 Error**: Return 500 with message "Storage operation failed"
- **Vector Store Error**: Return 500 with message "Search operation failed"

#### 4. Rate Limiting (429)
- **Bedrock Throttling**: Return 429 with message "Rate limit exceeded, please try again"

### Error Response Format

All error responses follow a consistent JSON structure:

```json
{
  "error": "Human-readable error message",
  "status_code": 400,
  "details": {
    "field": "source",
    "reason": "Missing required field"
  }
}
```

### Retry Strategy

**Exponential Backoff Configuration:**
- Base delay: 1 second
- Maximum retries: 3
- Backoff multiplier: 2
- Retry on: ThrottlingException, ServiceUnavailableException, InternalServerException
- No retry on: ValidationException, AccessDeniedException

**Implementation:**
```python
for attempt in range(max_retries):
    try:
        return bedrock_client.invoke_model(...)
    except ClientError as e:
        if e.response['Error']['Code'] in RETRYABLE_ERRORS:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
        else:
            raise
```

### Graceful Degradation

1. **Architecture Analysis Failure**: Return basic tech stack summary without LLM-generated insights
2. **Mermaid Diagram Generation Failure**: Return simple fallback diagram with basic structure
3. **File Explanation Failure**: Return metadata-based explanation (LOC, functions, imports)
4. **Cache Miss**: Generate fresh response (no error to user)
5. **Vector Store Cold Start**: Accept slower first query after Lambda cold start

### Logging Strategy

**Log Levels:**
- **ERROR**: Service failures, unhandled exceptions, data corruption
- **WARN**: Retries, fallback activations, rate limiting
- **INFO**: Request/response, ingestion progress, cache hits/misses
- **DEBUG**: Detailed execution flow, intermediate results

**Sensitive Data Handling:**
- Never log GitHub tokens or credentials
- Truncate code content in logs to first 200 characters
- Mask user identifiers in production logs

## Testing Strategy

### Dual Testing Approach

The CodeLens system requires both unit testing and property-based testing to ensure comprehensive correctness:

**Unit Tests** validate:
- Specific examples and edge cases
- Integration points between components
- Error conditions and boundary cases
- UI component rendering and interactions

**Property-Based Tests** validate:
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Invariants and round-trip properties
- System behavior across the input space

Together, unit tests catch concrete bugs while property tests verify general correctness.

### Property-Based Testing Configuration

**Framework Selection:**
- **Backend (Python)**: Use `hypothesis` library for property-based testing
- **Frontend (TypeScript)**: Use `fast-check` library for property-based testing

**Test Configuration:**
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: codelens, Property {number}: {property_text}`

**Example Property Test Structure:**

```python
from hypothesis import given, strategies as st
import pytest

# Feature: codelens, Property 1: Embedding Round Trip
@given(st.text(min_size=10, max_size=1000))
def test_embedding_round_trip(code_chunk: str):
    """
    For any code chunk, generating an embedding and storing it
    should allow retrieval with embedding intact.
    """
    # Generate embedding
    embedding = bedrock_client.generate_embedding(code_chunk)
    
    # Store in vector store
    chunk_id = vector_store.add_chunk(
        repo_id="test-repo",
        file_path="test.py",
        content=code_chunk,
        embedding=embedding,
        metadata={}
    )
    
    # Retrieve chunk
    retrieved = vector_store.get_chunk(chunk_id)
    
    # Verify embedding matches
    assert retrieved['content'] == code_chunk
    assert retrieved['embedding'] == embedding
```

### Unit Testing Strategy

#### Backend Unit Tests

**Test Coverage Areas:**
1. **Code Processor**
   - File discovery with various directory structures
   - Semantic chunking for different languages
   - Tech stack detection for common frameworks
   - Import extraction for Python, JavaScript, Java, Go
   - Complexity estimation accuracy

2. **Bedrock Client**
   - Embedding generation with valid text
   - Claude invocation with various prompts
   - Retry logic with simulated throttling
   - Error handling for service unavailability
   - Streaming response handling

3. **Vector Store**
   - Chunk storage and retrieval
   - Similarity search with known embeddings
   - Repository deletion cleanup
   - Maximum capacity handling
   - Empty store queries

4. **Lambda Handlers**
   - Request parsing and validation
   - Response formatting
   - Error response structure
   - CORS header inclusion
   - DynamoDB integration

**Test Fixtures:**
- Sample repositories with known structure
- Pre-generated embeddings for deterministic tests
- Mock Bedrock responses
- Mock DynamoDB tables (using moto library)
- Mock S3 buckets (using moto library)

#### Frontend Unit Tests

**Test Coverage Areas:**
1. **Components**
   - ExplanationPanel tab switching
   - ChatInterface message display
   - ArchitectureView diagram rendering
   - FileTree expand/collapse
   - DocGenerator export button states

2. **API Service**
   - Request construction
   - Response parsing
   - Error handling
   - Retry logic

3. **State Management**
   - Repository state updates
   - Chat message history
   - Session management
   - Cache invalidation

**Testing Libraries:**
- Vitest for test runner
- React Testing Library for component tests
- MSW (Mock Service Worker) for API mocking

### Integration Testing

**End-to-End Scenarios:**
1. Complete ingestion flow: URL → clone → parse → embed → store
2. Architecture generation: retrieve → analyze → diagram → cache
3. Chat conversation: query → search → RAG → response → history
4. Documentation export: compile → format → store → download

**Test Environment:**
- Dedicated AWS account for testing
- Separate DynamoDB tables with test prefix
- Separate S3 bucket for test artifacts
- Mock Bedrock responses for cost control

### Performance Testing

**Load Testing Scenarios:**
1. Concurrent ingestion of 10 repositories
2. 100 chat queries per minute
3. Architecture generation for 500-file repository
4. Vector search with 10,000 chunks

**Performance Targets:**
- Ingestion: < 60 seconds for 500 files
- Architecture: < 10 seconds for analysis
- File Explanation: < 5 seconds per file
- Chat Query: < 3 seconds for response
- Vector Search: < 1 second for top-k retrieval

### Security Testing

**Security Test Cases:**
1. CORS policy enforcement
2. Input sanitization (SQL injection, XSS)
3. GitHub token non-persistence
4. S3 presigned URL expiration
5. DynamoDB encryption at rest
6. HTTPS enforcement

### Continuous Integration

**CI Pipeline:**
1. Run unit tests on every commit
2. Run property tests on pull requests
3. Run integration tests on main branch
4. Deploy to staging environment
5. Run smoke tests in staging
6. Manual approval for production deployment

**Test Reporting:**
- Code coverage target: 80% for backend, 70% for frontend
- Property test failure reports with counterexamples
- Performance regression detection
- Security vulnerability scanning

