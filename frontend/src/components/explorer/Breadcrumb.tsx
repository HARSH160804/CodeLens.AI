import { Link, useParams } from 'react-router-dom'

interface BreadcrumbProps {
  filePath?: string
}

export function Breadcrumb({ filePath }: BreadcrumbProps) {
  const { repoId } = useParams()

  if (!filePath) return null

  const parts = filePath.split('/')
  const breadcrumbs = parts.map((part, index) => ({
    name: part,
    path: parts.slice(0, index + 1).join('/'),
  }))

  return (
    <nav className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 py-2 px-4 border-b border-gray-200 dark:border-gray-700">
      <Link
        to={`/repo/${repoId}`}
        className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
      >
        Repository
      </Link>
      
      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.path} className="flex items-center space-x-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          
          {index === breadcrumbs.length - 1 ? (
            <span className="font-medium text-gray-900 dark:text-gray-100">{crumb.name}</span>
          ) : (
            <Link
              to={`/repo/${repoId}/file/${encodeURIComponent(crumb.path)}`}
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {crumb.name}
            </Link>
          )}
        </div>
      ))}
    </nav>
  )
}
