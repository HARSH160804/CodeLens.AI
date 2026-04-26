import { useState, useCallback, useEffect } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  useReactFlow,
  ReactFlowProvider,
  Handle,
} from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'

// Types for our hierarchical data
interface Layer {
  name: string
  description?: string
  components: Component[]
}

interface Component {
  name: string
  type: string
  file_path: string
  dependencies?: string[]
}

interface HierarchicalArchitectureExplorerProps {
  layers: Layer[]
  onNodeClick?: (nodeId: string, nodeType: string) => void
}

// Layer color mapping
const LAYER_COLORS: Record<string, string> = {
  presentation: '#3b82f6', // Blue
  frontend: '#3b82f6',
  api: '#7c3aed', // Purple
  business: '#10b981', // Green
  service: '#10b981',
  data: '#f59e0b', // Orange
  database: '#f59e0b',
  infrastructure: '#ef4444', // Red
  uncategorized: '#64748b', // Slate gray
}

// Get color for layer
const getLayerColor = (layerName: string): string => {
  const normalized = layerName.toLowerCase()
  return LAYER_COLORS[normalized] || LAYER_COLORS.uncategorized
}

// Custom node component for system view
const SystemNode = ({ data }: any) => {
  return (
    <div
      className="px-8 py-6 rounded-xl shadow-lg cursor-pointer transition-all hover:shadow-xl"
      style={{
        background: '#1a1f2e',
        border: `3px solid ${data.color}`,
        minWidth: '200px',
        minHeight: '90px',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: data.color }} />
      <div className="flex items-center justify-between mb-2">
        <div className="text-white font-semibold text-base">{data.label}</div>
        {data.isExpanded ? (
          <span className="text-gray-400 text-sm">▼</span>
        ) : (
          <span className="text-gray-400 text-sm">▶</span>
        )}
      </div>
      <div className="text-gray-400 text-sm">{data.componentCount} components</div>
      <Handle type="source" position={Position.Bottom} style={{ background: data.color }} />
    </div>
  )
}

// Custom node component for layer/component view
const DetailNode = ({ data }: any) => {
  const hasChildren = data.subtitle && !data.subtitle.includes('file')
  return (
    <div
      className="px-5 py-4 rounded-lg shadow cursor-pointer transition-all hover:shadow-md"
      style={{
        background: '#1a1f2e',
        border: `2px solid ${data.color}`,
        minWidth: '180px',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: data.color }} />
      <div className="flex items-center justify-between mb-1">
        <div className="text-white font-medium text-sm">{data.label}</div>
        {hasChildren && (
          data.isExpanded ? (
            <span className="text-gray-400 text-xs">▼</span>
          ) : (
            <span className="text-gray-400 text-xs">▶</span>
          )
        )}
      </div>
      {data.subtitle && (
        <div className="text-gray-500 text-xs">{data.subtitle}</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: data.color }} />
    </div>
  )
}

// Node types
const nodeTypes = {
  system: SystemNode,
  detail: DetailNode,
}

// Dagre layout function
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction, nodesep: 120, ranksep: 150 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 90 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 100,
        y: nodeWithPosition.y - 45,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

