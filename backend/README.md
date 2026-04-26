# CodeLens Backend

Python-based AWS Lambda backend for CodeLens codebase understanding tool.

## Architecture

### Lambda Handlers
- `ingest_repo.py` - Repository ingestion (FR-1.1, FR-1.2, FR-1.3)
- `explain_file.py` - Multi-level file explanations (FR-2.1-2.4)
- `architecture.py` - Architecture summaries with Mermaid (FR-3.1-3.6)
- `chat.py` - RAG-based conversational chat (FR-4.1-4.6)
- `generate_docs.py` - Documentation export (FR-5.1-5.5)

### Library Modules
- `bedrock_client.py` - Amazon Bedrock integration (Claude 3.5 Sonnet + Titan Embeddings)
- `code_processor.py` - Code parsing and chunking
- `vector_store.py` - In-memory vector database
- `github_client.py` - GitHub API integration
- `session_manager.py` - DynamoDB session handling

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy with AWS SAM
sam build
sam deploy --guided
```

## Testing

```bash
pytest
```

## Environment Variables

- `SESSIONS_TABLE` - DynamoDB sessions table name
- `REPOSITORIES_TABLE` - DynamoDB repositories table name
- `EMBEDDINGS_TABLE` - DynamoDB embeddings table name
- `CODE_BUCKET` - S3 bucket for code artifacts
