import { createContext, useContext, useState, ReactNode } from 'react'

export type ExplanationLevel = 'beginner' | 'intermediate' | 'advanced'

interface Repository {
  repo_id: string
  source: string
  file_count: number
  chunk_count: number
  tech_stack: {
    languages: string[]
    frameworks: string[]
    libraries: string[]
  }
  status: string
}

interface AppState {
  currentRepo: Repository | null
  currentFile: string | null
  explanationLevel: ExplanationLevel
  darkMode: boolean
  setCurrentRepo: (repo: Repository | null) => void
  setCurrentFile: (file: string | null) => void
  setExplanationLevel: (level: ExplanationLevel) => void
  toggleDarkMode: () => void
}

const AppContext = createContext<AppState | undefined>(undefined)

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentRepo, setCurrentRepo] = useState<Repository | null>(null)
  const [currentFile, setCurrentFile] = useState<string | null>(null)
  const [explanationLevel, setExplanationLevel] = useState<ExplanationLevel>('intermediate')
  const [darkMode, setDarkMode] = useState(true)

  const toggleDarkMode = () => setDarkMode(!darkMode)

  return (
    <AppContext.Provider
      value={{
        currentRepo,
        currentFile,
        explanationLevel,
        darkMode,
        setCurrentRepo,
        setCurrentFile,
        setExplanationLevel,
        toggleDarkMode,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}
