export interface Repository {
  id: string
  name: string
  url: string
  fileCount: number
  ingestedAt: string
}

export interface Session {
  id: string
  createdAt: string
  expiresAt: string
  repositories: Repository[]
}

export interface ArchitectureSummary {
  summary: string
  mermaidDiagram: string
}

export interface FileExplanation {
  beginner: string
  intermediate: string
  advanced: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  references?: string[]
}
