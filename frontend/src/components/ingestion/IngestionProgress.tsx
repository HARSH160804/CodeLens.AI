interface IngestionProgressProps {
  current: number
  total: number
  className?: string
}

/**
 * Progress bar component for repository ingestion.
 * 
 * Displays:
 * - Progress bar visualization
 * - "Processing X/Y files" text
 * - Percentage calculation
 * - Loading animation
 * 
 * Requirements: 4.4
 */
export function IngestionProgress({ current, total, className = '' }: IngestionProgressProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0
  
  return (
    <div className={`space-y-5 ${className}`}>
      {/* Progress text */}
      <div className="flex items-center justify-between">
        <span className="text-gray-300 font-medium text-base">
          {current} / {total} files processed
        </span>
        <span className="text-blue-400 font-semibold text-base">
          {percentage}%
        </span>
      </div>
      
      {/* Progress bar - 8px thick with rounded corners */}
      <div className="relative w-full h-2 bg-gray-700 rounded-lg overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-lg transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        >
          {/* Animated shimmer effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
        </div>
      </div>
    </div>
  )
}
