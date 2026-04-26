import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod'

console.log('API_BASE_URL:', API_BASE_URL)

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds for ingestion
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url, config.baseURL)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor with retry logic
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as any

    // Initialize retry count
    if (!config._retryCount) {
      config._retryCount = 0
    }

    // Retry on 429 (rate limit) or 5xx errors, but NOT for ingestion POST (would cause duplicates)
    const isIngest = config.method === 'post' && config.url?.includes('/ingest')
    const shouldRetry =
      !isIngest && (
        error.response?.status === 429 ||
        (error.response?.status && error.response.status >= 500)
      )

    if (shouldRetry && config._retryCount < 3) {
      config._retryCount += 1

      // Exponential backoff: 1s, 2s, 4s
      const delay = Math.pow(2, config._retryCount - 1) * 1000

      await new Promise(resolve => setTimeout(resolve, delay))

      return apiClient(config)
    }

    return Promise.reject(error)
  }
)

// Type definitions
export interface IngestRequest {
  source_type: 'github' | 'zip'
  source: string
  auth_token?: string
  file?: File
}

export interface IngestResponse {
  repo_id: string
  session_id: string
  source: string
  status: 'completed' | 'processing' | 'failed'
  file_count: number
  chunk_count: number
  file_paths?: string[]
  tech_stack: {
    languages: string[]
    frameworks: string[]
    libraries: string[]
  }
}

export interface AsyncIngestResponse {
  job_id: string
  status: 'processing'
  source: string
  source_type: string
  created_at: string
  message: string
}

export interface RepoStatusResponse {
  repo_id: string
  status: 'completed' | 'processing' | 'failed'
  file_count: number
  chunk_count: number
  tech_stack: {
    languages: string[]
    frameworks: string[]
    libraries: string[]
  }
  file_paths: string[]
  source: string
  created_at: string
  updated_at: string
}

export interface ArchitectureResponse {
  schema_version: string
  repo_id: string
  generated_at: string
  execution_duration_ms: number
  analysis_level: string
  
  // New confidence scoring
  confidence: number
  confidence_signals: {
    layer_separation_score: number
    framework_detection_score: number
    database_integration_score: number
    dependency_direction_score: number
    dependency_depth_score: number
    naming_consistency_score: number
  }
  
  // Statistics
  statistics: {
    total_files: number
    total_lines: number
    primary_language: string
    language_breakdown: Record<string, number>
    folder_depth: number
    largest_file: {
      path: string
      lines: number
    }
  }
  
  // Patterns
  patterns: Array<{
    name: string
    confidence: number
    evidence_files: string[]
    description: string
    pros: string[]
    cons: string[]
    alternatives: string[]
  }>
  
  // Layers
  layers: Array<{
    name: string
    description: string
    components: Array<{
      name: string
      type: string
      file_path: string
      line_count: number
      complexity_score: number
      dependencies: string[]
      health_score: number
      responsibilities: string[]
    }>
    technologies: string[]
    entry_points: string[]
    connections: Array<{
      from_layer: string
      to_layer: string
      connection_type: string
      file_paths: string[]
    }>
  }>
  
  // Tech Stack
  tech_stack: Array<{
    name: string
    category: string
    icon: string
    version: string
    latest_version: string
    is_deprecated: boolean
    deprecation_warning: string | null
    license: string
    vulnerabilities: Array<{
      cve_id: string
      severity: string
      description: string
      fixed_version: string
      cvss_score: number
    }>
  }>
  
  // Data Flows
  data_flows: Array<{
    name: string
    description: string
    steps: Array<{
      step_number: number
      component: string
      action: string
      next_steps: string[]
      is_conditional: boolean
    }>
    bottlenecks: Array<{
      location: string
      severity: string
      description: string
      suggested_optimization: string
    }>
  }>
  
  // Dependencies
  dependencies: {
    dependency_tree: {
      root: any
      total_dependencies: number
      max_depth: number
    }
    circular_dependencies: Array<{
      cycle_path: string[]
      severity: string
      description: string
    }>
    outdated_packages: Array<{
      package_name: string
      current_version: string
      latest_version: string
      versions_behind: number
    }>
    vulnerabilities: any[]
    license_issues: any[]
  }
  
