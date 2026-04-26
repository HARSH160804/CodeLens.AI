# Requirements Document

## Introduction

CodeLens is an AI-powered codebase understanding tool that enables developers to quickly comprehend unfamiliar codebases through intelligent analysis, visualization, and interactive chat. The system ingests GitHub repositories, generates architecture summaries with visual diagrams, provides multi-level code explanations, and supports conversational queries using retrieval-augmented generation (RAG).

## Glossary

- **CodeLens_System**: The complete AI-powered codebase understanding application
- **Ingestion_Service**: Lambda handler that clones, parses, chunks, and embeds repository code
- **Architecture_Service**: Lambda handler that generates architecture summaries and Mermaid diagrams
- **Explanation_Service**: Lambda handler that provides file explanations at multiple complexity levels
- **Chat_Service**: Lambda handler that processes conversational queries using RAG
- **Documentation_Service**: Lambda handler that exports documentation artifacts
- **Vector_Store**: In-memory vector database for semantic code search
- **Embedding_Model**: Amazon Bedrock Titan Embeddings model for code vectorization
- **LLM**: Amazon Bedrock Claude 3.5 Sonnet model for text generation
- **Session**: A user's active workspace containing one or more analyzed repositories
- **Repository**: A GitHub codebase that has been ingested and analyzed
- **Code_Chunk**: A semantically meaningful segment of source code for embedding
- **RAG_Query**: A user question answered using retrieved code context

## Requirements

### Requirement 1: Repository Ingestion

**User Story:** As a developer, I want to ingest GitHub repositories, so that I can analyze and understand their codebase structure.

#### Acceptance Criteria

1. WHEN a valid GitHub repository URL is provided, THE Ingestion_Service SHALL clone the repository to temporary storage
2. WHEN the repository is cloned, THE Ingestion_Service SHALL parse all source code files and extract metadata
3. WHEN source code files are parsed, THE Ingestion_Service SHALL chunk the code into semantically meaningful segments
4. WHEN code chunks are created, THE Ingestion_Service SHALL generate embeddings using the Embedding_Model
5. WHEN embeddings are generated, THE Ingestion_Service SHALL store them in the Vector_Store and DynamoDB Embeddings table
6. IF a repository contains more than 500 files, THEN THE Ingestion_Service SHALL return an error indicating the file limit exceeded
7. WHEN ingestion begins, THE Ingestion_Service SHALL complete the entire process within 60 seconds
8. WHEN ingestion completes, THE Ingestion_Service SHALL store repository metadata in the DynamoDB Repositories table
9. WHEN ingestion completes, THE Ingestion_Service SHALL store code artifacts in the S3 bucket

### Requirement 2: Architecture Summary Generation

**User Story:** As a developer, I want to view architecture summaries with visual diagrams, so that I can quickly understand the high-level structure of a codebase.

#### Acceptance Criteria

1. WHEN a repository has been ingested, THE Architecture_Service SHALL analyze the codebase structure
2. WHEN the codebase structure is analyzed, THE Architecture_Service SHALL generate a textual architecture summary using the LLM
3. WHEN the architecture summary is generated, THE Architecture_Service SHALL create a Mermaid diagram representing the architecture
4. WHEN the Mermaid diagram is created, THE Architecture_Service SHALL return both the summary and diagram to the client
5. THE Architecture_Service SHALL identify key components, modules, and their relationships in the architecture summary
6. THE Mermaid diagram SHALL include all major system components and their dependencies

### Requirement 3: Multi-Level File Explanation

**User Story:** As a developer, I want to view file explanations at different complexity levels, so that I can understand code according to my expertise level.

#### Acceptance Criteria

1. WHEN a file from an ingested repository is selected, THE Explanation_Service SHALL generate three explanations at different complexity levels
2. THE Explanation_Service SHALL generate a beginner-level explanation using simple terminology and high-level concepts
3. THE Explanation_Service SHALL generate an intermediate-level explanation including implementation details and design patterns
4. THE Explanation_Service SHALL generate an advanced-level explanation covering optimization techniques, edge cases, and architectural implications
5. WHEN explanations are generated, THE Explanation_Service SHALL return all three levels to the client
6. THE Explanation_Service SHALL use the LLM to generate contextually accurate explanations based on the file content

