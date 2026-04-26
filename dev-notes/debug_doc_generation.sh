#!/bin/bash
# Comprehensive debugging script for documentation generation

echo "=== DOCUMENTATION GENERATION DEBUG ==="
echo ""

# Get repo ID from user
if [ -z "$1" ]; then
    echo "Usage: ./debug_doc_generation.sh <REPO_ID>"
    exit 1
fi

REPO_ID="$1"
API_BASE="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"

echo "Repository ID: $REPO_ID"
echo ""

# 1. Check DynamoDB state
echo "1. Checking DynamoDB state..."
python3 check_dynamodb_state.py "$REPO_ID"
echo ""

# 2. Check API status endpoint
echo "2. Checking API status endpoint..."
STATUS_RESPONSE=$(curl -s "${API_BASE}/repos/${REPO_ID}/docs/status")
echo "Response: $STATUS_RESPONSE"
echo ""

# 3. Check Lambda function configuration
echo "3. Checking Lambda timeout configuration..."
LAMBDA_NAME=$(aws lambda list-functions --region us-east-1 --query "Functions[?contains(FunctionName, 'GenerateDocs')].FunctionName" --output text)
if [ -n "$LAMBDA_NAME" ]; then
    echo "Lambda function: $LAMBDA_NAME"
    TIMEOUT=$(aws lambda get-function-configuration --function-name "$LAMBDA_NAME" --region us-east-1 --query 'Timeout' --output text)
    echo "Timeout: ${TIMEOUT}s"
else
    echo "Lambda function not found"
fi
echo ""

# 4. Check recent Lambda logs
echo "4. Checking recent Lambda logs (last 10 minutes)..."
if [ -n "$LAMBDA_NAME" ]; then
    aws logs tail "/aws/lambda/${LAMBDA_NAME}" --since 10m --region us-east-1 --format short | tail -50
else
    echo "Cannot check logs - Lambda function not found"
fi
echo ""

# 5. Test generation endpoint (optional)
echo "5. Would you like to trigger a new generation? (y/n)"
read -r TRIGGER
if [ "$TRIGGER" = "y" ]; then
    echo "Triggering generation..."
    GENERATE_RESPONSE=$(curl -s -X POST "${API_BASE}/repos/${REPO_ID}/docs/generate")
    echo "Response: $GENERATE_RESPONSE"
    echo ""
    echo "Waiting 5 seconds..."
    sleep 5
    echo "Checking status again..."
    STATUS_RESPONSE=$(curl -s "${API_BASE}/repos/${REPO_ID}/docs/status")
    echo "Response: $STATUS_RESPONSE"
fi

echo ""
echo "=== DEBUG COMPLETE ==="
