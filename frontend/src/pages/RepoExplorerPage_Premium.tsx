import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { ProcessingScreen } from '../components/common/ProcessingScreen'
import { getRepoStatus, getFileContent, explainFile, getRepoMetadata } from '../services/api'
import { useApp } from '../context/AppContext'

// Custom animations
const customStyles = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideUp {
    from { 
      opacity: 0;
      transform: translateY(10px);
    }
    to { 
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .dashboard-background {
    background: 
      linear-gradient(rgba(59,130,246,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,0.06) 1px, transparent 1px),
      radial-gradient(circle at 30% 20%, rgba(30, 64, 175, 0.15), transparent 40%),
      linear-gradient(180deg, #020617 0%, #030b1a 100%);
    background-size: 60px 60px, 60px 60px, 100% 100%, 100% 100%;
    background-attachment: fixed, fixed, fixed, fixed;
  }
`

interface FileItem {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileItem[]
}

interface Explanation {
  purpose: string
  businessContext?: string
  executionFlow?: string[]
  keyFunctions?: Array<{
    name: string
    description: string
    line: number
  }>
  designPatterns?: string[]
  dependencies?: string[]
  complexity?: {
    score: number
    reasoning: string
  }
  improvementSuggestions?: string[]
  securityRisks?: string[]
  impactAssessment?: string
  confidence?: number
}

interface RepoMetadata {
  repoName: string
  totalFiles: number
  totalLines: number
  languageBreakdown: Record<string, number>
  primaryLanguage: string
  techStack: {
    languages: string[]
    frameworks: string[]
    libraries: string[]
    databases?: string[]
  }
  architectureType: string
  indexedAt: string
}

export function RepoExplorerPagePremium() {
  const { repoId } = useParams<{ repoId: string }>()
  const { explanationLevel, setExplanationLevel } = useApp()
  
  // Loading states
  const [isIndexing, setIsIndexing] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Data states
  const [repoMetadata, setRepoMetadata] = useState<RepoMetadata | null>(null)
  const [fileTree, setFileTree] = useState<FileItem[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [fileLanguage, setFileLanguage] = useState<string>('typescript')
  const [explanation, setExplanation] = useState<Explanation | null>(null)
  
  // UI states
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())

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

          // Fetch metadata and file tree
          await fetchRepoData()
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

    checkStatus()
    pollInterval = setInterval(checkStatus, 3000)

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [repoId])

  const fetchRepoData = async () => {
    if (!repoId) return

    try {
      // Fetch file tree from status endpoint first (this is the critical one)
      const statusResponse = await getRepoStatus(repoId)
      console.log('Status response:', statusResponse.data)
      console.log('File paths:', statusResponse.data.file_paths)
      
      const filePaths = statusResponse.data.file_paths || []
      console.log('File paths count:', filePaths.length)
      
      // Build file tree
      const tree = buildFileTree(filePaths)
      console.log('Built file tree:', tree)
      setFileTree(tree)

      // Auto-select README or first file
      if (filePaths.length > 0) {
        const defaultFile = filePaths.find(f => f.toLowerCase().includes('readme')) || filePaths[0]
        console.log('Auto-selecting file:', defaultFile)
        setSelectedFile(defaultFile)
        
        // Auto-expand root folders
        const rootFolders = tree.filter(item => item.type === 'directory').map(item => item.path)
        setExpandedFolders(new Set(rootFolders))
      }

      // Try to fetch metadata (optional - may not be deployed yet)
      try {
        const metadataResponse = await getRepoMetadata(repoId)
        console.log('Metadata response:', metadataResponse.data)
        setRepoMetadata(metadataResponse.data)
      } catch (metaErr) {
        console.warn('Metadata endpoint not available (may not be deployed yet):', metaErr)
        // Create fallback metadata from status response
        const statusData = statusResponse.data
        setRepoMetadata({
          repoName: statusData.source || 'Repository',
          totalFiles: statusData.file_count || 0,
          totalLines: 0,
          languageBreakdown: {},
          primaryLanguage: '',
          techStack: statusData.tech_stack || { languages: [], frameworks: [], libraries: [] },
          architectureType: '',
          indexedAt: statusData.created_at || ''
        })
      }
    } catch (err) {
      console.error('Error fetching repo data:', err)
      setError('Failed to load repository data. Check console for details.')
    }
  }

  const buildFileTree = (filePaths: string[]): FileItem[] => {
    const root: FileItem = { name: '', path: '', type: 'directory', children: [] }

    filePaths.forEach(filePath => {
      const parts = filePath.split('/')
      let currentNode = root

      parts.forEach((part, index) => {
        const isFile = index === parts.length - 1
        const childPath = parts.slice(0, index + 1).join('/')

        let existing = currentNode.children?.find(c => c.name === part)

        if (!existing) {
          existing = {
            name: part,
            path: childPath,
            type: isFile ? 'file' : 'directory',
            children: isFile ? undefined : [],
          }
          currentNode.children!.push(existing)
        }

        if (!isFile) {
          currentNode = existing
        }
      })
    })

    const sortItems = (items: FileItem[]): FileItem[] => {
      return items
        .map(item => ({
          ...item,
          children: item.children ? sortItems(item.children) : undefined,
        }))
        .sort((a, b) => {
          if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
          return a.name.localeCompare(b.name)
        })
    }

    return sortItems(root.children || [])
  }

  // Fetch file content and explanation when file is selected
  useEffect(() => {
    if (!repoId || !selectedFile) return

    const fetchFileData = async () => {
      setIsLoadingFile(true)
      setIsLoadingExplanation(true)
      setExplanation(null)

      try {
        // Fetch file content
        const contentResponse = await getFileContent(repoId, selectedFile)
        setFileContent(contentResponse.data.content)
        setFileLanguage(contentResponse.data.language)
        setIsLoadingFile(false)

        // Fetch explanation
        try {
          const explanationResponse = await explainFile(repoId, selectedFile, explanationLevel)
          console.log('Explanation response:', explanationResponse.data)
          
          const explanationData = explanationResponse.data.explanation as any
          setExplanation({
            purpose: explanationData.purpose || 'No description available',
            businessContext: explanationData.businessContext || '',
            executionFlow: explanationData.executionFlow || [],
            keyFunctions: explanationData.keyFunctions || explanationData.key_functions || [],
            designPatterns: explanationData.designPatterns || explanationData.patterns || [],
            dependencies: explanationData.dependencies || [],
            complexity: {
              score: explanationData.complexity?.score || 0,
              reasoning: explanationData.complexity?.reasoning || ''
            },
            improvementSuggestions: explanationData.improvementSuggestions || [],
            securityRisks: explanationData.securityRisks || [],
            impactAssessment: explanationData.impactAssessment || '',
            confidence: explanationData.confidence || 0.5
          })
          setIsLoadingExplanation(false)
        } catch (explainErr) {
          console.error('Error fetching explanation:', explainErr)
          setExplanation({
            purpose: 'Unable to generate explanation for this file.',
            confidence: 0
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

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedFolders(newExpanded)
  }

  // Get file icon based on extension
  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    
    const iconMap: Record<string, string> = {
      // JavaScript/TypeScript
      'js': '📄',
      'jsx': '⚛️',
      'ts': '📘',
      'tsx': '⚛️',
      // Config
      'json': '📋',
      'yaml': '⚙️',
      'yml': '⚙️',
      'toml': '⚙️',
      // Styles
      'css': '🎨',
      'scss': '🎨',
      'sass': '🎨',
      // Markup
      'html': '🌐',
      'xml': '📰',
      'md': '📝',
      // Python
      'py': '🐍',
      // Other
      'sh': '🔧',
      'env': '🔐',
      'gitignore': '🚫',
    }
    
    return iconMap[ext || ''] || '📄'
  }

  const renderFileNode = (item: FileItem, level: number = 0): JSX.Element => {
    const isExpanded = expandedFolders.has(item.path)
    const isSelected = selectedFile === item.path

    if (item.type === 'directory') {
      return (
        <div key={item.path} className="select-none">
          <div
            onClick={() => toggleFolder(item.path)}
            style={{ paddingLeft: `${level * 12 + 8}px` }}
            className="group flex items-center space-x-1.5 py-1 px-2 hover:bg-white/5 rounded-md cursor-pointer transition-all"
          >
            {/* Chevron Icon */}
            <svg
              className={`w-3 h-3 transition-transform duration-200 text-gray-500 group-hover:text-gray-400 ${
                isExpanded ? 'rotate-90' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            
            {/* Folder Icon */}
            <svg
              className={`w-4 h-4 ${isExpanded ? 'text-blue-400' : 'text-gray-500'} group-hover:text-blue-400 transition-colors`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
            
            <span className="text-[13px] font-medium text-gray-300 group-hover:text-white transition-colors truncate">
              {item.name}
            </span>
          </div>
          
          {/* Animated Children */}
          <div
            className={`overflow-hidden transition-all duration-200 ${
              isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            {item.children && item.children.map(child => renderFileNode(child, level + 1))}
          </div>
        </div>
      )
    }

    return (
      <div
        key={item.path}
        onClick={() => setSelectedFile(item.path)}
        style={{ paddingLeft: `${level * 12 + 28}px` }}
        className={`group flex items-center space-x-2 py-1 px-2 rounded-md cursor-pointer transition-all duration-200 ${
          isSelected
            ? 'bg-blue-600/10 text-blue-400 shadow-[inset_2px_0_0_0_rgb(59,130,246)]'
            : 'hover:bg-white/5 text-gray-400 hover:text-gray-200'
        }`}
      >
        <span className="text-sm">{getFileIcon(item.name)}</span>
        <span className="text-[12px] truncate">{item.name}</span>
      </div>
    )
  }

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) {
      return <span className="px-2 py-0.5 bg-green-500/10 text-green-400 text-[10px] rounded font-semibold">High Confidence</span>
    } else if (confidence >= 0.5) {
      return <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 text-[10px] rounded font-semibold">Medium Confidence</span>
    } else {
      return <span className="px-2 py-0.5 bg-red-500/10 text-red-400 text-[10px] rounded font-semibold">Low Confidence</span>
    }
  }

  if (!repoId) {
    return <div>Repository not found</div>
  }

  if (isIndexing) {
    return <ProcessingScreen />
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-2">Error</h2>
          <p className="text-gray-400 mb-6">{error}</p>
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

  return (
    <div className="h-screen flex flex-col dashboard-background text-white overflow-hidden">
      <style>{customStyles}</style>
      
      {/* Premium Repository Header */}
      <div className="bg-[#0a0d12] border-b border-[#2d3748] px-6 py-3">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Left Section - Single Row */}
          <div className="flex items-center space-x-4 flex-wrap">
            {/* Logo */}
            <Link 
              to="/" 
              className="flex items-center space-x-2 hover:opacity-80 transition-opacity"
            >
              {/* BloomWay AI Logo */}
              <img 
                src="/logo_bloomway.png" 
                alt="CodeLens Logo"
                className="w-8 h-8 rounded-xl object-contain"
              />
              {/* Text */}
              <span className="text-[14px] font-bold tracking-wide">
                <span className="text-gray-200">CODELENS</span>
                <span className="text-gray-500">·</span>
                <span className="text-blue-400">AI</span>
              </span>
            </Link>
            
            {/* Vertical Divider */}
            <div className="h-8 w-px bg-gradient-to-b from-transparent via-gray-700 to-transparent"></div>
            
            {/* Repo Name */}
            <h1 className="text-[13px] font-normal leading-none flex items-center space-x-1.5">
              {repoMetadata?.repoName ? (
                repoMetadata.repoName.includes('/') ? (
                  <>
                    <span className="text-gray-500">{repoMetadata.repoName.split('/')[0]}</span>
                    <span className="text-gray-600">/</span>
                    <span className="text-gray-300">{repoMetadata.repoName.split('/')[1]}</span>
                  </>
                ) : (
                  <span className="text-gray-300">{repoMetadata.repoName}</span>
                )
              ) : (
                <span className="text-gray-300">Repository</span>
              )}
            </h1>
            
            {/* File Count */}
            <span className="text-[11px] text-gray-500 font-normal">
              {repoMetadata?.totalFiles || 0} files
            </span>
            
            {/* Tech Stack Badges */}
            <div className="flex items-center space-x-1.5">
              {repoMetadata?.techStack.languages.slice(0, 3).map(lang => (
                <span 
                  key={lang} 
                  className="px-1.5 py-0.5 bg-[#2d3748] text-gray-300 text-[9px] rounded-full font-medium border border-[#3d4758] hover:bg-[#3d4758] transition-colors"
                >
                  {lang}
                </span>
              ))}
            </div>
            
            {/* Indexed Badge */}
            <span className="px-1.5 py-0.5 bg-green-500/10 text-green-400 text-[9px] rounded-full font-medium flex items-center space-x-1 border border-green-500/30">
              <svg className="w-2 h-2 fill-current" viewBox="0 0 8 8">
                <circle cx="4" cy="4" r="3" />
              </svg>
              <span>Indexed</span>
            </span>
          </div>
          
          {/* Right Section - Actions */}
          <div className="flex items-center space-x-2">
            <Link
              to={`/repo/${repoId}/architecture`}
              className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
              style={{ fontSize: '12px' }}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>Architecture</span>
            </Link>
            
            <Link
              to={`/repo/${repoId}/chat`}
              className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
              style={{ fontSize: '12px' }}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span>Chat</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Layout - 3 Column Grid */}
      <div className="flex-1 flex overflow-hidden bg-transparent">
        {/* Left Sidebar - File Tree (VSCode Style) */}
        <div className="w-[240px] flex-shrink-0 border-r border-[#2d3748] flex flex-col bg-[#0a0d12]">
          {/* Search Input */}
          <div className="p-3 border-b border-[#2d3748]">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                placeholder="Search files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-[#0a0d12] border border-[#2d3748] rounded-full text-[12px] text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
              />
            </div>
          </div>
          
          {/* File Tree with Scroll Shadow */}
          <div className="flex-1 overflow-y-auto p-2">
            {fileTree.length === 0 ? (
              <div className="text-center py-8 px-4">
                <div className="text-4xl mb-3">📁</div>
                <div className="text-gray-400 text-sm mb-2">No files found</div>
                <div className="text-gray-500 text-xs mb-4">
                  This repository may have been ingested before the file tree feature was added.
                </div>
                <div className="text-gray-500 text-xs">
                  <strong>To fix:</strong>
                  <ol className="text-left mt-2 space-y-1 max-w-xs mx-auto">
                    <li>1. Open browser console (F12)</li>
                    <li>2. Check for "File paths count: 0"</li>
                    <li>3. Re-ingest this repository</li>
                  </ol>
                </div>
              </div>
            ) : (
              <div className="space-y-0.5">
                {fileTree.map(item => renderFileNode(item))}
              </div>
            )}
          </div>
        </div>

        {/* Center Panel - Code Viewer */}
        <div className="flex-1 min-w-0 flex flex-col bg-transparent">
          {selectedFile && (
            <div className="px-4 py-2 bg-[#0a0d12] border-b border-[#2d3748]">
              <span className="text-[11px] text-gray-500 font-mono">{selectedFile}</span>
            </div>
          )}
          <div className="flex-1 bg-[#0a0d12] overflow-hidden">
            {isLoadingFile ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <Editor
                height="100%"
                language={fileLanguage}
                value={fileContent}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: 'on',
                  glyphMargin: true,
                  folding: true,
                  lineDecorationsWidth: 10,
                  lineNumbersMinChars: 4,
                  renderLineHighlight: 'all',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
                beforeMount={(monaco) => {
                  monaco.editor.defineTheme('bloomway-dark', {
                    base: 'vs-dark',
                    inherit: true,
                    rules: [],
                    colors: {
                      'editor.background': '#0a0d12',
                      'editor.lineHighlightBackground': '#1a1f2e',
                      'editorLineNumber.foreground': '#4b5563',
                      'editorLineNumber.activeForeground': '#9ca3af',
                    }
                  });
                }}
                onMount={(_editor, monaco) => {
                  monaco.editor.setTheme('bloomway-dark');
                }}
              />
            )}
          </div>
        </div>

        {/* Right Panel - AI Insights */}
        <div className="w-[340px] flex-shrink-0 border-l border-[#2d3748] flex flex-col bg-[#0a0d12] overflow-hidden">
          {/* Header Section */}
          <div className="p-4 border-b border-[#2d3748] flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[13px] font-semibold text-gray-200">
                AI Insights
              </h3>
              {explanation && getConfidenceBadge(explanation.confidence || 0)}
            </div>
            
            {/* Explanation Level Toggle */}
            <div className="flex space-x-2">
              {(['beginner', 'intermediate', 'advanced'] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => setExplanationLevel(level)}
                  className={`flex-1 px-2.5 py-1.5 rounded-full text-[11px] font-medium transition-colors ${
                    explanationLevel === level
                      ? 'bg-blue-600 text-white'
                      : 'bg-[#2d3748] text-gray-400 hover:bg-[#3d4758] hover:text-gray-300'
                  }`}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Content Section */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoadingExplanation ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : explanation ? (
              <>
                {/* Purpose Card */}
                <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                  <h4 className="text-[12px] font-semibold text-white mb-2">
                    Purpose
                  </h4>
                  <p className="text-[12px] text-gray-400 leading-relaxed">{explanation.purpose}</p>
                </div>

                {/* Execution Flow Card */}
                {explanation.executionFlow && explanation.executionFlow.length > 0 && (
                  <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                    <h4 className="text-[12px] font-semibold text-white mb-3">
                      Execution Flow
                    </h4>
                    <ol className="space-y-2">
                      {explanation.executionFlow.map((step, index) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600/20 text-blue-400 text-[10px] font-bold flex items-center justify-center">
                            {index + 1}
                          </span>
                          <span className="text-[11px] text-gray-400 leading-relaxed pt-0.5">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Design Patterns Card */}
                {explanation.designPatterns && explanation.designPatterns.length > 0 && (
                  <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                    <h4 className="text-[12px] font-semibold text-white mb-2">
                      Design Patterns
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {explanation.designPatterns.map((pattern, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-purple-500/10 text-purple-400 text-[10px] font-medium rounded-full border border-purple-500/20"
                        >
                          {pattern}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Dependencies Card */}
                {explanation.dependencies && explanation.dependencies.length > 0 && (
                  <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                    <h4 className="text-[12px] font-semibold text-white mb-2">
                      Dependencies
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {explanation.dependencies.slice(0, 10).map((dep, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-[#2d3748] text-gray-400 text-[10px] rounded-full font-mono"
                        >
                          {dep}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Complexity Score Card */}
                {explanation.complexity && (
                  <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                    <h4 className="text-[12px] font-semibold text-white mb-3">
                      Complexity Score
                    </h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-2xl font-bold text-white">{explanation.complexity.score}<span className="text-sm text-gray-500">/10</span></span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          explanation.complexity.score <= 3 ? 'bg-green-500/20 text-green-400' :
                          explanation.complexity.score <= 6 ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {explanation.complexity.score <= 3 ? 'Low' :
                           explanation.complexity.score <= 6 ? 'Medium' : 'High'}
                        </span>
                      </div>
                      <div className="w-full bg-[#2d3748] rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-700 ease-out ${
                            explanation.complexity.score <= 3 ? 'bg-green-500' :
                            explanation.complexity.score <= 6 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${(explanation.complexity.score / 10) * 100}%` }}
                        ></div>
                      </div>
                      {explanation.complexity.reasoning && (
                        <p className="text-[11px] text-gray-500 leading-relaxed">{explanation.complexity.reasoning}</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Suggestions Card */}
                {explanation.improvementSuggestions && explanation.improvementSuggestions.length > 0 && (
                  <div className="p-4 bg-[#0a0d12] border border-[#2d3748] rounded">
                    <h4 className="text-[12px] font-semibold text-white mb-2">
                      Suggestions
                    </h4>
                    <ul className="space-y-2">
                      {explanation.improvementSuggestions.map((suggestion, index) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="text-yellow-500 mt-0.5 text-[10px]">▸</span>
                          <span className="text-[11px] text-gray-400 leading-relaxed">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-gray-500 text-[12px]">
                Select a file to view AI insights
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