### Requirement 4: Conversational Codebase Chat

**User Story:** As a developer, I want to ask questions about the codebase in natural language, so that I can quickly find specific information without manual searching.

#### Acceptance Criteria

1. WHEN a user submits a question about an ingested repository, THE Chat_Service SHALL retrieve relevant code chunks from the Vector_Store
2. WHEN relevant code chunks are retrieved, THE Chat_Service SHALL rank them by semantic similarity to the query
3. WHEN code chunks are ranked, THE Chat_Service SHALL select the top-k most relevant chunks as context
4. WHEN context is selected, THE Chat_Service SHALL construct a prompt combining the user question and retrieved code context
5. WHEN the prompt is constructed, THE Chat_Service SHALL generate a response using the LLM
6. WHEN the response is generated, THE Chat_Service SHALL return the answer with references to source files
7. THE Chat_Service SHALL maintain conversation history within a session for contextual follow-up questions

### Requirement 5: Documentation Export

**User Story:** As a developer, I want to export generated documentation, so that I can share insights with my team or save them for future reference.

#### Acceptance Criteria

1. WHEN a user requests documentation export, THE Documentation_Service SHALL compile all architecture summaries for the session
2. WHEN architecture summaries are compiled, THE Documentation_Service SHALL include all generated Mermaid diagrams
3. WHEN diagrams are included, THE Documentation_Service SHALL format the documentation in a readable structure
4. WHEN the documentation is formatted, THE Documentation_Service SHALL store the export artifact in the S3 bucket
5. WHEN the artifact is stored, THE Documentation_Service SHALL return a download URL to the client
6. THE Documentation_Service SHALL support export formats including Markdown and PDF

### Requirement 6: Session Management

**User Story:** As a developer, I want my analysis sessions to be managed automatically, so that I can resume work and avoid stale data accumulation.

#### Acceptance Criteria

1. WHEN a user begins analyzing a repository, THE CodeLens_System SHALL create a new session in the DynamoDB Sessions table
2. WHEN a session is created, THE CodeLens_System SHALL assign a unique session identifier
3. WHEN a session is created, THE CodeLens_System SHALL set a time-to-live (TTL) of 24 hours
4. WHEN the TTL expires, THE CodeLens_System SHALL automatically delete the session and associated data
5. WHEN a session is deleted, THE CodeLens_System SHALL remove all associated embeddings from the Vector_Store
6. WHEN a session is deleted, THE CodeLens_System SHALL remove all associated artifacts from the S3 bucket
7. WHEN a user returns to an active session, THE CodeLens_System SHALL restore the session state including all analyzed repositories

### Requirement 7: Frontend User Interface

**User Story:** As a developer, I want an intuitive web interface, so that I can easily interact with the codebase analysis features.

#### Acceptance Criteria

1. THE Frontend SHALL provide a repository URL input field for initiating ingestion
2. THE Frontend SHALL display ingestion progress with real-time status updates
3. THE Frontend SHALL render architecture summaries with interactive Mermaid diagrams
4. THE Frontend SHALL provide a file browser for navigating ingested repository structure
5. WHEN a file is selected, THE Frontend SHALL display explanation tabs for beginner, intermediate, and advanced levels
6. THE Frontend SHALL provide a chat interface for submitting natural language queries
7. WHEN chat responses are received, THE Frontend SHALL display them with syntax-highlighted code references
8. THE Frontend SHALL provide an export button for downloading generated documentation
9. THE Frontend SHALL implement dark mode as the default theme
10. THE Frontend SHALL be built using React, TypeScript, Tailwind CSS, and Vite

### Requirement 8: API Gateway Integration

**User Story:** As a system integrator, I want a REST API that routes requests to appropriate Lambda handlers, so that the frontend can communicate with backend services.

#### Acceptance Criteria

