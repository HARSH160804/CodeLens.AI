import { useState, useEffect, useRef } from 'react'
import mermaid from 'mermaid'
import { getArchitecture, ArchitectureResponse } from '../../services/api'
import { LoadingSpinner } from '../common/LoadingSpinner'

type ArchitectureLevel = 'basic' | 'intermediate' | 'advanced'

interface ArchitectureViewProps {
  repoId: string
  onFileClick?: (filePath: string) => void
}

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'ui-monospace, monospace',
})

export function ArchitectureView({ repoId, onFileClick }: ArchitectureViewProps) {
  const [activeLevel, setActiveLevel] = useState<ArchitectureLevel>('intermediate')
  const [architectures, setArchitectures] = useState<Record<ArchitectureLevel, ArchitectureResponse | null>>({
    basic: null,
    intermediate: null,
    advanced: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const diagramRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadArchitecture(activeLevel)
  }, [repoId, activeLevel])

  useEffect(() => {
    renderDiagram()
  }, [architectures, activeLevel])

  const loadArchitecture = async (level: ArchitectureLevel) => {
    // Return if already loaded
    if (architectures[level]) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await getArchitecture(repoId, level)
      setArchitectures(prev => ({
        ...prev,
        [level]: response.data,
      }))
    } catch (err) {
      console.error('Failed to load architecture:', err)
      setError('Failed to load architecture. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const renderDiagram = async () => {
    const currentArchitecture = architectures[activeLevel]
    if (!currentArchitecture?.diagram || !diagramRef.current) return

    try {
      // Clear previous diagram
      diagramRef.current.innerHTML = ''

      // Generate unique ID for this diagram
      const id = `mermaid-${Date.now()}`
      
      // Render the diagram
      const { svg } = await mermaid.render(id, currentArchitecture.diagram)
      diagramRef.current.innerHTML = svg

      // Make diagram responsive
      const svgElement = diagramRef.current.querySelector('svg')
      if (svgElement) {
        svgElement.style.maxWidth = '100%'
        svgElement.style.height = 'auto'
      }
    } catch (err) {
      console.error('Failed to render Mermaid diagram:', err)
      diagramRef.current.innerHTML = `
        <div class="text-red-600 dark:text-red-400 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          Failed to render diagram. The diagram syntax may be invalid.
        </div>
      `
    }
  }

  const currentArchitecture = architectures[activeLevel]

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Level Selector */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {(['basic', 'intermediate', 'advanced'] as ArchitectureLevel[]).map((level) => (
          <button
            key={level}
            onClick={() => setActiveLevel(level)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeLevel === level
                ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            {level.charAt(0).toUpperCase() + level.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && <LoadingSpinner message="Loading architecture..." />}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {!isLoading && !error && currentArchitecture && (
          <div className="space-y-8">
            {/* Overview */}
            {currentArchitecture.architecture.overview && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Architecture Overview
                </h2>
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {currentArchitecture.architecture.overview}
                </p>
              </section>
            )}

            {/* Mermaid Diagram */}
            {currentArchitecture.diagram && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Architecture Diagram
                </h2>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 overflow-x-auto">
                  <div ref={diagramRef} className="flex justify-center" />
                </div>
              </section>
            )}

            {/* Components */}
            {currentArchitecture.architecture.components && currentArchitecture.architecture.components.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Components
                </h2>
                <div className="grid gap-4 md:grid-cols-2">
                  {currentArchitecture.architecture.components.map((component, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700"
                    >
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                        {component.name}
                      </h3>
                      <p className="text-gray-700 dark:text-gray-300 text-sm mb-3">
                        {component.description}
                      </p>
                      {component.files && component.files.length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Files:
                          </p>
                          {component.files.map((file, fileIndex) => (
                            <button
                              key={fileIndex}
                              onClick={() => onFileClick?.(file)}
                              className="block w-full text-left px-2 py-1 text-xs bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 transition-colors"
                            >
                              <code className="text-blue-600 dark:text-blue-400">{file}</code>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Design Patterns */}
            {currentArchitecture.architecture.patterns && currentArchitecture.architecture.patterns.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Design Patterns
                </h2>
                <div className="flex flex-wrap gap-3">
                  {currentArchitecture.architecture.patterns.map((pattern, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg text-sm font-medium border border-purple-200 dark:border-purple-800"
                    >
                      {pattern}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Data Flow */}
            {currentArchitecture.architecture.data_flow && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Data Flow
                </h2>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {currentArchitecture.architecture.data_flow}
                  </p>
                </div>
              </section>
            )}

            {/* Entry Points */}
            {currentArchitecture.architecture.entry_points && currentArchitecture.architecture.entry_points.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                  Entry Points
                </h2>
                <div className="space-y-2">
                  {currentArchitecture.architecture.entry_points.map((entryPoint, index) => (
                    <button
                      key={index}
                      onClick={() => onFileClick?.(entryPoint)}
                      className="block w-full text-left px-4 py-3 bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg border border-green-200 dark:border-green-800 transition-colors"
                    >
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-green-600 dark:text-green-400 mr-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                          />
                        </svg>
                        <code className="text-sm text-green-700 dark:text-green-300 font-medium">
                          {entryPoint}
                        </code>
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {/* Metadata */}
            <section className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <span>Generated at</span>
                <span>{new Date(currentArchitecture.generated_at).toLocaleString()}</span>
              </div>
            </section>
          </div>
        )}

        {!isLoading && !error && !currentArchitecture && (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <p>No architecture data available</p>
          </div>
        )}
      </div>
    </div>
  )
}
