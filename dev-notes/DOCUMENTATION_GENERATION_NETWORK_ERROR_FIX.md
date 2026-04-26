# Documentation Generation Network Error Fix

## Error Observed
```
Documentation generation failed: AxiosError: Network Error
at async Object.mutationFn (useDocumentation.ts:66:24)
```

## Root Cause
The frontend cannot reach the backend API endpoint for documentation generation. This is a **network connectivity issue**, not a code bug.

## Possible Causes

### 1. Backend Not Deployed
The Lambda function `GenerateDocsFunction` may not be deployed to AWS.

**Check**:
```bash
# Check if the stack is deployed
aws cloudformation describe-stacks --stack-name codelens

# Check if the Lambda function exists
aws lambda get-function --function-name GenerateDocsFunction
```

**Fix**:
```bash
cd infrastructure
./deploy.sh
```

### 2. API Gateway Endpoint Not Configured
The API Gateway may not have the `/repos/{id}/docs/generate` endpoint.

**Check**:
```bash
# Get API Gateway ID
aws apigateway get-rest-apis --query "items[?name=='BloomWayApi'].id" --output text

# List resources (should show /repos/{id}/docs/generate)
aws apigateway get-resources --rest-api-id <API_ID>
```

**Fix**: Redeploy the SAM template

### 3. Wrong API Base URL
The frontend may be using an incorrect API base URL.

**Check**: Look at `frontend/src/services/api.ts`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://...'
```

**Fix**: Set the correct URL in `.env` or update the default

### 4. CORS Preflight Failure
The OPTIONS request may be failing due to CORS misconfiguration.

**Check**: Browser Network tab → Look for OPTIONS request with status 403 or 500

**Fix**: Ensure CORS is configured in SAM template (already done)

## Immediate Debugging Steps

### Step 1: Verify Backend is Deployed

```bash
# Check CloudFormation stack
aws cloudformation describe-stacks \
  --stack-name codelens \
  --query "Stacks[0].StackStatus"

# Should return: CREATE_COMPLETE or UPDATE_COMPLETE
```

### Step 2: Get the Correct API URL

```bash
# Get API Gateway endpoint
aws cloudformation describe-stacks \
  --stack-name codelens \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text

# Example output: https://abc123.execute-api.us-east-1.amazonaws.com/Prod/
```

### Step 3: Test the Endpoint Directly

```bash
# Replace with your actual API URL and repo_id
curl -X POST \
  "https://your-api-url/repos/test-repo/docs/generate" \
  -H "Content-Type: application/json" \
  -v

# Expected: 202 Accepted or 409 Conflict (if already generating)
# Error: Connection refused = backend not deployed
# Error: 404 = endpoint not configured
# Error: 403 = CORS or auth issue
```

### Step 4: Check Browser Network Tab

1. Open browser DevTools (F12)
2. Go to Network tab
3. Try generating documentation
4. Look for the POST request to `/repos/{id}/docs/generate`
5. Check:
   - Request URL (is it correct?)
   - Status code (what error?)
   - Response body (any error message?)

## Solutions

### Solution 1: Deploy the Backend

If the backend isn't deployed:

```bash
cd infrastructure
./deploy.sh
```

Wait for deployment to complete, then get the API URL:

```bash
aws cloudformation describe-stacks \
  --stack-name codelens \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text
```

### Solution 2: Update Frontend API URL

If the API URL is wrong, update it:

**Option A: Environment Variable**
Create `frontend/.env`:
```
VITE_API_BASE_URL=https://your-actual-api-url/Prod
```

**Option B: Update Default in Code**
Edit `frontend/src/services/api.ts`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://YOUR_ACTUAL_API_URL/Prod'
```

Then rebuild the frontend:
```bash
cd frontend
npm run build
```

### Solution 3: Add OPTIONS Handler (if CORS failing)

If OPTIONS requests are failing, add explicit OPTIONS handler in SAM template:

```yaml
GenerateDocsOptions:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: ../backend/
    Handler: handlers.options.lambda_handler
    Events:
      Options:
        Type: Api
        Properties:
          RestApiId: !Ref BloomWayApi
          Path: /repos/{id}/docs/generate
          Method: OPTIONS
```

### Solution 4: Check Lambda Permissions

Ensure the Lambda function has required permissions:

```bash
# Check Lambda execution role
aws lambda get-function --function-name GenerateDocsFunction \
  --query "Configuration.Role"

# Check role policies
aws iam list-attached-role-policies --role-name <ROLE_NAME>
```

Required permissions:
- DynamoDB: Read/Write to RepoDocumentationTable
- DynamoDB: Read from RepositoriesTable
- Bedrock: InvokeModel
- S3: Read/Write to CodeArtifactsBucket
- CloudWatch: Logs

## Quick Test Script

Create `test_docs_generate.sh`:

```bash
#!/bin/bash

# Configuration
API_URL="https://your-api-url/Prod"
REPO_ID="your-repo-id"

echo "Testing documentation generation endpoint..."
echo "API URL: $API_URL"
echo "Repo ID: $REPO_ID"
echo ""

# Test POST /repos/{id}/docs/generate
echo "1. Testing POST /repos/$REPO_ID/docs/generate"
curl -X POST \
  "$API_URL/repos/$REPO_ID/docs/generate" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -v

echo ""
echo "2. Testing GET /repos/$REPO_ID/docs/status"
curl -X GET \
  "$API_URL/repos/$REPO_ID/docs/status" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n"
```

Run it:
```bash
chmod +x test_docs_generate.sh
./test_docs_generate.sh
```

## Expected Behavior

### Successful Generation
1. POST request returns 202 Accepted
2. Status changes to "generating"
3. After ~10-30 seconds, status changes to "generated"
4. Export buttons become available

### Already Generating
1. POST request returns 409 Conflict
2. Message: "Documentation generation already in progress"

### Missing Analysis
1. POST request returns 400 Bad Request
2. Message: "Architecture analysis data is incomplete"
3. Solution: Run architecture analysis first

## Verification Checklist

- [ ] Backend is deployed (CloudFormation stack exists)
- [ ] Lambda function exists (GenerateDocsFunction)
- [ ] API Gateway has the endpoint configured
- [ ] Frontend has correct API URL
- [ ] curl test succeeds (returns 202 or 409)
- [ ] Browser can reach the endpoint
- [ ] CORS headers are present in response
- [ ] Lambda has required permissions

## Common Error Messages

### "Network Error"
- **Cause**: Cannot reach backend
- **Fix**: Deploy backend or fix API URL

### "404 Not Found"
- **Cause**: Endpoint doesn't exist
- **Fix**: Redeploy SAM template

### "403 Forbidden"
- **Cause**: CORS or authentication issue
- **Fix**: Check CORS configuration

### "500 Internal Server Error"
- **Cause**: Lambda execution error
- **Fix**: Check CloudWatch logs

### "409 Conflict"
- **Cause**: Already generating
- **Fix**: Wait for current generation to complete

## Next Steps

1. **Verify deployment**: Check if backend is deployed
2. **Get API URL**: Get the correct API Gateway URL
3. **Update frontend**: Set the correct API URL
4. **Test with curl**: Verify endpoint works
5. **Test in browser**: Try generating documentation again

If the issue persists after following these steps, share:
- CloudFormation stack status
- API Gateway endpoint URL
- curl test results
- Browser network tab screenshot
