import { useRepo } from '../../hooks/useRepo'
import { FileNode } from './FileNode'

interface FileTreeProps {
  repoId: string
  searchQuery: string
  onFileSelect?: (filePath: string) => void
}

interface FileItem {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileItem[]
}

export function FileTree({ repoId, searchQuery, onFileSelect }: FileTreeProps) {
  const { data: repo, isLoading: loading, error } = useRepo(repoId)

  const buildFileTree = (filePaths: string[]): FileItem[] => {
    const root: FileItem = { name: '', path: '', type: 'directory', children: [] }

    filePaths.forEach(filePath => {
      const parts = filePath.split('/')
      let currentNode = root

      parts.forEach((part, index) => {
        const isFile = index === parts.length - 1
        const childPath = parts.slice(0, index + 1).join('/')

        // Look for existing child with this name
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

    // Sort: directories first, then files, alphabetically
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

  const files = repo ? buildFileTree(repo.file_paths || []) : []

  const filterFiles = (items: FileItem[], query: string): FileItem[] => {
    if (!query) return items

    return items.reduce((acc: FileItem[], item) => {
      if (item.type === 'file' && item.name.toLowerCase().includes(query.toLowerCase())) {
        acc.push(item)
      } else if (item.type === 'directory' && item.children) {
        const filteredChildren = filterFiles(item.children, query)
        if (filteredChildren.length > 0) {
          acc.push({ ...item, children: filteredChildren })
        }
      }
      return acc
    }, [])
  }

  const filteredFiles = filterFiles(files, searchQuery)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-600 dark:text-red-400">
        Failed to load files
      </div>
    )
  }

  if (filteredFiles.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        {searchQuery ? 'No files found' : 'No files in repository'}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {filteredFiles.map((item) => (
        <FileNode key={item.path} item={item} level={0} onFileSelect={onFileSelect} />
      ))}
    </div>
  )
}
