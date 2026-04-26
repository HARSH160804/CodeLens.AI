import { useQuery, useQueryClient } from '@tanstack/react-query'
import { explainFile } from '../services/api'

export function useFileExplanation(
  repoId: string | undefined,
  filePath: string | undefined,
  level: 'beginner' | 'intermediate' | 'advanced' = 'intermediate'
) {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['fileExplanation', repoId, filePath, level],
    queryFn: async () => {
      if (!repoId || !filePath) throw new Error('Repository ID and file path are required')
      const response = await explainFile(repoId, filePath, level)
      return response.data
    },
    enabled: !!repoId && !!filePath,
    staleTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['fileExplanation', repoId, filePath] })
  }

  return {
    ...query,
    invalidate,
  }
}
