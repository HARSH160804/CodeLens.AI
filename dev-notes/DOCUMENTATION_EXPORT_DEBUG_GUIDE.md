# Documentation Export Debugging Guide

## Current Issue
User sees error: "Failed to export documentation. Please try again."

## Changes Made

### 1. Enhanced Logging
Added comprehensive console logging to track the export flow:
- Request URL
- Response status and headers
- Blob creation details
- Success/failure messages

### 2. Error State Management
Added error state to `useDocumentation` hook:
- `exportError`: Contains the error message
- `clearExportError()`: Clears the error state
- Errors are now displayed in the UI with details

### 3. UI Error Display
Added error banner in `ArchitectureView_Enhanced.tsx`:
- Shows detailed error message
- Dismissible with X button
- Red styling for visibility

## Debugging Steps

### Step 1: Check Browser Console
Open the browser console (F12) and look for these log messages when clicking export:

```
Exporting markdown from: <url>
Export response status: <status>
Export response headers: {...}
Blob created, size: <size>, type: <type>
Markdown export completed successfully
```

### Step 2: Identify the Failure Point

#### If you see "Export response status: 404"
**Problem**: Documentation doesn't exist in DynamoDB
**Solution**: 
1. Check if documentation was generated successfully
2. Verify the repo_id is correct
3. Check DynamoDB table `BloomWay-RepoDocumentation` for the record

#### If you see "Export response status: 500"
**Problem**: Backend error during export
**Solution**:
1. Check CloudWatch logs for the `ExportDocsFunction` Lambda
2. Look for Python errors in the logs
3. Common issues:
   - Missing dependencies (markdown, weasyprint)
   - DynamoDB connection issues
   - S3 access issues for large documents

#### If you see "Export response status: 403"
**Problem**: CORS or authentication issue
**Solution**:
1. Verify API Gateway CORS configuration
2. Check if the endpoint is publicly accessible
3. Verify the API URL is correct

#### If you see "Failed to fetch" or network error
**Problem**: Network connectivity or CORS
**Solution**:
1. Check if backend is deployed and running
2. Verify API Gateway endpoint URL
3. Check browser network tab for CORS errors
4. Verify the URL format is correct

### Step 3: Check Backend Logs

#### CloudWatch Logs Location
```
Log Group: /aws/lambda/ExportDocsFunction
```

#### What to Look For
1. **Lambda invocation logs**: Verify the function is being called
2. **Error traces**: Look for Python exceptions
3. **DynamoDB queries**: Check if the documentation record is found
4. **Export process**: Verify markdown/PDF conversion

### Step 4: Verify Backend Configuration

#### Check SAM Template
```yaml
ExportDocsFunction:
  Properties:
    Handler: handlers.docs_export.lambda_handler
    MemorySize: 2048
    Timeout: 30
    Environment:
      Variables:
        DOCS_TABLE: !Ref RepoDocumentationTable
```

#### Check API Gateway
```yaml
Events:
  ExportDocs:
    Type: Api
    Properties:
      Path: /repos/{id}/docs/export
      Method: GET
```

### Step 5: Test Backend Directly

Use curl to test the backend endpoint:

```bash
# Test markdown export
curl -v "https://your-api-gateway-url/repos/{repo_id}/docs/export?format=md"

# Test PDF export
curl -v "https://your-api-gateway-url/repos/{repo_id}/docs/export?format=pdf"
```

Expected response:
- Status: 200 OK
- Headers: Content-Type, Content-Disposition
- Body: Base64-encoded file content

### Step 6: Common Issues and Solutions

#### Issue: "Documentation not found"
**Cause**: Documentation wasn't generated or repo_id mismatch
**Fix**:
1. Generate documentation first
2. Verify repo_id matches between generation and export
3. Check DynamoDB for the record

#### Issue: "PDF conversion failed"
**Cause**: weasyprint dependencies missing or conversion error
**Fix**:
1. Verify weasyprint is installed in Lambda layer
2. Check if markdown content is valid
3. Try markdown export first (simpler, no conversion)

#### Issue: "Blob size is 0"
**Cause**: Empty response from backend
**Fix**:
1. Check if backend is returning content
2. Verify base64 encoding/decoding
3. Check if `isBase64Encoded: true` is set in Lambda response

#### Issue: CORS error
**Cause**: Missing or incorrect CORS headers
**Fix**:
1. Verify CORS headers in Lambda response
2. Check API Gateway CORS configuration
3. Ensure `Access-Control-Allow-Origin: *` is present

## Testing Checklist

- [ ] Documentation is generated (status shows "generated")
- [ ] Browser console shows export URL
- [ ] Response status is 200
- [ ] Response headers include Content-Type and Content-Disposition
- [ ] Blob is created with size > 0
- [ ] Download is triggered
- [ ] File appears in downloads folder
- [ ] File content is valid

## Expected Console Output (Success)

```
Exporting markdown from: https://api.example.com/repos/test-repo/docs/export?format=md
Export response status: 200
Export response headers: {
  "content-type": "text/markdown",
  "content-disposition": "attachment; filename=\"test-repo-docs.md\"",
  "access-control-allow-origin": "*"
}
Blob created, size: 15234, type: text/markdown
Markdown export completed successfully
```

## Next Steps

1. **Check the console logs** - This will tell you exactly where the failure occurs
2. **Share the error details** - Include:
   - Console logs
   - Network tab response
   - CloudWatch logs (if accessible)
   - Error message from UI
3. **Try markdown first** - Markdown export is simpler and can help isolate PDF-specific issues

## Quick Fixes to Try

### Fix 1: Clear Export Error and Retry
The error banner now has a dismiss button. Click it and try again.

### Fix 2: Regenerate Documentation
If the documentation is stale or corrupted:
1. Click "Regenerate Documentation"
2. Wait for generation to complete
3. Try export again

### Fix 3: Try Different Format
If PDF fails, try Markdown (or vice versa) to isolate format-specific issues.

### Fix 4: Check API URL
Verify the API base URL in `frontend/src/services/api.ts`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://...'
```

## Contact Information

If the issue persists after following these steps, provide:
1. Browser console logs (full output)
2. Network tab screenshot showing the failed request
3. Error message from the UI
4. CloudWatch logs (if accessible)
