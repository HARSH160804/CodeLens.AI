# Ingestion Test Guide

## Current Status
- ✅ Backend API deployed and working
- ✅ ZIP upload tested and working
- ✅ Frontend .env configured correctly
- ✅ Error handling improved

## Test Steps

### 1. Restart Frontend (Important!)
The .env file was updated, so you need to restart the dev server:
```bash
# Stop current server (Ctrl+C if running)
cd frontend
npm run dev
```

### 2. Test with ZIP Upload (Recommended)
I've created a test file for you: `test_upload.zip`

**Steps:**
1. Open http://localhost:5173
2. Scroll down to the ZIP upload section
3. Click or drag `test_upload.zip` into the upload zone
4. Click "Analyze"
5. Should complete in ~1-2 seconds

**Expected Result:**
- Progress bar shows
- Success! Redirects to repository view
- Shows 1 Python file

### 3. Test with GitHub URL (May Timeout)
**Small repos that should work:**
- `https://github.com/kennethreitz/setup.py` (very small)

**Repos that will timeout:**
- `https://github.com/miguelgrinberg/flasky` (39 files, ~22s backend time, but 60s timeout)
- `https://github.com/pallets/flask` (too large)

### 4. Check Browser Console
If you see "Failed to ingest repository":

1. Open DevTools (F12)
2. Go to Console tab
3. Look for error messages
4. Check Network tab for failed requests

## Common Issues

### Issue: "Request timed out"
**Cause:** Repository has too many files (>100)
**Solution:** Use ZIP upload or a smaller repository

### Issue: "Network error"
**Cause:** Can't reach API endpoint
**Solution:** 
- Check if backend is deployed
- Verify .env file has correct URL
- Check browser console for CORS errors

### Issue: "Failed to ingest repository" (generic)
**Cause:** Unknown error
**Solution:**
- Check browser console for details
- Check CloudWatch logs:
  ```bash
  aws logs tail /aws/lambda/h2s-backend-IngestRepoFunction-4DAH8i6iQdKC --since 5m
  ```

## Quick Verification

Test the API directly:
```bash
# Test ZIP upload (should work)
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/ingest" \
  -F "source_type=zip" \
  -F "file=@test_upload.zip"

# Test GitHub URL (may timeout)
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "github", "source": "https://github.com/kennethreitz/setup.py"}' \
  --max-time 65
```

## What to Share for Debugging

If still having issues, please share:
1. **Method used:** GitHub URL or ZIP upload?
2. **Exact error message:** From the UI
3. **Browser console errors:** Any red errors in DevTools Console
4. **Network tab:** Status code of the /repos/ingest request
5. **Repository:** Which repo/file are you trying to ingest?

## Next Steps

After successful ingestion:
1. Explore the file tree
2. Click on files to view code
3. Try the Chat feature
4. View Architecture diagram
