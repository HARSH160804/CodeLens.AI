# Dashboard Indexing State Implementation

## Overview

Added indexing state handling to the Repository Dashboard page to show a loading state while the repository is being processed, with automatic polling until indexing completes.

## Changes Made

### 1. API Service Updates (`frontend/src/services/api.ts`)

#### Added RepoStatusResponse Interface
```typescript
export interface RepoStatusResponse {
  repo_id: string
  status: 'completed' | 'processing' | 'failed'
  file_count: number
  chunk_count: number
  tech_stack: {
    languages: string[]
    frameworks: string[]
    libraries: string[]
  }
  file_paths: string[]
  source: string
  created_at: string
  updated_at: string
}
```

#### Added getRepoStatus Function
```typescript
export const getRepoStatus = (
  repositoryId: string
): Promise<AxiosResponse<RepoStatusResponse>> =>
  apiClient.get(`/repos/${repositoryId}/status`)
```

This function calls the backend endpoint: `GET /repos/{id}/status`

### 2. Repository Dashboard Updates (`frontend/src/pages/RepoExplorerPage.tsx`)

#### Added State Management
```typescript
const [isIndexing, setIsIndexing] = useState(true)
const [error, setError] = useState<string | null>(null)
```

#### Added Status Polling Logic
```typescript
useEffect(() => {
  if (!repoId) return

  let pollInterval: ReturnType<typeof setInterval> | null = null

  const checkStatus = async () => {
    try {
      const response = await getRepoStatus(repoId)
      const status = response.data.status

      if (status === 'completed') {
        setIsIndexing(false)
        clearInterval(pollInterval)
      } else if (status === 'failed') {
        setError('Repository indexing failed. Please try again.')
        setIsIndexing(false)
        clearInterval(pollInterval)
      }
      // If status is 'processing', keep polling
    } catch (err) {
      setError('Failed to check repository status')
      setIsIndexing(false)
      clearInterval(pollInterval)
    }
  }

  // Initial check
  checkStatus()

  // Poll every 3 seconds
  pollInterval = setInterval(checkStatus, 3000)

  // Cleanup on unmount
  return () => {
    if (pollInterval) clearInterval(pollInterval)
  }
}, [repoId])
```

#### Added Loading State UI
```tsx
if (isIndexing) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <svg className="animate-spin h-16 w-16 text-blue-600 mx-auto">
          {/* Circular spinner */}
        </svg>
        <h2 className="text-2xl font-bold mb-2">
          Analyzing Repository...
        </h2>
        <p className="text-gray-600">
          Processing files and generating embeddings. This may take a moment.
        </p>
      </div>
    </div>
  )
}
```

#### Added Error State UI
```tsx
if (error) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl mb-4">⚠️</div>
        <h2 className="text-2xl font-bold mb-2">Error</h2>
        <p className="text-gray-600 mb-6">{error}</p>
        <Link to="/" className="...">Back to Home</Link>
      </div>
    </div>
  )
}
```

## User Flow

### 1. User Clicks "Analyze Repository"
- Button shows loading spinner
- API call to `/repos/ingest` completes
- Extracts `repo_id` from response
- **Immediately navigates to `/repo/{repo_id}`**

### 2. Dashboard Loads
- Component mounts
- Calls `GET /repos/{repo_id}/status`
- Checks status field in response

### 3. Status = "processing"
- Shows full-page loading state:
  - Animated circular spinner
  - "Analyzing Repository..." heading
  - Descriptive text
- Starts polling every 3 seconds
- Continues until status changes

### 4. Status = "completed"
- Stops polling
- Hides loading state
- Renders full dashboard layout:
  - Sidebar with file tree
  - Main content area
  - Architecture and Chat cards

### 5. Status = "failed"
- Stops polling
- Shows error state:
  - Warning icon
  - Error message
  - "Back to Home" button

## Backend API Endpoint

The implementation expects this endpoint to exist:

```
GET /repos/{id}/status

Response:
{
  "repo_id": "uuid",
  "status": "completed" | "processing" | "failed",
  "file_count": 4,
  "chunk_count": 8,
  "tech_stack": {...},
  "file_paths": [...],
  "source": "github_url_or_zip",
  "created_at": "2026-03-03T...",
  "updated_at": "2026-03-03T..."
}
```

