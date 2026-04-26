# Getting Started with Premium Dashboard

## 🎉 What's New

Your CodeLens dashboard has been completely redesigned with a premium SaaS experience:

- ✨ Professional dark theme UI
- 📁 Real-time file tree navigation
- 💻 Monaco code editor with syntax highlighting
- 🤖 AI-powered insights with confidence scoring
- 📊 Complexity analysis with visual progress bars
- 🎯 Multi-level explanations (Beginner/Intermediate/Advanced)

## 🚀 Quick Start (5 Minutes)

### Step 1: Start the Frontend (1 min)

```bash
cd frontend
npm run dev
```

Open your browser to: **http://localhost:5173/**

### Step 2: Ingest a Test Repository (2 min)

On the home page, enter this small test repository:
```
https://github.com/kennethreitz/setup.py
```

Click **"Analyze Repository"** and wait for the processing screen (~10-15 seconds).

### Step 3: Explore the Dashboard (2 min)

You should now see:

**Left Sidebar:** File tree with all repository files
**Center Panel:** Code viewer with syntax highlighting  
**Right Panel:** AI insights with explanations and suggestions

Try:
- Click different files to view their code
- Switch explanation levels (Beginner/Intermediate/Advanced)
- Check the complexity score
- Click "Architecture" or "Chat" buttons

## 📋 What Was Deployed

### New Backend Endpoints

1. **GET /repos/{id}/file?path={filePath}**
   - Fetches actual file content from vector store
   - Returns syntax-highlighted code

2. **GET /repos/{id}/metadata**
   - Returns repository metadata
   - Includes tech stack, file counts, language breakdown

### Updated Components

1. **RepoExplorerPage_Premium.tsx** - Complete redesign
2. **API Service** - New endpoint functions
3. **Infrastructure** - New Lambda functions

## 🔍 Troubleshooting

### Problem: File tree is empty

**Cause:** Repository was ingested before the update

**Solution:** Re-ingest the repository
1. Go to home page
2. Enter the same repository URL
3. Click "Analyze Repository"
4. Wait for completion

### Problem: Code viewer shows error

**Cause:** GetFileContentFunction not deployed

**Solution:** Redeploy backend
```bash
cd infrastructure
./deploy.sh
```

### Problem: Console shows errors

**Solution:** Open browser DevTools (F12) and check:
- Console tab for JavaScript errors
- Network tab for failed API requests
- Look for specific error messages

## 🧪 Testing

### Quick Test Script

Test your API endpoints:

```bash
# Get a repo_id by ingesting a repository first
./test_api_endpoints.sh <repo_id>
```

### Manual Testing Checklist

- [ ] File tree shows files (not empty)
- [ ] Can click files to select them
- [ ] Code viewer shows syntax highlighting
- [ ] AI insights panel loads
- [ ] Confidence badge displays
- [ ] Explanation level switching works
- [ ] Complexity score shows progress bar
- [ ] Architecture button works
- [ ] Chat button works
- [ ] No console errors

## 📚 Documentation

- **TEST_PREMIUM_DASHBOARD.md** - Comprehensive testing guide
- **TROUBLESHOOTING_FILE_TREE.md** - File tree specific issues
- **PREMIUM_DASHBOARD_REDESIGN.md** - Technical architecture
- **test_api_endpoints.sh** - API testing script

## 🎯 Key Features

### 1. File Tree Navigation
- Collapsible folders
- File type icons
- Search functionality (UI ready, logic pending)
- Selected file highlighting

### 2. Code Viewer
- Monaco Editor (same as VS Code)
- Syntax highlighting for 20+ languages
- Line numbers and minimap
- Read-only mode

### 3. AI Insights Panel
- **Confidence Badge:** High/Medium/Low based on analysis quality
- **Explanation Levels:** Beginner, Intermediate, Advanced
- **Purpose:** One-sentence file description
- **Execution Flow:** Numbered steps showing how code works
- **Design Patterns:** Identified patterns (Singleton, Factory, etc.)
- **Dependencies:** External libraries and imports
- **Complexity Score:** 0-10 scale with visual progress bar
- **Suggestions:** Improvement recommendations

### 4. Top Navigation
- Repository name and metadata
- File count badge
- Tech stack language badges
- Status indicator (Indexed)
- Quick access to Architecture and Chat

## 🔧 Configuration

### Environment Variables

Frontend `.env` file (auto-updated by deploy script):
```
VITE_API_BASE_URL=https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod
```

### API Endpoints