  // Metrics
  metrics: {
    health_score: number
    complexity_metrics: {
      average_cyclomatic: number
      average_cognitive: number
      max_cyclomatic: number
      max_cognitive: number
      high_complexity_files: string[]
    }
    hotspots: Array<{
      file_path: string
      type: string
      complexity_score: number
      change_frequency: number
      severity: string
      recommendation: string
    }>
    technical_debt: {
      code_duplication_percentage: number
      duplicated_blocks: any[]
      test_coverage_gaps: string[]
      estimated_debt_hours: number
    }
  }
  
  // Recommendations
  recommendations: Array<{
    id: string
    category: string
    title: string
    description: string
    priority: string
    estimated_effort: string
    expected_impact: string
    file_paths: string[]
    code_locations: Array<{
      file_path: string
      line_start: number
      line_end: number
      snippet: string
    }>
    rationale: string
  }>
  
  // Visualizations
  visualizations: Record<string, any>
  
  // Legacy architecture field (backward compatibility)
  architecture: {
    overview: string
    architectureStyle: string
    components: Array<{
      name: string
      type: string
      file_path: string
      role: string
    }>
    dataFlowSteps: string[]
    mermaidDiagram: string
    confidence: number
  }
  
  // Mermaid diagram
  diagram: string
  
  // Errors/warnings (optional)
  errors?: Record<string, string>
  warnings?: string[]
}


export interface FileContentResponse {
  repo_id: string
  file_path: string
  content: string
  language: string
  lines: number
}

