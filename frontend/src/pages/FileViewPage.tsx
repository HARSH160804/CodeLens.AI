import { useParams, useNavigate } from 'react-router-dom'
import { MainLayout } from '../components/layout/MainLayout'
import { Sidebar } from '../components/layout/Sidebar'
import { Breadcrumb } from '../components/explorer/Breadcrumb'
import { CodeViewer } from '../components/code/CodeViewer'
import { SplitPane } from '../components/layout/SplitPane'
import { ExplanationPanel } from '../components/code/ExplanationPanel'

export function FileViewPage() {
  const { repoId, filePath } = useParams<{ repoId: string; filePath: string }>()
  const navigate = useNavigate()

  const decodedPath = filePath ? decodeURIComponent(filePath) : ''

  const mockCode = `// File content would be fetched from API
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

  const language = decodedPath.split('.').pop() || 'typescript'

  const handleRelatedFileClick = (relatedFilePath: string) => {
    navigate(`/repo/${repoId}/file/${encodeURIComponent(relatedFilePath)}`)
  }

  return (
    <MainLayout>
      <div className="flex h-full">
        <Sidebar repoId={repoId!} />
        
        <div className="flex-1 flex flex-col">
          <Breadcrumb filePath={decodedPath} />
          
          <div className="flex-1 overflow-hidden">
            <SplitPane
              left={
                <div className="h-full">
                  <CodeViewer
                    code={mockCode}
                    language={language}
                  />
                </div>
              }
              right={
                <ExplanationPanel
                  repoId={repoId!}
                  filePath={decodedPath}
                  onRelatedFileClick={handleRelatedFileClick}
                />
              }
            />
          </div>
        </div>
      </div>
    </MainLayout>
  )
}
