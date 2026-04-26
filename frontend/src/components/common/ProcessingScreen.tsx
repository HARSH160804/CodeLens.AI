import { useEffect, useState } from 'react'

const PROCESSING_STEPS = [
  { text: 'Parsing repository files', completed: true },
  { text: 'Building architecture graph', completed: true },
  { text: 'Generating embeddings', completed: true },
  { text: 'Detecting dependencies', completed: false, active: true },
  { text: 'Preparing AI insights', completed: false, active: false },
]

export function ProcessingScreen() {
  const [progress, setProgress] = useState(35)

  useEffect(() => {
    // Simulate realistic progress animation
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 85) return 35 // Reset for demo
        return prev + 0.3 // Slow, steady progress
      })
    }, 100)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      className="fixed inset-0 flex items-center justify-center overflow-hidden"
      style={{ backgroundColor: '#080b15' }}
    >
      {/* Subtle background glow */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(circle at center, rgba(59,130,246,0.08), transparent 60%)',
        }}
      />

      {/* Center Processing Card */}
      <div
        className="relative z-10 text-center px-8 py-10"
        style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '16px',
          width: '520px',
          maxWidth: '90vw',
        }}
      >
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
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #3b82f6, #6366f1)',
            }}
          />
        </div>

        {/* Processing steps with checkmarks */}
        <div className="space-y-3 text-left">
          {PROCESSING_STEPS.map((step, index) => (
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
