import { createContext, useContext, useState, ReactNode, useEffect } from 'react'

export type ExplanationLevel = 'beginner' | 'intermediate' | 'advanced'
export type Theme = 'light' | 'dark'

interface SettingsContextType {
  explanationLevel: ExplanationLevel
  setExplanationLevel: (level: ExplanationLevel) => void
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [explanationLevel, setExplanationLevel] = useState<ExplanationLevel>('intermediate')
  const [theme, setTheme] = useState<Theme>('dark')

  // Apply theme to document
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return (
    <SettingsContext.Provider
      value={{
        explanationLevel,
        setExplanationLevel,
        theme,
        setTheme,
        toggleTheme,
      }}
    >
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
