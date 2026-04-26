#!/bin/bash

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="h2s-backend"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  BloomWay AI Deployment Script${NC}"
echo -e "${BLUE}  Stack: ${STACK_NAME}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Error handler
error_exit() {
    print_error "$1"
    exit 1
}

# Step 1: Validate SAM template
print_info "Step 1: Validating SAM template..."
cd "$SCRIPT_DIR"
if sam validate; then
    print_success "SAM template is valid"
else
    error_exit "SAM template validation failed"
fi
echo ""

# Step 2: Build SAM application
print_info "Step 2: Building SAM application..."
if sam build; then
    print_success "SAM build completed successfully"
else
    error_exit "SAM build failed"
fi
echo ""

# Step 3: Deploy SAM application
print_info "Step 3: Deploying SAM application to stack: ${STACK_NAME}..."
if [ -f "samconfig.toml" ]; then
    print_info "Using existing samconfig.toml configuration"
    if sam deploy --no-confirm-changeset --stack-name "$STACK_NAME"; then
        print_success "SAM deployment completed successfully"
    else
        error_exit "SAM deployment failed"
    fi
else
    print_warning "No samconfig.toml found. Deploying with default configuration..."
    if sam deploy --no-confirm-changeset --stack-name "$STACK_NAME" --capabilities CAPABILITY_IAM --resolve-s3; then
        print_success "SAM deployment completed successfully"
    else
        error_exit "SAM deployment failed"
    fi
fi
echo ""

# Step 4: Extract API Gateway endpoint
print_info "Step 4: Extracting API Gateway endpoint..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -n "$API_ENDPOINT" ] && [ "$API_ENDPOINT" != "None" ]; then
    print_success "API Gateway endpoint: $API_ENDPOINT"
    
    # Create or update frontend .env file
    ENV_FILE="$FRONTEND_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        # Update existing .env file
        if grep -q "VITE_API_BASE_URL" "$ENV_FILE"; then
            sed -i.bak "s|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=$API_ENDPOINT|" "$ENV_FILE"
            rm -f "$ENV_FILE.bak"
            print_success "Updated $ENV_FILE"
        else
            echo "VITE_API_BASE_URL=$API_ENDPOINT" >> "$ENV_FILE"
            print_success "Added API endpoint to $ENV_FILE"
        fi
    else
        echo "VITE_API_BASE_URL=$API_ENDPOINT" > "$ENV_FILE"
        print_success "Created $ENV_FILE with API endpoint"
    fi
else
    print_warning "API Gateway endpoint not found in stack outputs"
    print_info "This is expected if API Gateway hasn't been added to the template yet"
    API_ENDPOINT="Not deployed yet"
fi
echo ""

# Step 5: Install frontend dependencies if needed
print_info "Step 5: Checking frontend dependencies..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    print_info "node_modules not found. Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    if npm install; then
        print_success "Frontend dependencies installed successfully"
    else
        print_warning "Failed to install frontend dependencies. You may need to run 'npm install' manually."
    fi
else
    print_success "Frontend dependencies already installed"
fi
echo ""

# Step 6: Output deployment summary
print_info "Step 6: Deployment Summary"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Stack Name:${NC} $STACK_NAME"
echo ""

# Get stack outputs
STACK_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs' \
    --output json 2>/dev/null || echo "[]")

if [ "$STACK_OUTPUTS" != "[]" ]; then
    echo -e "${GREEN}Stack Outputs:${NC}"
    echo "$STACK_OUTPUTS" | grep -o '"OutputKey"[^}]*' | while read -r line; do
        KEY=$(echo "$line" | grep -o '"OutputKey": "[^"]*"' | cut -d'"' -f4)
        VALUE=$(echo "$line" | grep -o '"OutputValue": "[^"]*"' | cut -d'"' -f4)
        echo -e "  ${YELLOW}$KEY:${NC} $VALUE"
    done
else
    print_warning "Could not retrieve stack outputs"
fi

echo ""
if [ "$API_ENDPOINT" != "Not deployed yet" ]; then
    echo -e "${GREEN}API Endpoint:${NC} $API_ENDPOINT"
    echo -e "${GREEN}Frontend .env:${NC} $FRONTEND_DIR/.env"
else
    echo -e "${YELLOW}API Endpoint:${NC} Not deployed yet (expected)"
fi
echo ""

# Get Lambda functions
print_info "Lambda Functions:"
aws lambda list-functions --query "Functions[?contains(FunctionName, '$STACK_NAME')].FunctionName" --output text 2>/dev/null | tr '\t' '\n' | while read -r func; do
    if [ -n "$func" ]; then
        echo -e "  ${YELLOW}•${NC} $func"
    fi
done

echo ""

# Get DynamoDB tables
print_info "DynamoDB Tables:"
aws dynamodb list-tables --query "TableNames[?contains(@, 'BloomWay')]" --output text 2>/dev/null | tr '\t' '\n' | while read -r table; do
    if [ -n "$table" ]; then
        echo -e "  ${YELLOW}•${NC} $table"
    fi
done

echo ""

# Get S3 buckets
print_info "S3 Buckets:"
aws s3 ls 2>/dev/null | grep bloomway | awk '{print $3}' | while read -r bucket; do
    if [ -n "$bucket" ]; then
        echo -e "  ${YELLOW}•${NC} $bucket"
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
print_success "Deployment completed successfully!"
echo ""
print_info "Next steps:"
echo "  1. Verify Bedrock model access in AWS Console"
if [ "$API_ENDPOINT" != "Not deployed yet" ]; then
    echo "  2. Test API endpoint: curl $API_ENDPOINT"
    echo "  3. Start frontend: cd frontend && npm run dev"
else
    echo "  2. API Gateway will be added in a future deployment"
    echo "  3. Lambda functions are ready and accessible"
fi
echo ""