function HierarchicalArchitectureExplorerInner({
  layers,
  onNodeClick,
}: HierarchicalArchitectureExplorerProps) {
  // Track which nodes are expanded
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>(['System'])

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  
  const { fitView } = useReactFlow()

  // Debug logging
  useEffect(() => {
    console.log('HierarchicalArchitectureExplorer - layers:', layers)
    console.log('HierarchicalArchitectureExplorer - layers length:', layers?.length)
    console.log('Expanded nodes:', Array.from(expandedNodes))
  }, [layers, expandedNodes])

  // Generate nodes and edges based on expanded state
  const generateGraphData = useCallback(() => {
    let newNodes: Node[] = []
    let newEdges: Edge[] = []

    // Safety check
    if (!layers || layers.length === 0) {
      console.warn('No layers data available')
      return { nodes: [], edges: [] }
    }

    // Always show all layer nodes
    layers.slice(0, 10).forEach((layer, layerIndex) => {
      const layerId = `layer-${layerIndex}`
      newNodes.push({
        id: layerId,
        type: 'system',
        data: {
          label: layer.name.charAt(0).toUpperCase() + layer.name.slice(1),
          componentCount: layer.components?.length || 0,
          color: getLayerColor(layer.name),
          layerIndex: layerIndex,
          isExpanded: expandedNodes.has(layerId),
        },
        position: { x: 0, y: 0 },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      })

      // If this layer is expanded, show its components
      if (expandedNodes.has(layerId) && layer.components && layer.components.length > 0) {
        layer.components.slice(0, 20).forEach((component, componentIndex) => {
          const componentId = `component-${layerIndex}-${componentIndex}`
          newNodes.push({
            id: componentId,
            type: 'detail',
            data: {
              label: component.name,
              subtitle: component.type,
              color: getLayerColor(layer.name),
              componentIndex: componentIndex,
              layerIndex: layerIndex,
              isExpanded: expandedNodes.has(componentId),
            },
            position: { x: 0, y: 0 },
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
          })

          // Add edge from layer to component
          newEdges.push({
            id: `edge-${layerId}-${componentId}`,
            source: layerId,
            target: componentId,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#6b7280', strokeWidth: 2, opacity: 0.7 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#6b7280',
            },
          })

          // If this component is expanded, show its file
          if (expandedNodes.has(componentId)) {
            const fileId = `file-${layerIndex}-${componentIndex}`
            newNodes.push({
              id: fileId,
              type: 'detail',
              data: {
                label: component.file_path.split('/').pop() || component.name,
                subtitle: `${component.type} file`,
                color: '#6b7280', // Gray for files
                layerIndex: layerIndex,
                componentIndex: componentIndex,
              },
              position: { x: 0, y: 0 },
              sourcePosition: Position.Bottom,
              targetPosition: Position.Top,
            })

            // Add edge from component to file
            newEdges.push({
              id: `edge-${componentId}-${fileId}`,
              source: componentId,
              target: fileId,
              type: 'smoothstep',
              animated: false,
              style: { stroke: '#6b7280', strokeWidth: 2, opacity: 0.7 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#6b7280',
              },
            })
          }
        })
      }
    })

    // Add edges between layers (sequential flow) - only for non-expanded layers
    for (let i = 0; i < Math.min(layers.length, 10) - 1; i++) {
      const currentLayerId = `layer-${i}`
      const nextLayerId = `layer-${i + 1}`
      
      // Only add layer-to-layer edges if neither is expanded
      if (!expandedNodes.has(currentLayerId) && !expandedNodes.has(nextLayerId)) {
        newEdges.push({
          id: `edge-layer-${i}`,
          source: currentLayerId,
          target: nextLayerId,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#6b7280', strokeWidth: 2, opacity: 0.7 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6b7280',
          },
        })
      }
    }

    // Apply dagre layout only if we have nodes
    if (newNodes.length === 0) {
      console.warn('No nodes generated')
      return { nodes: [], edges: [] }
    }

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges,
      'TB'
    )

    return { nodes: layoutedNodes, edges: layoutedEdges }
  }, [expandedNodes, layers])

  // Update graph when expansion state changes
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = generateGraphData()
    console.log('Generated nodes:', newNodes.length)
    console.log('Generated edges:', newEdges.length)
    console.log('Edge details:', newEdges)
    setNodes(newNodes)
    setEdges(newEdges)
  }, [generateGraphData, setNodes, setEdges])

  // Handle node click - toggle expansion
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const nodeId = node.id
      
      setExpandedNodes((prev) => {
        const newExpanded = new Set(prev)
        if (newExpanded.has(nodeId)) {
          // Collapse: remove this node and all its children
          newExpanded.delete(nodeId)
          
          // Remove all child nodes
          if (nodeId.startsWith('layer-')) {
            // Remove all components of this layer
            const layerIndex = node.data.layerIndex
            for (let i = 0; i < 20; i++) {
              newExpanded.delete(`component-${layerIndex}-${i}`)
              newExpanded.delete(`file-${layerIndex}-${i}`)
            }
          } else if (nodeId.startsWith('component-')) {
            // Remove the file of this component
            const parts = nodeId.split('-')
            const layerIndex = parts[1]
            const componentIndex = parts[2]
            newExpanded.delete(`file-${layerIndex}-${componentIndex}`)
          }
        } else {
          // Expand: add this node
          newExpanded.add(nodeId)
        }
        return newExpanded
      })
      
      // Update breadcrumbs
      if (nodeId.startsWith('layer-')) {
        const layerName = node.data.label
        if (!expandedNodes.has(nodeId)) {
          setBreadcrumbs(['System', layerName])
        } else {
          setBreadcrumbs(['System'])
        }
      } else if (nodeId.startsWith('component-')) {
        const componentName = node.data.label
        const layerIndex = node.data.layerIndex
        const layerName = layers[layerIndex]?.name || 'Layer'
        if (!expandedNodes.has(nodeId)) {
          setBreadcrumbs(['System', layerName.charAt(0).toUpperCase() + layerName.slice(1), componentName])
        } else {
          setBreadcrumbs(['System', layerName.charAt(0).toUpperCase() + layerName.slice(1)])
        }
      }
      
      onNodeClick?.(nodeId, node.type || 'unknown')
    },
    [expandedNodes, onNodeClick, layers]
  )

  // Handle breadcrumb navigation
  const handleBreadcrumbClick = useCallback((index: number) => {
    if (index === 0) {
      // Back to system view - collapse all
      setExpandedNodes(new Set())
      setBreadcrumbs(['System'])
    } else if (index === 1) {
      // Back to layer view - keep only layer expanded
      setExpandedNodes((prev) => {
        const newExpanded = new Set<string>()
        // Find the expanded layer
        for (const nodeId of prev) {
          if (nodeId.startsWith('layer-')) {
            newExpanded.add(nodeId)
            break
          }
        }
        return newExpanded
      })
      setBreadcrumbs((prev) => prev.slice(0, 2))
    }
  }, [])

  // Reset view
  const handleResetView = useCallback(() => {
    setExpandedNodes(new Set())
    setBreadcrumbs(['System'])
    // Fit view after state updates
    setTimeout(() => {
      fitView({ padding: 0.2, duration: 300 })
    }, 50)
  }, [fitView])

  return (
    <div className="relative w-full" style={{ height: '800px' }}>
      {/* Breadcrumb Navigation */}
      <div
        className="absolute top-4 left-4 z-10 flex items-center space-x-2 px-4 py-2 rounded-full shadow-lg"
        style={{ background: '#1a1f2e', border: '1px solid #374151' }}
      >
        {breadcrumbs.map((crumb, index) => (
          <div key={index} className="flex items-center">
            {index > 0 && <span className="text-gray-500 mx-2">›</span>}
            <button
              onClick={() => handleBreadcrumbClick(index)}
              className={`text-xs font-medium transition-colors ${
                index === breadcrumbs.length - 1
                  ? 'text-white cursor-default'
                  : 'text-blue-400 hover:text-blue-300 cursor-pointer'
              }`}
              disabled={index === breadcrumbs.length - 1}
            >
              {crumb}
            </button>
          </div>
        ))}
      </div>

      {/* Graph Controls */}
      <button
        onClick={handleResetView}
        className="absolute top-4 right-4 z-10 px-4 py-2 text-xs font-medium text-white rounded-full transition-all backdrop-blur-md"
        style={{ 
          background: 'rgba(59, 130, 246, 0.2)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)'
        }}
        title="Reset to System View"
      >
        Reset View
      </button>

      {/* React Flow */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        style={{ background: '#0a0c12' }}
      >
        <Background color="#1a1f2e" gap={16} />
        <Controls
          style={{
            background: '#1a1f2e',
            border: '1px solid #374151',
            borderRadius: '8px',
          }}
        />
      </ReactFlow>

      {/* Instructions Overlay */}
      {expandedNodes.size === 0 && (
        <div
          className="absolute bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-lg shadow-lg"
          style={{ background: '#1a1f2e', border: '1px solid #374151' }}
        >
          <p className="text-xs text-gray-400">
            Click on a layer to expand and see its components
          </p>
        </div>
      )}
    </div>
  )
}

// Wrapper component with ReactFlowProvider
export function HierarchicalArchitectureExplorer(props: HierarchicalArchitectureExplorerProps) {
  return (
    <ReactFlowProvider>
      <HierarchicalArchitectureExplorerInner {...props} />
    </ReactFlowProvider>
  )
}

