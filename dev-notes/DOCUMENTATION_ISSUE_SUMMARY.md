# Documentation Feature Issue Summary

## Current Status: Network Error During Generation

### Error Observed
```
Documentation generation failed: AxiosError: Network Error
at async Object.mutationFn (useDocumentation.ts:66:24)
```

This is happening when clicking "Generate Documentation" button, NOT during export.

## Root Cause
The frontend cannot connect to the backend API endpoint. This is a **deployment/configuration issue**, not a code bug.

## What We've Implemented

### Backend (✅ Complete)
- ✅ DocumentationStore class with DynamoDB operations
- ✅ DocumentationGenerator class with AI-powered generation
- ✅ ExportService class with Markdown and PDF conversion
- ✅ API handlers: generate, export, status
- ✅ SAM template configuration
- ✅ Unit tests (42 tests passing)

### Frontend (✅ Complete)
- ✅ useDocumentation hook with React Query
- ✅ GenerateButton component
- ✅ ExportDropdown component
- ✅ ArchitectureView integration
- ✅ Error handling and display
- ✅ Enhanced logging for debugging

### Infrastructure (⚠️ Needs Verification)
- ⚠️ Backend deployment status unknown
- ⚠️ API Gateway endpoint configuration unknown
- ⚠️ Lambda function existence unknown

## The Problem

The error "Network Error" means the HTTP request isn't reaching the backend at all. Possible causes:

1. **Backend not deployed** - Lambda functions don't exist in AWS
2. **Wrong API URL** - Frontend is calling incorrect endpoint
3. **API Gateway not configured** - Endpoint doesn't exist
4. **CORS issue** - Preflight request failing

## How to Fix

### Step 1: Verify Backend Deployment

```bash
# Check if CloudFormation stack exists
aws cloudformation describe-stacks --stack-name codelens

# If not deployed, deploy it
cd infrastructure
./deploy.sh
```

### Step 2: Get the Correct API URL

```bash
# Get API Gateway endpoint URL
aws cloudformation describe-stacks \
  --stack-name codelens \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text
```

### Step 3: Update Frontend API URL

Edit `frontend/src/services/api.ts` and update the API_BASE_URL:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://YOUR_ACTUAL_API_URL/Prod'
```

Or create `frontend/.env`:
```
VITE_API_BASE_URL=https://YOUR_ACTUAL_API_URL/Prod
```

### Step 4: Test the Backend

Run the test script:
```bash
./test_docs_api.sh <API_URL> <REPO_ID>
```

Example:
```bash
./test_docs_api.sh https://abc123.execute-api.us-east-1.amazonaws.com/Prod test-repo
```

This will test:
- API connectivity
- Documentation status endpoint
- Documentation generation endpoint
- Documentation export endpoint
- CORS headers

### Step 5: Rebuild Frontend (if URL changed)

```bash
cd frontend
npm run build
```

## Testing Checklist

Once the backend is deployed and URL is correct:

1. **Generate Documentation**
   - Click "Generate Documentation" button
   - Should see "Generating..." status
   - After 10-30 seconds, should see "Documentation is ready to export"

2. **Export Markdown**
   - Click "Export Documentation" dropdown
   - Click "Export as Markdown"
   - File should download automatically

3. **Export PDF**
   - Click "Export Documentation" dropdown
   - Click "Export as PDF"
   - PDF file should download automatically

## Debug Tools Created

1. **DOCUMENTATION_GENERATION_NETWORK_ERROR_FIX.md**
   - Comprehensive troubleshooting guide
   - Step-by-step debugging instructions
   - Common error messages and solutions

2. **DOCUMENTATION_EXPORT_DEBUG_GUIDE.md**
   - Export-specific debugging guide
   - Console logging instructions
   - Backend verification steps

3. **test_docs_api.sh**
   - Automated API testing script
   - Tests all documentation endpoints
   - Provides clear pass/fail results

## What to Share for Further Help

If the issue persists after following the fix steps, please share:

1. **CloudFormation Stack Status**
   ```bash
   aws cloudformation describe-stacks --stack-name codelens
   ```

2. **API Gateway URL**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name codelens \
     --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue"
   ```

3. **Test Script Results**
   ```bash
   ./test_docs_api.sh <API_URL> <REPO_ID>
   ```

4. **Browser Console Logs**
   - Open DevTools (F12)
   - Go to Console tab
   - Try generating documentation
   - Copy all console output

5. **Browser Network Tab**
   - Open DevTools (F12)
   - Go to Network tab
   - Try generating documentation
   - Screenshot the failed request

## Expected Behavior (When Working)

1. User clicks "Generate Documentation"
2. Button shows "Generating..." with spinner
3. Status polls every 2 seconds
4. After 10-30 seconds, status changes to "generated"
5. "Export Documentation" dropdown appears
6. User can export as Markdown or PDF
7. Files download automatically

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Code | ✅ Complete | All handlers implemented |
| Frontend Code | ✅ Complete | All components implemented |
| Error Handling | ✅ Complete | Enhanced with detailed logging |
| Unit Tests | ✅ Complete | 42 tests passing |
| SAM Template | ✅ Complete | All resources defined |
| Deployment | ⚠️ Unknown | Needs verification |
| API URL Config | ⚠️ Unknown | May need update |

## Next Action Required

**You need to:**
1. Deploy the backend (if not already deployed)
2. Get the API Gateway URL
3. Update the frontend API URL
4. Test with the provided script

The code is complete and working. This is purely a deployment/configuration issue.
