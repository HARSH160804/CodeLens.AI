import { useState, useEffect } from 'react'
import { explainFile, FileExplanationResponse } from '../../services/api'
import { LoadingSpinner } from '../common/LoadingSpinner'

type ExplanationLevel = 'beginner' | 'intermediate' | 'advanced'

interface ExplanationPanelProps {
  repoId: string
  filePath: string
  onRelatedFileClick?: (filePath: string) => void
}

export function ExplanationPanel({ repoId, filePath, onRelatedFileClick }: ExplanationPanelProps) {
  const [activeLevel, setActiveLevel] = useState<ExplanationLevel>('intermediate')
  const [explanations, setExplanations] = useState<Record<ExplanationLevel, FileExplanationResponse | null>>({
    beginner: null,
    intermediate: null,
    advanced: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadExplanation(activeLevel)
  }, [repoId, filePath, activeLevel])

  const loadExplanation = async (level: ExplanationLevel) => {
    // Return if already loaded
    if (explanations[level]) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await explainFile(repoId, filePath, level)
      setExplanations(prev => ({
        ...prev,
        [level]: response.data,
      }))
    } catch (err) {
      console.error('Failed to load explanation:', err)
      setError('Failed to load explanation. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const currentExplanation = explanations[activeLevel]

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Tab Switcher */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {(['beginner', 'intermediate', 'advanced'] as ExplanationLevel[]).map((level) => (
          <button
            key={level}
            onClick={() => setActiveLevel(level)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${activeLevel === level
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
        {isLoading && <LoadingSpinner message="Loading explanation..." />}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {!isLoading && !error && currentExplanation && (
          <div className="space-y-6">
            {/* Purpose */}
            {currentExplanation.explanation.purpose && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Purpose
                </h3>
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                  {currentExplanation.explanation.purpose}
                </p>
              </section>
            )}

            {/* Business Context */}
            {currentExplanation.explanation.businessContext && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Business Context
                </h3>
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                  {currentExplanation.explanation.businessContext}
                </p>
              </section>
            )}

            {/* Execution Flow */}
            {currentExplanation.explanation.executionFlow && currentExplanation.explanation.executionFlow.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Execution Flow
                </h3>
                <ol className="list-decimal list-inside space-y-2">
                  {currentExplanation.explanation.executionFlow.map((step, index) => (
                    <li key={index} className="text-gray-700 dark:text-gray-300">
                      {step}
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {/* Key Functions */}
            {(currentExplanation.explanation.key_functions || currentExplanation.explanation.keyFunctions) &&
              (currentExplanation.explanation.key_functions?.length || currentExplanation.explanation.keyFunctions?.length) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    Key Functions
                  </h3>
                  <div className="space-y-3">
                    {(currentExplanation.explanation.key_functions || currentExplanation.explanation.keyFunctions)?.map((func, index) => (
                      <div
                        key={index}
                        className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
                      >
                        <div className="flex items-baseline justify-between mb-1">
                          <code className="text-sm font-mono text-blue-600 dark:text-blue-400">
                            {func.name}
                          </code>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Line {func.line}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {func.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

            {/* Design Patterns */}
            {(currentExplanation.explanation.patterns || currentExplanation.explanation.designPatterns) &&
              (currentExplanation.explanation.patterns?.length || currentExplanation.explanation.designPatterns?.length) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    Design Patterns
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(currentExplanation.explanation.patterns || currentExplanation.explanation.designPatterns)?.map((pattern, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm font-medium"
                      >
                        {pattern}
                      </span>
                    ))}
                  </div>
                </section>
              )}

            {/* Dependencies */}
            {currentExplanation.explanation.dependencies && currentExplanation.explanation.dependencies.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Dependencies
                </h3>
                <div className="flex flex-wrap gap-2">
                  {currentExplanation.explanation.dependencies.map((dep, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium"
                    >
                      {dep}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Complexity */}
            {currentExplanation.explanation.complexity && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  Complexity Metrics
                </h3>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-2 gap-4">
                    {currentExplanation.explanation.complexity.lines !== undefined && (
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Lines of Code</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {currentExplanation.explanation.complexity.lines}
                        </p>
                      </div>
                    )}
                    {currentExplanation.explanation.complexity.functions !== undefined && (
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Functions</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {currentExplanation.explanation.complexity.functions}
                        </p>
                      </div>
                    )}
                  </div>
                  {currentExplanation.explanation.complexity.score !== undefined && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-gray-600 dark:text-gray-400">Complexity Score</p>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {currentExplanation.explanation.complexity.score}/10
                        </p>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${currentExplanation.explanation.complexity.score <= 3
                              ? 'bg-green-500'
                              : currentExplanation.explanation.complexity.score <= 6
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            }`}
                          style={{ width: `${(currentExplanation.explanation.complexity.score / 10) * 100}%` }}
                        />
                      </div>
                      {currentExplanation.explanation.complexity.reasoning && (
                        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                          {currentExplanation.explanation.complexity.reasoning}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Improvement Suggestions */}
            {currentExplanation.explanation.improvementSuggestions &&
              currentExplanation.explanation.improvementSuggestions.length > 0 && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    Improvement Suggestions
                  </h3>
                  <ul className="list-disc list-inside space-y-2">
                    {currentExplanation.explanation.improvementSuggestions.map((suggestion, index) => (
                      <li key={index} className="text-gray-700 dark:text-gray-300">
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

            {/* Security Risks */}
            {currentExplanation.explanation.securityRisks &&
              currentExplanation.explanation.securityRisks.length > 0 && (
                <section>
                  <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-2">
                    Security Risks
                  </h3>
                  <ul className="list-disc list-inside space-y-2">
                    {currentExplanation.explanation.securityRisks.map((risk, index) => (
                      <li key={index} className="text-red-700 dark:text-red-300">
                        {risk}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

            {/* Related Files */}
            {currentExplanation.related_files && currentExplanation.related_files.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Related Files
                </h3>
                <div className="space-y-2">
                  {currentExplanation.related_files.map((file, index) => (
                    <button
                      key={index}
                      onClick={() => onRelatedFileClick?.(file)}
                      className="block w-full text-left px-3 py-2 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-700 transition-colors"
                    >
                      <code className="text-sm text-blue-600 dark:text-blue-400">
                        {file}
                      </code>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {/* Confidence Score */}
            {currentExplanation.explanation.confidence !== undefined && (
              <section className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Confidence</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {Math.round(currentExplanation.explanation.confidence * 100)}%
                  </span>
                </div>
              </section>
            )}
          </div>
        )}

        {!isLoading && !error && !currentExplanation && (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <p>No explanation available</p>
          </div>
        )}
      </div>
    </div>
  )
}
