/**
 * GenerateButton Component
 * 
 * Button for triggering documentation generation.
 * Shows loading state and changes label based on whether docs exist.
 */

import { Loader2, FileText } from 'lucide-react'

interface GenerateButtonProps {
  status: 'not_generated' | 'generating' | 'generated' | 'failed'
  isGenerating: boolean
  onGenerate: () => void
}

export function GenerateButton({ status, isGenerating, onGenerate }: GenerateButtonProps) {
  const isDisabled = isGenerating || status === 'generating'
  
  // Determine button text
  const getButtonText = () => {
    if (isGenerating || status === 'generating') {
      return 'Generating...'
    }
    if (status === 'generated' || status === 'failed') {
      return 'Regenerate Documentation'
    }
    return 'Generate Documentation'
  }
  
  return (
    <button
      onClick={onGenerate}
      disabled={isDisabled}
      className={`
        inline-flex items-center gap-2 px-6 py-2.5 rounded-full font-medium
        transition-all duration-200
        ${isDisabled
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
          : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
        }
      `}
    >
      {isGenerating || status === 'generating' ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <FileText className="w-4 h-4" />
      )}
      <span>{getButtonText()}</span>
    </button>
  )
}
