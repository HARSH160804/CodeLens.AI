import { useState, useRef, useEffect } from 'react'
import { useChat } from '../../hooks/useChat'

interface ChatInterfaceProps {
  repoId: string
}

export function ChatInterface({ repoId }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const [showScrollButton, setShowScrollButton] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const { messages, sendMessage, isLoading, error, suggestedQuestions } = useChat(repoId)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle scroll to show/hide scroll button
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
      setShowScrollButton(!isNearBottom && messages.length > 0)
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [messages.length])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    sendMessage(input.trim())
    setInput('')
  }

  const handleSuggestedQuestion = (question: string) => {
    if (isLoading) return
    sendMessage(question)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Empty State - Compact header with suggestions */}
      {messages.length === 0 && !error && (
        <div className="flex flex-col space-y-6 pt-8 pb-6">
          {/* Header - Premium typography */}
          <div className="text-center space-y-3">
            <h1 className="font-semibold text-white" style={{ 
              fontSize: '42px',
              lineHeight: '1.2',
              letterSpacing: '-0.02em'
            }}>
              Ask anything about this <span style={{ color: '#3b82f6' }}>repository</span>
            </h1>
            <p className="text-gray-400" style={{ 
              fontSize: '16px',
              opacity: 0.75
            }}>
              AI-powered answers with code citations
            </p>
          </div>

          {/* Suggested Questions as Chips */}
          <div className="flex flex-wrap gap-2 justify-center">
            {(suggestedQuestions && suggestedQuestions.length > 0 ? suggestedQuestions : [
              "What are the main entry points?",
              "How does error handling work?",
              "Explain the database schema",
              "What testing patterns are used?"
            ]).map((question, index) => (
              <button
                key={index}
                onClick={() => handleSuggestedQuestion(question)}
                disabled={isLoading}
                className="text-gray-300 rounded-full transition-all hover:text-white hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: '#0f1419',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  fontSize: '14px',
                  padding: '8px 14px'
                }}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages - Left-aligned conversation */}
      {messages.length > 0 && (
        <div 
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto py-4 space-y-4 relative"
        >
          {messages.map((message, index) => (
            <div key={index} className="w-full">
              {message.role === 'user' ? (
                // User message - Right aligned, compact bubble
                <div className="flex justify-end">
                  <div
                    className="max-w-[70%] px-4 py-2 rounded-2xl text-white"
                    style={{ 
                      background: '#3b82f6',
                      fontSize: '15px'
                    }}
                  >
                    {message.content}
                  </div>
                </div>
              ) : (
                // Assistant message - Left aligned, wider panel
                <div className="flex justify-start">
                  <div
                    className="max-w-[85%] px-5 py-4 rounded-2xl text-gray-100 space-y-4"
                    style={{
                      background: '#0f1419',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      lineHeight: '1.6'
                    }}
                  >
                    {/* AI Response Content */}
                    <div className="whitespace-pre-wrap leading-relaxed" style={{ fontSize: '15px' }}>
                      {message.content}
                    </div>
                    
                    {/* Code Citation Blocks */}
                    {message.citations && message.citations.length > 0 && (
                      <div className="space-y-2 pt-3 border-t border-gray-700">
                        <p className="text-gray-400 font-medium mb-2" style={{ fontSize: '12px' }}>Referenced Files</p>
                        {message.citations.map((citation, idx) => (
                          <div 
                            key={idx} 
                            className="flex items-start space-x-2 px-3 py-2 rounded-lg"
                            style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)' }}
                          >
                            <svg className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <div className="flex-1 min-w-0">
                              <div className="font-mono text-blue-300 truncate" style={{ fontSize: '14px' }}>
                                {citation.file.split('/').pop()}
                              </div>
                              <div className="text-gray-500 truncate" style={{ fontSize: '12px' }}>
                                {citation.file.substring(0, citation.file.lastIndexOf('/'))}
                                {citation.line && <span className="ml-2">Line {citation.line}</span>}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div
                className="px-5 py-4 rounded-2xl flex items-center space-x-3"
                style={{
                  background: '#0f1419',
                  border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
              >
                <svg className="animate-spin h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-gray-400" style={{ fontSize: '15px' }}>CodeLens is analyzing the repository...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="flex justify-center">
              <div className="rounded-2xl px-4 py-3 text-red-400" style={{ 
                background: 'rgba(239, 68, 68, 0.1)', 
                border: '1px solid rgba(239, 68, 68, 0.2)',
                fontSize: '15px'
              }}>
                Failed to send message. Please try again.
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />

          {/* Scroll to Bottom Button */}
          {showScrollButton && (
            <button
              onClick={scrollToBottom}
              className="fixed bottom-24 right-8 p-3 rounded-full shadow-lg transition-all hover:scale-110"
              style={{
                background: '#3b82f6',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}
            >
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* Input Area - Enhanced with shortcuts hint */}
      <div className="py-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the codebase... (@file, /search, /explain)"
            disabled={isLoading}
            className="flex-1 px-5 py-3 rounded-full text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            style={{ 
              background: '#0f1419',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              fontSize: '15px'
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 text-white font-medium rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            style={{
              background: !input.trim() || isLoading ? '#374151' : '#3b82f6'
            }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  )
}