All endpoints use the base URL above:
- `POST /repos/ingest` - Ingest repository
- `GET /repos/{id}/status` - Get repository status
- `GET /repos/{id}/metadata` - Get repository metadata
- `GET /repos/{id}/file?path={path}` - Get file content
- `GET /repos/{id}/files/{path}?level={level}` - Get file explanation
- `GET /repos/{id}/architecture` - Get architecture diagram
- `POST /repos/{id}/chat` - Chat with codebase

## 💡 Tips & Tricks

### Best Repositories to Test With

**Small (< 10 files):**
- `https://github.com/kennethreitz/setup.py` - 4 files, Python
- `https://github.com/sindresorhus/is` - ~10 files, TypeScript

**Medium (10-50 files):**
- Your own small projects
- Simple npm packages

**Large (50-500 files):**
- Test after verifying small repos work

### Explanation Levels

- **Beginner:** Simple terms, no jargon, like teaching a CS freshman
- **Intermediate:** Implementation details, design patterns, system context
- **Advanced:** Trade-offs, performance, edge cases, architectural critique

### Keyboard Shortcuts (Future)

Coming soon:
- `Ctrl/Cmd + P` - Quick file search
- `Ctrl/Cmd + F` - Search in file
- `Ctrl/Cmd + B` - Toggle sidebar
- Arrow keys - Navigate file tree

## 🐛 Known Issues

1. **Search not implemented** - Input is there but filtering logic pending
2. **Generate Docs button** - UI present but functionality not connected
3. **File content caching** - Files re-fetch on every selection
4. **Mobile layout** - Needs responsive design optimization

## 🚧 Roadmap

### Phase 1: Core Features (✅ Complete)
- [x] Premium UI design
- [x] File tree navigation
- [x] Code viewer with syntax highlighting
- [x] AI insights panel
- [x] Backend API integration

### Phase 2: Enhancements (Next)
- [ ] File tree search functionality
- [ ] Generate Docs implementation
- [ ] File content caching
- [ ] Keyboard shortcuts
- [ ] Mobile responsive design

### Phase 3: Advanced Features (Future)
- [ ] Code navigation (jump to definition)
- [ ] Diff view
- [ ] File tabs (multiple files open)
- [ ] Split view (side-by-side)
- [ ] Collaborative features

## 📞 Support

### Getting Help

1. **Check documentation** in this folder
2. **Review console logs** for specific errors
3. **Test API endpoints** using the test script
4. **Check CloudWatch logs** for backend errors

### Common Questions

**Q: Why is my file tree empty?**
A: Repository was ingested before the update. Re-ingest it.

**Q: Can I use old repositories?**
A: No, they need to be re-ingested with the new backend.

**Q: How long does ingestion take?**
A: Small repos (< 10 files): 10-15 seconds
   Medium repos (10-50 files): 30-60 seconds
   Large repos (50-500 files): 2-5 minutes

**Q: What's the file limit?**
A: 500 files maximum (MVP limit)

**Q: Which languages are supported?**
A: Python, JavaScript, TypeScript, Java, Go, Ruby, PHP, C++, C, C#, Rust, and more

## 🎓 Learning Resources

### Understanding the Architecture

```
User Browser
    ↓
React Frontend (Premium Dashboard)
    ↓
API Gateway
    ↓
Lambda Functions
    ├── GetRepoStatus
    ├── GetFileContent (NEW)
    ├── GetRepoMetadata (NEW)
    └── ExplainFile
    ↓
DynamoDB + Bedrock AI
```

### Code Structure

```
frontend/src/pages/
  └── RepoExplorerPage_Premium.tsx  ← Main dashboard component

backend/handlers/
  ├── get_file_content.py           ← NEW: File content endpoint
  ├── get_repo_metadata.py          ← NEW: Metadata endpoint
  ├── explain_file.py               ← AI explanations
  └── ingest_repo.py                ← Repository ingestion

infrastructure/
  └── template.yaml                 ← AWS SAM template
```

## ✅ Success Checklist

Before considering the dashboard "working":

- [ ] Backend deployed successfully
- [ ] Frontend starts without errors
- [ ] Can ingest a new repository
- [ ] Processing screen completes
- [ ] Dashboard loads with all 3 panels
- [ ] File tree shows files
- [ ] Code viewer displays code
- [ ] AI insights panel works
- [ ] Can switch between files
- [ ] Can change explanation levels
- [ ] Navigation buttons work
- [ ] No console errors
- [ ] API requests return 200 OK

## 🎉 You're Ready!

Your premium dashboard is now deployed and ready to use. Start by ingesting a small test repository and exploring the features.

Enjoy your new premium SaaS developer tool experience! 🚀
