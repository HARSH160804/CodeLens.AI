import { useState, useRef, useEffect, ReactNode } from 'react'

interface SplitPaneProps {
  left: ReactNode
  right: ReactNode
  defaultSize?: number
  minSize?: number
  maxSize?: number
}

export function SplitPane({ 
  left, 
  right, 
  defaultSize = 50, 
  minSize = 20, 
  maxSize = 80 
}: SplitPaneProps) {
  const [leftWidth, setLeftWidth] = useState(defaultSize)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return

      const container = containerRef.current
      const containerRect = container.getBoundingClientRect()
      const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100

      if (newWidth >= minSize && newWidth <= maxSize) {
        setLeftWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, minSize, maxSize])

  return (
    <div ref={containerRef} className="flex h-full w-full relative">
      {/* Left Pane */}
      <div style={{ width: `${leftWidth}%` }} className="overflow-auto">
        {left}
      </div>

      {/* Resizer */}
      <div
        className={`w-1 bg-gray-300 dark:bg-gray-600 hover:bg-blue-500 cursor-col-resize transition-colors ${
          isDragging ? 'bg-blue-500' : ''
        }`}
        onMouseDown={() => setIsDragging(true)}
      />

      {/* Right Pane */}
      <div style={{ width: `${100 - leftWidth}%` }} className="overflow-auto">
        {right}
      </div>
    </div>
  )
}
