import { useParams, Link } from 'react-router-dom'
import { ChatInterface } from '../components/chat/ChatInterface'

export function ChatPage() {
  const { repoId } = useParams<{ repoId: string }>()

  if (!repoId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#0a0c12' }}>
        <div className="text-center">
          <p className="text-gray-400 text-lg">Repository not found</p>
          <p className="text-gray-500 text-sm mt-2">Please select a repository from the dashboard</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#0a0c12' }}>
      {/* Custom Navbar with Glassmorphism */}
      <header className="sticky top-0 z-50 backdrop-blur-md" style={{ 
        background: 'rgba(10, 12, 18, 0.8)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div className="px-6 py-3 flex items-center justify-between">
          {/* Left Section */}
          <div className="flex items-center space-x-3">
            {/* BloomWay AI Logo */}
            <Link to={`/repo/${repoId}`} className="flex items-center space-x-2">
              <img 
                src="/logo_bloomway.png" 
                alt="CodeLens Logo"
                className="w-8 h-8 rounded-xl object-contain"
              />
              <span className="text-[14px] font-bold tracking-wide">
                <span className="text-gray-200">CODELENS</span>
                <span className="text-gray-500">·</span>
                <span className="text-blue-400">AI</span>
              </span>
            </Link>
            
            {/* Vertical Separator */}
            <div className="h-5 w-px" style={{ background: 'rgba(255, 255, 255, 0.1)' }}></div>
            
            {/* AI Chat Capsule */}
            <div className="px-3 py-1 rounded-full text-xs font-medium" style={{ 
              background: 'rgba(59, 130, 246, 0.15)',
              color: '#60a5fa',
              border: '1px solid rgba(59, 130, 246, 0.3)'
            }}>
              AI Chat
            </div>
          </div>

          {/* Right Section - Navigation */}
          <div className="flex items-center space-x-2">
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
          </div>
        </div>
      </header>

      {/* Main Chat Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-4xl">
          <ChatInterface repoId={repoId} />
        </div>
      </div>
    </div>
  )
}
