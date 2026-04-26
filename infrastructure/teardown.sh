#!/bin/bash

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STACK_NAME="bloomway-ai"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  BloomWay AI Teardown Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

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

# Confirm deletion
echo -e "${RED}WARNING: This will delete all BloomWay AI resources!${NC}"
echo -e "Stack: ${YELLOW}$STACK_NAME${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Teardown cancelled"
    exit 0
fi

# Empty S3 buckets first (required before deletion)
print_info "Emptying S3 buckets..."
BUCKETS=$(aws s3 ls 2>/dev/null | grep bloomway | awk '{print $3}')
if [ -n "$BUCKETS" ]; then
    echo "$BUCKETS" | while read -r bucket; do
        if [ -n "$bucket" ]; then
            print_info "Emptying bucket: $bucket"
            aws s3 rm "s3://$bucket" --recursive 2>/dev/null || true
            print_success "Emptied $bucket"
        fi
    done
else
    print_info "No BloomWay S3 buckets found"
fi
echo ""

# Delete CloudFormation stack
print_info "Deleting CloudFormation stack: $STACK_NAME"
if aws cloudformation delete-stack --stack-name "$STACK_NAME" 2>/dev/null; then
    print_info "Waiting for stack deletion to complete..."
    if aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" 2>/dev/null; then
        print_success "Stack deleted successfully"
    else
        print_warning "Stack deletion may still be in progress. Check AWS Console."
    fi
else
    print_error "Failed to delete stack. It may not exist or you may lack permissions."
fi
echo ""

# Clean up local build artifacts
print_info "Cleaning up local build artifacts..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -d "$SCRIPT_DIR/.aws-sam" ]; then
    rm -rf "$SCRIPT_DIR/.aws-sam"
    print_success "Removed .aws-sam directory"
fi

if [ -f "$SCRIPT_DIR/samconfig.toml" ]; then
    rm -f "$SCRIPT_DIR/samconfig.toml"
    print_success "Removed samconfig.toml"
fi
echo ""

print_success "Teardown completed!"
echo ""
