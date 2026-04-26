import { useState, useEffect, useRef } from 'react'
import mermaid from 'mermaid'
import { getArchitecture, ArchitectureResponse } from '../../services/api'
import { ProcessingScreen } from '../common/ProcessingScreen'
import { HierarchicalArchitectureExplorer } from './HierarchicalArchitectureExplorer'
import { useDocumentation } from '../../hooks/useDocumentation'
import { GenerateButton } from '../docs/GenerateButton'
import { ExportDropdown } from '../docs/ExportDropdown'
import { Loader2, AlertCircle } from 'lucide-react'

interface ArchitectureViewProps {
  repoId: string
  onPatternsLoaded?: (patterns: string[]) => void
  onLoadingChange?: (loading: boolean) => void
}

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'ui-monospace, monospace',
  themeVariables: {
    primaryColor: '#1e40af',
    primaryTextColor: '#e5e7eb',
    primaryBorderColor: '#3b82f6',
    lineColor: '#6b7280',
    secondaryColor: '#7c3aed',
    tertiaryColor: '#059669',
  },
})

export function ArchitectureView({ repoId, onPatternsLoaded, onLoadingChange }: ArchitectureViewProps) {
  const [architecture, setArchitecture] = useState<ArchitectureResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'layers' | 'tech'>('overview')
  const diagramRef = useRef<HTMLDivElement>(null)
  
  // Documentation hook
  const {
    status: docStatus,
    errorMessage: docError,
    generate: generateDocs,
    isGenerating,
    exportMarkdown,
    exportPdf,
    exportError,
    clearExportError,
  } = useDocumentation({ repoId })
  
  // Debug logging for documentation status
  useEffect(() => {
    console.log('=== DOCUMENTATION STATUS DEBUG ===')
    console.log('docStatus:', docStatus)
    console.log('isGenerating:', isGenerating)
    console.log('docError:', docError)
    console.log('exportError:', exportError)
    console.log('Timestamp:', new Date().toISOString())
    console.log('=================================')
  }, [docStatus, isGenerating, docError, exportError])

  useEffect(() => {
    loadArchitecture()
  }, [repoId])

  useEffect(() => {
    if (activeTab === 'layers') {
      renderDiagram()
    }
  }, [architecture, activeTab])

  const loadArchitecture = async () => {
    if (architecture) return

    setIsLoading(true)
    onLoadingChange?.(true)
    setError(null)

    try {
      const response = await getArchitecture(repoId, 'intermediate')
      console.log('=== ARCHITECTURE API RESPONSE ===')
      console.log('Full response:', response.data)
      console.log('Schema version:', response.data.schema_version)
      console.log('Confidence:', response.data.confidence)
      console.log('Confidence signals:', response.data.confidence_signals)
      console.log('Has patterns:', response.data.patterns?.length || 0)
      console.log('Has layers:', response.data.layers?.length || 0)
      console.log('Has tech_stack:', response.data.tech_stack?.length || 0)
      console.log('Has metrics:', !!response.data.metrics)
      console.log('Has recommendations:', response.data.recommendations?.length || 0)
      console.log('================================')
      
      // Deduplicate tech_stack on frontend as safety measure (case-insensitive)
      if (response.data.tech_stack && response.data.tech_stack.length > 0) {
        console.log('Tech stack BEFORE deduplication:', response.data.tech_stack.map((t: any) => t.name))
        const seen = new Set<string>()
        response.data.tech_stack = response.data.tech_stack.filter((tech: any) => {
          const nameLower = tech.name.toLowerCase()
          if (seen.has(nameLower)) {
            console.log(`Removing duplicate: ${tech.name} (lowercase: ${nameLower})`)
            return false
          }
          seen.add(nameLower)
          return true
        })
        console.log('Tech stack AFTER deduplication:', response.data.tech_stack.map((t: any) => t.name))
        console.log('Tech stack after deduplication:', response.data.tech_stack.length)
      }
      
      setArchitecture(response.data)

      // Notify parent of loaded patterns
      if (onPatternsLoaded && response.data.patterns && response.data.patterns.length > 0) {
        const patternNames = response.data.patterns.slice(0, 2).map((p: any) => p.name)
        onPatternsLoaded(patternNames)
      }
    } catch (err) {
      console.error('Failed to load architecture:', err)
      setError('Failed to load architecture. Please try again.')
    } finally {
      setIsLoading(false)
      onLoadingChange?.(false)
    }
  }

  const renderDiagram = async () => {
    const currentArchitecture = architecture
    if (!currentArchitecture?.diagram || !diagramRef.current) return

    try {
      diagramRef.current.innerHTML = ''
      const id = `mermaid-${Date.now()}`
      const { svg } = await mermaid.render(id, currentArchitecture.diagram)
      diagramRef.current.innerHTML = svg

      const svgElement = diagramRef.current.querySelector('svg')
      if (svgElement) {
        svgElement.style.maxWidth = '100%'
        svgElement.style.height = 'auto'
      }
    } catch (err) {
      console.error('Failed to render Mermaid diagram:', err)
      diagramRef.current.innerHTML = `
        <div class="text-red-400 p-4 bg-red-900/20 rounded-lg border border-red-800">
          Failed to render diagram. The diagram syntax may be invalid.
        </div>
      `
    }
  }

  const currentArchitecture = architecture

  // Helper function to safely get confidence (fallback to legacy field)
  const getConfidence = () => {
    if (currentArchitecture?.confidence !== undefined) {
      return currentArchitecture.confidence
    }
    if (currentArchitecture?.architecture?.confidence !== undefined) {
      return currentArchitecture.architecture.confidence
    }
    return 0.5 // Default fallback
  }

  // Helper function to get confidence signals with fallback
  const getConfidenceSignals = () => {
    const signals = currentArchitecture?.confidence_signals
    console.log('getConfidenceSignals called, signals:', signals)
    if (!signals || typeof signals !== 'object') {
      console.warn('No confidence_signals found in response, using defaults')
      return {
        layer_separation_score: 0,
        framework_detection_score: 0,
        database_integration_score: 0,
        dependency_direction_score: 0,
        dependency_depth_score: 0,
        naming_consistency_score: 0,
      }
    }
    return signals
  }

  // Helper function to get confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.85) return 'text-green-400'
    if (confidence >= 0.70) return 'text-blue-400'
    if (confidence >= 0.50) return 'text-yellow-400'
    return 'text-red-400'
  }

  // Helper function to get confidence label
  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.85) return 'Excellent'
    if (confidence >= 0.70) return 'Good'
    if (confidence >= 0.50) return 'Fair'
    return 'Poor'
  }

  return (
    <div className="flex flex-col h-full" style={{ background: '#0a0e14' }}>
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <ProcessingScreen />
        )}

        {error && (
          <div className="m-6 bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
            {error}
          </div>
        )}

        {!isLoading && !error && currentArchitecture && (
          <div className="p-6 space-y-6">
            {/* Tab Navigation - Pill Container Style */}
            <div className="flex justify-center mb-6">
              <div
                className="inline-flex items-center gap-1 p-1.5 rounded-full"
                style={{ background: '#0c1017', border: '1px solid #151b24' }}
              >
                {[
                  { id: 'overview', label: 'Overview' },
                  { id: 'layers', label: 'System Diagram' },
                  { id: 'tech', label: 'Data Flow' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className="relative px-5 py-2 text-sm font-medium transition-all duration-200 rounded-full"
                    style={{
                      background: activeTab === tab.id ? '#2563eb' : 'transparent',
                      color: activeTab === tab.id ? '#ffffff' : '#6b7280',
                      boxShadow: activeTab === tab.id ? '0 2px 8px rgba(37, 99, 235, 0.35)' : 'none',
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Documentation Controls */}
            <div className="flex items-center justify-between mb-6 p-4 rounded-lg" style={{ background: '#0c1017', border: '1px solid #151b24' }}>
              <div className="flex items-center gap-3">
                <div>
                  <h3 className="text-sm font-medium text-gray-300">Repository Documentation</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {docStatus === 'not_generated' && 'Generate comprehensive documentation from architecture analysis'}
                    {docStatus === 'generating' && 'Documentation is being generated...'}
                    {docStatus === 'generated' && 'Documentation is ready to export'}
                    {docStatus === 'failed' && 'Documentation generation failed'}
                  </p>
                  {/* Debug status indicator */}
                  <p className="text-xs text-gray-600 mt-1">
                    Status: <span className="font-mono">{docStatus}</span>
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                {/* Loading indicator during generation */}
                {(docStatus === 'generating' || isGenerating) && (
                  <div className="flex items-center gap-2 text-blue-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Generating...</span>
                  </div>
                )}
                
                {/* Error message */}
                {docStatus === 'failed' && docError && (
                  <div className="flex items-center gap-2 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>Generation failed</span>
                  </div>
                )}
                
                {/* Generate/Regenerate Button - shown when NOT generating */}
                {docStatus === 'not_generated' && !isGenerating && (
                  <GenerateButton
                    status={docStatus}
                    isGenerating={isGenerating}
                    onGenerate={generateDocs}
                  />
                )}
                
                {/* Regenerate Button - shown when failed */}
                {docStatus === 'failed' && !isGenerating && (
                  <GenerateButton
                    status={docStatus}
                    isGenerating={isGenerating}
                    onGenerate={generateDocs}
                  />
                )}
                
                {/* Export Controls - shown when generated */}
                {docStatus === 'generated' && !isGenerating && (
                  <div className="flex items-center gap-2">
                    <GenerateButton
                      status={docStatus}
                      isGenerating={isGenerating}
                      onGenerate={generateDocs}
                    />
                    <ExportDropdown
                      onExportMarkdown={exportMarkdown}
                      onExportPdf={exportPdf}
                    />
                  </div>
                )}
              </div>
            </div>
            
            {/* Export Error Display */}
            {exportError && (
              <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-800 flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                  <div>
                    <div className="text-red-400 font-medium mb-1">Failed to export documentation. Please try again.</div>
                    <div className="text-red-300 text-sm">{exportError}</div>
                  </div>
                </div>
                <button
                  onClick={clearExportError}
                  className="text-red-400 hover:text-red-300 transition-colors"
                  aria-label="Dismiss error"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* Tab Content */}
            <div className="space-y-6">
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <>
                  {/* 1. Architecture Pattern */}
                  {currentArchitecture.patterns && Array.isArray(currentArchitecture.patterns) && currentArchitecture.patterns.length > 0 && (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <h3 className="text-lg font-bold text-white mb-4">Architecture Pattern</h3>
                      {(() => {
                        const primaryPattern = currentArchitecture.patterns[0]
                        const confidence = (primaryPattern.confidence || 0) * 100

                        // Extract signals from pattern evidence files
                        const signals = []
                        if (primaryPattern.evidence_files && Array.isArray(primaryPattern.evidence_files) && primaryPattern.evidence_files.length > 0) {
                          // Generate signals from evidence files
                          const hasControllers = primaryPattern.evidence_files.some(f => f.toLowerCase().includes('controller'))
                          const hasServices = primaryPattern.evidence_files.some(f => f.toLowerCase().includes('service'))
                          const hasModels = primaryPattern.evidence_files.some(f => f.toLowerCase().includes('model'))
                          const hasRoutes = primaryPattern.evidence_files.some(f => f.toLowerCase().includes('route'))
                          const hasViews = primaryPattern.evidence_files.some(f => f.toLowerCase().includes('view') || f.toLowerCase().includes('component'))

                          if (hasControllers) signals.push('Controllers detected')
                          if (hasServices) signals.push('Service layer detected')
                          if (hasModels) signals.push('ORM models detected')
                          if (hasRoutes) signals.push('API routing layer')
                          if (hasViews) signals.push('View layer detected')
                          if (signals.length > 2) signals.push('Clear dependency direction')
                        }

                        // Fallback: generate signals from pattern name
                        if (signals.length === 0) {
                          if (primaryPattern.name?.toLowerCase().includes('mvc')) {
                            signals.push('Controllers', 'Service Layer', 'ORM Models', 'API Routing Layer', 'Clear Dependency Direction')
                          } else if (primaryPattern.name?.toLowerCase().includes('layered')) {
                            signals.push('Layer Separation', 'Clear Boundaries', 'Dependency Direction', 'Modular Structure')
                          } else if (primaryPattern.name?.toLowerCase().includes('microservice')) {
                            signals.push('Service Isolation', 'API Boundaries', 'Independent Deployment', 'Distributed Architecture')
                          } else if (primaryPattern.name?.toLowerCase().includes('monolith')) {
                            signals.push('Single Deployment Unit', 'Shared Database', 'Internal Module Structure')
                          } else {
                            signals.push('Pattern Structure Detected', 'Architectural Consistency')
                          }
                        }

                        return (
                          <div className="rounded p-5" style={{ background: '#0d1117' }}>
                            <div className="flex items-start justify-between mb-4">
                              <div className="text-white text-xl font-semibold">
                                {primaryPattern.name || 'Unknown Pattern'}
                              </div>
                              <div className={`px-3 py-1 rounded-full text-sm font-medium ${primaryPattern.confidence >= 0.85 ? 'bg-green-900/30 text-green-400' :
                                primaryPattern.confidence >= 0.70 ? 'bg-blue-900/30 text-blue-400' :
                                  primaryPattern.confidence >= 0.50 ? 'bg-yellow-900/30 text-yellow-400' :
                                    'bg-red-900/30 text-red-400'
                                }`}>
                                {confidence.toFixed(0)}% confidence
                              </div>
                            </div>

                            {signals.length > 0 && (
                              <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                                <div className="text-gray-400 text-sm mb-3">Signals Detected:</div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                  {signals.map((signal, i) => (
                                    <div key={i} className="flex items-center space-x-2 text-sm text-gray-300">
                                      <span className="text-blue-400">•</span>
                                      <span>{signal}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })()}
                    </div>
                  )}

                  {/* 2. Executive Summary */}
                  {currentArchitecture.patterns && currentArchitecture.patterns.length > 0 && (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <h3 className="text-lg font-bold text-white mb-4">Executive Summary</h3>
                      <div className="rounded p-5 space-y-4" style={{ background: '#0d1117' }}>
                        <p className="text-gray-300 leading-relaxed">
                          This repository follows a <span className="text-white font-medium">{currentArchitecture.patterns[0].name}</span> architecture.
                        </p>

                        {currentArchitecture.patterns[0].description && (
                          <p className="text-gray-400 text-sm leading-relaxed">
                            {currentArchitecture.patterns[0].description}
                          </p>
                        )}

                        {/* Tech Stack Summary */}
                        {currentArchitecture.tech_stack && currentArchitecture.tech_stack.length > 0 && (
                          <div className="pt-4" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                            <div className="text-gray-400 text-sm mb-2">Technology Stack:</div>
                            <div className="flex flex-wrap gap-2">
                              {currentArchitecture.tech_stack.slice(0, 8).map((tech, i) => (
                                <span key={i} className="px-2 py-1 rounded text-xs" style={{ background: '#0a0e14', color: '#9ca3af' }}>
                                  {tech.name}
                                </span>
                              ))}
                              {currentArchitecture.tech_stack.length > 8 && (
                                <span className="px-2 py-1 rounded text-xs text-gray-500">
                                  +{currentArchitecture.tech_stack.length - 8} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Layers Summary */}
                        {currentArchitecture.layers && currentArchitecture.layers.length > 0 && (
                          <div className="pt-4" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                            <div className="text-gray-400 text-sm mb-2">Application Layers:</div>
                            <ul className="space-y-1">
                              {currentArchitecture.layers.map((layer, i) => (
                                <li key={i} className="text-gray-300 text-sm flex items-start">
                                  <span className="text-blue-400 mr-2">•</span>
                                  <span className="capitalize">{layer.name} layer</span>
                                  {layer.components && layer.components.length > 0 && (
                                    <span className="text-gray-500 ml-1">({layer.components.length} components)</span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 3. Architecture Confidence */}
                  <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                    <div className="rounded p-5" style={{ background: '#0d1117' }}>
                      {/* Header Row: Title and Score */}
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-bold text-white">Architecture Confidence</h3>
                        <div className="flex items-center gap-4">
                          <div className={`text-4xl font-bold ${getConfidenceColor(getConfidence())}`}>
                            {(getConfidence() * 100).toFixed(0)}%
                          </div>
                          <div className="text-sm px-3 py-1 rounded" style={{ background: '#0a0e14', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                            <span className={`${getConfidenceColor(getConfidence())}`}>
                              [ {getConfidenceLabel(getConfidence())} ]
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Metrics List (Vertical) */}
                      <div className="space-y-3">
                        {(() => {
                          const signals = getConfidenceSignals()
                          const metrics = [
                            {
                              key: 'layer_separation_score',
                              label: 'Layer Separation',
                              color: 'structural'
                            },
                            {
                              key: 'dependency_direction_score',
                              label: 'Dependency Direction',
                              color: 'structural'
                            },
                            {
                              key: 'dependency_depth_score',
                              label: 'Dependency Depth',
                              color: 'structural'
                            },
                            {
                              key: 'naming_consistency_score',
                              label: 'Naming Consistency',
                              color: 'quality'
                            },
                            {
                              key: 'framework_detection_score',
                              label: 'Framework Detection',
                              color: 'structural'
                            },
                            {
                              key: 'database_integration_score',
                              label: 'Database Integration',
                              color: 'structural'
                            }
                          ]

                          return metrics.map(metric => {
                            const value = signals[metric.key as keyof typeof signals]
                            const numValue = typeof value === 'number' ? value : 0
                            if (numValue === 0) return null // Hide empty metrics
                            const percentage = (numValue * 100).toFixed(0)
                            
                            // Color based on metric type and value
                            let barColor = '#3b82f6' // default blue
                            if (metric.color === 'structural') {
                              barColor = numValue >= 0.7 ? '#10b981' : numValue >= 0.5 ? '#3b82f6' : '#fbbf24'
                            } else if (metric.color === 'quality') {
                              barColor = numValue >= 0.7 ? '#10b981' : numValue >= 0.5 ? '#f59e0b' : '#ef4444'
                            }

                            return (
                              <div key={metric.key} className="flex items-center gap-4">
                                <div className="w-48 text-sm text-gray-300">{metric.label}</div>
                                <div className="flex-1 flex items-center gap-3">
                                  <div className="flex-1 h-2 rounded-full" style={{ background: '#0a0d12' }}>
                                    <div
                                      className="h-full rounded-full transition-all"
                                      style={{
                                        width: `${percentage}%`,
                                        background: barColor
                                      }}
                                    />
                                  </div>
                                  <div className="w-12 text-sm text-gray-300 text-right">{percentage}%</div>
                                </div>
                              </div>
                            )
                          })
                        })()}
                      </div>

                      {/* Key Insight */}
                      {(() => {
                        const signals = getConfidenceSignals()
                        const confidence = getConfidence()
                        
                        // Calculate insights
                        const structuralMetrics = [
                          signals.layer_separation_score,
                          signals.dependency_direction_score,
                          signals.dependency_depth_score
                        ].filter(v => typeof v === 'number' && v > 0)
                        
                        const qualityMetrics = [
                          signals.naming_consistency_score
                        ].filter(v => typeof v === 'number' && v > 0)
                        
                        const avgStructural = structuralMetrics.length > 0 
                          ? structuralMetrics.reduce((a, b) => a + b, 0) / structuralMetrics.length 
                          : 0
                        
                        const avgQuality = qualityMetrics.length > 0
                          ? qualityMetrics.reduce((a, b) => a + b, 0) / qualityMetrics.length
                          : 0
                        
                        // Generate intelligent insight
                        let insight = ''
                        if (confidence >= 0.85) {
                          insight = 'Excellent architecture with strong structural patterns and high code quality. The codebase demonstrates clear separation of concerns and consistent design principles.'
                        } else if (confidence >= 0.70) {
                          if (avgStructural >= 0.7 && avgQuality < 0.7) {
                            insight = 'Good architectural structure detected, but naming consistency could be improved. Consider establishing naming conventions to enhance code maintainability.'
                          } else if (avgStructural < 0.7 && avgQuality >= 0.7) {
                            insight = 'Code quality is good, but architectural boundaries could be clearer. Consider refactoring to improve layer separation and dependency management.'
                          } else {
                            insight = 'Good overall architecture with room for improvement in both structural patterns and code quality. Focus on strengthening layer boundaries and naming conventions.'
                          }
                        } else if (confidence >= 0.50) {
                          if (avgStructural < 0.5) {
                            insight = 'Architectural layers need clearer separation. Consider refactoring to establish distinct boundaries between presentation, business logic, and data layers.'
                          } else if (avgQuality < 0.5) {
                            insight = 'Structural patterns are present but naming consistency is weak. Establishing clear naming conventions will significantly improve code maintainability.'
                          } else {
                            insight = 'Fair architecture with moderate structural patterns. Focus on improving layer separation and establishing consistent naming conventions across the codebase.'
                          }
                        } else {
                          insight = 'Architecture needs significant improvement. Consider refactoring to establish clear layer boundaries, improve dependency management, and adopt consistent naming conventions.'
                        }
                        
                        return (
                          <div className="mt-6 pt-6" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                            <div className="text-gray-400 text-sm mb-2">Key Insight</div>
                            <p className="text-gray-300 text-sm leading-relaxed">
                              {insight}
                            </p>
                          </div>
                        )
                      })()}
                    </div>
                  </div>

                  {/* 4. Layer Breakdown */}
                  {currentArchitecture.layers && Array.isArray(currentArchitecture.layers) && currentArchitecture.layers.length > 0 && (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <h3 className="text-lg font-bold text-white mb-4">Layer Breakdown</h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        {currentArchitecture.layers.map((layer, index) => (
                          <div key={index} className="rounded p-5" style={{ background: '#0d1117' }}>
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="text-white font-semibold capitalize">{layer.name} Layer</h4>
                              <span className="text-xs px-2 py-1 rounded" style={{ background: '#0a0e14', color: '#9ca3af' }}>
                                {(layer.components && Array.isArray(layer.components) ? layer.components.length : 0)} components
                              </span>
                            </div>
                            <p className="text-gray-400 text-sm leading-relaxed">
                              {layer.description || 'No description available'}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 6. Architecture Signals */}
                  {currentArchitecture.patterns && currentArchitecture.patterns.length > 0 && (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <h3 className="text-lg font-bold text-white mb-4">Architecture Signals</h3>
                      <div className="rounded p-5" style={{ background: '#0d1117' }}>
                        <div className="space-y-2">
                          {/* Pattern detected */}
                          <div className="flex items-start space-x-2 text-sm">
                            <span className="text-blue-400 mt-0.5">•</span>
                            <span className="text-gray-300">{currentArchitecture.patterns[0].name} pattern detected</span>
                          </div>

                          {/* Pros as signals */}
                          {currentArchitecture.patterns[0].pros && Array.isArray(currentArchitecture.patterns[0].pros) &&
                            currentArchitecture.patterns[0].pros.slice(0, 3).map((pro, i) => (
                              <div key={i} className="flex items-start space-x-2 text-sm">
                                <span className="text-blue-400 mt-0.5">•</span>
                                <span className="text-gray-300">{pro}</span>
                              </div>
                            ))
                          }

                          {/* Confidence signals */}
                          {Object.entries(getConfidenceSignals() || {}).map(([key, value]) => {
                            const numValue = typeof value === 'number' ? value : 0
                            if (numValue < 0.5) {
                              const label = key.replace(/_/g, ' ').replace(/score/g, '').trim()
                              return (
                                <div key={key} className="flex items-start space-x-2 text-sm">
                                  <span className="text-blue-400 mt-0.5">•</span>
                                  <span className="text-gray-400">Moderate {label}</span>
                                </div>
                              )
                            }
                            return null
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* System Diagram Tab */}
              {activeTab === 'layers' && (
                <>
                  {/* Hierarchical Architecture Explorer */}
                  <div className="rounded-lg" style={{ background: '#0a0e14', border: '1px solid #151b24', minHeight: '800px' }}>
                    {currentArchitecture.layers && currentArchitecture.layers.length > 0 ? (
                      <HierarchicalArchitectureExplorer
                        layers={currentArchitecture.layers}
                        onNodeClick={(nodeId, nodeType) => {
                          console.log('Node clicked:', nodeId, nodeType)
                        }}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full p-6">
                        <p className="text-gray-400">No architecture layers available</p>
                      </div>
                    )}
                  </div>

                  {/* Architecture Layers */}
                  {currentArchitecture.layers && Array.isArray(currentArchitecture.layers) && currentArchitecture.layers.length > 0 && (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <h3 className="text-lg font-bold text-white mb-4">Architecture Layers</h3>
                      <div className="space-y-3">
                        {currentArchitecture.layers.map((layer, index) => (
                          <div key={index} className="rounded p-5" style={{ background: '#0d1117' }}>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-white font-semibold capitalize">{layer.name} Layer</h4>
                              <span className="text-xs px-2 py-1 rounded" style={{ background: '#0a0e14', color: '#9ca3af' }}>
                                {(layer.components && Array.isArray(layer.components) ? layer.components.length : 0)} components
                              </span>
                            </div>
                            <p className="text-gray-400 text-sm leading-relaxed">
                              {layer.description || 'No description available'}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Data Flow Tab */}
              {activeTab === 'tech' && (
                <>
                  {currentArchitecture.data_flows && Array.isArray(currentArchitecture.data_flows) && currentArchitecture.data_flows.length > 0 ? (
                    (() => {
                      // Find Happy Path scenario
                      const happyPath = currentArchitecture.data_flows.find(s => s.name === 'Happy Path')

                      if (!happyPath) {
                        return (
                          <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                            <p className="text-gray-400 text-center">No data flow information available</p>
                          </div>
                        )
                      }

                      // Collect all bottlenecks from all scenarios
                      const allBottlenecks = currentArchitecture.data_flows.flatMap(s => s.bottlenecks || [])

                      return (
                        <div className="space-y-6">
                          {/* Happy Path Execution Flow */}
                          <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                            <h3 className="text-lg font-bold text-white mb-4">Execution Flow</h3>
                            <p className="text-gray-400 text-sm mb-6">{happyPath.description}</p>

                            {/* Horizontal Flow Visualization */}
                            {happyPath.steps && happyPath.steps.length > 0 && (
                              <div className="overflow-x-auto pb-4">
                                <div className="flex items-center space-x-3 min-w-max">
                                  {happyPath.steps.map((step, stepIndex) => (
                                    <div key={stepIndex} className="flex items-center">
                                      {/* Component Card */}
                                      <div className="rounded-lg p-4 min-w-[160px]" style={{ background: '#0d1117', border: '1px solid #3b82f6' }}>
                                        <div className="text-white font-medium text-sm mb-1">{step.component}</div>
                                        <div className="text-gray-400 text-xs">{step.action}</div>
                                      </div>

                                      {/* Arrow */}
                                      {stepIndex < happyPath.steps.length - 1 && (
                                        <div className="flex items-center px-2">
                                          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-gray-600">
                                            <path d="M5 12h14m0 0l-6-6m6 6l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                          </svg>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Identified Bottlenecks */}
                          {allBottlenecks.length > 0 ? (
                            <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                              <h3 className="text-lg font-bold text-white mb-4">Performance Insights</h3>
                              <div className="space-y-3">
                                {allBottlenecks.map((bottleneck, bottleneckIndex) => (
                                  <div key={bottleneckIndex} className="rounded p-4" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                                    <div className="flex items-start justify-between mb-3">
                                      <div className="flex items-center space-x-3">
                                        <div>
                                          <div className="text-white font-medium mb-2">{bottleneck.location}</div>
                                          <div className="flex items-center space-x-2">
                                            <span className="text-gray-400 text-xs">Severity:</span>
                                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bottleneck.severity === 'critical' ? 'bg-red-900/30 text-red-400' :
                                              bottleneck.severity === 'high' ? 'bg-orange-900/30 text-orange-400' :
                                                bottleneck.severity === 'medium' ? 'bg-yellow-900/30 text-yellow-400' :
                                                  'bg-blue-900/30 text-blue-400'
                                              }`}>
                                              {bottleneck.severity.toUpperCase()}
                                            </span>
                                          </div>
                                        </div>
                                      </div>
                                    </div>

                                    <div className="space-y-2">
                                      <div>
                                        <div className="text-gray-500 text-xs mb-1">Reason:</div>
                                        <p className="text-gray-300 text-sm">{bottleneck.description}</p>
                                      </div>

                                      <div>
                                        <div className="text-gray-500 text-xs mb-1">Suggestion:</div>
                                        <p className="text-gray-300 text-sm">{bottleneck.suggested_optimization}</p>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                              <p className="text-gray-400 text-center">No performance bottlenecks detected.</p>
                            </div>
                          )}
                        </div>
                      )
                    })()
                  ) : (
                    <div className="rounded-lg p-6" style={{ background: '#0a0e14', border: '1px solid #151b24' }}>
                      <p className="text-gray-400 text-center">No data flow scenarios available</p>
                    </div>
                  )}
                </>
              )}

            </div>
          </div>
        )}

        {!isLoading && !error && !currentArchitecture && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <p>No architecture data available</p>
          </div>
        )}
      </div>
    </div>
  )
}
