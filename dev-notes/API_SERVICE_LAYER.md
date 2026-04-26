# API Service Layer Implementation

## Overview

Comprehensive API service layer with React Query hooks, context providers, and error handling for the CodeLens frontend.

## Files Created

### Core API Service
- **`src/services/api.ts`**: Axios instance with interceptors, retry logic, and typed API functions
  - Base URL from environment variable (defaults to production API)
  - Request/response interceptors
  - Automatic retry on 429 (rate limit) and 5xx errors with exponential backoff
  - TypeScript interfaces for all request/response types
  - Exported functions: `ingestRepository`, `getArchitecture`, `explainFile`, `chat`, `exportDocumentation`

### React Query Hooks
- **`src/hooks/useRepo.ts`**: Fetch and cache repository metadata
  - Query key: `['repo', repoId]`
  - Stale time: 5 minutes
  - Retry: 2 attempts

- **`src/hooks/useArchitecture.ts`**: Fetch architecture with level support
  - Query key: `['architecture', repoId, level]`
  - Auto-refetch when level changes
  - Stale time: 10 minutes

- **`src/hooks/useFileExplanation.ts`**: Fetch file explanations with invalidation
  - Query key: `['fileExplanation', repoId, filePath, level]`
  - Includes `invalidate()` method for manual cache invalidation
  - Stale time: 15 minutes

- **`src/hooks/useChat.ts`**: Manage chat conversations with optimistic updates
  - Maintains message history and session ID
  - Optimistic updates: user messages appear immediately
  - Automatic rollback on error
  - Suggested questions management
  - `sendMessage()`, `clearHistory()` methods

- **`src/hooks/index.ts`**: Barrel export for all hooks

### Context Providers
- **`src/context/RepoContext.tsx`**: Repository state management
  - Current repository
  - File tree structure
  - Loading states
  - Error handling

- **`src/context/ChatContext.tsx`**: Chat state management
  - Message history
  - Current session
  - Streaming state
  - Scope selector (all/file/directory)

- **`src/context/SettingsContext.tsx`**: User preferences
  - Explanation level (default: intermediate)
  - Theme (default: dark)
  - Auto-applies theme to document

### Error Handling
- **`src/components/common/ErrorBoundary.tsx`**: React error boundary
  - Catches component errors
  - Displays user-friendly error UI
  - Retry and "Go Home" actions
  - Logs errors to console

- **`src/components/common/LoadingSpinner.tsx`**: Loading indicator
  - Three sizes: sm, md, lg
  - Optional message
  - Tailwind-styled with dark mode support

## API Endpoints

### Repository Ingestion
```typescript
POST /repos/ingest
Body: { source_type: 'github' | 'zip', source: string, auth_token?: string }
Response: { repo_id, session_id, source, status, file_count, chunk_count, tech_stack }
```

### Architecture
```typescript
GET /repos/{id}/architecture?level=basic|intermediate|advanced
Response: { repo_id, architecture: {...}, diagram, generated_at }
```

### File Explanation
```typescript
GET /repos/{id}/files/{path}/explain?level=beginner|intermediate|advanced
Response: { repo_id, file_path, explanation: {...}, related_files, level, generated_at }
```

### Chat
```typescript
POST /repos/{id}/chat
Body: { message, session_id?, scope?, history? }
Response: { repo_id, response, citations, suggested_questions, confidence, session_id }
```

### Documentation Export
```typescript
POST /sessions/{id}/export
Body: { format: 'markdown' | 'pdf' }
Response: { session_id, download_url, format, expires_at }
```

## Retry Logic

- **Retryable Errors**: 429 (rate limit), 5xx (server errors)
- **Max Retries**: 3 attempts
- **Backoff Strategy**: Exponential (1s, 2s, 4s)
- **Implementation**: Axios response interceptor

## Cache Strategy

| Resource | Stale Time | Retry | Notes |
|----------|------------|-------|-------|
| Repository | 5 min | 2 | Basic metadata |
| Architecture | 10 min | 2 | Expensive AI generation |
| File Explanation | 15 min | 2 | Cached per level |
| Chat | N/A | N/A | Uses mutation, not query |

## Usage Examples

### Fetching Architecture
```typescript
import { useArchitecture } from '@/hooks'

function ArchitecturePage() {
  const { data, isLoading, error } = useArchitecture(repoId, 'intermediate')
  
  if (isLoading) return <LoadingSpinner />
  if (error) return <div>Error: {error.message}</div>
  
  return <ArchitectureView data={data} />
}
```

### Sending Chat Messages
```typescript
import { useChat } from '@/hooks'

function ChatInterface({ repoId }: { repoId: string }) {
  const { messages, sendMessage, isLoading } = useChat(repoId)
  
  const handleSend = (message: string) => {
    sendMessage(message, { type: 'all' })
  }
  
  return (
    <div>
      {messages.map(msg => <Message key={msg.timestamp} {...msg} />)}
      <Input onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
```

### Using Context Providers
```typescript
import { RepoProvider, ChatProvider, SettingsProvider } from '@/context'

function App() {
  return (
    <SettingsProvider>
      <RepoProvider>
        <ChatProvider>
          <Routes />
        </ChatProvider>
      </RepoProvider>
    </SettingsProvider>
  )
}
```

## Environment Variables

```env
VITE_API_BASE_URL=https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod
```

If not set, defaults to production API endpoint.

## TypeScript Compilation

All files pass TypeScript strict mode checks:
```bash
npx tsc --noEmit  # ✅ No errors
```

## Next Steps

1. Integrate hooks into existing pages (RepoInputPage, ArchitecturePage, FileViewPage)
2. Implement AI interaction components (ExplanationPanel, ArchitectureView, ChatInterface)
3. Add error boundaries to page-level components
4. Test API integration with real backend
5. Add loading states and skeleton screens

## Related Spec Tasks

- ✅ Task 1.1: Update API service to match backend endpoint structure
- ⏳ Task 2-6: Implement AI interaction components
- ⏳ Task 7: Integrate components into pages
- ⏳ Task 8: Add error boundaries and loading states