1. THE API_Gateway SHALL expose a REST endpoint for repository ingestion requests
2. THE API_Gateway SHALL expose a REST endpoint for architecture summary requests
3. THE API_Gateway SHALL expose a REST endpoint for file explanation requests
4. THE API_Gateway SHALL expose a REST endpoint for chat query requests
5. THE API_Gateway SHALL expose a REST endpoint for documentation export requests
6. WHEN a request is received, THE API_Gateway SHALL route it to the appropriate Lambda handler
7. WHEN a Lambda handler responds, THE API_Gateway SHALL return the response to the client with appropriate HTTP status codes
8. THE API_Gateway SHALL enforce request validation and return descriptive error messages for invalid requests

### Requirement 9: Data Persistence

**User Story:** As a system administrator, I want repository data and embeddings persisted reliably, so that analysis results are available throughout the session lifetime.

#### Acceptance Criteria

1. THE DynamoDB_Sessions_Table SHALL store session metadata including session ID, creation timestamp, and TTL
2. THE DynamoDB_Repositories_Table SHALL store repository metadata including URL, name, file count, and ingestion timestamp
3. THE DynamoDB_Embeddings_Table SHALL store code chunk embeddings with associated metadata including file path and chunk index
4. THE S3_Bucket SHALL store cloned repository code artifacts organized by session and repository
5. THE S3_Bucket SHALL store exported documentation artifacts with unique identifiers
6. WHEN data is written to DynamoDB, THE CodeLens_System SHALL handle write capacity errors gracefully
7. WHEN data is written to S3, THE CodeLens_System SHALL use server-side encryption

### Requirement 10: Error Handling and Resilience

**User Story:** As a developer, I want the system to handle errors gracefully, so that I receive clear feedback when operations fail.

#### Acceptance Criteria

1. WHEN a GitHub repository URL is invalid or inaccessible, THE Ingestion_Service SHALL return an error message indicating the repository cannot be accessed
2. WHEN a Lambda function times out, THE CodeLens_System SHALL return an error message indicating the operation exceeded time limits
3. WHEN the LLM service is unavailable, THE CodeLens_System SHALL return an error message indicating the AI service is temporarily unavailable
4. WHEN the Vector_Store is empty for a query, THE Chat_Service SHALL return a message indicating no relevant code was found
5. WHEN DynamoDB or S3 operations fail, THE CodeLens_System SHALL log the error and return a user-friendly error message
6. THE CodeLens_System SHALL implement retry logic with exponential backoff for transient AWS service failures
7. THE CodeLens_System SHALL validate all user inputs and return descriptive validation errors

### Requirement 11: Performance and Scalability

**User Story:** As a system administrator, I want the system to perform efficiently under load, so that multiple users can analyze codebases concurrently.

#### Acceptance Criteria

1. WHEN multiple ingestion requests are received concurrently, THE Ingestion_Service SHALL process them in parallel using separate Lambda invocations
2. THE Vector_Store SHALL support efficient similarity search with sub-second query latency for repositories up to 500 files
3. WHEN the LLM generates responses, THE Chat_Service SHALL stream responses to the client to reduce perceived latency
4. THE Lambda_Functions SHALL be configured with appropriate memory and timeout settings to handle maximum repository size
5. THE DynamoDB_Tables SHALL use on-demand billing mode to automatically scale with request volume
6. THE S3_Bucket SHALL use lifecycle policies to automatically delete expired session artifacts

### Requirement 12: Security and Access Control

**User Story:** As a security administrator, I want the system to protect user data and control access, so that repository code remains confidential.

#### Acceptance Criteria

1. THE API_Gateway SHALL enforce HTTPS for all client communications
2. THE Lambda_Functions SHALL execute with IAM roles granting least-privilege access to AWS services
3. THE S3_Bucket SHALL enforce server-side encryption for all stored artifacts
4. THE DynamoDB_Tables SHALL encrypt data at rest using AWS managed keys
5. WHEN a session expires, THE CodeLens_System SHALL ensure all associated data is permanently deleted
6. THE CodeLens_System SHALL not store GitHub credentials or access tokens beyond the ingestion request lifecycle
7. THE Frontend SHALL implement CORS policies to restrict API access to authorized origins
