# Documentation Generation "Stuck on Generating" Fix

## Problem
Documentation generation gets stuck showing "Generating..." indefinitely. The status never updates to "generated".

## Root Cause
The Lambda function had a 60-second timeout, but documentation generation (which calls Bedrock AI) takes longer than that. The Lambda was timing out before completing, leaving the state stuck on 'generating'.

## Solution Applied

### 1. Increased Lambda Timeout
- Changed timeout from 60 seconds to 300 seconds (5 minutes) in `infrastructure/template.yaml`
- This gives the AI generation enough time to complete

### 2. Fixed State Management
- Modified `backend/lib/documentation/store.py` to use `update_item` instead of `put_item`
- This preserves the `generation_state` field when saving content
- Prevents race conditions between state updates

### 3. Added Better Logging
- Enhanced logging in `backend/handlers/docs_generate.py` to track each step
- Added detailed console logging in `frontend/src/hooks/useDocumentation.ts`

## Files Modified

1. `infrastructure/template.yaml` - Increased Lambda timeout to 300s
2. `backend/lib/documentation/store.py` - Fixed save() method to preserve state
3. `backend/handlers/docs_generate.py` - Added detailed logging
4. `frontend/src/hooks/useDocumentation.ts` - Added generation time tracking and detailed error logging

## How to Test

### Step 1: Clear Browser Cache
The frontend code is cached. You MUST do a hard refresh:
- **Mac**: Cmd + Shift + R
- **Windows/Linux**: Ctrl + Shift + F5
- Or open DevTools (F12) → Right-click refresh button → "Empty Cache and Hard Reload"

### Step 2: Clear Stuck State (if needed)
If you have a repository stuck on "generating", run:
```bash
python3 clear_doc_state.py <REPO_ID>
```

### Step 3: Test Generation
1. Navigate to the Architecture page
2. Click "Generate Documentation"
3. Watch the browser console for detailed logs
4. Generation should complete in 1-3 minutes
5. Status should update from "generating" to "generated"
6. Export buttons should appear

## Verification Commands

### Check Lambda Configuration
```bash
aws lambda get-function-configuration \
  --function-name h2s-backend-GenerateDocsFunction-XE93G3N2AcGt \
  --region us-east-1 \
  --query 'Timeout'
```
Should return: `300`

### Check DynamoDB State
```bash
python3 check_dynamodb_state.py <REPO_ID>
```

### Watch Lambda Logs
```bash
aws logs tail /aws/lambda/h2s-backend-GenerateDocsFunction-XE93G3N2AcGt \
  --since 5m \
  --region us-east-1 \
  --follow
```

## Expected Console Logs (After Hard Refresh)

When you click "Generate Documentation", you should see:
```
[useDocumentation] ===== GENERATE MUTATION CALLED =====
[useDocumentation] Starting generation for repo: <REPO_ID>
[useDocumentation] API call about to be made...
[useDocumentation] ===== GENERATE API SUCCESS =====
[useDocumentation] Generation response: {status: "generating", message: "..."}
[useDocumentation] ===== ON SUCCESS CALLED =====
[useDocumentation] Refetch interval check - state: generating shouldPoll: true
... (polling every 2 seconds) ...
[useDocumentation] Refetch interval check - state: generated shouldPoll: false
```

## If Still Not Working

1. **Verify deployment succeeded**:
   ```bash
   cd infrastructure && ./deploy.sh
   ```

2. **Check if frontend is using cached code**:
   - Open DevTools → Application tab → Clear Storage → Clear site data
   - Close and reopen the browser

3. **Manually test the API**:
   ```bash
   # Trigger generation
   curl -X POST 'https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/<REPO_ID>/docs/generate'
   
   # Check status
   curl 'https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/<REPO_ID>/docs/status'
   ```

4. **Check Lambda logs for errors**:
   ```bash
   aws logs tail /aws/lambda/h2s-backend-GenerateDocsFunction-XE93G3N2AcGt \
     --since 10m \
     --region us-east-1
   ```

## Deployment Status
- ✅ Backend deployed with 300s timeout
- ✅ State management fixed
- ⚠️ Frontend requires hard refresh to load new code

## Next Steps
1. Do a hard refresh (Cmd+Shift+R or Ctrl+Shift+F5)
2. Clear any stuck states with `clear_doc_state.py`
3. Try generating documentation again
4. Watch console for the new detailed logs
