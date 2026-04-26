#!/bin/bash

# Test documentation generation endpoint
API_BASE="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"

# Replace with an actual repo_id from your system
REPO_ID="test-repo-123"

echo "Testing documentation generation..."
echo "POST ${API_BASE}/repos/${REPO_ID}/docs/generate"
echo ""

curl -X POST "${API_BASE}/repos/${REPO_ID}/docs/generate" \
  -H "Content-Type: application/json" \
  -v

echo ""
echo ""
echo "Testing documentation status..."
echo "GET ${API_BASE}/repos/${REPO_ID}/docs/status"
echo ""

curl -X GET "${API_BASE}/repos/${REPO_ID}/docs/status" \
  -H "Content-Type: application/json" \
  -v
