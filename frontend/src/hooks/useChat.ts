import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { chat, ChatRequest, ChatResponse } from '../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: ChatResponse['citations']
  timestamp: string
}

export function useChat(repoId: string | undefined) {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])

  const mutation = useMutation({
    mutationFn: async (request: Omit<ChatRequest, 'session_id' | 'history'>) => {
      if (!repoId) throw new Error('Repository ID is required')
      
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }))

      const response = await chat(repoId, {
        ...request,
        session_id: sessionId,
        history,
      })
      
      return response.data
    },
    onMutate: async (request) => {
      // Optimistic update: add user message immediately
      const userMessage: Message = {
        role: 'user',
        content: request.message,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, userMessage])
    },
    onSuccess: (data) => {
      // Add assistant response
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        citations: data.citations,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMessage])
      
      // Update session ID and suggested questions
      setSessionId(data.session_id)
      setSuggestedQuestions(data.suggested_questions)
    },
    onError: (_error, request) => {
      // Remove optimistic user message on error
      setMessages(prev => prev.filter(msg => msg.content !== request.message))
    },
  })

  const sendMessage = useCallback((
    message: string,
    scope?: ChatRequest['scope']
  ) => {
    mutation.mutate({ message, scope })
  }, [mutation])

  const clearHistory = useCallback(() => {
    setMessages([])
    setSessionId(undefined)
    setSuggestedQuestions([])
  }, [])

  return {
    messages,
    sessionId,
    suggestedQuestions,
    sendMessage,
    clearHistory,
    isLoading: mutation.isPending,
    error: mutation.error,
  }
}
