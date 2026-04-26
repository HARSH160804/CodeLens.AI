interface ProgressIndicatorProps {
  progress: number
  message?: string
}

export function ProgressIndicator({ progress, message }: ProgressIndicatorProps) {
  const getStatusMessage = () => {
    if (progress < 20) return 'Downloading repository...'
    if (progress < 40) return 'Extracting files...'
    if (progress < 60) return 'Analyzing code structure...'
    if (progress < 80) return 'Generating embeddings...'
    if (progress < 100) return 'Finalizing...'
    return 'Complete!'
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">
          {message || getStatusMessage()}
        </span>
        <span className="font-medium">{progress}%</span>
      </div>
      
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="bg-blue-600 h-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
