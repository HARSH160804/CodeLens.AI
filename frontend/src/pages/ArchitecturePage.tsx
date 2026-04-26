import { useParams } from 'react-router-dom'
import { useState } from 'react'
import { MainLayout } from '../components/layout/MainLayout'
import { ArchitectureView } from '../components/architecture/ArchitectureView_Enhanced'

export function ArchitecturePage() {
  const { repoId } = useParams<{ repoId: string }>()
  const [architecturePatterns, setArchitecturePatterns] = useState<string[]>([])

  const handlePatternsLoaded = (patterns: string[]) => {
    setArchitecturePatterns(patterns)
  }

  const handleLoadingChange = (_loading: boolean) => {
    // Can be used for global loading state if needed
  }

  return (
    <MainLayout architecturePatterns={architecturePatterns}>
      <div className="h-full relative">
        <ArchitectureView
          repoId={repoId!}
          onPatternsLoaded={handlePatternsLoaded}
          onLoadingChange={handleLoadingChange}
        />
      </div>
    </MainLayout>
  )
}