This endpoint already exists in the backend (`backend/handlers/ingest_repo.py` - `get_status_handler`).

## Polling Behavior

### Polling Interval
- **3 seconds** between status checks
- Configurable by changing the interval value

### Polling Stops When
1. Status becomes "completed" ✅
2. Status becomes "failed" ❌
3. API call fails (network error) ⚠️
4. Component unmounts (cleanup) 🧹

### Cleanup
- `useEffect` cleanup function clears the interval
- Prevents memory leaks
- Stops polling when user navigates away

## Visual Design

### Loading State
- **Full-page centered layout**
- **Animated spinner**: Blue circular spinner (16x16)
- **Heading**: "Analyzing Repository..." (2xl, bold)
- **Description**: Helpful text explaining what's happening
- **Background**: Matches app theme (light/dark mode)

### Error State
- **Full-page centered layout**
- **Warning icon**: ⚠️ emoji (6xl size)
- **Heading**: "Error" (2xl, bold)
- **Error message**: Dynamic error text
- **Action button**: "Back to Home" link styled as button

### Success State (Completed)
- **Original dashboard layout**
- **Sidebar**: File tree navigation
- **Main content**: Welcome message with cards
- **Cards**: Architecture and Chat quick links

## Benefits

1. **Better UX**: User sees immediate feedback after clicking "Analyze"
2. **No waiting on home page**: User is taken to dashboard right away
3. **Clear progress indication**: Loading state shows work is happening
4. **Automatic updates**: Polling ensures UI updates when indexing completes
5. **Error handling**: Clear error states with recovery options
6. **Clean code**: Separation of concerns (loading wrapper vs dashboard content)

## Technical Details

### State Management
- Uses React `useState` for local state
- `isIndexing`: Boolean flag for loading state
- `error`: String for error messages (null when no error)

### Side Effects
- Uses React `useEffect` for polling logic
- Dependency array: `[repoId]` - re-runs when repo changes
- Cleanup function: Clears interval on unmount

### API Integration
- Uses existing `apiClient` from services
- Leverages retry logic and interceptors
- Timeout: Default 60 seconds

### TypeScript
- Fully typed with interfaces
- No `any` types (except in error handlers)
- Type-safe API responses

## Testing Checklist

- [x] TypeScript compilation passes
- [ ] Loading state shows on navigation
- [ ] Polling starts automatically
- [ ] Status updates every 3 seconds
- [ ] Dashboard renders when status = "completed"
- [ ] Error state shows when status = "failed"
- [ ] Error state shows on API failure
- [ ] Polling stops when status changes
- [ ] Cleanup works on unmount
- [ ] Works with both GitHub and ZIP ingestion

## Performance Considerations

### Polling Frequency
- 3 seconds is a good balance between:
  - **Responsiveness**: User sees updates quickly
  - **Server load**: Not too many requests
  - **Battery/network**: Reasonable resource usage

### Optimization Opportunities
1. **Exponential backoff**: Increase interval over time
2. **WebSocket**: Real-time updates instead of polling
3. **Server-sent events**: Push updates from backend
4. **Caching**: Cache status response briefly

## Future Enhancements

1. **Progress percentage**: Show actual progress (e.g., "Processing 3/10 files")
2. **Estimated time**: Show time remaining
3. **Cancel button**: Allow user to cancel indexing
4. **Retry button**: On error, allow retry without going home
5. **Background processing**: Allow navigation while indexing continues
6. **Notifications**: Browser notification when indexing completes

## Files Modified

1. `frontend/src/services/api.ts`
   - Added `RepoStatusResponse` interface
   - Added `getRepoStatus` function
   - Exported in `api` object

2. `frontend/src/pages/RepoExplorerPage.tsx`
   - Added state management
   - Added polling logic
   - Added loading state UI
   - Added error state UI
   - Wrapped existing dashboard in conditional render

## No Breaking Changes

- ✅ Existing dashboard layout unchanged
- ✅ File tree logic untouched
- ✅ Sidebar component unchanged
- ✅ MainLayout component unchanged
- ✅ Backward compatible with existing code

## Deployment

Frontend changes only:
1. Build: `npm run build`
2. Deploy frontend
3. Backend already has status endpoint

No backend changes needed! ✅