export interface RepoMetadataResponse {
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

export interface FileExplanationResponse {
  repo_id: string
  file_path: string
  explanation: {
    purpose: string
    businessContext?: string
    executionFlow?: string[]
    key_functions?: Array<{
      name: string
      description: string
      line: number
    }>
    keyFunctions?: Array<{
      name: string
      description: string
      line: number
    }>
    patterns?: string[]
    designPatterns?: string[]
    dependencies?: string[]
    complexity?: {
      lines?: number
      functions?: number
      score?: number
      reasoning?: string
    }
    improvementSuggestions?: string[]
    securityRisks?: string[]
    impactAssessment?: string
    confidence?: number
  }
  related_files: string[]
  level: 'beginner' | 'intermediate' | 'advanced'
  generated_at: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  scope?: {
    type: 'all' | 'file' | 'directory'
    path?: string
  }
  history?: Array<{
    role: 'user' | 'assistant'
    content: string
  }>
}

export interface ChatResponse {
  repo_id: string
  response: string
  citations: Array<{
    file: string
    line?: number
    snippet: string
  }>
  suggested_questions: string[]
  confidence: 'high' | 'medium' | 'low'
  session_id: string
}

export interface ExportRequest {
  format: 'markdown' | 'pdf'
}

export interface ExportResponse {
  session_id: string
  download_url: string
  format: string
  expires_at: string
}

// Documentation Generation Types
export interface DocumentationStatusResponse {
  state: 'not_generated' | 'generating' | 'generated' | 'failed'
  created_at: string | null
  error_message: string | null
}

export interface DocumentationGenerateResponse {
  status: 'generating' | 'generated'
  message: string
}

// API functions
export const ingestRepository = (data: IngestRequest): Promise<AxiosResponse<IngestResponse>> => {
  console.log('ingestRepository called with:', { source_type: data.source_type, has_file: !!data.file })

  if (data.source_type === 'zip' && data.file) {
    const formData = new FormData()
    formData.append('source_type', 'zip')
    formData.append('file', data.file)
    if (data.auth_token) {
      formData.append('auth_token', data.auth_token)
    }

    console.log('Making ZIP upload request to:', `${API_BASE_URL}/repos/ingest`)

    // Use a separate axios instance for FormData to avoid Content-Type conflicts
    return axios.post(`${API_BASE_URL}/repos/ingest`, formData, {
      timeout: 60000,
      headers: {
        // Let browser set Content-Type with boundary for multipart/form-data
      },
    })
  }

  if (data.source_type === 'github') {
    console.log('Making GitHub URL request')
    return apiClient.post('/repos/ingest', {
      source_type: 'github',
      source: data.source,
      auth_token: data.auth_token,
    })
  }

  throw new Error('Invalid source_type')
}

export const ingestRepositoryAsync = (data: IngestRequest): Promise<AxiosResponse<AsyncIngestResponse>> => {
  console.log('ingestRepositoryAsync called with:', { source_type: data.source_type, has_file: !!data.file })

  if (data.source_type === 'zip' && data.file) {
    const formData = new FormData()
    formData.append('source_type', 'zip')
    formData.append('file', data.file)
    if (data.auth_token) {
      formData.append('auth_token', data.auth_token)
    }

    console.log('Making async ZIP upload request to:', `${API_BASE_URL}/repos/ingest`)

    return axios.post(`${API_BASE_URL}/repos/ingest`, formData, {
      timeout: 10000, // Async endpoint should respond quickly
      headers: {
        // Let browser set Content-Type with boundary for multipart/form-data
      },
    })
  }

  if (data.source_type === 'github') {
    console.log('Making async GitHub URL request')
    return apiClient.post('/repos/ingest', {
      source_type: 'github',
      source: data.source,
      auth_token: data.auth_token,
    }, {
      timeout: 10000 // Async endpoint should respond quickly
    })
  }

  throw new Error('Invalid source_type')
}

export const getRepoStatus = (
  repositoryId: string
): Promise<AxiosResponse<RepoStatusResponse>> =>
  apiClient.get(`/repos/${repositoryId}/status`)

export const getArchitecture = (
  repositoryId: string,
  level?: 'basic' | 'intermediate' | 'advanced'
): Promise<AxiosResponse<ArchitectureResponse>> =>
  apiClient.get(`/repos/${repositoryId}/architecture`, {
    params: level ? { level } : undefined
  })

export const getFileContent = (
  repositoryId: string,
  filePath: string
): Promise<AxiosResponse<FileContentResponse>> =>
  apiClient.get(`/repos/${repositoryId}/file`, {
    params: { path: filePath }
  })

export const getRepoMetadata = (
  repositoryId: string
): Promise<AxiosResponse<RepoMetadataResponse>> =>
  apiClient.get(`/repos/${repositoryId}/metadata`)

export const explainFile = (
  repositoryId: string,
  filePath: string,
  level?: 'beginner' | 'intermediate' | 'advanced'
): Promise<AxiosResponse<FileExplanationResponse>> =>
  apiClient.get(`/repos/${repositoryId}/files/${encodeURIComponent(filePath)}`, {
    params: level ? { level } : undefined
  })

export const chat = (
  repositoryId: string,
  data: ChatRequest
): Promise<AxiosResponse<ChatResponse>> =>
  apiClient.post(`/repos/${repositoryId}/chat`, data)

export const exportDocumentation = (
  sessionId: string,
  data: ExportRequest
): Promise<AxiosResponse<ExportResponse>> =>
  apiClient.post(`/sessions/${sessionId}/export`, data)

// Documentation Generation API functions
export const getDocumentationStatus = (
  repositoryId: string
): Promise<AxiosResponse<DocumentationStatusResponse>> =>
  apiClient.get(`/repos/${repositoryId}/docs/status`)

export const generateDocumentation = (
  repositoryId: string
): Promise<AxiosResponse<DocumentationGenerateResponse>> =>
  apiClient.post(`/repos/${repositoryId}/docs/generate`)

export const getDocumentationExportUrl = (
  repositoryId: string,
  format: 'md' | 'pdf'
): string =>
  `${API_BASE_URL}/repos/${repositoryId}/docs/export?format=${format}`

// Legacy api object for backward compatibility
export const api = {
  ingestRepository,
  ingestRepositoryAsync,
  getRepoStatus,
  getFileContent,
  getRepoMetadata,
  getArchitecture,
  explainFile,
  chat,
  exportDocumentation,
  // Documentation generation
  getDocumentationStatus,
  generateDocumentation,
  getDocumentationExportUrl,
}
