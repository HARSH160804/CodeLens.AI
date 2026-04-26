import { Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import { RepoInputPage } from './pages/RepoInputPage'
import { RepoExplorerPagePremium } from './pages/RepoExplorerPage_Premium'
import { ArchitecturePage } from './pages/ArchitecturePage'
import { FileViewPage } from './pages/FileViewPage'
import { ChatPage } from './pages/ChatPage'
import { IngestionStatusPage } from './pages/IngestionStatusPage'

function App() {
  return (
    <AppProvider>
      <Routes>
        <Route path="/" element={<RepoInputPage />} />
        <Route path="/ingestion/:jobId" element={<IngestionStatusPage />} />
        <Route path="/repo/:repoId" element={<RepoExplorerPagePremium />} />
        <Route path="/repo/:repoId/architecture" element={<ArchitecturePage />} />
        <Route path="/repo/:repoId/chat" element={<ChatPage />} />
        <Route path="/repo/:repoId/file/:filePath" element={<FileViewPage />} />
        {/* Redirect /chat to home - requires repo selection */}
        <Route path="/chat" element={<Navigate to="/" replace />} />
      </Routes>
    </AppProvider>
  )
}

export default App
