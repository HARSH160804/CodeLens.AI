#!/bin/bash

# Test documentation generation status flow
# This script tests the complete flow: generate -> poll status -> verify state

REPO_ID="test-repo-123"
API_BASE="https://your-api-gateway-url.amazonaws.com/prod"

echo "=== Testing Documentation Generation Flow ==="
echo ""

# Step 1: Check initial status
echo "1. Checking initial status..."
curl -s "${API_BASE}/repos/${REPO_ID}/docs/status" | jq '.'
echo ""

# Step 2: Trigger generation
echo "2. Triggering documentation generation..."
GENERATE_RESPONSE=$(curl -s -X POST "${API_BASE}/repos/${REPO_ID}/docs/generate")
echo "$GENERATE_RESPONSE" | jq '.'
echo ""

# Step 3: Poll status every 2 seconds
echo "3. Polling status (will check 10 times, every 2 seconds)..."
for i in {1..10}; do
  echo "   Poll #$i:"
  STATUS_RESPONSE=$(curl -s "${API_BASE}/repos/${REPO_ID}/docs/status")
  echo "   $STATUS_RESPONSE" | jq '.'
  
  STATE=$(echo "$STATUS_RESPONSE" | jq -r '.state')
  echo "   Current state: $STATE"
  
  if [ "$STATE" = "generated" ]; then
    echo "   ✓ Generation completed successfully!"
    break
  elif [ "$STATE" = "failed" ]; then
    echo "   ✗ Generation failed!"
    echo "   Error: $(echo "$STATUS_RESPONSE" | jq -r '.error_message')"
    break
  fi
  
  sleep 2
  echo ""
done

echo ""
echo "=== Test Complete ==="
