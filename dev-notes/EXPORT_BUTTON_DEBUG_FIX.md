# Export Button Debug Fix

## Issue
User reported that the export button disappeared from the documentation controls.

## Root Cause Analysis
The export button visibility is controlled by the `docStatus` state, which comes from the backend API. The button only appears when `docStatus === 'generated'`. If the button is missing, it means the status is not 'generated'.

Possible reasons:
1. Documentation was never successfully generated (backend not deployed)
2. Documentation generation failed
3. Status API is returning incorrect state
4. React Query cache issue

## Changes Made

### 1. Enhanced Debug Logging

#### ArchitectureView_Enhanced.tsx
- Added `useEffect` hook to log documentation status changes
- Added visual status indicator showing current `docStatus` value
- Logs: docStatus, isGenerating, docError, exportError

#### useDocumentation.ts
- Added detailed logging to status query
- Added logging to generation mutation (success/error)
- Added logging to generate function call
- Logs show: repo ID, API responses, state transitions

### 2. Improved UI Clarity

#### Status Indicator
Added a debug line showing the current status:
```
Status: not_generated | generating | generated | failed
```

This helps identify what state the UI thinks it's in.

### 3. Code Structure (No Logic Changes)

The button visibility logic remains the same:
- `docStatus === 'not_generated' || 'failed'` → Show "Generate" button only
- `docStatus === 'generating'` → Show loading indicator + "Generate" button (disabled)
- `docStatus === 'generated'` → Show "Regenerate" button + "Export" dropdown

## How to Debug

### Step 1: Check Browser Console
Open the browser console and look for these log messages:

```
=== DOCUMENTATION STATUS DEBUG ===
docStatus: [value]
isGenerating: [true/false]
docError: [error message or null]
exportError: [error message or null]
=================================

[useDocumentation] Fetching status for repo: [repo_id]
[useDocumentation] Status response: { state: '...', created_at: '...', error_message: '...' }
```

### Step 2: Check Visual Status Indicator
Look at the documentation controls section. Below the description text, you should see:
```
Status: [current_status]
```

### Step 3: Verify Backend Deployment
The most common issue is that the backend Lambda functions are not deployed.

Check if these endpoints work:
```bash
# Status endpoint (should always work)
curl https://[API_URL]/repos/[REPO_ID]/docs/status

# Generate endpoint (requires deployed Lambda)
curl -X POST https://[API_URL]/repos/[REPO_ID]/docs/generate
```

### Step 4: Test Generation Flow
1. Click "Generate Documentation" button
2. Watch console logs for generation request
3. Status should change: `not_generated` → `generating` → `generated`
4. Export button should appear when status reaches `generated`

## Expected Behavior

### When Backend is NOT Deployed
- Status: `not_generated`
- UI: Shows "Generate Documentation" button
- Clicking generates: Network error or 404
- Export button: NOT visible (correct behavior)

### When Backend IS Deployed
- Status: `not_generated` initially
- Click "Generate Documentation"
- Status changes to: `generating` (polls every 2s)
- Status changes to: `generated` (when complete)
- UI: Shows "Regenerate Documentation" + "Export Documentation" dropdown
- Export button: VISIBLE (correct behavior)

### When Generation Fails
- Status: `failed`
- UI: Shows "Generate Documentation" button + error message
- Export button: NOT visible (correct behavior)

## Next Steps

1. **Check the console logs** to see what status is being returned
2. **Verify backend deployment** - run `cd infrastructure && ./deploy.sh`
3. **Test the generation flow** - click Generate and watch the status transitions
4. **Check API Gateway URL** - ensure `VITE_API_BASE_URL` is correct in `.env`

## Files Modified
- `frontend/src/components/architecture/ArchitectureView_Enhanced.tsx`
- `frontend/src/hooks/useDocumentation.ts`

## No Breaking Changes
All changes are additive (logging and debug UI). The core logic remains unchanged.
