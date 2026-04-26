# Hierarchical Expansion Implementation

## Overview
Modified the System Diagram to support hierarchical drill-down expansion instead of view replacement. Parent nodes now remain visible when drilling down into children.

## Changes Made

### 1. State Management
**Before**: Used `zoomLevel`, `selectedLayer`, `selectedComponent` to track current view
**After**: Use `expandedNodes` Set to track which nodes are expanded

```typescript
// Old approach
const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('system')
const [selectedLayer, setSelectedLayer] = useState<string | null>(null)
const [selectedComponent, setSelectedComponent] = useState<string | null>(null)

// New approach
const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
```

### 2. Graph Generation Logic
**Before**: Generated completely different node sets based on zoom level
**After**: Always show all layers, then conditionally add children based on expansion state

**Key Changes**:
- All layer nodes are always visible
- When a layer is expanded, its components appear below it
- When a component is expanded, its file appears below it
- Parent-child relationships are maintained with edges
- Layer-to-layer edges only show when layers are not expanded

### 3. Node Click Behavior
**Before**: Clicking a node changed the view and replaced all nodes
**After**: Clicking a node toggles its expansion state

**Expansion Logic**:
- Click collapsed node → Expand and show children
- Click expanded node → Collapse and hide all descendants
- Collapsing a layer removes all its components and files
- Collapsing a component removes its file

### 4. Visual Indicators
Added expand/collapse icons to nodes:
- **▶** (right arrow) = Node is collapsed (has children)
- **▼** (down arrow) = Node is expanded (showing children)

### 5. Node Hierarchy
```
Layer (always visible)
  ↓
Component (visible when layer expanded)
  ↓
File (visible when component expanded)
```

### 6. Edge Behavior
- **Layer → Component**: Always shown when component is visible
- **Component → File**: Always shown when file is visible
- **Layer → Layer**: Only shown when neither layer is expanded

### 7. Breadcrumb Navigation
Updated to reflect expansion state:
- System view: `System`
- Layer expanded: `System > Layer Name`
- Component expanded: `System > Layer Name > Component Name`

### 8. Reset View
Collapses all nodes and returns to system view showing only layers

## User Interaction Flow

### Example: Expanding Presentation Layer
1. **Initial State**: All layers visible (Presentation, API, Business, Data, Infrastructure)
2. **Click Presentation**: 
   - Presentation layer stays visible
   - Components appear below (AppComponent, TutorialList, etc.)
   - Edge from Presentation → each component
3. **Click AppComponent**:
   - Presentation layer still visible
   - AppComponent still visible
   - File appears below (app.component.ts)
   - Edge from AppComponent → file
4. **Click Presentation again**:
   - Collapses all components and files
   - Returns to showing only layers

### Example: Multiple Expansions
1. Expand Presentation → Shows components
2. Expand API → Shows API components (Presentation components still visible)
3. Expand AppComponent → Shows file (all other nodes still visible)

## Technical Implementation

### Node ID Format
- Layers: `layer-{index}`
- Components: `component-{layerIndex}-{componentIndex}`
- Files: `file-{layerIndex}-{componentIndex}`

### Expansion State Tracking
```typescript
expandedNodes = Set([
  'layer-0',              // Presentation layer expanded
  'component-0-1',        // AppComponent expanded
  'layer-1'               // API layer expanded
])
```

### Collapse Logic
When collapsing a node, remove:
1. The node itself from expandedNodes
2. All direct children
3. All descendants (recursive)

Example: Collapsing `layer-0` removes:
- `layer-0`
- `component-0-0`, `component-0-1`, ... `component-0-19`
- `file-0-0`, `file-0-1`, ... `file-0-19`

## Benefits

1. **Better Context**: Users can see the full hierarchy at once
2. **Easier Navigation**: No need to go back and forth between views
3. **Visual Clarity**: Parent-child relationships are explicit with edges
4. **Flexible Exploration**: Can expand multiple branches simultaneously
5. **Intuitive UX**: Similar to file tree explorers

## Performance Considerations

- Maximum 10 layers shown
- Maximum 20 components per layer
- Lazy expansion prevents rendering all nodes at once
- Dagre layout recalculates only when expansion state changes

## Future Enhancements

1. **Persist Expansion State**: Remember which nodes were expanded
2. **Expand All / Collapse All**: Buttons for bulk operations
3. **Search and Auto-Expand**: Search for a component and auto-expand path to it
4. **Keyboard Navigation**: Arrow keys to navigate and expand/collapse
5. **Animation**: Smooth transitions when expanding/collapsing
6. **Component Dependencies**: Show edges between components based on actual dependencies
