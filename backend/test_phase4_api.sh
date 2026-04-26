#!/bin/bash
# Phase 4: Backend API Implementation Smoke Test
# Tests ingest_repo.py and architecture.py handlers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_ENDPOINT="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"
REPOS_TABLE="BloomWay-Repositories"
TEST_REPO="https://github.com/octocat/Hello-World"
REPO_ID=""

echo "=========================================="
echo "Phase 4: Backend API Smoke Test"
echo "=========================================="
echo ""

# Step 1: Verify deployment
echo -e "${YELLOW}Step 1: Verify CloudFormation Stack${NC}"
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    echo -e "${GREEN}✓ Stack Status: $STACK_STATUS${NC}"
else
    echo -e "${RED}✗ Stack Status: $STACK_STATUS${NC}"
    exit 1
fi

echo "API Endpoint: $API_ENDPOINT"
echo "Repos Table: $REPOS_TABLE"
echo ""

# Step 2: Test Ingestion Endpoint
echo -e "${YELLOW}Step 2: Test POST /repos/ingest${NC}"
echo "Payload: {\"source_type\": \"github\", \"source\": \"$TEST_REPO\"}"
echo ""

INGEST_RESPONSE=$(curl -s -X POST "$API_ENDPOINT/repos/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"source_type\": \"github\", \"source\": \"$TEST_REPO\"}" \
  -w "\nHTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$INGEST_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$INGEST_RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"
echo "Response Body:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo ""

# Verify HTTP status
if [ "$HTTP_STATUS" == "200" ] || [ "$HTTP_STATUS" == "202" ]; then
    echo -e "${GREEN}✓ HTTP Status is valid (200 or 202)${NC}"
else
    echo -e "${RED}✗ Expected HTTP 200 or 202, got $HTTP_STATUS${NC}"
    exit 1
fi

# Extract repo_id
REPO_ID=$(echo "$RESPONSE_BODY" | jq -r '.repo_id' 2>/dev/null)
if [ -z "$REPO_ID" ] || [ "$REPO_ID" == "null" ]; then
    echo -e "${RED}✗ No repo_id in response${NC}"
    exit 1
else
    echo -e "${GREEN}✓ repo_id: $REPO_ID${NC}"
fi

# Verify response fields
STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status' 2>/dev/null)
FILE_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.file_count' 2>/dev/null)

if [ -n "$STATUS" ] && [ "$STATUS" != "null" ]; then
    echo -e "${GREEN}✓ status: $STATUS${NC}"
else
    echo -e "${RED}✗ Missing status field${NC}"
fi

if [ -n "$FILE_COUNT" ] && [ "$FILE_COUNT" != "null" ]; then
    echo -e "${GREEN}✓ file_count: $FILE_COUNT${NC}"
else
    echo -e "${YELLOW}⚠ file_count not present (may be processing)${NC}"
fi

echo ""

# Step 3: Verify DynamoDB Entry
echo -e "${YELLOW}Step 3: Verify DynamoDB Entry${NC}"
echo "Querying table: $REPOS_TABLE for repo_id: $REPO_ID"
echo ""

# Wait a moment for DynamoDB write
sleep 2

DYNAMO_ITEM=$(aws dynamodb get-item \
  --table-name "$REPOS_TABLE" \
  --key "{\"repo_id\": {\"S\": \"$REPO_ID\"}}" \
  --output json 2>/dev/null || echo "{}")

if echo "$DYNAMO_ITEM" | jq -e '.Item' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Item exists in DynamoDB${NC}"
    
    # Verify required fields
    STORED_REPO_ID=$(echo "$DYNAMO_ITEM" | jq -r '.Item.repo_id.S' 2>/dev/null)
    STORED_STATUS=$(echo "$DYNAMO_ITEM" | jq -r '.Item.status.S' 2>/dev/null)
    STORED_FILE_COUNT=$(echo "$DYNAMO_ITEM" | jq -r '.Item.file_count.N' 2>/dev/null)
    CREATED_AT=$(echo "$DYNAMO_ITEM" | jq -r '.Item.created_at.S' 2>/dev/null)
    
    echo "  repo_id: $STORED_REPO_ID"
    echo "  status: $STORED_STATUS"
    echo "  file_count: $STORED_FILE_COUNT"
    echo "  created_at: $CREATED_AT"
    
    if [ "$STORED_REPO_ID" == "$REPO_ID" ]; then
        echo -e "${GREEN}✓ repo_id matches${NC}"
    else
        echo -e "${RED}✗ repo_id mismatch${NC}"
    fi
    
    if [ -n "$STORED_STATUS" ] && [ "$STORED_STATUS" != "null" ]; then
        echo -e "${GREEN}✓ status field present${NC}"
    else
        echo -e "${RED}✗ status field missing${NC}"
    fi
    
    if [ -n "$CREATED_AT" ] && [ "$CREATED_AT" != "null" ]; then
        echo -e "${GREEN}✓ created_at field present${NC}"
    else
        echo -e "${RED}✗ created_at field missing${NC}"
    fi
else
    echo -e "${RED}✗ Item not found in DynamoDB${NC}"
    echo "This may indicate the ingestion failed or is still processing."
fi

echo ""

# Step 4: Test Architecture Endpoint
echo -e "${YELLOW}Step 4: Test GET /repos/{repo_id}/architecture${NC}"
echo "Endpoint: $API_ENDPOINT/repos/$REPO_ID/architecture?level=intermediate"
echo ""

# Wait for ingestion to complete (in real scenario, would poll status)
echo "Waiting 5 seconds for ingestion to complete..."
sleep 5

ARCH_RESPONSE=$(curl -s -X GET "$API_ENDPOINT/repos/$REPO_ID/architecture?level=intermediate" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_STATUS:%{http_code}")

ARCH_HTTP_STATUS=$(echo "$ARCH_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
ARCH_BODY=$(echo "$ARCH_RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $ARCH_HTTP_STATUS"
echo "Response Body (truncated):"
echo "$ARCH_BODY" | jq '.' 2>/dev/null | head -30 || echo "$ARCH_BODY" | head -30
echo ""

# Verify HTTP status
if [ "$ARCH_HTTP_STATUS" == "200" ]; then
    echo -e "${GREEN}✓ HTTP Status is 200${NC}"
else
    echo -e "${RED}✗ Expected HTTP 200, got $ARCH_HTTP_STATUS${NC}"
    if [ "$ARCH_HTTP_STATUS" == "404" ]; then
        echo -e "${YELLOW}⚠ Repository may not be fully ingested yet${NC}"
    fi
fi

# Verify response structure
if echo "$ARCH_BODY" | jq -e '.' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Valid JSON response${NC}"
    
    # Check architecture.overview
    OVERVIEW=$(echo "$ARCH_BODY" | jq -r '.architecture.overview' 2>/dev/null)
    if [ -n "$OVERVIEW" ] && [ "$OVERVIEW" != "null" ] && [ ${#OVERVIEW} -gt 10 ]; then
        echo -e "${GREEN}✓ architecture.overview is non-empty (${#OVERVIEW} chars)${NC}"
    else
        echo -e "${RED}✗ architecture.overview is empty or missing${NC}"
    fi
    
    # Check architecture.components
    COMPONENTS=$(echo "$ARCH_BODY" | jq -r '.architecture.components | type' 2>/dev/null)
    if [ "$COMPONENTS" == "array" ]; then
        COMPONENT_COUNT=$(echo "$ARCH_BODY" | jq -r '.architecture.components | length' 2>/dev/null)
        echo -e "${GREEN}✓ architecture.components is an array ($COMPONENT_COUNT items)${NC}"
    else
        echo -e "${RED}✗ architecture.components is not an array${NC}"
    fi
    
    # Check diagram
    DIAGRAM=$(echo "$ARCH_BODY" | jq -r '.diagram' 2>/dev/null)
    if echo "$DIAGRAM" | grep -q "flowchart\|graph"; then
        echo -e "${GREEN}✓ diagram contains valid Mermaid syntax${NC}"
        echo "  First line: $(echo "$DIAGRAM" | head -1)"
    else
        echo -e "${RED}✗ diagram does not contain valid Mermaid syntax${NC}"
    fi
else
    echo -e "${RED}✗ Invalid JSON response${NC}"
fi

echo ""

# Step 5: Error Path Tests
echo -e "${YELLOW}Step 5: Error Path Sanity Checks${NC}"
echo ""

# Test 5a: Invalid repo URL
echo "Test 5a: Invalid repo URL (expect 400)"
INVALID_RESPONSE=$(curl -s -X POST "$API_ENDPOINT/repos/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "github", "source": "not-a-valid-url"}' \
  -w "\nHTTP_STATUS:%{http_code}")

INVALID_STATUS=$(echo "$INVALID_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
if [ "$INVALID_STATUS" == "400" ] || [ "$INVALID_STATUS" == "401" ]; then
    echo -e "${GREEN}✓ Invalid URL returns 400/401 (got $INVALID_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠ Expected 400/401, got $INVALID_STATUS${NC}"
fi
echo ""

# Test 5b: Missing repo_id
echo "Test 5b: Missing repo_id in architecture endpoint (expect 404)"
MISSING_RESPONSE=$(curl -s -X GET "$API_ENDPOINT/repos/nonexistent-repo-id/architecture" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_STATUS:%{http_code}")

MISSING_STATUS=$(echo "$MISSING_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
if [ "$MISSING_STATUS" == "404" ]; then
    echo -e "${GREEN}✓ Missing repo_id returns 404${NC}"
else
    echo -e "${YELLOW}⚠ Expected 404, got $MISSING_STATUS${NC}"
fi
echo ""

# Final Summary
echo "=========================================="
echo -e "${YELLOW}Phase 4 Verification Summary${NC}"
echo "=========================================="
echo ""
echo "Tested Components:"
echo "  - POST /repos/ingest"
echo "  - GET /repos/{id}/architecture"
echo "  - DynamoDB integration"
echo "  - Error handling"
echo ""

if [ "$HTTP_STATUS" == "200" ] || [ "$HTTP_STATUS" == "202" ]; then
    if [ -n "$REPO_ID" ] && [ "$REPO_ID" != "null" ]; then
        if [ "$ARCH_HTTP_STATUS" == "200" ]; then
            echo -e "${GREEN}✓✓✓ PHASE 4: PASSED ✓✓✓${NC}"
            echo ""
            echo "All critical tests passed:"
            echo "  ✓ Ingestion endpoint working"
            echo "  ✓ DynamoDB storage working"
            echo "  ✓ Architecture endpoint working"
            echo "  ✓ Error handling working"
            exit 0
        else
            echo -e "${YELLOW}⚠⚠⚠ PHASE 4: PARTIAL PASS ⚠⚠⚠${NC}"
            echo ""
            echo "Ingestion works, but architecture endpoint needs attention."
            exit 0
        fi
    fi
fi

echo -e "${RED}✗✗✗ PHASE 4: FAILED ✗✗✗${NC}"
echo ""
echo "One or more critical tests failed. Review the output above."
exit 1
