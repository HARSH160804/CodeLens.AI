import { createContext, useContext, useState, ReactNode } from 'react'
import { IngestResponse } from '../services/api'

export type RepoStatus = 'idle' | 'uploading' | 'processing' | 'ready' | 'error'

interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
}

interface RepoContextType {
  repoId: string | null
  status: RepoStatus
  currentRepo: IngestResponse | null
  fileTree: FileTreeNode[]
  isLoadingRepo: boolean
  repoError: string | null
  setRepoId: (id: string | null) => void
  setStatus: (status: RepoStatus) => void
  setCurrentRepo: (repo: IngestResponse | null) => void
  setFileTree: (tree: FileTreeNode[]) => void
  setIsLoadingRepo: (loading: boolean) => void
  setRepoError: (error: string | null) => void
}

const RepoContext = createContext<RepoContextType | undefined>(undefined)

export function RepoProvider({ children }: { children: ReactNode }) {
  const [repoId, setRepoId] = useState<string | null>(null)
  const [status, setStatus] = useState<RepoStatus>('idle')
  const [currentRepo, setCurrentRepo] = useState<IngestResponse | null>(null)
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [isLoadingRepo, setIsLoadingRepo] = useState(false)
  const [repoError, setRepoError] = useState<string | null>(null)

  return (
    <RepoContext.Provider
      value={{
        repoId,
        status,
        currentRepo,
        fileTree,
        isLoadingRepo,
        repoError,
        setRepoId,
        setStatus,
        setCurrentRepo,
        setFileTree,
        setIsLoadingRepo,
        setRepoError,
      }}
    >
      {children}
    </RepoContext.Provider>
  )
}

export function useRepoContext() {
  const context = useContext(RepoContext)
  if (context === undefined) {
    throw new Error('useRepoContext must be used within a RepoProvider')
  }
  return context
}
