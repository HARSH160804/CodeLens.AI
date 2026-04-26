# Deployment Checkpoint 2.2: First Deployment

**Status:** ✅ COMPLETED

**Date:** March 2, 2026

**Stack Name:** `h2s-backend`

---

## Deployment Summary

The CodeLens backend has been successfully deployed to AWS using SAM.

### What Was Deployed

✅ **CloudFormation Stack:** `h2s-backend`
- Status: CREATE_COMPLETE
- Created: 2026-03-02T08:24:35Z

✅ **Lambda Functions (6):**
- `h2s-backend-IngestRepoFunction-*`
- `h2s-backend-GetRepoStatusFunction-*`
- `h2s-backend-ArchitectureFunction-*`
- `h2s-backend-ExplainFileFunction-*`
- `h2s-backend-ChatFunction-*`
- `h2s-backend-GenerateDocsFunction-*`

✅ **DynamoDB Tables (3):**
- `BloomWay-Sessions` (with 24h TTL)
- `BloomWay-Repositories`
- `BloomWay-Embeddings`

✅ **S3 Bucket:**
- `bloomway-code-055392178569-us-east-1`
- Lifecycle policy: Delete after 1 day

✅ **API Gateway:**
- Endpoint: `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/`
- Status: Active (returns 403 for root path, as expected)

✅ **IAM Roles:**
- Lambda execution roles with Bedrock permissions
- DynamoDB and S3 access configured

✅ **Bedrock Access:**
- Claude 3.5 Sonnet v2: Enabled
- Titan Text Embeddings v1: Enabled

---

## Verification (Corrected)

### 1. CloudFormation Stack

```bash
aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].StackStatus'
```

**Expected:** `CREATE_COMPLETE`

**Actual:** ✅ `CREATE_COMPLETE`

### 2. Lambda Functions

```bash
aws lambda list-functions --query "Functions[?contains(FunctionName, 'h2s-backend')].FunctionName" --output table
```

**Expected:** 6 Lambda functions with prefix `h2s-backend-`

**Actual:** ✅ All 6 functions exist

### 3. API Gateway

```bash
aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text
```

**Expected:** API Gateway endpoint URL

**Actual:** ✅ `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/`

**Test endpoint:**
```bash
curl -i https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/
```

**Expected:** HTTP 403 or 404 (not 5xx)

**Actual:** ✅ HTTP 403 (API Gateway is active, no route defined for root path)

### 4. DynamoDB Tables

```bash
aws dynamodb list-tables --query "TableNames[?contains(@, 'BloomWay')]"
```

**Expected:** 3 tables (Sessions, Repositories, Embeddings)

**Actual:** ✅ All 3 tables exist

### 5. S3 Bucket

```bash
aws s3 ls | grep bloomway
```

**Expected:** 1 bucket with lifecycle policy

**Actual:** ✅ `bloomway-code-055392178569-us-east-1`

---

## Deployment Script

The production-ready deployment script is located at:

```
infrastructure/deploy.sh
```

### Usage

```bash
cd infrastructure
./deploy.sh
```

### What It Does

1. ✅ Validates SAM template
2. ✅ Runs `sam build`
3. ✅ Runs `sam deploy --no-confirm-changeset --stack-name h2s-backend`
4. ✅ Extracts API Gateway endpoint (if exists)
5. ✅ Updates `frontend/.env` with API endpoint
6. ✅ Installs frontend dependencies if needed
7. ✅ Outputs comprehensive deployment summary

### Key Features

- Uses existing `h2s-backend` stack (does NOT create new stack)
- Gracefully handles missing API Gateway output
- Error handling with `set -e`
- Color-coded output
- Works with or without `samconfig.toml`

---

## Current State vs Documentation

### ⚠️ Important Notes

1. **Stack Name Mismatch:**
   - Documentation originally referenced: `codelens`
   - Actual deployed stack: `h2s-backend`
   - **Resolution:** All scripts and docs updated to use `h2s-backend`

2. **API Gateway Status:**
   - Originally expected: Not deployed
   - Actual status: ✅ Deployed and active
   - Endpoint: `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/`

3. **Bedrock Access:**
   - Status: ✅ Enabled
   - Models: Claude 3.5 Sonnet v2, Titan Embeddings v1

---

## Next Steps

### Immediate Actions

1. ✅ Update frontend `.env` with API endpoint
2. ✅ Test Lambda functions individually
3. ✅ Verify API Gateway routes

### Future Checkpoints

- **Checkpoint 2.3:** API Integration Testing
- **Checkpoint 2.4:** Frontend-Backend Integration
- **Checkpoint 2.5:** End-to-End Testing

---

## Rollback Instructions

If you need to rollback or teardown:

```bash
cd infrastructure
./teardown.sh
```

This will:
1. Empty S3 buckets
2. Delete CloudFormation stack `h2s-backend`
3. Clean up local build artifacts

---

## Troubleshooting

### Issue: Stack name mismatch

**Symptom:** Scripts reference `codelens` but stack is `h2s-backend`

**Solution:** ✅ Fixed - All scripts now use `h2s-backend`

### Issue: API Gateway not found

**Symptom:** Cannot find API endpoint

**Solution:** ✅ API Gateway exists at `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/`

### Issue: Lambda functions not visible

**Symptom:** Cannot list Lambda functions

**Solution:** Use correct prefix: `h2s-backend-*` (not `bloomway-*`)

---

## Verification Commands (Quick Reference)

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].StackStatus'

# List Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, 'h2s-backend')].FunctionName" --output table

# Get API endpoint
aws cloudformation describe-stacks --stack-name h2s-backend --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text

# Test API endpoint
curl -i https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/

# List DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'BloomWay')]"

# List S3 buckets
aws s3 ls | grep bloomway
```

---

**Checkpoint Status:** ✅ COMPLETED

**Last Updated:** March 2, 2026

**Next Checkpoint:** API Integration Testing
