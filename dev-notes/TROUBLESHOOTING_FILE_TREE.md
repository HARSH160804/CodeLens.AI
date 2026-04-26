# Troubleshooting: File Tree Not Showing

## Issue
The file tree in the premium dashboard is empty, showing "0 files" even though the repository is indexed.

## Debugging Steps

### 1. Check Browser Console
Open browser DevTools (F12) and check the Console tab for:

**Expected logs:**
```
Status response: {repo_id: "...", status: "completed", file_paths: [...]}
File paths: ["file1.py", "file2.js", ...]
File paths count: 42
Built file tree: [{name: "...", type: "directory", ...}]
```

**Common errors:**
- `404 Not Found` - Backend endpoint doesn't exist
- `CORS error` - CORS headers not configured
- `file_paths: undefined` - Repository doesn't have file_paths in response
- `file_paths: []` - Repository was ingested before file_paths feature was added

### 2. Check Network Tab
1. Open DevTools → Network tab
2. Filter by "XHR" or "Fetch"
3. Look for request to `/repos/{repoId}/status`
4. Check the response:
   - Status code should be 200
   - Response should include `file_paths` array

### 3. Verify Repository Data
The repository needs to have been ingested with the latest backend code that includes `file_paths` in the response.

**Check if repository has file_paths:**
```bash
# Using curl
curl https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/{REPO_ID}/status

# Look for "file_paths" in the response
```

**Expected response:**
```json
{
  "repo_id": "uuid",
  "status": "completed",
  "file_count": 42,
  "file_paths": [
    "README.md",
    "src/index.js",
    "src/utils/helper.js"
  ],
  ...
}
```

### 4. Re-ingest Repository (If Needed)
If the repository was ingested before the `file_paths` feature was added, you need to re-ingest it:

1. Go to home page
2. Ingest the same repository again
3. Wait for indexing to complete
4. Navigate to dashboard

## Common Causes & Solutions

### Cause 1: Backend Not Deployed
**Symptom:** 404 errors in console for `/repos/{id}/metadata`

**Solution:** 
The metadata endpoint is optional. The code now falls back to using status endpoint data. However, if you see 404 for `/repos/{id}/status`, deploy the backend:
```bash
cd infrastructure
./deploy.sh
```

### Cause 2: Old Repository Data
**Symptom:** `file_paths: []` or `file_paths: undefined` in console

**Solution:**
Re-ingest the repository with the latest backend code.

### Cause 3: CORS Issues
**Symptom:** CORS errors in console

**Solution:**
Check that `infrastructure/template.yaml` has CORS configured:
```yaml
Globals:
  Api:
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
      AllowOrigin: "'*'"
```

### Cause 4: Empty Repository
**Symptom:** `file_paths: []` but file_count > 0

**Solution:**
This might be a bug in the ingestion handler. Check CloudWatch logs for the ingestion Lambda function.

### Cause 5: Frontend Not Rebuilt
**Symptom:** Old code still running

**Solution:**
```bash
cd frontend
npm run dev
# Or if using production build
npm run build
```

## Quick Fix: Use Fallback Data

If you need to test the UI without fixing the backend, you can temporarily add mock data:

```typescript
// In RepoExplorerPage_Premium.tsx, add this after line 150:
const filePaths = statusResponse.data.file_paths || [
  'README.md',
  'src/index.js',
  'src/components/App.tsx',
  'src/utils/helper.js',
  'package.json'
]
```

## Verification Checklist

- [ ] Browser console shows no errors
- [ ] Network tab shows 200 response for `/repos/{id}/status`
- [ ] Response includes `file_paths` array with items
- [ ] Console logs show "File paths count: X" where X > 0
- [ ] Console logs show "Built file tree: [...]" with items
- [ ] File tree renders in left sidebar
- [ ] Can click on files to select them

## Still Not Working?

1. **Check the repo_id in the URL** - Make sure it matches a valid repository
2. **Try a fresh ingestion** - Ingest a new small repository (like `https://github.com/kennethreitz/setup.py`)
3. **Check backend logs** - Look at CloudWatch logs for the GetRepoStatus Lambda function
4. **Verify DynamoDB** - Check that the Repositories table has the repo_id with file_paths

## Contact Support

If none of these solutions work, provide:
1. Browser console logs (full output)
2. Network tab screenshot showing the status request/response
3. Repository ID you're trying to view
4. Steps you took to ingest the repository
