# Testing Premium Dashboard - Step by Step Guide

## Prerequisites
✅ Backend deployed successfully
✅ Frontend .env updated with API endpoint
✅ API endpoint: `https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/`

## Step 1: Start Frontend Development Server

Open a terminal and run:

```bash
cd frontend
npm run dev
```

Expected output:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

Open your browser to: **http://localhost:5173/**

## Step 2: Ingest a Test Repository

### Option A: Use Small GitHub Repository (Recommended)
1. On the home page, enter: `https://github.com/kennethreitz/setup.py`
2. Click "Analyze Repository"
3. Wait for the processing screen (should take ~10-15 seconds)

### Option B: Upload a ZIP File
1. Create a small test ZIP with a few Python/JS files
2. Drag and drop onto the upload zone
3. Click "Analyze Repository"

## Step 3: Verify Processing Screen

You should see:
- Dark gradient background (#0a0e1a → #1a1f35)
- Animated spinner
- Rotating messages:
  - "Analyzing your codebase..."
  - "Building architecture graph..."
  - "Generating embeddings..."
  - "Detecting patterns and dependencies..."
  - "Indexing code structure..."
  - "Preparing AI insights..."

## Step 4: Verify Premium Dashboard Loads

After processing completes, you should see:

### Top Navigation Bar
- ✅ "CodeLens" logo (left)
- ✅ Repository name (e.g., "kennethreitz/setup.py")
- ✅ File count badge (e.g., "4 files")
- ✅ Language badges (e.g., "Python")
- ✅ "Indexed" status badge (green)
- ✅ "Generate Docs" button
- ✅ "Architecture" button
- ✅ "Chat" button (blue, primary)

### Left Sidebar (File Tree)
- ✅ Search input at top
- ✅ File tree with folders and files
- ✅ Files should be visible (not empty)
- ✅ Folders can be expanded/collapsed
- ✅ Selected file highlighted in blue

### Center Panel (Code Viewer)
- ✅ Breadcrumb showing file path
- ✅ Monaco editor with syntax highlighting
- ✅ Line numbers visible
- ✅ Minimap on right side
- ✅ Dark theme

### Right Panel (AI Insights)
- ✅ "AI Insights" header
- ✅ Confidence badge (High/Medium/Low)
- ✅ Explanation level toggle (Beginner/Intermediate/Advanced)
- ✅ Purpose section
- ✅ Execution Flow (numbered steps)
- ✅ Design Patterns (badge chips)
- ✅ Dependencies (code chips)
- ✅ Complexity Score (progress bar 0-10)
- ✅ Suggestions (bullet list)

## Step 5: Test File Selection

1. **Click on a different file** in the left sidebar
2. Verify:
   - ✅ File highlights in blue
   - ✅ Code viewer updates with new content
   - ✅ Breadcrumb updates with new file path
   - ✅ AI Insights panel shows loading spinner
   - ✅ AI Insights updates with new explanation

## Step 6: Test Explanation Level Switching

1. **Click "Advanced"** in the explanation level toggle
2. Verify:
   - ✅ Button highlights in blue
   - ✅ AI Insights panel shows loading spinner
   - ✅ Explanation updates (may be more technical)

3. **Click "Beginner"**
4. Verify:
   - ✅ Explanation updates (should be simpler)

## Step 7: Test Navigation Buttons

1. **Click "Architecture"** button
   - ✅ Navigates to architecture page
   - ✅ Shows architecture diagram

2. **Go back** and click "Chat" button
   - ✅ Navigates to chat page
   - ✅ Chat interface loads

3. **Click "CodeLens" logo**
   - ✅ Returns to home page

## Step 8: Browser Console Verification

Open DevTools (F12) → Console tab

Expected logs:
```
Repository status: completed
Status response: {repo_id: "...", status: "completed", file_paths: [...]}
File paths: ["README.md", "setup.py", ...]
File paths count: 4
Built file tree: [{name: "README.md", type: "file", ...}]
Auto-selecting file: README.md
Metadata response: {repoName: "kennethreitz/setup.py", ...}
```

**No errors should appear!**

## Step 9: Network Tab Verification

Open DevTools (F12) → Network tab → Filter by "Fetch/XHR"

Expected requests:
1. ✅ `GET /repos/{id}/status` → 200 OK
2. ✅ `GET /repos/{id}/metadata` → 200 OK (or 404 if not deployed)
3. ✅ `GET /repos/{id}/file?path=README.md` → 200 OK
4. ✅ `GET /repos/{id}/files/README.md?level=intermediate` → 200 OK

## Step 10: Test Edge Cases

### Test 1: Empty File Tree (Old Repository)
1. Navigate to an old repository (ingested before deployment)
2. Verify:
   - ✅ Shows "No files found" message
   - ✅ Displays helpful instructions
   - ✅ No JavaScript errors

### Test 2: File with No Explanation
1. Select a very small file (e.g., `.gitignore`)
2. Verify:
   - ✅ Code viewer shows content
   - ✅ AI Insights shows fallback message or basic explanation
   - ✅ No crashes

### Test 3: Search Functionality
1. Type in the search box
2. Note: Search is not implemented yet, but input should work

## Common Issues & Solutions

### Issue 1: File Tree Empty
**Symptom:** Left sidebar shows "No files found"

**Console shows:** `File paths count: 0`

**Solution:** Re-ingest the repository (it was ingested before the update)

### Issue 2: Code Viewer Shows Error
**Symptom:** Center panel shows "Error loading file content"

**Console shows:** `404 Not Found` for `/repos/{id}/file`

**Solution:** 
- Check that GetFileContentFunction was deployed
- Verify the endpoint exists in API Gateway

### Issue 3: AI Insights Not Loading
**Symptom:** Right panel stuck on loading spinner

**Console shows:** Error fetching explanation

**Solution:**
- Check CloudWatch logs for ExplainFileFunction
- Verify Bedrock permissions
- Check if file_path is URL-encoded correctly

### Issue 4: Metadata Shows Fallback Data
**Symptom:** Top bar shows "Repository" instead of actual name

**Console shows:** `Metadata endpoint not available`

**Solution:** This is expected if GetRepoMetadataFunction isn't deployed yet. It falls back to status data.

### Issue 5: CORS Errors
**Symptom:** Console shows CORS policy errors

**Solution:**
- Verify CORS is configured in `infrastructure/template.yaml`
- Redeploy backend
- Clear browser cache

## Performance Benchmarks

Expected load times:
- Initial dashboard load: **2-3 seconds**
- File switch: **500ms - 1s**
- Explanation level change: **300ms - 1s**
- File tree render: **<100ms** for 500 files

## API Endpoint Testing (Manual)

### Test Status Endpoint
```bash
curl -X GET \
  "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/{REPO_ID}/status" \
  | jq .
```

Expected response:
```json
{
  "repo_id": "uuid",
  "status": "completed",
  "file_count": 4,
  "file_paths": ["README.md", "setup.py", ...],
  ...
}
```

### Test File Content Endpoint
```bash
curl -X GET \
  "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/{REPO_ID}/file?path=README.md" \
  | jq .
```

Expected response:
```json
{
  "repo_id": "uuid",
  "file_path": "README.md",
  "content": "# Project Title\n\n...",
  "language": "markdown",
  "lines": 42
}
```

### Test Metadata Endpoint
```bash
curl -X GET \
  "https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod/repos/{REPO_ID}/metadata" \
  | jq .
```

Expected response:
```json
{
  "repoName": "owner/repo",
  "totalFiles": 42,
  "totalLines": 8500,
  "techStack": {...},
  ...
}
```

## Success Criteria

All of these should be ✅:

- [ ] Backend deployed without errors
- [ ] Frontend starts on http://localhost:5173/
- [ ] Can ingest a new repository
- [ ] Processing screen shows and completes
- [ ] Premium dashboard loads with all 3 panels
- [ ] File tree shows files (not empty)
- [ ] Can click files to select them
- [ ] Code viewer shows syntax-highlighted code
- [ ] AI Insights panel shows explanation
- [ ] Confidence badge displays correctly
- [ ] Explanation level switching works
- [ ] Complexity score shows with progress bar
- [ ] Navigation buttons work (Architecture, Chat)
- [ ] No JavaScript errors in console
- [ ] All API requests return 200 OK
- [ ] File paths array is populated in status response

## Next Steps After Testing

Once all tests pass:

1. **Test with larger repositories** (50-100 files)
2. **Test different file types** (Python, JavaScript, TypeScript, Java, etc.)
3. **Test explanation quality** at different levels
4. **Optimize performance** if needed
5. **Add search functionality** to file tree
6. **Implement Generate Docs** button
7. **Add keyboard shortcuts**
8. **Mobile responsive design**

## Reporting Issues

If you encounter issues, provide:
1. Screenshot of the dashboard
2. Browser console logs (full output)
3. Network tab showing failed requests
4. Repository ID you're testing with
5. Steps to reproduce

## Contact

For questions or issues, check:
- `TROUBLESHOOTING_FILE_TREE.md` - File tree specific issues
- `PREMIUM_DASHBOARD_REDESIGN.md` - Architecture overview
- CloudWatch logs - Backend errors
