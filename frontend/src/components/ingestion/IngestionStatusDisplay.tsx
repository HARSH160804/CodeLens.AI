import { useNavigate } from 'react-router-dom'
import { useIngestionStatus } from '../../hooks/useIngestionStatus'

interface IngestionStatusDisplayProps {
  jobId: string
  onRetry?: () => void
}

/**
 * Component that displays ingestion status with polling.
 * 
 * Features:
 * - Integrates useIngestionStatus hook
 * - Displays progress during processing
 * - Shows success message on completion
 * - Shows error message on failure
 * - Navigates to dashboard on completion
 * - Provides retry button on failure
 * 
 * Requirements: 4.4, 14.5
 */
export function IngestionStatusDisplay({ jobId, onRetry }: IngestionStatusDisplayProps) {
  const navigate = useNavigate()
  
  const { status, error, retryCount } = useIngestionStatus({
    jobId,
    onCompleted: (completedStatus) => {
      console.log('Ingestion completed:', completedStatus)
      // Navigate to repository dashboard after a short delay
      setTimeout(() => {
        if (completedStatus.repo_id) {
          navigate(`/repo/${completedStatus.repo_id}`)
        }
      }, 2000)
    },
    onFailed: (failedStatus) => {
      console.error('Ingestion failed:', failedStatus)
    }
  })

  // Processing state - show step-by-step checklist (includes initial loading before first status fetch)
  if (!status || status.status === 'processing') {
    const percentage = status?.progress_total && status.progress_total > 0 
      ? Math.round((status.progress_current / status.progress_total) * 100) 
      : 0
    
    // Determine which steps are completed based on progress
    const steps = [
      { text: 'Parsing repository files', completed: percentage >= 20, active: percentage < 20 },
      { text: 'Building architecture graph', completed: percentage >= 40, active: percentage >= 20 && percentage < 40 },
      { text: 'Generating embeddings', completed: percentage >= 60, active: percentage >= 40 && percentage < 60 },
      { text: 'Detecting dependencies', completed: percentage >= 80, active: percentage >= 60 && percentage < 80 },
      { text: 'Preparing AI insights', completed: percentage >= 100, active: percentage >= 80 && percentage < 100 }
    ]
    
    return (
      <div className="relative z-10 text-center px-8 py-10" style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
        width: '520px',
        maxWidth: '90vw',
        margin: '0 auto'
      }}>
        {/* Spinner with subtle glow */}
        <div className="mb-6 relative inline-block">
          {/* Subtle glow behind spinner */}
          <div
            className="absolute inset-0 rounded-full blur-xl"
            style={{
              background: 'radial-gradient(circle, rgba(59,130,246,0.15), transparent 60%)',
            }}
          />
          {/* Improved spinner with gradient */}
          <div
            className="relative w-12 h-12 rounded-full"
            style={{
              border: '3px solid rgba(255,255,255,0.1)',
              borderTopColor: '#3b82f6',
              animation: 'spin 1s linear infinite',
            }}
          />
        </div>

        {/* Title - Larger and more specific */}
        <h2 className="text-[30px] font-semibold text-white mb-2 leading-tight">
          Analyzing repository architecture
        </h2>

        {/* Subtitle - More technical */}
        <p className="text-gray-400 text-base mb-6 leading-relaxed">
          Parsing files and detecting architectural patterns.
        </p>

        {/* Progress bar with animated progress */}
        <div
          className="w-full rounded-full h-1.5 mb-6 overflow-hidden"
          style={{ background: '#1f2937' }}
        >
          <div
            className="h-full rounded-full transition-all duration-300 ease-out"
            style={{
              width: `${percentage}%`,
              background: 'linear-gradient(90deg, #3b82f6, #6366f1)',
            }}
          />
        </div>

        {/* Processing steps with checkmarks */}
        <div className="space-y-3 text-left">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex items-center space-x-3 text-sm"
            >
              {step.completed ? (
                <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold bg-blue-600 text-white">
                  ✓
                </span>
              ) : step.active ? (
                <div className="flex-shrink-0 w-5 h-5 rounded-full border-2 border-blue-600 flex items-center justify-center">
                  <div
                    className="w-2 h-2 rounded-full bg-blue-600"
                    style={{ animation: 'pulse 1.5s ease-in-out infinite' }}
                  />
                </div>
              ) : (
                <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs bg-gray-800 text-gray-600">
                  ○
                </span>
              )}
              <span
                className={
                  step.completed
                    ? 'text-gray-300'
                    : step.active
                    ? 'text-blue-400'
                    : 'text-gray-500'
                }
              >
                {step.text}
              </span>
            </div>
          ))}
        </div>

        {error && retryCount > 0 && (
          <div className="mt-5 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <p className="text-sm text-yellow-200">
              {error}
            </p>
          </div>
        )}

        {/* CSS animations */}
        <style>{`
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
          
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
              transform: scale(1);
            }
            50% {
              opacity: 0.5;
              transform: scale(0.8);
            }
          }
        `}</style>
      </div>
    )
  }

  // Completed state - show same design with all steps completed
  if (status.status === 'completed') {
    const steps = [
      { text: 'Parsing repository files', completed: true, active: false },
      { text: 'Building architecture graph', completed: true, active: false },
      { text: 'Generating embeddings', completed: true, active: false },
      { text: 'Detecting dependencies', completed: true, active: false },
      { text: 'Preparing AI insights', completed: true, active: false }
    ]
    
    return (
      <div className="relative z-10 text-center px-8 py-10" style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
        width: '520px',
        maxWidth: '90vw',
        margin: '0 auto'
      }}>
        {/* Spinner with subtle glow */}
        <div className="mb-6 relative inline-block">
          {/* Subtle glow behind spinner */}
          <div
            className="absolute inset-0 rounded-full blur-xl"
            style={{
              background: 'radial-gradient(circle, rgba(59,130,246,0.15), transparent 60%)',
            }}
          />
          {/* Improved spinner with gradient */}
          <div
            className="relative w-12 h-12 rounded-full"
            style={{
              border: '3px solid rgba(255,255,255,0.1)',
              borderTopColor: '#3b82f6',
              animation: 'spin 1s linear infinite',
            }}
          />
        </div>

        {/* Title - Larger and more specific */}
        <h2 className="text-[30px] font-semibold text-white mb-2 leading-tight">
          Analyzing repository architecture
        </h2>

        {/* Subtitle - More technical */}
        <p className="text-gray-400 text-base mb-6 leading-relaxed">
          Parsing files and detecting architectural patterns.
        </p>

        {/* Progress bar at 100% */}
        <div
          className="w-full rounded-full h-1.5 mb-6 overflow-hidden"
          style={{ background: '#1f2937' }}
        >
          <div
            className="h-full rounded-full"
            style={{
              width: '100%',
              background: 'linear-gradient(90deg, #3b82f6, #6366f1)',
            }}
          />
        </div>

        {/* Processing steps - all completed */}
        <div className="space-y-3 text-left">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex items-center space-x-3 text-sm"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold bg-blue-600 text-white">
                ✓
              </span>
              <span className="text-gray-300">
                {step.text}
              </span>
            </div>
          ))}
        </div>

        {/* CSS animations */}
        <style>{`
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
        `}</style>
      </div>
    )
  }

  // Failed state
  if (status.status === 'failed') {
    return (
      <div className="relative z-10 text-center px-8 py-10" style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,68,68,0.2)',
        borderRadius: '16px',
        width: '520px',
        maxWidth: '90vw',
        margin: '0 auto'
      }}>
        <div className="mb-6 relative inline-block">
          <div
            className="absolute inset-0 rounded-full blur-xl"
            style={{
              background: 'radial-gradient(circle, rgba(239,68,68,0.15), transparent 60%)',
            }}
          />
          <div className="relative w-12 h-12 rounded-full flex items-center justify-center bg-red-500/10">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        </div>
          
        <h2 className="text-[30px] font-semibold text-white mb-2 leading-tight">
          Indexing Failed
        </h2>
          
        {status.error_message && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg mb-6">
            <p className="text-sm text-red-200">
              {status.error_message}
            </p>
          </div>
        )}
          
        <div className="flex items-center justify-center space-x-3">
          {onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-all font-medium shadow-lg hover:shadow-xl text-sm"
            >
              Try Again
            </button>
          )}
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center px-6 py-3 bg-gray-700 text-gray-200 rounded-full hover:bg-gray-600 transition-all font-medium text-sm"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  return null
}
