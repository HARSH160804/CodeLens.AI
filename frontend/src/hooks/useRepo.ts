import { useQuery } from '@tanstack/react-query'
import { apiClient, IngestResponse } from '../services/api'

export function useRepo(repoId: string | undefined) {
  return useQuery({
    queryKey: ['repo', repoId],
    queryFn: async () => {
      if (!repoId) throw new Error('Repository ID is required')
      const response = await apiClient.get<IngestResponse>(`/repos/${repoId}/status`)
      return response.data
    },
    enabled: !!repoId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  })
}
