import { useEffect, useRef, useState } from 'react'

interface Node {
  id: string
  label: string
  x: number
  y: number
  type?: string
  metadata?: any
}

interface Edge {
  source: string
  target: string
  label?: string
}

interface InteractiveGraphProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (node: Node) => void
  width?: number
  height?: number
}

export function InteractiveGraph({ nodes, edges, onNodeClick, width = 800, height = 600 }: InteractiveGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  // Auto-layout nodes if positions not provided
  useEffect(() => {
    if (nodes.length > 0 && nodes.every(n => !n.x && !n.y)) {
      // Simple force-directed layout simulation
      const centerX = width / 2
      const centerY = height / 2
      const radius = Math.min(width, height) / 3

      nodes.forEach((node, i) => {
        const angle = (i / nodes.length) * 2 * Math.PI
        node.x = centerX + radius * Math.cos(angle)
        node.y = centerY + radius * Math.sin(angle)
      })
    }
  }, [nodes, width, height])

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const newScale = Math.max(0.1, Math.min(3, transform.scale * delta))
    setTransform(prev => ({ ...prev, scale: newScale }))
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setTransform(prev => ({
        ...prev,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      }))
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const getNodeColor = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'presentation':
      case 'frontend':
        return '#3b82f6' // blue
      case 'api':
      case 'controller':
        return '#8b5cf6' // purple
      case 'business':
      case 'service':
        return '#10b981' // green
      case 'data':
      case 'database':
        return '#f59e0b' // amber
      case 'infrastructure':
      case 'cache':
        return '#ef4444' // red
      default:
        return '#6b7280' // gray
    }
  }

  const resetView = () => {
    setTransform({ x: 0, y: 0, scale: 1 })
  }

  return (
    <div className="relative" style={{ width: '100%', height: `${height}px` }}>
      {/* Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col space-y-2">
        <button
          onClick={resetView}
          className="px-3 py-2 rounded text-sm font-medium transition-all"
          style={{ background: '#1a1f2e', color: '#e5e7eb' }}
        >
          Reset View
        </button>
        <div className="px-3 py-2 rounded text-xs" style={{ background: '#1a1f2e', color: '#9ca3af' }}>
          Zoom: {(transform.scale * 100).toFixed(0)}%
        </div>
      </div>

      {/* Graph */}
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isDragging ? 'grabbing' : 'grab', background: '#0a0c12' }}
      >
        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
          {/* Edges */}
          {edges.map((edge, i) => {
            const sourceNode = nodes.find(n => n.id === edge.source)
            const targetNode = nodes.find(n => n.id === edge.target)
            if (!sourceNode || !targetNode) return null

            return (
              <g key={i}>
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke="#374151"
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                />
                {edge.label && (
                  <text
                    x={(sourceNode.x + targetNode.x) / 2}
                    y={(sourceNode.y + targetNode.y) / 2}
                    fill="#9ca3af"
                    fontSize="10"
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const isHovered = hoveredNode === node.id
            const nodeColor = getNodeColor(node.type)

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => onNodeClick?.(node)}
                style={{ cursor: 'pointer' }}
              >
                <circle
                  r={isHovered ? 35 : 30}
                  fill={nodeColor}
                  stroke={isHovered ? '#ffffff' : nodeColor}
                  strokeWidth={isHovered ? 3 : 0}
                  style={{ transition: 'all 0.2s' }}
                />
                <text
                  textAnchor="middle"
                  dy="0.3em"
                  fill="#ffffff"
                  fontSize="12"
                  fontWeight="500"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {node.label.length > 12 ? node.label.substring(0, 12) + '...' : node.label}
                </text>
              </g>
            )
          })}
        </g>

        {/* Arrow marker definition */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M0,0 L0,6 L9,3 z" fill="#374151" />
          </marker>
        </defs>
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 rounded p-3" style={{ background: '#1a1f2e' }}>
        <div className="text-xs font-medium text-gray-400 mb-2">Layer Types</div>
        <div className="space-y-1">
          {[
            { type: 'Frontend', color: '#3b82f6' },
            { type: 'API', color: '#8b5cf6' },
            { type: 'Business', color: '#10b981' },
            { type: 'Data', color: '#f59e0b' },
            { type: 'Infrastructure', color: '#ef4444' }
          ].map(item => (
            <div key={item.type} className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full" style={{ background: item.color }} />
              <span className="text-xs text-gray-300">{item.type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Instructions */}
      <div className="absolute top-4 left-4 rounded p-3 text-xs text-gray-400" style={{ background: '#1a1f2e' }}>
        <div>🖱️ Drag to pan</div>
        <div>🔍 Scroll to zoom</div>
        <div>👆 Click nodes for details</div>
      </div>
    </div>
  )
}
