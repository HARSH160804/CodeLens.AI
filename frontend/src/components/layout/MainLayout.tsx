import { ReactNode } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { useApp } from '../../context/AppContext'

interface MainLayoutProps {
  children: ReactNode
  showSidebar?: boolean
  architecturePatterns?: string[]
  repoId?: string
}

export function MainLayout({ children, showSidebar = false, architecturePatterns, repoId: propRepoId }: MainLayoutProps) {
  const { darkMode } = useApp()
  const params = useParams<{ repoId: string }>()
  const location = useLocation()
  const repoId = propRepoId || params.repoId
  
  // Check if we're on the architecture page
  const isArchitecturePage = location.pathname.includes('/architecture')

  return (
    <div className={`min-h-screen ${darkMode ? 'dark' : ''}`}>
      <div className="min-h-screen text-gray-100" style={{ background: '#0a0e14' }}>
        {/* Header */}
        <header className="sticky top-0 z-50" style={{ 
          background: '#0a0e14',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
        }}>
          <div className="px-6 py-3 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Link to="/" className="flex items-center space-x-2">
                {/* BloomWay AI Logo */}
                <img 
                  src="/logo_bloomway.png" 
                  alt="CodeLens Logo"
                  className="w-8 h-8 rounded-xl object-contain"
                />
                {/* CODELENS·AI Text */}
                <span className="text-[14px] font-bold tracking-wide">
                  <span className="text-gray-200">CODELENS</span>
                  <span className="text-gray-500">·</span>
                  <span className="text-blue-400">AI</span>
                </span>
              </Link>
              {/* Vertical Separator Line */}
              <div className="h-5 w-px" style={{ background: 'rgba(255, 255, 255, 0.1)' }}></div>
              {architecturePatterns && architecturePatterns.length > 0 && (
                <div className="flex items-center space-x-2">
                  {architecturePatterns.map((pattern, index) => (
                    <div
                      key={index}
                      className="px-2.5 py-0.5 rounded-full text-xs font-medium"
                      style={{ 
                        background: 'rgba(55, 65, 81, 0.8)',
                        color: '#d1d5db'
                      }}
                    >
                      {pattern}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {repoId ? (
                <Link 
                  to={`/repo/${repoId}`}
                  className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
                  style={{ fontSize: '12px' }}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                  <span>Dashboard</span>
                </Link>
              ) : (
                <Link 
                  to="/" 
                  className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
                  style={{ fontSize: '12px' }}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  <span>Home</span>
                </Link>
              )}
              {repoId && (
                <>
                  {!isArchitecturePage && (
                    <Link 
                      to={`/repo/${repoId}/architecture`}
                      className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
                      style={{ fontSize: '12px' }}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      <span>Architecture</span>
                    </Link>
                  )}
                  <Link 
                    to={`/repo/${repoId}/chat`}
                    className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition-colors font-medium flex items-center space-x-1.5"
                    style={{ fontSize: '12px' }}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span>Chat</span>
                  </Link>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex h-[calc(100vh-57px)]">
          {showSidebar && (
            <aside className="w-64 overflow-y-auto" style={{ 
              background: '#0a0e14',
              borderRight: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              {/* Sidebar content will be injected here */}
            </aside>
          )}
          <main className="flex-1 overflow-hidden">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}
