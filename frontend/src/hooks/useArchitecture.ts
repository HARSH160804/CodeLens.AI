import { useQuery } from '@tanstack/react-query'
import { getArchitecture } from '../services/api'

export function useArchitecture(
  repoId: string | undefined,
  level: 'basic' | 'intermediate' | 'advanced' = 'intermediate'
) {
  return useQuery({
    queryKey: ['architecture', repoId, level],
    queryFn: async () => {
      if (!repoId) throw new Error('Repository ID is required')
      const response = await getArchitecture(repoId, level)
      return response.data
    },
    enabled: !!repoId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  })
}
