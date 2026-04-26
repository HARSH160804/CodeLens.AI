import { useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { useApp } from '../../context/AppContext'

interface FileItem {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileItem[]
}

interface FileNodeProps {
  item: FileItem
  level: number
  onFileSelect?: (filePath: string) => void
}

export function FileNode({ item, level, onFileSelect }: FileNodeProps) {
  const [isExpanded, setIsExpanded] = useState(level === 0)
  const navigate = useNavigate()
  const location = useLocation()
  const { repoId } = useParams()
  const { setCurrentFile } = useApp()

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    
    const iconMap: Record<string, string> = {
      ts: '📘', tsx: '📘', js: '📙', jsx: '📙',
      py: '🐍', java: '☕', go: '🔷',
      json: '📋', md: '📝', txt: '📄',
      css: '🎨', scss: '🎨', html: '🌐',
    }

    return iconMap[ext || ''] || '📄'
  }

  const handleClick = () => {
    if (item.type === 'directory') {
      setIsExpanded(!isExpanded)
    } else {
      setCurrentFile(item.path)
      
      // If we're on the RepoExplorerPage and have onFileSelect callback, use it
      // Otherwise, navigate to FileViewPage
      if (onFileSelect && location.pathname === `/repo/${repoId}`) {
        onFileSelect(item.path)
      } else {
        navigate(`/repo/${repoId}/file/${encodeURIComponent(item.path)}`)
      }
    }
  }

  return (
    <div>
      <div
        onClick={handleClick}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        className="flex items-center space-x-2 py-1.5 px-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer transition-colors"
      >
        {item.type === 'directory' && (
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        )}
        
        <span className="text-lg">{item.type === 'directory' ? '📁' : getFileIcon(item.name)}</span>
        
        <span className="text-sm truncate">{item.name}</span>
      </div>

      {item.type === 'directory' && isExpanded && item.children && (
        <div>
          {item.children.map((child) => (
            <FileNode key={child.path} item={child} level={level + 1} onFileSelect={onFileSelect} />
          ))}
        </div>
      )}
    </div>
  )
}
