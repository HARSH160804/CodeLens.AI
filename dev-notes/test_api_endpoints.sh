#!/bin/bash

# Test API Endpoints for Premium Dashboard
# Usage: ./test_api_endpoints.sh <repo_id>

API_BASE="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"
REPO_ID="${1}"

if [ -z "$REPO_ID" ]; then
    echo "❌ Error: Repository ID required"
    echo "Usage: ./test_api_endpoints.sh <repo_id>"
    echo ""
    echo "To get a repo_id, ingest a repository first:"
    echo "  1. Go to http://localhost:5173/"
    echo "  2. Ingest https://github.com/kennethreitz/setup.py"
    echo "  3. Copy the repo_id from the URL"
    exit 1
fi

echo "========================================="
echo "  Testing BloomWay AI API Endpoints"
echo "  Repo ID: $REPO_ID"
echo "========================================="
echo ""

# Test 1: Status Endpoint
echo "📋 Test 1: GET /repos/$REPO_ID/status"
echo "---"
STATUS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/repos/$REPO_ID/status")
HTTP_CODE=$(echo "$STATUS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$STATUS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: 200 OK"
    echo "$BODY" | jq -r '.status' | xargs -I {} echo "   Status: {}"
    echo "$BODY" | jq -r '.file_count' | xargs -I {} echo "   Files: {}"
    FILE_PATHS_COUNT=$(echo "$BODY" | jq -r '.file_paths | length')
    echo "   File paths: $FILE_PATHS_COUNT"
    
    if [ "$FILE_PATHS_COUNT" -gt 0 ]; then
        echo "   ✅ File paths populated"
        FIRST_FILE=$(echo "$BODY" | jq -r '.file_paths[0]')
        echo "   First file: $FIRST_FILE"
    else
        echo "   ❌ File paths empty (repository needs re-ingestion)"
    fi
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 2: Metadata Endpoint
echo "📊 Test 2: GET /repos/$REPO_ID/metadata"
echo "---"
METADATA_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/repos/$REPO_ID/metadata")
HTTP_CODE=$(echo "$METADATA_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$METADATA_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: 200 OK"
    echo "$BODY" | jq -r '.repoName' | xargs -I {} echo "   Repo: {}"
    echo "$BODY" | jq -r '.totalFiles' | xargs -I {} echo "   Total files: {}"
    echo "$BODY" | jq -r '.totalLines' | xargs -I {} echo "   Total lines: {}"
    echo "$BODY" | jq -r '.primaryLanguage' | xargs -I {} echo "   Language: {}"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "⚠️  Status: 404 (Endpoint not deployed yet - this is OK)"
    echo "   Dashboard will use fallback data from status endpoint"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 3: File Content Endpoint (if we have a file path)
if [ "$FILE_PATHS_COUNT" -gt 0 ]; then
    echo "📄 Test 3: GET /repos/$REPO_ID/file?path=$FIRST_FILE"
    echo "---"
    ENCODED_PATH=$(echo "$FIRST_FILE" | jq -sRr @uri)
    FILE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/repos/$REPO_ID/file?path=$ENCODED_PATH")
    HTTP_CODE=$(echo "$FILE_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$FILE_RESPONSE" | sed '/HTTP_CODE/d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Status: 200 OK"
        echo "$BODY" | jq -r '.file_path' | xargs -I {} echo "   File: {}"
        echo "$BODY" | jq -r '.language' | xargs -I {} echo "   Language: {}"
        echo "$BODY" | jq -r '.lines' | xargs -I {} echo "   Lines: {}"
        CONTENT_LENGTH=$(echo "$BODY" | jq -r '.content | length')
        echo "   Content length: $CONTENT_LENGTH chars"
        
        if [ "$CONTENT_LENGTH" -gt 0 ]; then
            echo "   ✅ File content retrieved"
        else
            echo "   ❌ File content empty"
        fi
    elif [ "$HTTP_CODE" = "404" ]; then
        echo "⚠️  Status: 404 (Endpoint not deployed yet)"
    else
        echo "❌ Status: $HTTP_CODE"
        echo "$BODY"
    fi
    echo ""
    
    # Test 4: Explain File Endpoint
    echo "🤖 Test 4: GET /repos/$REPO_ID/files/$ENCODED_PATH?level=intermediate"
    echo "---"
    EXPLAIN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/repos/$REPO_ID/files/$ENCODED_PATH?level=intermediate")
    HTTP_CODE=$(echo "$EXPLAIN_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$EXPLAIN_RESPONSE" | sed '/HTTP_CODE/d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Status: 200 OK"
        echo "$BODY" | jq -r '.explanation.purpose' | head -c 100 | xargs -I {} echo "   Purpose: {}..."
        echo "$BODY" | jq -r '.explanation.confidence' | xargs -I {} echo "   Confidence: {}"
        echo "$BODY" | jq -r '.level' | xargs -I {} echo "   Level: {}"
        echo "   ✅ Explanation generated"
    else
        echo "❌ Status: $HTTP_CODE"
        echo "$BODY" | head -20
    fi
else
    echo "⚠️  Skipping file content tests (no file paths available)"
fi

echo ""
echo "========================================="
echo "  Test Summary"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. If file_paths is empty, re-ingest the repository"
echo "  2. If endpoints return 404, verify deployment"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Open http://localhost:5173/"
echo "  5. Navigate to /repo/$REPO_ID"
echo ""
