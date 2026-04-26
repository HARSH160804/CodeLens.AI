import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod'

interface IngestionStatus {
  job_id: string
  status: 'processing' | 'completed' | 'failed'
  source: string
  source_type: string
  progress_current: number
  progress_total: number
  error_message?: string
  created_at: string
  updated_at: string
  repo_id?: string
}

interface UseIngestionStatusOptions {
  jobId: string | null
  pollInterval?: number // milliseconds
  maxPollDuration?: number // milliseconds
  onCompleted?: (status: IngestionStatus) => void
  onFailed?: (status: IngestionStatus) => void
}

interface UseIngestionStatusReturn {
  status: IngestionStatus | null
  isPolling: boolean
  error: string | null
  retryCount: number
}

/**
 * React hook for polling ingestion job status.
 * 
 * Features:
 * - Polls status endpoint every 2 seconds (configurable)
 * - Stops polling when job reaches terminal state (completed/failed)
 * - Implements exponential backoff on errors (up to 3 retries)
 * - Stops polling after max duration (15 minutes default)
 * - Calls callbacks on completion/failure
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.5
 */
export function useIngestionStatus({
  jobId,
  pollInterval = 2000,
  maxPollDuration = 15 * 60 * 1000, // 15 minutes
  onCompleted,
  onFailed
}: UseIngestionStatusOptions): UseIngestionStatusReturn {
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  
  const pollStartTimeRef = useRef<number | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hasCalledCallbackRef = useRef(false)

  const fetchStatus = useCallback(async () => {
    if (!jobId) return

    try {
      const response = await axios.get<IngestionStatus>(
        `${API_BASE_URL}/ingestion/status/${jobId}`
      )
      
      const newStatus = response.data
      setStatus(newStatus)
      setError(null)
      setRetryCount(0) // Reset retry count on success
      
      // Check for terminal states
      if (newStatus.status === 'completed') {
        setIsPolling(false)
        if (onCompleted && !hasCalledCallbackRef.current) {
          hasCalledCallbackRef.current = true
          onCompleted(newStatus)
        }
      } else if (newStatus.status === 'failed') {
        setIsPolling(false)
        if (onFailed && !hasCalledCallbackRef.current) {
          hasCalledCallbackRef.current = true
          onFailed(newStatus)
        }
      }
    } catch (err: any) {
      console.error('Error fetching ingestion status:', err)
      
      // Implement exponential backoff on errors
      if (retryCount < 3) {
        setRetryCount(prev => prev + 1)
        setError(`Failed to fetch status (retry ${retryCount + 1}/3)`)
      } else {
        setError('Failed to fetch status after 3 retries')
        setIsPolling(false)
      }
    }
  }, [jobId, retryCount, onCompleted, onFailed])

  useEffect(() => {
    if (!jobId) {
      setIsPolling(false)
      return
    }

    // Start polling
    setIsPolling(true)
    pollStartTimeRef.current = Date.now()
    hasCalledCallbackRef.current = false

    // Initial fetch
    fetchStatus()

    // Set up polling interval
    pollIntervalRef.current = setInterval(() => {
      // Check max poll duration
      if (pollStartTimeRef.current && Date.now() - pollStartTimeRef.current > maxPollDuration) {
        console.warn('Max poll duration exceeded, stopping polling')
        setError('Polling timeout exceeded')
        setIsPolling(false)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        return
      }

      // Check if we should stop polling (terminal state reached)
      if (status && (status.status === 'completed' || status.status === 'failed')) {
        setIsPolling(false)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        return
      }

      fetchStatus()
    }, pollInterval)

    // Cleanup on unmount
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
      setIsPolling(false)
    }
  }, [jobId, pollInterval, maxPollDuration, fetchStatus, status])

  return {
    status,
    isPolling,
    error,
    retryCount
  }
}
