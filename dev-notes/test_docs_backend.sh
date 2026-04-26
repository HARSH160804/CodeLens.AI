#!/bin/bash

# Quick test of documentation generation backend
# Replace REPO_ID with an actual repository ID from your system

REPO_ID="${1:-test-repo}"
API_BASE="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"

echo "=== Testing Documentation Backend ==="
echo "Repository ID: $REPO_ID"
echo "API Base: $API_BASE"
echo ""

# Test 1: Check status endpoint
echo "1. Checking status endpoint..."
STATUS_RESPONSE=$(curl -s "${API_BASE}/repos/${REPO_ID}/docs/status")
echo "Response: $STATUS_RESPONSE"
echo ""

# Test 2: Trigger generation (if you want to test)
# Uncomment the lines below to actually trigger generation
# echo "2. Triggering generation..."
# GEN_RESPONSE=$(curl -s -X POST "${API_BASE}/repos/${REPO_ID}/docs/generate")
# echo "Response: $GEN_RESPONSE"
# echo ""

echo "=== Test Complete ==="
echo ""
echo "To trigger generation, run:"
echo "curl -X POST '${API_BASE}/repos/${REPO_ID}/docs/generate'"
