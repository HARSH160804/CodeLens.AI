#!/bin/bash

# Documentation API Test Script
# Tests the documentation generation and export endpoints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${1:-https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod}"
REPO_ID="${2:-test-repo}"

echo "========================================="
echo "Documentation API Test"
echo "========================================="
echo "API URL: $API_URL"
echo "Repo ID: $REPO_ID"
echo ""

# Test 1: Check if API is reachable
echo -e "${YELLOW}Test 1: Checking API connectivity...${NC}"
if curl -s -o /dev/null -w "%{http_code}" "$API_URL/repos/$REPO_ID/status" | grep -q "200\|404"; then
    echo -e "${GREEN}✓ API is reachable${NC}"
else
    echo -e "${RED}✗ API is not reachable${NC}"
    echo "Please check if the backend is deployed"
    exit 1
fi
echo ""

# Test 2: Check documentation status
echo -e "${YELLOW}Test 2: Checking documentation status...${NC}"
STATUS_RESPONSE=$(curl -s "$API_URL/repos/$REPO_ID/docs/status")
echo "Response: $STATUS_RESPONSE"

if echo "$STATUS_RESPONSE" | grep -q "state"; then
    STATE=$(echo "$STATUS_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Status endpoint works${NC}"
    echo "Current state: $STATE"
else
    echo -e "${RED}✗ Status endpoint failed${NC}"
fi
echo ""

# Test 3: Try to generate documentation
echo -e "${YELLOW}Test 3: Testing documentation generation...${NC}"
GEN_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/repos/$REPO_ID/docs/generate")
HTTP_STATUS=$(echo "$GEN_RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$GEN_RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"
echo "Response: $BODY"

if [ "$HTTP_STATUS" = "202" ]; then
    echo -e "${GREEN}✓ Generation started successfully${NC}"
elif [ "$HTTP_STATUS" = "409" ]; then
    echo -e "${YELLOW}⚠ Generation already in progress${NC}"
elif [ "$HTTP_STATUS" = "400" ]; then
    echo -e "${RED}✗ Bad request - check if architecture analysis exists${NC}"
else
    echo -e "${RED}✗ Generation failed with status $HTTP_STATUS${NC}"
fi
echo ""

# Test 4: Check if documentation exists for export
echo -e "${YELLOW}Test 4: Checking if documentation can be exported...${NC}"
EXPORT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/repos/$REPO_ID/docs/export?format=md")

if [ "$EXPORT_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Documentation exists and can be exported${NC}"
elif [ "$EXPORT_STATUS" = "404" ]; then
    echo -e "${YELLOW}⚠ Documentation not found - generate it first${NC}"
else
    echo -e "${RED}✗ Export check failed with status $EXPORT_STATUS${NC}"
fi
echo ""

# Test 5: Check CORS headers
echo -e "${YELLOW}Test 5: Checking CORS headers...${NC}"
CORS_HEADERS=$(curl -s -I -X OPTIONS "$API_URL/repos/$REPO_ID/docs/generate" | grep -i "access-control")

if [ -n "$CORS_HEADERS" ]; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
    echo "$CORS_HEADERS"
else
    echo -e "${RED}✗ CORS headers missing${NC}"
fi
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo "If all tests pass, the backend is working correctly."
echo "If tests fail, check the error messages above."
echo ""
echo "Common issues:"
echo "- API not reachable: Backend not deployed"
echo "- 404 errors: Endpoint not configured in API Gateway"
echo "- 400 errors: Architecture analysis missing"
echo "- 500 errors: Lambda execution error (check CloudWatch logs)"
echo ""
