# Documentation Generation Troubleshooting Guide

## Current Situation
You've been saying "still same" multiple times, which means the documentation generation is still not working after all the fixes. Let's systematically debug this.

## Step-by-Step Debugging

### Step 1: Identify Your Repository ID
First, we need to know which repository you're trying to generate documentation for.

**How to find it:**
1. Open your browser DevTools (F12)
2. Go to the Console tab
3. Look for logs that mention `repo:` or `repoId:`
4. Copy the repository ID (it looks like: `856fcb92-8a41-4b8f-9f13-d350d7c3e81e`)

### Step 2: Check Current State
Once you have the repo ID, run:
```bash
python3 check_dynamodb_state.py <YOUR_REPO_ID>
```

This will show you:
- Current generation state (not_generated, generating, generated, or failed)
- When it was last updated
- Any error messages

### Step 3: Check Browser Console
Open your browser DevTools (F12) and look for these specific logs:

**When you click "Generate Documentation", you should see:**
```
[useDocumentation] ===== GENERATE MUTATION CALLED =====
[useDocumentation] Starting generation for repo: <REPO_ID>
```

**If you DON'T see these logs:**
- Your browser is using cached JavaScript
- Solution: Do a HARD refresh (Cmd+Shift+R on Mac, Ctrl+Shift+F5 on Windows)
- Or: Clear browser cache completely

**If you DO see these logs but nothing happens:**
- Check the Network tab in DevTools
- Look for a POST request to `/docs/generate`
- Check if it returns 202 (success) or an error

### Step 4: Verify Frontend Dev Server
If you're running a local dev server, make sure it has recompiled:

```bash
# Check if the dev server is running
ps aux | grep "vite\|webpack\|react-scripts"

# If it's running, check the terminal where it's running
# You should see compilation messages when files change
```

### Step 5: Test Backend Directly
Test if the backend is working by calling the API directly:

```bash
# Replace <REPO_ID> with your actual repo ID
REPO_ID="<YOUR_REPO_ID>"

# Check current status
curl "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/${REPO_ID}/docs/status"

# Trigger generation
curl -X POST "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/${REPO_ID}/docs/generate"

# Wait 10 seconds
sleep 10

# Check status again
curl "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/${REPO_ID}/docs/status"
```

### Step 6: Check Lambda Logs
If the backend test works but the frontend doesn't, check Lambda logs:

```bash
# Find the Lambda function name
aws lambda list-functions --region us-east-1 --query "Functions[?contains(FunctionName, 'GenerateDocs')].FunctionName" --output text

# Tail the logs (replace <FUNCTION_NAME> with the actual name)
aws logs tail /aws/lambda/<FUNCTION_NAME> --since 10m --region us-east-1 --follow
```

## Common Issues and Solutions

### Issue 1: Browser Cache
**Symptom:** No console logs appear when clicking "Generate Documentation"

**Solution:**
1. Close all browser tabs with your app
2. Clear browser cache (Cmd+Shift+Delete or Ctrl+Shift+Delete)
3. Reopen the app
4. Try again

### Issue 2: Stuck State
**Symptom:** Button shows "Generating..." forever

**Solution:**
```bash
# Clear the stuck state
python3 clear_doc_state.py <REPO_ID>

# Refresh the page
# Try generating again
```

### Issue 3: Lambda Timeout
**Symptom:** Generation starts but never completes

**Solution:**
```bash
# Check Lambda timeout
aws lambda get-function-configuration \
  --function-name <FUNCTION_NAME> \
  --region us-east-1 \
  --query 'Timeout'

# Should be 300 seconds
# If not, redeploy:
cd infrastructure && ./deploy.sh
```

### Issue 4: Frontend Not Recompiling
**Symptom:** Code changes don't appear in the browser

**Solution:**
```bash
# Stop the dev server (Ctrl+C)
# Clear node_modules cache
cd frontend
rm -rf node_modules/.vite

# Restart dev server
npm run dev
```

## Quick Diagnostic Script
Run this to get a complete picture:

```bash
./debug_doc_generation.sh <YOUR_REPO_ID>
```

## What to Share for Help
If none of the above works, share:

1. **Repository ID** you're testing with
2. **Browser console logs** (full output from clicking "Generate Documentation")
3. **Network tab** showing the POST request to `/docs/generate`
4. **DynamoDB state** output from `check_dynamodb_state.py`
5. **Lambda logs** from the last 10 minutes

## Nuclear Option: Complete Reset
If nothing works, try a complete reset:

```bash
# 1. Clear DynamoDB state
python3 clear_doc_state.py <REPO_ID>

# 2. Redeploy backend
cd infrastructure
./deploy.sh

# 3. Clear frontend cache
cd ../frontend
rm -rf node_modules/.vite
rm -rf dist

# 4. Restart dev server
npm run dev

# 5. Clear browser cache completely
# (Cmd+Shift+Delete or Ctrl+Shift+Delete)

# 6. Try again
```

## Expected Working Flow

When everything is working correctly:

1. Click "Generate Documentation"
2. Console shows: `===== GENERATE MUTATION CALLED =====`
3. Button changes to show loading spinner
4. Status polls every 2 seconds
5. After 1-3 minutes, status changes to "generated"
6. Export buttons appear
7. You can download Markdown or PDF

If any step fails, that's where the problem is.
