# Phase 4: Backend API Implementation - Smoke Test Plan

## Overview
This document provides a comprehensive smoke test plan for verifying the backend API implementation, specifically the `ingest_repo.py` and `architecture.py` Lambda handlers.

## Prerequisites
- AWS CLI configured with appropriate credentials
- `jq` installed for JSON parsing
- `curl` installed for API testing
- CloudFormation stack `h2s-backend` deployed

## Test Scope
- **In Scope**: 
  - POST /repos/ingest endpoint
  - GET /repos/{id}/architecture endpoint
  - DynamoDB integration
  - Basic error handling
  
- **Out of Scope**:
  - Load testing
  - Comprehensive error scenarios
  - Performance benchmarking
  - Security testing

## Automated Test Script

Run the automated test script:
```bash
cd backend
./test_phase4_api.sh
```

## Manual Test Steps

### Step 1: Verify Deployment

**Command:**
```bash
aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].StackStatus' --output text
```

**Expected Output:**
```
CREATE_COMPLETE
```

**Get API Endpoint:**
```bash
aws cloudformation describe-stacks --stack-name h2s-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

**Expected Output:**
```
https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/
```

**Get DynamoDB Table Name:**
```bash
aws cloudformation describe-stacks --stack-name h2s-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoriesTableName`].OutputValue' \
  --output text
```

**Expected Output:**
```
BloomWay-Repositories
```

---

### Step 2: Test Ingestion Endpoint

**Command:**
```bash
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github",
    "source": "https://github.com/octocat/Hello-World"
  }' | jq '.'
```

**Expected Response Structure:**
```json
{
  "repo_id": "uuid-string",
  "session_id": "uuid-string",
  "status": "completed",
  "file_count": 3,
  "chunk_count": 5,
  "tech_stack": {
    "languages": ["..."],
    "frameworks": ["..."],
    "libraries": ["..."]
  },
  "message": "Repository ingested successfully"
}
```

**Verification Checklist:**
- [ ] HTTP Status: 200 or 202
- [ ] Response contains `repo_id` (UUID format)
- [ ] Response contains `status` field
- [ ] Response contains `file_count` (integer)
- [ ] Response contains `chunk_count` (integer)
- [ ] Response contains `tech_stack` object
- [ ] Response contains `message` string

**Save the `repo_id` for subsequent tests:**
```bash
REPO_ID="<paste-repo-id-here>"
```

---

### Step 3: Verify DynamoDB Entry

**Command:**
```bash
aws dynamodb get-item \
  --table-name BloomWay-Repositories \
  --key '{"repo_id": {"S": "'$REPO_ID'"}}' \
  --output json | jq '.Item'
```

**Expected Output Structure:**
```json
{
  "repo_id": {"S": "uuid-string"},
  "source": {"S": "https://github.com/octocat/Hello-World"},
  "source_type": {"S": "github"},
  "file_count": {"N": "3"},
  "chunk_count": {"N": "5"},
  "tech_stack": {"M": {...}},
  "architecture_summary": {"S": "..."},
  "status": {"S": "completed"},
  "created_at": {"S": "2024-03-02T12:00:00Z"},
  "updated_at": {"S": "2024-03-02T12:00:00Z"}
}
```

**Verification Checklist:**
- [ ] Item exists in DynamoDB
- [ ] `repo_id` matches the ingestion response
- [ ] `status` field is present
- [ ] `file_count` field is present
- [ ] `created_at` timestamp is present
- [ ] `updated_at` timestamp is present

---

### Step 4: Test Architecture Endpoint

**Wait for ingestion to complete (if async):**
```bash
sleep 5
```

**Command:**
```bash
curl -X GET "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/$REPO_ID/architecture?level=intermediate" \
  -H "Content-Type: application/json" | jq '.'
```

**Expected Response Structure:**
```json
{
  "repo_id": "uuid-string",
  "architecture": {
    "overview": "Brief description of the architecture...",
    "components": [
      {
        "name": "Component Name",
        "description": "Component description",
        "files": ["file1.py", "file2.js"]
      }
    ],
    "patterns": ["Pattern1", "Pattern2"],
    "data_flow": "Description of data flow...",
    "entry_points": ["main.py", "index.js"]
  },
  "diagram": "flowchart TD\n    A[Component] --> B[Component]\n    ...",
  "generated_at": "2024-03-02T12:00:00Z"
}
```

