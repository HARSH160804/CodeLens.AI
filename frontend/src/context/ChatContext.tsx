import { createContext, useContext, useState, ReactNode } from 'react'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: Array<{
    file: string
    line?: number
    snippet: string
  }>
  timestamp: string
}

interface ChatContextType {
  messages: ChatMessage[]
  setMessages: (messages: ChatMessage[]) => void
  currentSession: string | null
  setCurrentSession: (session: string | null) => void
  isStreaming: boolean
  setIsStreaming: (streaming: boolean) => void
  scope: {
    type: 'all' | 'file' | 'directory'
    path?: string
  }
  setScope: (scope: { type: 'all' | 'file' | 'directory'; path?: string }) => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentSession, setCurrentSession] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [scope, setScope] = useState<{
    type: 'all' | 'file' | 'directory'
    path?: string
  }>({ type: 'all' })

  return (
    <ChatContext.Provider
      value={{
        messages,
        setMessages,
        currentSession,
        setCurrentSession,
        isStreaming,
        setIsStreaming,
        scope,
        setScope,
      }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export function useChatContext() {
  const context = useContext(ChatContext)
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider')
  }
  return context
}
