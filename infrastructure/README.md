# CodeLens Infrastructure

AWS SAM infrastructure for CodeLens serverless application.

## Architecture

### API Gateway Endpoints
- `POST /repos/ingest` - Ingest a GitHub repository
- `GET /repos/{id}/status` - Get repository ingestion status
- `GET /repos/{id}/architecture` - Get architecture summary with Mermaid diagram
- `GET /repos/{id}/files/{path}` - Get file explanation (query param: `explanation_level`)
- `POST /repos/{id}/chat` - Chat with codebase using RAG
- `POST /repos/{id}/docs` - Generate and export documentation

### Lambda Functions
| Function | Memory | Timeout | Purpose |
|----------|--------|---------|---------|
| IngestRepoFunction | 512MB | 5min | Clone, parse, chunk, and embed repository |
| GetRepoStatusFunction | 256MB | 30sec | Check ingestion status |
| ArchitectureFunction | 512MB | 2min | Generate architecture summaries |
| ExplainFileFunction | 256MB | 30sec | Multi-level file explanations |
| ChatFunction | 512MB | 1min | RAG-based conversational chat |
| GenerateDocsFunction | 512MB | 2min | Export documentation |

### DynamoDB Tables
- **SessionsTable** - User sessions with 24h TTL
  - PK: `session_id`
  - TTL: `ttl` attribute
- **RepositoriesTable** - Repository metadata
  - PK: `repo_id`
- **EmbeddingsTable** - Code chunk embeddings
  - PK: `repo_id`
  - SK: `chunk_id`

### S3 Bucket
- **CodeArtifactsBucket** - Stores cloned repositories and exports
  - Lifecycle: Delete after 1 day
  - Encryption: AES256

### IAM Permissions
All Lambda functions have:
- Bedrock: `InvokeModel`, `InvokeModelWithResponseStream`
- DynamoDB: CRUD operations on respective tables
- S3: `GetObject`, `PutObject`, `DeleteObject`
- CloudWatch Logs: Full logging permissions

## Deployment

### Prerequisites
```bash
# Install AWS SAM CLI
brew install aws-sam-cli

# Configure AWS credentials
aws configure
```

### Deploy
```bash
# Build
sam build

# Deploy with guided prompts
sam deploy --guided

# Or deploy with saved config
sam deploy
```

### Local Testing
```bash
# Start local API
sam local start-api

# Invoke function locally
sam local invoke IngestRepoFunction -e events/ingest.json
```

## Environment Variables

Each Lambda function receives:
- `SESSIONS_TABLE` - DynamoDB Sessions table name
- `REPOSITORIES_TABLE` - DynamoDB Repositories table name
- `EMBEDDINGS_TABLE` - DynamoDB Embeddings table name
- `CODE_BUCKET` - S3 bucket name
- `BEDROCK_REGION` - AWS region for Bedrock

## CORS Configuration

API Gateway is configured with CORS:
- Allow Methods: GET, POST, PUT, DELETE, OPTIONS
- Allow Headers: Content-Type, Authorization, X-Api-Key
- Allow Origin: * (configure for production)

## Monitoring

CloudWatch Logs are automatically created for all Lambda functions:
- Log Group: `/aws/lambda/{FunctionName}`
- Retention: Default (never expire)

## Cost Optimization

- DynamoDB: Pay-per-request billing
- Lambda: ARM64 architecture for cost savings
- S3: Lifecycle policy deletes objects after 1 day
- Sessions: Automatic cleanup via TTL

## Cleanup

```bash
sam delete
```


## Deployment Scripts

### deploy.sh

Automated deployment script that:
1. Validates SAM template
2. Builds SAM application
3. Deploys to AWS (with or without guided setup)
4. Extracts API Gateway endpoint
5. Updates frontend/.env with API endpoint
6. Installs frontend dependencies if needed
7. Outputs deployment summary

**Usage:**
```bash
cd infrastructure
./deploy.sh
```

**Features:**
- Color-coded output for easy reading
- Error handling with automatic rollback
- Automatic frontend configuration
- Comprehensive deployment summary
- CI/CD ready (use --no-confirm-changeset)

### teardown.sh

Cleanup script that safely removes all resources:
1. Empties S3 buckets (required before deletion)
2. Deletes CloudFormation stack
3. Cleans up local build artifacts
4. Confirms before deletion

**Usage:**
```bash
cd infrastructure
./teardown.sh
```

**Safety Features:**
- Requires explicit "yes" confirmation
- Empties S3 buckets before deletion
- Waits for complete stack deletion
- Cleans up local artifacts

## Quick Start

```bash
# First time deployment
cd infrastructure
./deploy.sh

# Start frontend
cd ../frontend
npm run dev

# Teardown everything
cd ../infrastructure
./teardown.sh
```
