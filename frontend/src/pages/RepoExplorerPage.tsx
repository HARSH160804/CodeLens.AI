import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { MainLayout } from '../components/layout/MainLayout'
import { Sidebar } from '../components/layout/Sidebar'
import { ProcessingScreen } from '../components/common/ProcessingScreen'
import { CodeViewer } from '../components/code/CodeViewer'
import { SplitPane } from '../components/layout/SplitPane'
import { getRepoStatus, explainFile } from '../services/api'
import { useApp } from '../context/AppContext'

interface FileExplanation {
  purpose: string
  key_functions: Array<{
    name: string
    description: string
    line: number
  }>
  patterns: string[]
  dependencies: string[]
  complexity: {
    lines: number
    functions: number
  }
}

export function RepoExplorerPage() {
  const { repoId } = useParams<{ repoId: string }>()
  const { explanationLevel, setExplanationLevel } = useApp()
  const [isIndexing, setIsIndexing] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [explanation, setExplanation] = useState<FileExplanation | null>(null)
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false)
  const [selectedLine, setSelectedLine] = useState<number | null>(null)

  // Poll for indexing status
  useEffect(() => {
    if (!repoId) return

    let pollInterval: ReturnType<typeof setInterval> | null = null

    const checkStatus = async () => {
      try {
        const response = await getRepoStatus(repoId)
        const status = response.data.status

        console.log('Repository status:', status)

        if (status === 'completed') {
          setIsIndexing(false)
          if (pollInterval) {
            clearInterval(pollInterval)
          }

          // Auto-select default file after indexing completes
          const filePaths = response.data.file_paths || []
          if (filePaths.length > 0 && !selectedFile) {
            // Prefer README.md, otherwise first file
            const defaultFile = filePaths.find(f => f.toLowerCase().includes('readme')) || filePaths[0]
            setSelectedFile(defaultFile)
          }
        } else if (status === 'failed') {
          setError('Repository indexing failed. Please try again.')
          setIsIndexing(false)
          if (pollInterval) {
            clearInterval(pollInterval)
          }
        }
      } catch (err: any) {
        console.error('Error checking repository status:', err)
        setError('Failed to check repository status')
        setIsIndexing(false)
        if (pollInterval) {
          clearInterval(pollInterval)
        }
      }
    }

    // Initial check
    checkStatus()

    // Poll every 3 seconds if still indexing
    pollInterval = setInterval(checkStatus, 3000)

    // Cleanup on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [repoId, selectedFile])

  // Fetch file content and explanation when file is selected
  useEffect(() => {
    if (!repoId || !selectedFile) return

    const fetchFileData = async () => {
      setIsLoadingFile(true)
      setIsLoadingExplanation(true)
      setExplanation(null) // Clear previous explanation

      try {
        // Fetch file content (mock for now - backend doesn't have this endpoint yet)
        // TODO: Replace with actual API call when backend supports file content endpoint
        const mockContent = `// File: ${selectedFile}
// Content would be fetched from backend API
// Currently showing placeholder

import { useState, useEffect } from 'react'

export function ExampleComponent() {
  const [count, setCount] = useState(0)
  
  useEffect(() => {
    console.log('Count changed:', count)
  }, [count])
  
  return (
    <div>
      <h1>Counter: {count}</h1>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  )
}`
        setFileContent(mockContent)
        setIsLoadingFile(false)

        // Fetch explanation
        try {
          const explanationResponse = await explainFile(repoId, selectedFile, explanationLevel)
          console.log('Explanation response:', explanationResponse.data)
          
          // Ensure explanation has all required fields with defaults
          const explanationData = explanationResponse.data.explanation
          setExplanation({
            purpose: explanationData.purpose || 'No description available',
            key_functions: explanationData.key_functions || [],
            patterns: explanationData.patterns || [],
            dependencies: explanationData.dependencies || [],
            complexity: {
              lines: explanationData.complexity?.lines || 0,
              functions: explanationData.complexity?.functions || 0
            }
          })
          setIsLoadingExplanation(false)
        } catch (explainErr) {
          console.error('Error fetching explanation:', explainErr)
          // Set a default explanation on error
          setExplanation({
            purpose: 'Unable to generate explanation for this file.',
            key_functions: [],
            patterns: [],
            dependencies: [],
            complexity: { lines: 0, functions: 0 }
          })
          setIsLoadingExplanation(false)
        }
      } catch (err) {
        console.error('Error fetching file data:', err)
        setFileContent('// Error loading file content')
        setIsLoadingFile(false)
        setIsLoadingExplanation(false)
      }
    }

    fetchFileData()
  }, [repoId, selectedFile, explanationLevel])

  if (!repoId) {
    return <div>Repository not found</div>
  }

  // Show loading state while indexing
  if (isIndexing) {
    return <ProcessingScreen />
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Error
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
          <Link
            to="/"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    )
  }

  const language = selectedFile ? selectedFile.split('.').pop() || 'typescript' : 'typescript'

  // Show full dashboard layout
  return (
    <MainLayout showSidebar>
      <div className="flex h-full">
        <Sidebar repoId={repoId} onFileSelect={setSelectedFile} />
        
        <div className="flex-1 flex flex-col">
          {/* Breadcrumb / File Path */}
          {selectedFile && (
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                  <span className="font-mono">{selectedFile}</span>
                </div>
                <div className="flex items-center space-x-4">
                  <Link
                    to={`/repo/${repoId}/architecture`}
                    className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    🏗️ Architecture
                  </Link>
                  <Link
                    to={`/repo/${repoId}/chat`}
                    className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    💬 Chat
                  </Link>
                </div>
              </div>
            </div>
          )}
          
          {/* Main Content Area */}
          <div className="flex-1 overflow-hidden">
            {selectedFile ? (
              <SplitPane
                left={
                  <div className="h-full">
                    {isLoadingFile ? (
                      <div className="flex items-center justify-center h-full">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      </div>
                    ) : (
                      <CodeViewer
                        code={fileContent}
                        language={language}
                        onLineClick={setSelectedLine}
                      />
                    )}
                  </div>
                }
                right={
                  <div className="h-full overflow-y-auto p-6 bg-gray-50 dark:bg-gray-900">
                    {/* Level Selector */}
                    <div className="mb-6">
                      <label className="block text-sm font-medium mb-2">Explanation Level</label>
                      <div className="flex space-x-2">
                        {(['beginner', 'intermediate', 'advanced'] as const).map((level) => (
                          <button
                            key={level}
                            onClick={() => setExplanationLevel(level)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                              explanationLevel === level
                                ? 'bg-blue-600 text-white'
                                : 'bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                          >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Loading State */}
                    {isLoadingExplanation && (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      </div>
                    )}

                    {/* Explanation */}
                    {!isLoadingExplanation && explanation && (
                      <div className="space-y-6">
                        <div>
                          <h3 className="text-lg font-semibold mb-2">Purpose</h3>
                          <p className="text-gray-700 dark:text-gray-300">
                            {explanation.purpose}
                          </p>
                        </div>

                        {explanation.key_functions && explanation.key_functions.length > 0 && (
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Key Functions</h3>
                            <div className="space-y-2">
                              {explanation.key_functions.map((func, index) => (
                                <div
                                  key={func.name || index}
                                  className="p-3 bg-white dark:bg-gray-800 rounded-lg"
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-mono text-sm font-medium">{func.name}()</span>
                                    <span className="text-xs text-gray-500">Line {func.line}</span>
                                  </div>
                                  <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {func.description}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {explanation.patterns && explanation.patterns.length > 0 && (
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Patterns</h3>
                            <div className="flex flex-wrap gap-2">
                              {explanation.patterns.map((pattern, index) => (
                                <span
                                  key={pattern || index}
                                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm"
                                >
                                  {pattern}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {explanation.dependencies && explanation.dependencies.length > 0 && (
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Dependencies</h3>
                            <div className="flex flex-wrap gap-2">
                              {explanation.dependencies.map((dep, index) => (
                                <span
                                  key={dep || index}
                                  className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono"
                                >
                                  {dep}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {explanation.complexity && (
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Complexity</h3>
                            <div className="grid grid-cols-2 gap-4">
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                                <div className="text-2xl font-bold text-blue-600">
                                  {explanation.complexity.lines || 0}
                                </div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Lines</div>
                              </div>
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                                <div className="text-2xl font-bold text-blue-600">
                                  {explanation.complexity.functions || 0}
                                </div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Functions</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {selectedLine && (
                          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                            <p className="text-sm">
                              <span className="font-medium">Line {selectedLine} selected.</span> Ask a
                              question about this line in the chat.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                }
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500 dark:text-gray-400">
                  <div className="text-6xl mb-4">📁</div>
                  <p>Select a file from the sidebar to view its contents</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  )
}