**Verification Checklist:**
- [ ] HTTP Status: 200
- [ ] Response is valid JSON
- [ ] `architecture.overview` is non-empty string (>10 chars)
- [ ] `architecture.components` is an array
- [ ] `architecture.components` has at least 1 item
- [ ] `architecture.patterns` is an array
- [ ] `architecture.data_flow` is a string
- [ ] `architecture.entry_points` is an array
- [ ] `diagram` contains "flowchart" or "graph" keyword
- [ ] `generated_at` is an ISO timestamp

**Test different levels:**
```bash
# Basic level
curl -X GET "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/$REPO_ID/architecture?level=basic" | jq '.architecture.overview'

# Advanced level
curl -X GET "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/$REPO_ID/architecture?level=advanced" | jq '.architecture.overview'
```

---

### Step 5: Error Path Sanity Checks

#### Test 5a: Invalid Repository URL

**Command:**
```bash
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github",
    "source": "not-a-valid-url"
  }' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Expected:**
- HTTP Status: 400 or 401
- Error message in response body

#### Test 5b: Missing Source Field

**Command:**
```bash
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github"
  }' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Expected:**
- HTTP Status: 400
- Error message: "Missing required field: 'source'"

#### Test 5c: Non-existent Repository ID

**Command:**
```bash
curl -X GET "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/nonexistent-repo-id/architecture" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"
```

**Expected:**
- HTTP Status: 404
- Error message: "Repository nonexistent-repo-id not found"

#### Test 5d: Invalid Level Parameter

**Command:**
```bash
curl -X GET "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/$REPO_ID/architecture?level=invalid" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"
```

**Expected:**
- HTTP Status: 400
- Error message about invalid level

---

## Test Results Template

### Ingestion Endpoint Test
- [ ] PASS: HTTP 200/202 returned
- [ ] PASS: repo_id present in response
- [ ] PASS: status field present
- [ ] PASS: file_count present
- [ ] PASS: DynamoDB entry created
- [ ] PASS: All required fields in DynamoDB

### Architecture Endpoint Test
- [ ] PASS: HTTP 200 returned
- [ ] PASS: Valid JSON response
- [ ] PASS: architecture.overview non-empty
- [ ] PASS: architecture.components is array
- [ ] PASS: diagram contains Mermaid syntax
- [ ] PASS: Cache working (second call faster)

### Error Handling Test
- [ ] PASS: Invalid URL returns 400/401
- [ ] PASS: Missing source returns 400
- [ ] PASS: Non-existent repo returns 404
- [ ] PASS: Invalid level returns 400

---

## Common Issues and Troubleshooting

### Issue: Ingestion returns 500 error
**Possible Causes:**
- Lambda timeout (increase timeout in template.yaml)
- Bedrock API throttling (implement retry logic)
- Git clone failure (check network/permissions)

**Debug:**
```bash
aws logs tail /aws/lambda/IngestRepoFunction --follow
```

### Issue: Architecture endpoint returns 404
**Possible Causes:**
- Repository not fully ingested
- DynamoDB write failed
- repo_id mismatch

**Debug:**
```bash
# Check if repo exists in DynamoDB
aws dynamodb scan --table-name BloomWay-Repositories --limit 5
```

### Issue: Mermaid diagram is empty
**Possible Causes:**
- Bedrock generation failed
- Fallback not triggered properly

**Debug:**
Check CloudWatch logs for the ArchitectureFunction

---

## Performance Benchmarks (Reference Only)

These are NOT part of the smoke test but provided for reference:

- Ingestion time: ~30-60 seconds for small repos (<50 files)
- Architecture generation: ~5-10 seconds (first call)
- Architecture generation: ~1-2 seconds (cached)
- DynamoDB write latency: <100ms

---

## Final Verification Checklist

- [ ] CloudFormation stack deployed successfully
- [ ] API Gateway endpoint accessible
- [ ] POST /repos/ingest working
- [ ] DynamoDB integration working
- [ ] GET /repos/{id}/architecture working
- [ ] Mermaid diagram generation working
- [ ] Error handling working
- [ ] CORS headers present in responses

---

## Phase 4 Status

**PASS Criteria:**
- All ingestion tests pass
- All architecture tests pass
- At least 2 error path tests pass
- DynamoDB integration verified

**FAIL Criteria:**
- Ingestion endpoint returns 500
- Architecture endpoint returns 500
- DynamoDB writes fail
- Critical fields missing from responses

---

## Notes

- This is a smoke test, not comprehensive testing
- Production deployment would require additional tests:
  - Load testing
  - Security testing
  - Integration testing with frontend
  - End-to-end user flows
  - Performance testing under load
  - Chaos engineering tests
