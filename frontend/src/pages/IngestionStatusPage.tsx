import { useParams } from 'react-router-dom'
import { IngestionStatusDisplay } from '../components/ingestion/IngestionStatusDisplay'

export function IngestionStatusPage() {
  const { jobId } = useParams<{ jobId: string }>()

  if (!jobId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#080b15' }}>
        <div className="text-center p-8 bg-[#1a1f2e] rounded-2xl border border-gray-800">
          <h2 className="text-2xl font-bold text-white mb-2">
            Invalid Job ID
          </h2>
          <p className="text-gray-400">
            No ingestion job ID provided
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ backgroundColor: '#080b15' }}>
      <IngestionStatusDisplay jobId={jobId} />
    </div>
  )
}
